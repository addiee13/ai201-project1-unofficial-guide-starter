"""
Milestone 5 — Grounded response generation.

ask(question) retrieves the top-5 chunks from ChromaDB, builds a context
prompt, and calls Groq to generate an answer grounded strictly in the
retrieved reviews. Source attribution is returned programmatically — it
is not left to the LLM to add on its own.

Run directly to test generation end-to-end:
  .venv/bin/python3 query.py
"""

import os
from groq import Groq
from dotenv import load_dotenv
from embed import retrieve

load_dotenv()

GROQ_MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are a student advisor for Georgia State University's CS department.
You answer questions using ONLY the student reviews provided to you — no outside knowledge, no assumptions, no invented details.
When answering, reference the professor by name and make clear the information comes from student reviews.
If the provided reviews do not contain enough information to answer the question, respond with exactly:
"I don't have enough information in the available reviews to answer that."
Never fabricate reviews, ratings, or opinions."""


def ask(question, k=5):
    """
    Retrieve relevant chunks and generate a grounded answer.

    Returns a dict with:
      answer   — LLM response grounded in retrieved context
      sources  — list of source filenames the answer draws from
      chunks   — raw retrieved chunk dicts (for inspection/evaluation)
    """
    chunks = retrieve(question, k=k)

    context_blocks = []
    for c in chunks:
        context_blocks.append(
            f"[Source: {c['metadata']['source']}]\n{c['text']}"
        )
    context = "\n\n---\n\n".join(context_blocks)

    user_message = f"""Here are the retrieved student reviews:

{context}

Question: {question}"""

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.1,
    )

    answer = response.choices[0].message.content

    # Source attribution is built programmatically from retrieved metadata,
    # not extracted from the LLM response.
    sources = list(dict.fromkeys(c["metadata"]["source"] for c in chunks))

    return {
        "answer": answer,
        "sources": sources,
        "chunks": chunks,
    }


if __name__ == "__main__":
    test_questions = [
        "What kind of professor is Abdullah Bal?",
        "Does Professor Rahman offer extra credit?",
        "What is the best restaurant near campus?",  # out-of-scope — should decline
    ]

    for question in test_questions:
        print(f"\nQuestion: {question}")
        print("-" * 60)
        result = ask(question)
        print(result["answer"])
        print(f"\nSources: {', '.join(result['sources'])}")
        print("=" * 60)
