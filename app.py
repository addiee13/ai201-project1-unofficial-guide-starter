"""
Milestone 5 — Gradio query interface.

Run with:
  .venv/bin/python3 app.py

Then open http://localhost:7860 in your browser.
"""

import gradio as gr
from query import ask


def handle_query(question):
    if not question.strip():
        return "Please enter a question.", ""

    result = ask(question)
    declined = "I don't have enough information" in result["answer"]
    sources = "" if declined else "\n".join(f"  {s}" for s in result["sources"])
    return result["answer"], sources


with gr.Blocks(title="The Unofficial GSU CS Guide") as demo:
    gr.Markdown(
        "## The Unofficial GSU CS Guide\n"
        "Ask questions about CS professors at Georgia State University, "
        "based on real student reviews from Rate My Professors."
    )

    with gr.Row():
        with gr.Column():
            inp = gr.Textbox(
                label="Your question",
                placeholder="Which professor should I take for CSC 1301?",
                lines=2,
            )
            btn = gr.Button("Ask", variant="primary")

    with gr.Row():
        with gr.Column():
            answer = gr.Textbox(label="Answer", lines=10)
        with gr.Column():
            sources = gr.Textbox(label="Retrieved from", lines=10)

    btn.click(handle_query, inputs=inp, outputs=[answer, sources])
    inp.submit(handle_query, inputs=inp, outputs=[answer, sources])

demo.launch()
