**Upload Form API**

- **Purpose**: Document the `upload-form` endpoint which accepts a PDF form via multipart/form-data, converts it to binary, and uploads it to an S3 bucket. Forms are stored for later processing to create user records.

Overview
 - **Endpoint**: `POST /user/upload-form`
 - **Handler**: `app/routes/user_routes.py` -> `upload_form`
 - **Auth**: Admin-only (depends on `require_admin`)
 - **Accepted file type**: `application/pdf` (file field name: `file`)
 - **S3 key structure**: `forms/pending/{timestamp}_{uuid}_{filename}.bin` (stored as binary)

Request
- Content-Type: `multipart/form-data`
- No path parameters required
- Form fields:
  - `file`: PDF file. The API will validate `file.content_type == 'application/pdf'` and reject other types with HTTP 400.

Behavior
- The endpoint reads the uploaded PDF into memory as bytes (`await file.read()`), then calls the S3 helper service to upload the bytes directly to S3 using `put_object`.
- The S3 bucket to use is taken from the environment variable `S3_BUCKET`.
- A unique S3 key is generated using: timestamp (YYYYMMDD_HHMMSS) + 8-char UUID + sanitized filename.
- Forms are stored under `forms/pending/` prefix for later processing to create user records.
- After successful upload, an audit log entry is created using `AuthService.create_audit_log(...)` with metadata including S3 key, filename, and file size.

Response (success)
- JSON object with these keys:
  - `ok`: `true`
  - `key`: uploaded S3 key (e.g. `forms/pending/20251207_143022_a1b2c3d4_application.bin`)
  - `url`: constructed virtual-hosted-style URL to the object (if `AWS_REGION` is set)
  - `filename`: original filename
  - `file_size`: size of uploaded file in bytes

Error responses
- `400 Bad Request` — invalid content type (non-PDF) or invalid parameters
- `500 Internal Server Error` — missing S3 configuration or S3 upload failure

Environment variables
- `AWS_ACCESS_KEY_ID` — AWS access key id used by boto3 client
- `AWS_SECRET_ACCESS_KEY` — AWS secret key
- `AWS_REGION` — AWS region (used to construct returned URL)
- `S3_BUCKET` — bucket used for storing uploaded forms
- `S3_PROFILE_PIC_BUCKET` — legacy bucket variable (not used by `upload-form`)
- `S3_ADDRESSING_STYLE` — `virtual` by default; controls boto3 addressing style

Security and operational notes
- Authentication: the endpoint uses `require_admin` dependency. Ensure admin tokens are issued securely.
- Credentials: avoid committing AWS credentials to Git. Use a secrets manager in production. If `.env` is used locally, add it to `.gitignore`.
- Memory usage: the endpoint loads the whole PDF into memory via `await file.read()`. For very large PDFs this may cause high memory usage. Consider streaming uploads or a multipart S3 upload for large files.
- S3 ACL: current implementation uses `put_object` without setting ACL. If you need public access, set the proper ACL or presigned URLs.
- URL construction: the returned `url` is constructed using virtual-hosted-style format. If you use a custom S3-compatible endpoint or path-style addressing, adjust URL generation accordingly.

Testing examples

1) Local manual test using `curl` (replace host, token and file path):

```bash
curl -X POST "http://127.0.0.1:8000/user/upload-form" \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -F "file=@/path/to/form.pdf;type=application/pdf"
```

2) Using Python `requests`:

```python
import requests

url = "http://127.0.0.1:8000/user/upload-form"
headers = {"Authorization": "Bearer <ADMIN_TOKEN>"}
files = {"file": ("form.pdf", open("/path/to/form.pdf", "rb"), "application/pdf")}
resp = requests.post(url, headers=headers, files=files)
print(resp.status_code, resp.json())
# Example response:
# {
#   "ok": true,
#   "key": "forms/pending/20251207_143022_a1b2c3d4_form.bin",
#   "url": "https://amzn-s3-pathway-bucket.s3.eu-north-1.amazonaws.com/forms/pending/20251207_143022_a1b2c3d4_form.bin",
#   "filename": "form.pdf",
#   "file_size": 245678
# }
```

Recommended improvements
- Stream uploads to S3 for large files instead of reading full file into memory.
- Use multipart upload for large objects (>100MB) and retry logic.
- Add server-side file size limits and validate file metadata.
- If `pdf_service.py` will be used (text extraction and KYC parsing), consider integrating `process_kyc_pdf` to run extraction after upload and store parsed results referencing the S3 key.
- Use presigned URLs for client-side direct-to-S3 uploads if you want to avoid routing file bytes through the API server.

Files referenced
- `app/routes/user_routes.py` (endpoint implementation)
- `app/services/s3_service.py` (S3 helper using `boto3`)
- `app/services/pdf_service.py` (optional: PDF parsing and extraction)

Contact / next steps
- If you'd like, I can:
  - Add server-side file-size validation and streaming upload support.
  - Integrate `pdf_service.process_kyc_pdf` so the uploaded PDF is parsed and the parsed fields are saved.
  - Add automated tests for the endpoint.
