import logging
from fastapi import FastAPI
import inngest
import inngest.fast_api
from inngest.experimental import ai
from dotenv import load_dotenv
import uuid
import os
import datetime
from data_loader import load_and_chunk_pdf, embed_texts
from vector_db import QdrantStorage
from custom_types import RAGChunkAndSrc, RAFQueryResult, RAGSearchResult, RAGUpsertResult

load_dotenv()

inngest_client = inngest.Inngest(
    app_id = "rag_pdf_scanner",
    logger = logging.getLogger("uvicorn"),
    is_production = False,
    serializer = inngest.PydanticSerializer()
)

@inngest_client.create_function(
    fn_id = "RAG: Inngest PDF",
    trigger = inngest.TriggerEvent(event="rag/inngest_pdf")
)
async def rag_inngest_pdf(ctx: inngest.Context):
    def _load(ctx: inngest.Context) -> RAGChunkAndSrc:
        pass

    def _upsert(chunks_and_src: RAGChunkAndSrc) -> RAGUpsertResult:
        pass

    chunks_and_src = await ctx.step.run("load-and-chunk-pdf", lambda: _load(ctx), output_type = RAGChunkAndSrc)
    ingested = await ctx.step.run("embed-and-upsert", lambda: _upsert(chunks_and_src), output_type=RAGUpsertResult)

    return ingested.model_dump()

app = FastAPI()

inngest.fast_api.serve(app, inngest_client, [rag_inngest_pdf])