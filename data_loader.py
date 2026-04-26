import os

from openai import OpenAI
from llama_index.readers.file import PDFReader
from llama_index.core.node_parser import SentenceSplitter
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()
EMBED_MODEL = "text-embedding-3-large"
EMBED_DIMENSION = 3072

splitter = SentenceSplitter(chunk_size = 1000, chunk_overlap = 200)

def load_and_chunk_pdf(path: str):
    docs = PDFReader().load_data(file = path)
    texts = [the_doc.text for the_doc in docs if getattr(the_doc, "text", None)]
    chunks = []
    for t in texts:
        chunks.extend(splitter.split_text(t))
    return chunks

def embed_texts(texts: list[str]) -> list[list[float]]:
    response = client.embeddings.create(model = EMBED_MODEL, input = texts)
    return [item.embedding for item in response.data]