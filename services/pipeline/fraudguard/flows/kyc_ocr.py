"""KYC form intake — S3 in, ``entities`` topic out.

Watches an S3 prefix for uploaded KYC PDFs and, for each one:

1. downloads it,
2. extracts the structured fields with Google Document AI,
3. crops any faces from the pages,
4. uploads the primary crop as the profile picture,
5. reverse-searches the crops to find public photographs of the applicant,
6. publishes the applicant record for the enrichment flow.

Replaces ``OCR/process_kyc.py``.  Behaviour changes:

* ``entity_id`` was ``str(random.randint(1, 1000))`` — two applicants collided
  roughly every 25 forms, and the "id" changed if the same form was reprocessed.
  It is now a deterministic hash of the identity fields, so re-processing a form
  updates the same record instead of creating a duplicate.
* the field cache was written but the read side was commented out, so every
  reprocessing paid for Document AI again.  The cache is active and keyed on the
  document's content hash.
* ``pics[0]`` was indexed without checking that any face was found — a form with
  no detectable face raised ``IndexError`` and killed the flow.
* the Document AI client was constructed at import, so the module could not be
  imported without GCP credentials.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import string
import threading
from pathlib import Path
from typing import Any

import pathway as pw

from fraudguard.flows._runtime import FlowContext, flow_main
from fraudguard.logging import get_logger, log_context

log = get_logger("fraudguard.flows.kyc_ocr")

FLOW_NAME = "kyc-ocr"

#: Fields the Document AI processor is configured to extract.
FIELD_TEMPLATE: dict[str, Any] = {
    "annual_income": "",
    "applicant_email": "",
    "applicant_first_name": "",
    "applicant_last_name": "",
    "applicant_middle_name": "",
    "applicant_mobile_number": "",
    "applicant_name_prefix": "",
    "current_address": "",
    "date_of_birth": "",
    "father_first_name": "",
    "father_last_name": "",
    "father_middle_name": "",
    "father_name_prefix": "",
    "gender": "",
    "marital_status": "",
    "mother_first_name": "",
    "mother_last_name": "",
    "mother_middle_name": "",
    "mother_name_prefix": "",
    "nationality": "",
    "occupation": "",
    "passport_number": "",
    "permanent_address": "",
    "residential_status": "",
    "sources_of_income": [],
    "unique_identification_number": "",
}

_PRINTABLE = string.ascii_letters + string.digits + string.whitespace + string.punctuation
_CLEANUP_RE = re.compile(f"[^{re.escape(_PRINTABLE)}]")

_DOCAI_LOCK = threading.Lock()
_DOCAI: tuple[Any, Any] | None = None
_S3_LOCK = threading.Lock()
_S3: Any | None = None


# --------------------------------------------------------------------------- #
# Lazily-built clients
# --------------------------------------------------------------------------- #


def _document_ai() -> tuple[Any, Any]:
    """(client, processor) for Google Document AI."""
    global _DOCAI
    if _DOCAI is None:
        with _DOCAI_LOCK:
            if _DOCAI is None:
                from google.api_core.client_options import ClientOptions
                from google.cloud import documentai_v1

                from fraudguard.config import ConfigError, get_settings

                settings = get_settings()
                if not settings.gcp_processor_name:
                    raise ConfigError("PROCESSOR_NAME (Document AI processor) is not configured.")
                options = ClientOptions(api_endpoint="us-documentai.googleapis.com")
                client = documentai_v1.DocumentProcessorServiceClient(client_options=options)
                processor = client.get_processor(
                    request=documentai_v1.GetProcessorRequest(name=settings.gcp_processor_name)
                )
                _DOCAI = (client, processor)
                log.info("Document AI ready", extra={"processor": processor.name})
    return _DOCAI


def _s3_client() -> Any:
    global _S3
    if _S3 is None:
        with _S3_LOCK:
            if _S3 is None:
                import boto3

                from fraudguard.config import get_settings

                aws = get_settings().aws
                _S3 = boto3.client(
                    "s3",
                    region_name=aws.region,
                    aws_access_key_id=aws.access_key_id,
                    aws_secret_access_key=aws.secret_access_key,
                )
    return _S3


# --------------------------------------------------------------------------- #
# Field extraction
# --------------------------------------------------------------------------- #


def _clean(value: Any) -> Any:
    if isinstance(value, str):
        return _CLEANUP_RE.sub("", value).strip().lower()
    if isinstance(value, list):
        return [_CLEANUP_RE.sub("", str(item)).strip().lower() for item in value]
    return value


def _merge_name(fields: dict[str, Any], prefix: str) -> str:
    parts = [
        fields.pop(f"{prefix}_first_name", ""),
        fields.pop(f"{prefix}_middle_name", ""),
        fields.pop(f"{prefix}_last_name", ""),
    ]
    return " ".join(part for part in parts if part)


def _cache_path(digest: str) -> Path:
    from fraudguard.config import get_settings

    directory = get_settings().paths.out / "kyc_cache"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{digest}.json"


@pw.udf(deterministic=False)
def save_document(payload: bytes, s3_key: str) -> str:
    """Persist the downloaded PDF locally and return its path."""
    from fraudguard.config import get_settings

    directory = get_settings().paths.out / "kyc_pdfs"
    directory.mkdir(parents=True, exist_ok=True)
    filename = os.path.basename(str(s3_key).strip('"')) or "form.pdf"
    path = directory / filename
    path.write_bytes(payload)
    log.info("KYC document saved", extra={"path": str(path), "bytes": len(payload)})
    return str(path)


@pw.udf(return_type=dict, deterministic=False)
def extract_fields(pdf_path: str) -> dict:
    """Run Document AI over a form, with a content-addressed cache."""
    path = Path(pdf_path)
    content = path.read_bytes()
    digest = hashlib.sha256(content).hexdigest()[:32]
    cache_file = _cache_path(digest)

    if cache_file.is_file():
        log.info("Field cache hit", extra={"document": path.name})
        return json.loads(cache_file.read_text())

    with log_context(document=path.name):
        from google.cloud import documentai_v1

        client, processor = _document_ai()
        request = documentai_v1.ProcessRequest(
            name=processor.name,
            raw_document=documentai_v1.RawDocument(
                content=content, mime_type="application/pdf"
            ),
        )
        document = client.process_document(request=request).document

        fields = dict(FIELD_TEMPLATE)
        fields.update({entity.type_: entity.mention_text for entity in document.entities})

        # Names are extracted part by part so the whole name survives; the
        # processor returns only the first name for a combined "applicant_name".
        applicant_name = _merge_name(fields, "applicant")
        father_name = _merge_name(fields, "father")
        mother_name = _merge_name(fields, "mother")
        fields["applicant_name"] = applicant_name
        fields["father_name"] = father_name
        fields["mother_name"] = mother_name

        fields = {key: _clean(value) for key, value in fields.items()}
        cache_file.write_text(json.dumps(fields, indent=2))
        log.info("KYC fields extracted", extra={"applicant": fields.get("applicant_name")})
        return fields


@pw.udf(deterministic=False)
def derive_entity_id(fields: dict) -> str:
    """Stable numeric id derived from the applicant's identifying fields.

    ``Users.user_id`` is a BIGINT, so the hash is folded into a positive 48-bit
    integer — large enough that collisions are negligible, small enough to fit.
    """
    identity = "|".join(
        str(fields.get(key, "")).strip().lower()
        for key in ("unique_identification_number", "passport_number", "applicant_name", "date_of_birth")
    )
    digest = hashlib.sha256(identity.encode("utf-8")).digest()
    return str(int.from_bytes(digest[:6], "big"))


# --------------------------------------------------------------------------- #
# Face handling
# --------------------------------------------------------------------------- #


@pw.udf(deterministic=False)
def crop_faces(pdf_path: str, applicant_name: str) -> list[str]:
    """Detect and crop faces on every page; returns the saved crop paths."""
    import cv2
    import numpy as np
    from pdf2image import convert_from_path

    from fraudguard.config import get_settings

    out_dir = get_settings().paths.out / "faces"
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        pages = convert_from_path(pdf_path, dpi=300)
    except Exception as exc:
        log.error(
            "PDF rasterisation failed (is Poppler installed?)",
            extra={"path": pdf_path, "error": str(exc)},
        )
        return []

    cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    slug = re.sub(r"[^a-z0-9]+", "_", (applicant_name or "applicant").lower()).strip("_")
    crops: list[str] = []

    for page_number, page in enumerate(pages, start=1):
        image = cv2.cvtColor(np.array(page), cv2.COLOR_RGB2BGR)
        grey = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(grey, scaleFactor=1.1, minNeighbors=4, minSize=(80, 80))
        for index, (x, y, width, height) in enumerate(faces, start=1):
            target = out_dir / f"{slug}_p{page_number}_{index}.jpg"
            cv2.imwrite(str(target), image[y : y + height, x : x + width])
            crops.append(str(target))

    try:
        os.remove(pdf_path)
    except OSError as exc:
        log.warning("Could not delete the temporary PDF", extra={"path": pdf_path, "error": str(exc)})

    log.info("Faces cropped", extra={"count": len(crops), "pages": len(pages)})
    return crops


@pw.udf(deterministic=False)
def upload_profile_picture(crops: list[str]) -> str:
    """Upload the first crop as the profile picture; empty string when none exist."""
    if not crops:
        log.info("No face detected; profile picture omitted")
        return ""

    from fraudguard.config import get_settings

    aws = get_settings().aws
    local = crops[0]
    key = f"profilepics/{os.path.basename(local)}"
    try:
        _s3_client().upload_file(local, aws.profile_pic_bucket, key)
    except Exception as exc:
        log.error("Profile picture upload failed", extra={"error": str(exc)})
        return ""
    return f"https://{aws.profile_pic_bucket}.s3.{aws.region}.amazonaws.com/{key}"


@pw.udf(deterministic=False)
def find_face_matches(crops: list[str], applicant_name: str) -> list[str]:
    """Reverse-search the crops and return the source pages that match."""
    if not crops:
        return []
    try:
        from fraudguard.vision.face_matching import CustomPathwayWorkflow

        workflow = CustomPathwayWorkflow(face_image_paths=crops)
        urls = workflow.run(
            input_folder="input",
            cleanup=True,
            search_keyword=(applicant_name or "").title(),
            num_results=10,
        )
    except Exception as exc:
        log.warning("Face match search failed", extra={"error": str(exc)[:300]})
        urls = []
    finally:
        for path in crops:
            try:
                os.remove(path)
            except OSError:
                pass
    return list(urls or [])


# --------------------------------------------------------------------------- #
# Graph
# --------------------------------------------------------------------------- #


class DocumentSchema(pw.Schema):
    data: bytes


def build(context: FlowContext) -> None:
    context.require(
        "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "PROCESSOR_NAME",
        "GOOGLE_APPLICATION_CREDENTIALS",
    )
    aws = context.settings.aws

    documents = pw.io.s3.read(
        path=aws.forms_uri,
        format="binary",
        aws_access_key_id=aws.access_key_id,
        aws_secret_access_key=aws.secret_access_key,
        region=aws.region,
        s3_path_style=False,
        with_metadata=True,
        mode="streaming",
    )

    s3_key = pw.apply(str, documents._metadata["path"])
    saved = documents.select(path=save_document(pw.this.data, s3_key), s3_key=s3_key)

    parsed = saved.select(path=pw.this.path, fields=extract_fields(pw.this.path))

    with_faces = parsed.select(
        fields=pw.this.fields,
        crops=crop_faces(pw.this.path, pw.this.fields["applicant_name"].as_str()),
    )

    applicants = with_faces.select(
        entity_id=derive_entity_id(pw.this.fields),
        profile_pic=upload_profile_picture(pw.this.crops),
        face_match_urls=find_face_matches(
            pw.this.crops, pw.this.fields["applicant_name"].as_str()
        ),
        applicant_name=pw.this.fields["applicant_name"].as_str(),
        date_of_birth=pw.this.fields["date_of_birth"].as_str(),
        gender=pw.this.fields["gender"].as_str(),
        marital_status=pw.this.fields["marital_status"].as_str(),
        nationality=pw.this.fields["nationality"].as_str(),
        annual_income=pw.this.fields["annual_income"].as_str(),
        applicant_email=pw.this.fields["applicant_email"].as_str(),
        applicant_mobile_number=pw.this.fields["applicant_mobile_number"].as_str(),
        occupation=pw.this.fields["occupation"].as_str(),
        sources_of_income=pw.this.fields["sources_of_income"],
        current_address=pw.this.fields["current_address"].as_str(),
        permanent_address=pw.this.fields["permanent_address"].as_str(),
        residential_status=pw.this.fields["residential_status"].as_str(),
        passport_number=pw.this.fields["passport_number"].as_str(),
        unique_identification_number=pw.this.fields["unique_identification_number"].as_str(),
        father_name=pw.this.fields["father_name"].as_str(),
        mother_name=pw.this.fields["mother_name"].as_str(),
    )

    pw.io.jsonlines.write(applicants, context.out("ocr_results.jsonl"))
    pw.io.kafka.write(
        applicants,
        context.kafka,
        topic_name=context.topics.entities_topic,
        format="json",
    )
    context.log.info(
        "Graph built",
        extra={"source": aws.forms_uri, "out_topic": context.topics.entities_topic},
    )


main = flow_main(FLOW_NAME, build, persistent=True)

if __name__ == "__main__":
    raise SystemExit(main())
