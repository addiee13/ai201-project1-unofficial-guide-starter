# The Unofficial Guide — Project 1

---

## Domain

Student reviews of CS professors at Georgia State University, focused on core undergraduate courses. This knowledge is valuable because it reflects what students actually experience — teaching style, exam difficulty, grading fairness, and attendance policies — none of which appears in official course catalogs, department websites, or syllabi. Every semester, students have to cross-reference Rate My Professors, Reddit threads, and word-of-mouth just to make an informed course selection. This system makes that knowledge searchable through plain-language questions.

---

## Document Sources

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | Rate My Professors — Abdullah Bal | Student reviews, CSC4520 / CSC6260 / CSC3210 | docs/professor_bal.md |
| 2 | Rate My Professors — Sayed Hossein Esfahani | Student reviews, CSC1301 | docs/professor_esfahani.md |
| 3 | Rate My Professors — Lan Gao | Student reviews, CSC3210 | docs/professor_gao.md |
| 4 | Rate My Professors — William Johnson | Student reviews, CSC1302 | docs/professor_johnson.md |
| 5 | Rate My Professors — Amin Karim | Student reviews, CSC1301 | docs/professor_karim.md |
| 6 | Rate My Professors — Kiril Kuzmin | Student reviews, CSC4520 / CSC2510 / DATA1501 | docs/professor_kuzmin.md |
| 7 | Rate My Professors — Md Mahfuzur Rahman | Student reviews, CSC3320 | docs/professor_rahman.md |
| 8 | Rate My Professors — Rajshekhar Sunderraman | Student reviews, CSC1301 | docs/professor_sunderraman.md |
| 9 | Rate My Professors — Farhan Tanvir | Student reviews, CSC4760 | docs/professor_tanvir.md |
| 10 | Rate My Professors — Islam S M Towhidul | Student reviews, CSC3320 / CSC2720 / CSC1302 | docs/professor_towhidul.md |
| 11 | Rate My Professors — Yanqing Zhang | Student reviews, CSC4810 | docs/professor_zhang.md |

---

## Chunking Strategy

**Chunk size:** ~300–600 characters per chunk, naturally varying by review length. No fixed character limit is enforced — each chunk maps to exactly one student review.

**Overlap:** 0. Reviews are already atomic, self-contained units. Overlapping across review boundaries would blend two different students' opinions into a single embedding, degrading retrieval precision.

**Why these choices fit your documents:** The documents are structured around individual student reviews as the natural semantic unit. Fixed-character splitting would risk cutting mid-opinion and losing the professor/course context that makes a chunk attributable. Instead, each chunk is built from one review's verbatim text and key points, prefixed with professor name, course, rating, and date — so every retrieved chunk stands alone and can be cited. In addition to per-review chunks, the OVERALL_SIGNALS and COMMON_THEMES sections of each professor file are stored as separate summary chunks, which retrieve well for broad questions. Structured fields that carry no semantic meaning (SOURCE_ID, RATING_DISTRIBUTION, thumbs_up, for_credit, etc.) are excluded from the embedded text and stored only as ChromaDB metadata — keeping cosine similarity driven purely by review meaning.

**Final chunk count:** 167 total — 156 per-review chunks and 11 summary chunks across 11 professor files.

**Sample chunks:**

```
[professor_bal.md]
Professor: Abdullah Bal | Course: CSC4520 | Rating: 3.0/5.0 | Date: 2025-12-22
Review: His class isn't necessarily hard, so if you study for the exams, you'll be fine.
HOWEVER: He said attendance was mandatory & passed out an attendance sheet, but it wasn't
included in the syllabus' percentage breakdown. His quizzes (30%) are only two questions,
so if you mess up 1 question, your grade is tanked.
```

```
[professor_karim.md]
Professor: Amin Karim | Course: CSC1301 | Rating: 5.0/5.0 | Date: 2025-05-05
Review: Good professor can sometime arrive late. Exams are pretty straightforward just make
sure you do the Zybooks and study guide.
```

```
[professor_rahman.md]
Professor: Md Mahfuzur Rahman | Course: CSC3320 | Rating: 2.0/5.0 | Date: 2025-12-22
Review: He has pretty good lectures and explains concepts thoroughly in class but is a very
tough grader on exams as he is a stickler for semantics. Lots of extra credit opportunities
(up to 7 pts) to make up for the abysmal test scores he gives out.
```

```
[professor_esfahani.md]
Professor: Sayed Hossein Esfahani | Course: CSC1301 | Rating: 5.0/5.0 | Date: 2026-04-06
Review: He is one of the best professors I've ever had. He was nice and made his class fun;
however, like every computer science class, it is difficult. It challenges you to think.
He allows help from tutors.
```

```
[professor_sunderraman.md]
Professor: Rajshekhar Sunderraman | Course: CSC1301 | Rating: 5.0/5.0 | Date: 2024-12-06
Review: I wouldn't say the class is easy, this is an honors class, so the pace is fast
compared to general lab classes. But the professor is very kind, passionate and teaches
really well.
```

---

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` via `sentence-transformers`. Runs entirely locally — no API key, no rate limits, no cost. Input limit is 256 tokens, which is sufficient for review-level chunks (one verbatim review + metadata header stays well under that limit). Only the semantically meaningful chunk text is embedded; structured metadata fields (course, quality, difficulty, grade, tags) are stored separately in ChromaDB.

**Production tradeoff reflection:** For a real deployment, the main tradeoffs when choosing an embedding model are: (1) Context length — `all-MiniLM-L6-v2`'s 256-token limit is fine for short reviews but would truncate longer documents like syllabi or housing guides; models like `text-embedding-3-small` (OpenAI) support up to 8,191 tokens. (2) Accuracy on domain-specific text — general-purpose models like MiniLM are trained on web text and perform well on informal opinion language, but a model fine-tuned on academic or student-written text could improve retrieval precision for edge cases. (3) Multilingual support — not a concern for this corpus since all reviews are in English, but a model like `paraphrase-multilingual-MiniLM-L12-v2` would be necessary for a broader student population. (4) Latency and cost — local models have zero marginal cost and no network latency but require compute on the host machine; API-hosted models offload compute but introduce per-token cost and network dependency. For a corpus of ~167 chunks, local inference is the right call.

---

## Grounded Generation

**System prompt grounding instruction:** The following system prompt is passed to `llama-3.3-70b-versatile` on every request:

```
You are a student advisor for Georgia State University's CS department.
You answer questions using ONLY the student reviews provided to you — no outside knowledge,
no assumptions, no invented details.
When answering, reference the professor by name and make clear the information comes from
student reviews.
If the provided reviews do not contain enough information to answer the question, respond
with exactly: "I don't have enough information in the available reviews to answer that."
Never fabricate reviews, ratings, or opinions.
```

The system prompt uses the word "ONLY" explicitly and lists specific prohibitions (no outside knowledge, no assumptions, no invented details) rather than just asking the model to "use the documents." It also specifies a verbatim refusal phrase so out-of-scope responses are consistent and recognizable.

**How source attribution is surfaced in the response:** Source attribution is built programmatically from chunk metadata — not left to the LLM. After generation, the `ask()` function collects the `source` field from each retrieved chunk's metadata and returns a deduplicated list of source filenames alongside the answer. The Gradio interface displays these in a separate "Retrieved from" panel. This guarantees attribution is present even if the LLM forgets to cite in its response.

**Example response with source citation:**

> Question: Does Professor Rahman offer extra credit?
>
> Answer: According to the reviews from students, Professor Md Mahfuzur Rahman offers extra credit opportunities. As one student review states, "extra credit for tophat assignments and attendence which can boost a lot." Another review mentions "Lots of extra credit opportunities (up to 7 pts) to make up for the abysmal test scores he gives out."
>
> Retrieved from: professor_rahman.md

**Out-of-scope refusal example:**

> Question: What is the best restaurant near campus?
>
> Answer: I don't have enough information in the available reviews to answer that.
>
> Retrieved from: professor_esfahani.md, professor_kuzmin.md

---

## Retrieval Test Results

**Query 1: "What kind of professor is Abdullah Bal?"**

| Rank | Distance | Professor | Course | Snippet |
|------|----------|-----------|--------|---------|
| 1 | 0.539 | Abdullah Bal | CSC4520 | "Bal is easily one of the best professors at GSU..." |
| 2 | 0.777 | Abdullah Bal | CSC6260 | "He is a very nice professor, one of the best in teaching concepts..." |
| 3 | 0.782 | Abdullah Bal | CSC4520 | "What I thought would be a boring class turned into engaging learning..." |
| 4 | 0.794 | Abdullah Bal | CSC4520 | "Difficult to deal with professor imo, a lot of lectures and reading from slides..." |
| 5 | 0.815 | Abdullah Bal | CSC4520 | "My biggest complaint is that he is slow to grade..." |

These chunks are relevant because the query names a specific professor and asks for a general characterization. All 5 results are Bal reviews covering both positive and negative perspectives, giving the LLM a balanced view to synthesize from. The distance of 0.539 on the top result indicates a strong semantic match.

**Query 2: "Does Professor Rahman offer extra credit?"**

| Rank | Distance | Professor | Course | Snippet |
|------|----------|-----------|--------|---------|
| 1 | 0.646 | Md Mahfuzur Rahman | CSC3320 | "extra credit for tophat assignments and attendence which can boost a lot..." |
| 2 | 0.646 | Md Mahfuzur Rahman | CSC3320 | "Lots of extra credit opportunities (up to 7 pts)..." |
| 3 | 0.647 | Md Mahfuzur Rahman | CSC3320 | "...exams are ridiculously long. he does not respond to emails..." |

The top two chunks directly mention extra credit with specific details (TopHat assignments, 7 bonus points), making this a strong retrieval result. Distances are consistent around 0.646–0.647, reflecting that several reviews mention extra credit in similar terms.

**Query 3: "Which professor should I take for CSC 1301?" (with course metadata filter)**

| Rank | Distance | Professor | Course | Snippet |
|------|----------|-----------|--------|---------|
| 1 | 0.801 | Rajshekhar Sunderraman | CSC1301 | "Probably the best professor you'll ever have..." |
| 2 | 0.848 | Rajshekhar Sunderraman | CSC1301 | "...assignments are difficult but professor is excellent..." |
| 3 | 0.897 | Sayed Hossein Esfahani | CSC1301 | "one of the best professors I've ever had..." |
| 4 | 0.942 | Sayed Hossein Esfahani | CSC1301 | "Don't take bros class unless you already have experience with coding..." |

The course metadata filter (`where={"course": "CSC1301"}`) restricts retrieval to CSC1301 chunks only, preventing unrelated courses from dominating the results. Without the filter, this query returned CSC1302 and CSC3210 reviews. Distances are higher here (~0.80–0.94) because the query is a general recommendation question that doesn't share vocabulary with individual reviews.

---

## Evaluation Report

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | Which professor should I take for CSC 1301? | Karim (4.8/5), Sunderraman (4.8/5), Esfahani (2.5/5) | Compared Sunderraman and Esfahani — Sunderraman described as highly recommended, Esfahani more mixed. Karim omitted because all 8 retrieval slots filled before his chunks appeared. | Partially relevant — correct course, missing one professor | Partially accurate |
| 2 | What kind of professor is Abdullah Bal? | Well-structured, attendance essential, exams based on class examples, mixed feedback on communication | Described as caring and effective with easy-to-follow lectures, but noted slowness to grade and lack of study materials. Balanced and grounded in reviews. | Relevant | Accurate |
| 3 | Does Professor Rahman offer extra credit? | Yes — up to 7 bonus points via TopHat and attendance | Confirmed extra credit, quoted specific reviews including the 7-point detail. | Relevant | Accurate |
| 4 | What is Professor Esfahani's attendance policy? | Mandatory, tracked through Kahoot at end of class | Correctly identified mandatory attendance and Kahoot-based tracking, noted flexibility for late arrivals who still complete the Kahoot. | Partially relevant — right professor, distances 0.72–0.88 | Accurate |
| 5 | Is Professor Karim good for a student with no coding experience? | Yes — student went from zero CS experience to working on an AI startup | Confirmed yes, cited the exact student quote about going from no experience to an AI startup. | Relevant | Accurate |

**Retrieval quality:** Relevant / Partially relevant / Off-target
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

**Question that failed:** "Which professor should I take for CSC 1301?"

**What the system returned (before fix):** The system returned "I don't have enough information in the available reviews to answer that." The retrieved chunks were from William Johnson (CSC1302), Lan Gao (CSC3210), and Kiril Kuzmin (CSC4520) — all wrong courses. None of the three CSC1301 professors (Karim, Esfahani, Sunderraman) appeared in the results.

**Root cause (tied to a specific pipeline stage):** Retrieval stage. The query "Which professor should I take for CSC 1301?" is a course-recommendation question, and `all-MiniLM-L6-v2` embedded it based on its general meaning — "which professor is good." Course numbers like "CSC1301" are treated as low-frequency tokens with weak semantic weight. The embedding similarity matched on "good professor" language in Johnson and Kuzmin reviews instead of on the course number. Since retrieval is purely semantic with no course awareness, it had no mechanism to prioritize CSC1301 chunks.

**What you would change to fix it:** Course number detection + metadata filtering, which was implemented after this failure was observed. The `retrieve()` function now uses a regex to detect course numbers in the query (e.g., `CSC\s?\d{4}`) and passes a ChromaDB `where={"course": "CSC1301"}` filter, restricting results to chunks from that course only. After this fix, retrieval returned CSC1301 reviews from Sunderraman and Esfahani. The remaining limitation is that with k=8 and only two professors' chunks filling the slots, Karim's reviews were not retrieved — a partial improvement, not a complete fix.

---

## Spec Reflection

**One way the spec helped you during implementation:** The embed/metadata split decision made in `planning.md` before any code was written directly enabled the metadata filtering fix during implementation. Because the spec required storing `course`, `professor`, `quality`, `difficulty`, and other fields as ChromaDB metadata rather than embedding them, the course number was available as a queryable field the moment retrieval failed. If course had been embedded into the text only, adding a filter would have required re-ingesting and re-chunking everything. The spec decision paid off immediately.

**One way your implementation diverged from the spec, and why:** The spec specified `top-k = 5` for retrieval. During evaluation, Q4 (Esfahani attendance) returned all 5 results from the right professor but with distances between 0.72 and 0.88 — higher than ideal. To increase the chance of retrieving a chunk that explicitly mentions Kahoot, k was increased to 8. Additionally, the course metadata filter was not in the original spec — it was added after Q1 failed during evaluation. The spec anticipated the failure but proposed summary chunks as the mitigation; the actual fix turned out to be direct metadata filtering, which was simpler and more reliable.

---

## AI Usage

**Instance 1 — Ingestion and chunking pipeline**

- *What I gave the AI:* The Documents section of `planning.md` (listing all 11 professor files and noting the two different field formats), the Chunking Strategy section (review-level chunking, embed/metadata split, normalized field names), and the Architecture diagram.
- *What it produced:* `ingest.py` — a parser that reads each professor `.md` file, normalizes both field formats into a consistent structure, builds one chunk dict per review with embedded text and metadata, and creates separate summary chunks from COMMON_THEMES and OVERALL_SIGNALS sections.
- *What I changed or overrode:* The initial implementation assumed a single field format. After inspecting both `professor_bal.md` and `professor_esfahani.md` side by side, the field name differences were identified (e.g., `term_or_date` vs `date`, `rating_if_available` vs `quality`) and the parser was directed to normalize both using fallback field name lookups.

**Instance 2 — Embedding, retrieval, and metadata filtering**

- *What I gave the AI:* The Retrieval Approach section (all-MiniLM-L6-v2, ChromaDB, top-k=5), the Architecture diagram, and the chunk dict format from Milestone 3. After Q1 failed evaluation, the failure description was also provided.
- *What it produced:* `embed.py` — embedding script, ChromaDB store builder, and `retrieve()` function. After the evaluation failure was shown, the course detection regex and ChromaDB `where` filter were added to `retrieve()`.
- *What I changed or overrode:* The default k was raised from 5 to 8 after observing that Q4 (attendance policy) had high distances despite returning the right professor. The course filter fallback (retry without filter if filtered count < k) was added to prevent errors on courses with very few reviews.

**Instance 3 — Grounded generation and Gradio interface**

- *What I gave the AI:* The grounding requirement from the project instructions, the Groq model choice (`llama-3.3-70b-versatile`), the `retrieve()` function from Milestone 4, and the Gradio skeleton from the project instructions.
- *What it produced:* `query.py` with a system prompt and `ask()` function, and `app.py` with a two-column Gradio layout (answer + sources panels).
- *What I changed or overrode:* The system prompt was made more explicit — adding "no outside knowledge, no assumptions, no invented details" rather than just "use only the documents" — after testing showed the model would sometimes add general advice beyond what the reviews said. Source attribution was confirmed to be built programmatically from chunk metadata rather than extracted from the LLM response, ensuring it is always present regardless of whether the model includes citations in its text.
