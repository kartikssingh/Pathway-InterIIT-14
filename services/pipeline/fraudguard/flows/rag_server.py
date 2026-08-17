"""RAG server used by the watchdog for delta re-assessment.

Indexes the ``{old evidence, new evidence}`` documents the watchdog writes and
answers ``POST /v2/answer`` with an updated risk verdict.

Replaces ``watcher/rag.py``:

* every client (embedder, chat model, reranker, vector store) was built at
  import from ``os.environ[...]``, so importing the module without a full set of
  keys raised ``KeyError``; construction is now inside :func:`build` with clear
  configuration errors;
* the document text put the two prompts in one blob without the entity id or the
  previous score, so the retrieved context could not be attributed;
* ``app.run(...)`` executed at import, meaning the module could not be imported
  at all without starting a server.
"""

from __future__ import annotations

import pathway as pw

from fraudguard.config import ConfigError
from fraudguard.flows._runtime import FlowContext
from fraudguard.logging import configure, get_logger
from fraudguard.schemas import RagInputSchema

log = get_logger("fraudguard.flows.rag")

FLOW_NAME = "rag-server"

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8000

PROMPT_TEMPLATE = (
    "You are a compliance analyst. Answer the question using only the context.\n"
    "Context: {context}\n\nQuestion: {query}"
)


@pw.udf
def render_document(
    entity_id: str, name: str, rps_score: float, web_prompt_old: str, web_prompt_new: str
) -> str:
    return (
        f"Entity ID: {entity_id}\n"
        f"Entity: {name}\n"
        f"Previous risk propensity score: {rps_score}\n\n"
        f"PREVIOUS ADVERSE-MEDIA ANALYSIS:\n{web_prompt_old}\n\n"
        f"CURRENT ADVERSE-MEDIA ANALYSIS:\n{web_prompt_new}\n"
    )


def build_app(context: FlowContext):
    """Assemble the RAG REST server (does not start it)."""
    from pathway.udfs import DiskCache
    from pathway.xpacks.llm import rerankers, splitters
    from pathway.xpacks.llm.question_answering import BaseRAGQuestionAnswerer
    from pathway.xpacks.llm.servers import QASummaryRestServer
    from pathway.xpacks.llm.vector_store import VectorStoreServer

    from fraudguard.llm.client import chat_model, embedder

    settings = context.settings
    data_dir = settings.paths.state / "rag_documents"
    data_dir.mkdir(parents=True, exist_ok=True)

    documents = pw.io.fs.read(
        path=str(data_dir),
        format="json",
        schema=RagInputSchema,
        with_metadata=True,
    )

    sources = documents.select(
        data=render_document(
            pw.this.entity_id,
            pw.this.name,
            pw.this.rps_score,
            pw.this.web_prompt_old,
            pw.this.web_prompt_new,
        ),
        _metadata=pw.this._metadata,
        entity_id=pw.this.entity_id,
        name=pw.this.name,
    )

    index = VectorStoreServer(
        sources,
        embedder=embedder(),
        splitter=splitters.TokenCountSplitter(max_tokens=400),
        parser=None,
    )

    reranker = None
    if settings.llm.cross_encoder_model:
        reranker = rerankers.CrossEncoderReranker(
            model_name=settings.llm.cross_encoder_model,
            cache_strategy=DiskCache(),
        )
    else:
        log.info("CROSS_ENCODER_MODEL not set; running without a reranker")

    answerer = BaseRAGQuestionAnswerer(
        llm=chat_model(),
        indexer=index,
        reranker=reranker,
        prompt_template=PROMPT_TEMPLATE,
    )

    host = str(settings.rag_url).split("//")[-1].split(":")[0] or DEFAULT_HOST
    port = DEFAULT_PORT
    try:
        port = int(str(settings.rag_url).rsplit(":", 1)[-1].split("/")[0])
    except ValueError:
        pass

    log.info("RAG server configured", extra={"host": DEFAULT_HOST, "port": port, "docs": str(data_dir)})
    return QASummaryRestServer(DEFAULT_HOST, port, answerer), host


def main() -> int:
    configure(FLOW_NAME)
    context = FlowContext(FLOW_NAME)
    try:
        server, _host = build_app(context)
    except ConfigError as exc:
        log.error("Cannot start the RAG server: %s", exc)
        return 2

    cache_dir = context.state_dir("rag_cache")
    server.run(
        with_cache=True,
        cache_backend=pw.persistence.Backend.filesystem(str(cache_dir)),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
