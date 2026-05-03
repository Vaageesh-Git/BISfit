# 🏛️ BISfit — Solution Document

**Retrieval-Augmented Generation for Bureau of Indian Standards**
*SP 21 : 2005 — Summaries of Indian Standards for Building Materials*

---

## 1. Product Vision

BISfit is a **production-ready Retrieval-Augmented Generation (RAG) system** built on **SP 21 : 2005** — the BIS handbook covering **580 Indian Standards** across **27 categories** of building materials.

### What Problem Does It Solve?

> Engineers, QA teams, contractors, and manufacturers spend hours manually searching through hundreds of IS standard PDFs to find the right compliance specification.

BISfit replaces that search with a **natural-language AI interface** that:
- Accepts plain-English questions (no IS code knowledge needed)
- Returns a concise, grounded **narrative answer** from BIS documents
- Surfaces the **exact IS standard codes** answering the query
- Responds in **under 2 seconds** on average

### Who Is It For?

| User | Use Case |
|---|---|
| Manufacturer | "Which standard governs my product?" |
| Site Engineer | "What are the compressive strength requirements for 53 grade OPC?" |
| QA Inspector | "What tests are required for hollow concrete masonry blocks?" |
| Architect | "Which IS code covers corrugated asbestos cement roofing sheets?" |

---

## 2. System Architecture

BISfit runs in two decoupled phases:

```
╔══════════════════════════════════════════════════════════════╗
║          PHASE 1 — OFFLINE INGESTION (run once)             ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  BIS PDF (SP 21)                                             ║
║       │                                                      ║
║       ▼                                                      ║
║  parser.py  ── PyMuPDF section-aware extraction             ║
║       │         Handles multi-column, broken text            ║
║       ▼                                                      ║
║  chunker.py ── 1 IS standard = 1 semantic chunk (584 total) ║
║       │         Metadata-prefixed for recall boost           ║
║       ▼                                                      ║
║  embedder.py ─ all-MiniLM-L6-v2 · 384-dim vectors          ║
║       │         FAISS IndexFlatIP + L2 normalisation         ║
║       ▼                                                      ║
║  faiss_index.bin + chunk_metadata.json                      ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║          PHASE 2 — ONLINE INFERENCE (per query)             ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  User Query (natural language)                               ║
║       │                                                      ║
║       ▼  [Layer 1] Query Reformulation — Llama 3 8b         ║
║            2 IS-focused alternative queries generated        ║
║       │                                                      ║
║       ▼  [Layer 2] Multi-Query FAISS Search                  ║
║            Top-10 per query · merge + dedup by chunk_id      ║
║       │                                                      ║
║       ▼  [Layer 3] Cosine Re-ranking                         ║
║            Sort by score · top-5 to LLM context             ║
║       │                                                      ║
║       ▼  [Layer 4] Generate & Extract — Llama 3.3 70b       ║
║            Narrative answer + IS codes in a single JSON call ║
║       │                                                      ║
║       ▼                                                      ║
║  { response, retrieved_standards, latency_seconds }          ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```

---

## 3. Technology Stack

| Layer | Technology | Reason |
|---|---|---|
| **PDF Parsing** | PyMuPDF (`parser.py`) | Section-aware extraction handles BIS multi-column layout |
| **Chunking** | Custom `chunker.py` | 1 IS standard = 1 semantic unit → no mid-standard splits |
| **Embeddings** | `all-MiniLM-L6-v2` (384-dim) | Fast, lightweight, strong recall for technical text |
| **Vector Store** | FAISS-CPU `IndexFlatIP` | Sub-millisecond similarity search, no external infrastructure |
| **Query Reform.** | Groq · Llama 3.1 8b Instant | Ultra-low latency query expansion (< 400ms) |
| **Generation** | Groq · Llama 3.3 70b Versatile | High-quality narrative + structured IS code extraction |
| **LPU Inference** | Groq LPU hardware | 750–900 tokens/sec vs 30–60 on standard GPU |
| **Key Rotation** | Round-robin (3 Groq keys) | 3× effective rate-limit headroom for batch inference |
| **API Layer** | FastAPI + Uvicorn | Async, typed, auto-documented REST API |
| **Frontend** | Vanilla HTML / CSS / JS | Zero build toolchain, instant load, fully portable |

---

## 4. Ingestion Pipeline Detail

### `parser.py` — PDF Extraction
- Uses **PyMuPDF** to extract block-level text from SP 21 : 2005
- Implements **section-aware parsing** — correctly identifies IS number headings, scopes, and clause boundaries across multi-column BIS layout
- Handles interleaved columns, header repetitions, and footnotes

### `chunker.py` — Semantic Chunking

The foundational design decision: **one IS standard = one chunk**.

Every chunk has two distinct text fields:
- **`text_to_embed`** — IS number + title + section prepended → embedding vector carries exact keyword signal
- **`content_only`** — clean prose only → fed to LLM to maximise useful content per token

```json
{
  "chunk_id":      "CHUNK_0004",
  "is_number":     "IS 269 : 1989",
  "title":         "ORDINARY PORTLAND CEMENT, 33 GRADE",
  "section_name":  "CEMENT AND CONCRETE",
  "text_to_embed": "IS Number: IS 269 : 1989\nTitle: ORDINARY PORTLAND CEMENT...",
  "content_only":  "1. Scope — This standard covers ordinary Portland cement..."
}
```

### `embedder.py` — FAISS Index
- Embeds all 584 chunks with `all-MiniLM-L6-v2`
- Builds `IndexFlatIP` with L2-normalised vectors (equivalent to cosine similarity)
- Output: `faiss_index.bin` (897 KB) + `chunk_metadata.json` (5.1 MB) — loaded **once** at server startup

---

## 5. Inference Pipeline Detail

### Layer 1 — Query Reformulation
```
Input:  "I need to comply with regulations for coarse aggregates for structural concrete"
Output: ["Indian Standard natural coarse aggregates structural concrete IS 383",
          "BIS specification fine aggregates concrete construction"]
```
The original query is always appended — no information is ever discarded.

### Layer 2 — Multi-Query FAISS Search
- Each reformulated query independently searched (top-10)
- Results across all queries merged and **deduplicated by `chunk_id`**

### Layer 3 — Cosine Re-ranking
- Merged pool sorted by FAISS cosine score (descending)
- Top-5 chunks selected for LLM context
- Each chunk hard-capped at **600 chars (~150 tokens)** → ~900 tokens total context

### Layer 4 — Generate & Extract
A single `Llama 3.3 70b` call returns both the answer and IS codes in one structured JSON:
```json
{
  "response": "The BIS standard covering coarse and fine aggregates from natural sources for structural concrete is IS 383 : 1970...",
  "standards": ["IS 383:1970"]
}
```

**Fallback:** If JSON parsing fails, a regex extractor (`IS\s*\d+...`) scans retrieved chunks — the pipeline **never returns empty-handed**.

---

## 6. REST API Layer (`api.py`)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | `{ status, pipeline_ready }` — polled by frontend every 30s |
| `POST` | `/query` | `{ query }` → `{ response, retrieved_standards, latency_seconds }` |
| `GET` | `/` | Serves `frontend/index.html` |
| `GET` | `/static/*` | Serves CSS + JS assets |

- **CORS** open for all origins — safe for local demo, easily restricted for production
- Frontend served **directly from FastAPI** — no separate web server needed
- `eval_script.py` and `inference.py` import the pipeline directly — zero HTTP overhead during evaluation

---

## 7. Frontend

### 7.1 Design Philosophy

Built with **zero build toolchain** — plain HTML, CSS, and vanilla JavaScript.

- No Node.js, no bundler, no framework install
- Fully portable: copy three files, it works
- `eval_script.py` and `inference.py` are completely unaffected

### 7.2 Visual Design — Dark Glassmorphism

| Element | Style | Effect |
|---|---|---|
| Background | `#080b14` deep navy | Cinematic dark mode |
| Cards | `rgba(255,255,255,0.04)` + `backdrop-filter: blur` | Glass surface effect |
| Primary gradient | `#4f6ef7 → #8b5cf6` (blue → purple) | Title, CTA button, accents |
| Latency chip | `#10b981` green | Signals speed at a glance |
| IS code chips | `#8b5cf6` purple monospace | Visually distinct from prose |
| Typography | Inter 300–800 + JetBrains Mono | Google Fonts — premium feel |
| BG orbs | 3 blurred radial gradients + `float` keyframes | Living, breathing background |

### 7.3 UI Components

```
┌─ Header ────────────────────────────────────────────────────┐
│  BISfit logo  ·  "Standards Intelligence"                    │
│  [580 IS Standards] [Groq · Llama 3] [● Ready]             │
└─────────────────────────────────────────────────────────────┘

┌─ Hero ──────────────────────────────────────────────────────┐
│  "Ask any question about Indian Standards"                   │
│  Gradient headline · tech stack subtitle                     │
└─────────────────────────────────────────────────────────────┘

┌─ Query Card (glassmorphic) ─────────────────────────────────┐
│  ┌─ Textarea ─────────────────────┐  [ Ask BISfit → ]      │
│  └────────────────────────────────┘                         │
│  Try: [33 Grade OPC] [Aggregates] [Slag Cement] [Pipes]    │
│                                                              │
│  ── Loading ──────────────────────────────────────────────  │
│  ⠿  "Searching FAISS index across 584 chunks…"              │
│                                                              │
│  ── Result ────────────────────────────────────────────── ─ │
│  ✓ RESPONSE                                    ⚡ 1.71s    │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ The BIS standard covering 33 Grade OPC is             │  │
│  │ IS 269 : 1989. This standard outlines...              │  │
│  └───────────────────────────────────────────────────────┘  │
│  📋 RETRIEVED STANDARDS                                      │
│  [IS 269:1989]  [IS 269:2015]                               │
└─────────────────────────────────────────────────────────────┘

┌─ How It Works (4 step cards) ──────────────────────────────┐
│  01 🔄 Query Reform.   02 🔍 FAISS Search                   │
│  03 📊 Re-ranking      04 ⚡ Llama 3 70b Generation         │
└─────────────────────────────────────────────────────────────┘
```

### 7.4 UX Optimisations

| Feature | Implementation | Why It Matters |
|---|---|---|
| **Animated loading steps** | 4-message cycle (2.2s interval) | Tells users exactly what the pipeline is doing |
| **Live health badge** | `/health` polled every 30s | Shows backend readiness before the user types |
| **Example pills** | Pre-fill textarea on click | Judges/evaluators can test in one click |
| **Enter to submit** | `keydown` intercept | Expected UX — no mouse needed |
| **Shift+Enter** | Preserved for newlines | Multi-line queries work naturally |
| **Latency chip** | Green monospace, top-right of result | Highlights sub-2s speed immediately |
| **Friendly error panel** | Shows server URL + error message | Debuggable without DevTools |
| **Responsive layout** | CSS `clamp`, flex-wrap, media query | Works on laptop, tablet, and phone |
| **Glass hover on step cards** | CSS `::before` + gradient + `transform` | Delightful interaction — zero JS |

### 7.5 Performance

- No JS frameworks → zero parse overhead, instant DOMContentLoaded
- CSS animations use only `transform` + `opacity` → GPU-composited, no layout thrash
- Google Fonts loaded with `rel=preconnect` → minimal FTTFB impact
- Single `POST /query` per question → no polling, no streaming setup

---

## 8. Evaluation Metrics

| Metric | Definition | Target | BISfit |
|---|---|---|---|
| **Hit Rate @3** | ≥1 expected IS code in top-3 retrieved | > 80% | ✅ ~90% |
| **MRR @5** | Mean Reciprocal Rank of first correct code (top-5) | > 0.70 | ✅ ~0.90 |
| **Avg Latency** | End-to-end per query | < 5.0s | ✅ ~1.7s |

### Why These Numbers Are Strong

1. **Multi-query retrieval** casts a wider net — the correct chunk is nearly always retrieved
2. **Metadata-prefixed embeddings** give the vector an exact IS number signal
3. **Groq LPU** eliminates GPU bottleneck — Llama 3 70b at 750+ tokens/sec
4. **Regex fallback** keeps Hit@3 robust even if LLM JSON extraction fails

---

## 9. Key Design Decisions

### Decision 1 — One Chunk Per Standard (Not Sliding Window)
Sliding-window chunking (256 tokens, 50 overlap) would split a standard mid-clause, destroying semantic integrity. BISfit uses **domain-aware chunking** to preserve each standard as a self-contained unit.

### Decision 2 — Metadata Prefix in Embedding Input
```
"IS Number: IS 269 : 1989\nTitle: ORDINARY PORTLAND CEMENT, 33 GRADE\n\n1. Scope..."
```
The IS number and title are embedded _inside_ the vector — so exact-match keyword queries ("IS 383") and semantic queries ("coarse aggregate for concrete") both hit the same chunk.

### Decision 3 — Two Different LLM Models
| Layer | Model | Reason |
|---|---|---|
| Reformulation | Llama 3.1 8b Instant | 400ms, low cost, JSON output |
| Generation | Llama 3.3 70b Versatile | High quality narrative, accurate IS extraction |

Using 70b for reformulation would add ~800ms with negligible quality gain.

### Decision 4 — Single Combined LLM Call for Generate + Extract
Instead of two calls (generate → extract), one structured JSON call returns both simultaneously — saves ~600ms and halves the rate-limit cost.

### Decision 5 — Round-Robin Key Rotation
Three Groq API keys rotate per-call during batch inference, giving 3× the RPM headroom without any external queue or sleep beyond the evaluation-required 3s inter-query pause.

---

## 10. Project File Map

```
BISfit/
├── api.py                        ← FastAPI REST + frontend server (new)
├── inference.py                  ← Batch evaluation runner (unchanged)
├── eval_script.py                ← Hit@3 · MRR@5 · Latency (unchanged)
│
├── frontend/
│   ├── index.html                ← Single-page app
│   └── static/
│       ├── style.css             ← Dark glassmorphism design system
│       └── app.js                ← API client · loading UX · result rendering
│
├── src/
│   ├── ingestion/
│   │   ├── parser.py             ← PDF → structured section text
│   │   ├── chunker.py            ← Sections → 584 IS-standard chunks
│   │   └── embedder.py           ← Chunks → FAISS index (384-dim)
│   └── pipeline/
│       ├── rag.py                ← Full pipeline orchestrator
│       └── llm_client.py         ← Groq client with key rotation
│
├── data/
│   ├── faiss_index.bin           ← Pre-built vector index (897 KB)
│   ├── chunk_metadata.json       ← Chunk metadata (5.1 MB)
│   ├── rag_chunks.json           ← Full chunk text (3.5 MB)
│   ├── public_test_set.json      ← 10 benchmark queries + ground truth
│   └── public_test_results.json  ← Inference output (eval input)
│
├── .env                          ← GROQ_API_KEY_1/2/3 (git-ignored)
├── requirements.txt
└── README.md
```

---

## 11. Running the System

### Start the Full System (API + Frontend)

```bash
source venv/bin/activate        # macOS/Linux
uvicorn api:app --reload --port 8000
```

Open **http://127.0.0.1:8000** — the UI and API are both served.

### Run Evaluation (Unchanged)

```bash
python inference.py \
  --input  data/public_test_set.json \
  --output data/public_test_results.json

python eval_script.py \
  --results data/public_test_results.json
```

### Environment Setup

```dotenv
# .env (never commit)
GROQ_API_KEY_1=gsk_xxxx
GROQ_API_KEY_2=gsk_yyyy
GROQ_API_KEY_3=gsk_zzzz
```

---

## 12. Evaluation-Readiness Summary

| Requirement | BISfit Approach |
|---|---|
| **Correctness** | Multi-query retrieval + metadata-prefixed embeddings → Hit@3 ≥ 90% |
| **Speed** | Groq LPU + single combined LLM call → avg ~1.7s |
| **Robustness** | Regex fallback if LLM JSON parse fails — never empty |
| **Isolation** | `eval_script.py` and `inference.py` 100% unchanged |
| **Reproducibility** | Pre-built FAISS index committed — no re-ingestion needed |
| **Portability** | No external DB, no Docker — just Python + pip |

---

*BISfit · SP 21 : 2005 · 580 Standards · 584 Chunks*
*Independent research tool. Not affiliated with or endorsed by the Bureau of Indian Standards.*
