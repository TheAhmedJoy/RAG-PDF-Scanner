import logging
from fastapi import FastAPI
import inngest
import inngest.fast_api
from inngest.experimental import ai
from dotenv import load_dotenv
import uuid
import os
import datetime

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
    return {"hello": "world"}

app = FastAPI()

inngest.fast_api.serve(app, inngest_client, [rag_inngest_pdf])