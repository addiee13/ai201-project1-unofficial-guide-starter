"""
Milestone 4 — Embedding and retrieval.

Run once to build the ChromaDB vector store:
  python3 embed.py

The retrieve() function is imported by app.py in Milestone 5.
"""

import re
import chromadb
from sentence_transformers import SentenceTransformer
from ingest import load_chunks

MODEL_NAME = "all-MiniLM-L6-v2"
COLLECTION_NAME = "professor_reviews"
CHROMA_PATH = "chroma"

# Module-level singletons — loaded once, reused across calls.
_model = None
_collection = None


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def _get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        _collection = client.get_collection(COLLECTION_NAME)
    return _collection


# ---------------------------------------------------------------------------
# Build store (run once)
# ---------------------------------------------------------------------------

def build_store():
    """
    Embed all chunks from ingest.py and store them in ChromaDB.
    Deletes and recreates the collection on each run so re-runs stay clean.
    """
    print("Loading chunks...")
    chunks = load_chunks()
    print(f"  {len(chunks)} chunks ready.\n")

    print("Loading embedding model...")
    model = _get_model()

    client = chromadb.PersistentClient(path=CHROMA_PATH)

    try:
        client.delete_collection(COLLECTION_NAME)
        print("  Deleted existing collection.")
    except Exception:
        pass

    collection = client.create_collection(COLLECTION_NAME)

    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]
    ids = [str(i) for i in range(len(chunks))]

    print("Embedding chunks...")
    embeddings = model.encode(texts, show_progress_bar=True).tolist()

    print("\nStoring in ChromaDB...")
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )

    print(f"Done. {collection.count()} chunks stored in '{COLLECTION_NAME}'.")
    return collection


# ---------------------------------------------------------------------------
# Retrieval function (imported by app.py)
# ---------------------------------------------------------------------------

def _detect_course(query):
    """
    Extract and normalize a course number from the query string.
    Handles formats like 'CSC 1301', 'CSC1301', 'CS1301', 'DATA1501'.
    'CS' is normalized to 'CSC' to match stored metadata.
    Returns a normalized string (e.g. 'CSC1301') or None.
    """
    m = re.search(r"\b(CSC|CS|DATA)\s?(\d{4})\b", query, re.IGNORECASE)
    if m:
        prefix = m.group(1).upper()
        if prefix == "CS":
            prefix = "CSC"
        return prefix + m.group(2)
    return None


def retrieve(query, k=8):
    """
    Return the top-k most relevant chunks for a query string.

    If the query contains a course number (e.g. CSC1301), retrieval is
    restricted to chunks where metadata.course matches — preventing
    cross-course contamination on comparison queries.

    Each result dict contains:
      text      — the embedded chunk text
      metadata  — professor, course, quality, date, source, etc.
      distance  — cosine distance (lower = more similar)
    """
    model = _get_model()
    collection = _get_collection()

    query_embedding = model.encode([query]).tolist()
    course = _detect_course(query)

    query_kwargs = dict(
        query_embeddings=query_embedding,
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    if course:
        query_kwargs["where"] = {"course": course}

    try:
        results = collection.query(**query_kwargs)
    except Exception:
        # Fallback: if filtered count < k, retry without the filter
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )

    return [
        {
            "text": doc,
            "metadata": meta,
            "distance": round(dist, 4),
        }
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )
    ]


# ---------------------------------------------------------------------------
# Entrypoint — build store and test retrieval with 3 evaluation queries
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    build_store()

    test_queries = [
        "Which professor should I take for CSC 1301?",
        "What kind of professor is Abdullah Bal?",
        "What is Professor Esfahani's attendance policy?",
    ]

    print("\n" + "=" * 60)
    print("Retrieval test — 3 evaluation plan queries")
    print("=" * 60)

    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 50)
        results = retrieve(query)
        for r in results:
            prof = r["metadata"].get("professor", "?")
            course = r["metadata"].get("course", "N/A")
            dist = r["distance"]
            snippet = r["text"][:120].replace("\n", " ")
            print(f"  [{dist:.3f}] {prof} ({course})")
            print(f"         {snippet}...")
