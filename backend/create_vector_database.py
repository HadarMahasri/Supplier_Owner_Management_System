import os
import logging

import requests
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

KNOWLEDGE_FILE = os.getenv("KNOWLEDGE_FILE", "suppliers_knowledge.txt")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333").rstrip("/")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "suppliers_knowledge")
VECTOR_SIZE = int(os.getenv("QDRANT_VECTOR_SIZE", "768"))

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
EMBED_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
EMB_URL = f"{OLLAMA_URL}/api/embeddings"


def get_embedding(text: str):
    # 1) input
    try:
        r = requests.post(EMB_URL, json={"model": EMBED_MODEL, "input": text}, timeout=60)
        if r.ok:
            data = r.json()
            emb = data.get("embedding") or (data.get("data") or [{}])[0].get("embedding")
            if emb:
                return emb
    except Exception:
        pass
    # 2) prompt
    r = requests.post(EMB_URL, json={"model": EMBED_MODEL, "prompt": text}, timeout=60)
    r.raise_for_status()
    data = r.json()
    return data.get("embedding") or (data.get("data") or [{}])[0].get("embedding")


def split_text_into_chunks(text: str, chunk_size=300, overlap=50):
    words = text.split()
    out = []
    step = max(1, chunk_size - overlap)
    for i in range(0, len(words), step):
        chunk = " ".join(words[i : i + chunk_size]).strip()
        if chunk:
            out.append(chunk)
        if i + chunk_size >= len(words):
            break
    return out


def main():
    # בדיקות זמינות
    try:
        r = requests.get(f"{QDRANT_URL}/readyz", timeout=5)
        r.raise_for_status()
    except Exception as e:
        logger.error(f"Qdrant not ready: {e}")
        return 1

    try:
        r = requests.get(f"{OLLAMA_URL}/api/version", timeout=5)
        r.raise_for_status()
    except Exception as e:
        logger.error(f"Ollama not ready: {e}")
        return 1

    if not os.path.exists(KNOWLEDGE_FILE):
        logger.error(f"file not found: {KNOWLEDGE_FILE}")
        return 1

    with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    chunks = split_text_into_chunks(content, chunk_size=300, overlap=50)
    logger.info(f"chunks: {len(chunks)}")

    client = QdrantClient(QDRANT_URL)

    # צור/אתחל אוסף
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )

    points = []
    UI_TERMS = ["רשימת הזמנות","רשימת ספקים","הזמנה חדשה","חיבורים","בקשות ממתינות","ניהול מוצרים"]

    for i, chunk in enumerate(chunks):
        emb = get_embedding(chunk)
        if not emb:
            continue

        role = "Any"
        if "[OWNER]" in chunk:
            role = "StoreOwner"
        elif "[SUPPLIER]" in chunk:
            role = "Supplier"

        meta = {
            "text": chunk,
            "type": "how_to" if "[HOWTO]" in chunk else "doc",
            "role": role,
            "title": chunk.split("\n", 1)[0].strip(),
            "ui_terms": [t for t in UI_TERMS if t in chunk]
        }

        points.append(PointStruct(id=i, vector=emb, payload=meta))

    if not points:
        logger.error("no points to upsert")
        return 1

    client.upsert(collection_name=COLLECTION_NAME, points=points)
    client = QdrantClient(url=QDRANT_URL)
    info = client.get_collection(COLLECTION_NAME)
    client.upsert(collection_name=COLLECTION_NAME, points=points)
    logger.info(f"done. points_count={info.points_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
