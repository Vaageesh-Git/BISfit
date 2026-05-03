<div align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=700&size=14&duration=1&pause=1000&color=58A6FF&center=true&vCenter=true&multiline=true&repeat=false&width=500&height=120&lines=+%E2%96%88%E2%96%88%E2%96%88%E2%96%88%E2%96%88%E2%96%88%E2%95%97+%E2%96%88%E2%96%88%E2%95%97%E2%96%88%E2%96%88%E2%96%88%E2%96%88%E2%96%88%E2%96%88%E2%96%88%E2%95%97%E2%96%88%E2%96%88%E2%96%88%E2%96%88%E2%96%88%E2%96%88%E2%96%88%E2%95%97%E2%96%88%E2%96%88%E2%95%97%E2%96%88%E2%96%88%E2%96%88%E2%96%88%E2%96%88%E2%96%88%E2%96%88%E2%96%88%E2%95%97;%E2%96%88%E2%96%88%E2%95%94%E2%95%90%E2%95%90%E2%96%88%E2%96%88%E2%95%97%E2%96%88%E2%96%88%E2%95%91%E2%96%88%E2%96%88%E2%95%94%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%9D%E2%96%88%E2%96%88%E2%95%94%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%9D%E2%96%88%E2%96%88%E2%95%91%E2%95%9A%E2%95%90%E2%95%90%E2%96%88%E2%96%88%E2%95%94%E2%95%90%E2%95%90%E2%95%9D"/>
</picture>
<pre><code>
 ██████╗ ██╗███████╗███████╗██╗████████╗
 ██╔══██╗██║██╔════╝██╔════╝██║╚══██╔══╝
 ██████╔╝██║███████╗█████╗  ██║   ██║   
 ██╔══██╗██║╚════██║██╔══╝  ██║   ██║   
 ██████╔╝██║███████║██║     ██║   ██║   
 ╚═════╝ ╚═╝╚══════╝╚═╝     ╚═╝   ╚═╝  
</code></pre>

**Retrieval-Augmented Generation System for Bureau of Indian Standards**
*SP 21 : 2005 — Summaries of Indian Standards for Building Materials*

<br/>

[![BIS](https://img.shields.io/badge/BIS-SP%2021%20%3A%202005-003580?style=for-the-badge&logoColor=white)](https://www.bis.gov.in)
[![Standards](https://img.shields.io/badge/IS%20Standards-580-FF6B35?style=for-the-badge)](#)
[![Chunks](https://img.shields.io/badge/Vector%20Chunks-584-2ECC71?style=for-the-badge)](#)
[![FAISS](https://img.shields.io/badge/Vector%20DB-FAISS%20384d-8E44AD?style=for-the-badge)](#)
[![Groq](https://img.shields.io/badge/LLM-Groq%20%7C%20Llama%203-F55036?style=for-the-badge)](#)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](#)

<br/>

> *"Ask anything about Indian Standards for building materials — and get accurate, cited, hallucination-resistant answers in under 5 seconds."*

</div>

---

## 📖 What is BISfit?

**BISfit** is a production-ready RAG pipeline built on **SP 21 : 2005** — the Bureau of Indian Standards handbook containing summaries of **580 Indian Standards** across **27 categories** of building materials: cement, steel, timber, glass, plastics, sanitary fittings, and more.

The original PDF caused critical retrieval failures — broken multi-column extraction, interleaved text, zero semantic boundaries. BISfit solves this entirely by restructuring the dataset into **584 clean, metadata-rich chunks**, embedding them into a **FAISS index (384-dim)**, and serving answers through **Groq's LPU-accelerated Llama models** with query reformulation, cosine re-ranking, and structured JSON output.

---

## 🏗️ System Architecture

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║                          PHASE 1 — OFFLINE INGESTION                            ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║                                                                                  ║
║   BIS PDFs       parser.py        chunker.py        embedder.py      FAISS       ║
║   (SP 21)    ──▶ PyMuPDF      ──▶ 1 IS = 1 chunk ──▶ MiniLM-L6-v2 ──▶ Index    ║
║   580 stds       Section           584 chunks         384-dim          .bin       ║
║                  extractor                            vectors          + meta     ║
║                                                                                  ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║                    PHASE 2 — ONLINE INFERENCE  (Per Query)                       ║
║                                          ▲ Index loaded at startup               ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║                                                                                  ║
║  User Query ──▶ Query Reform. ──▶ FAISS Search ──▶ Re-ranking ──▶ Generate ──▶  ║
║  Natural lang   Llama 3 8b       Top-k = 10        Cosine sim    Llama 3 70b    ║
║                 2 alt queries    Multi-query        De-dupl.      Narrative      ║
║                                  retrieval                        + IS codes     ║
║                                                                        │         ║
║                                                               JSON Output        ║
║                                                               + Fallback         ║
║                                                               IS codes returned  ║
║                                                                                  ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║                                  EVALUATION                                      ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║                                                                                  ║
║  inference.py ──▶ output.json   ──▶ eval_script.py    TARGET METRICS            ║
║  Batch runner     Results store      Hit@3 · MRR@5    ● Hit@3   > 80%           ║
║  3s sleep/query   id+stds+latency    Latency           ● MRR@5   > 0.70          ║
║                                                        ● Latency < 5s            ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

### Tech Stack

| Layer | Technology | Role |
|---|---|---|
| **PDF Parsing** | PyMuPDF (`parser.py`) | Section-aware structured text extraction |
| **Chunking** | Custom `chunker.py` | 1 IS standard = 1 semantic chunk, 584 total |
| **Embeddings** | `all-MiniLM-L6-v2` | 384-dimensional sentence embeddings |
| **Vector Store** | FAISS-CPU (`faiss_index.bin`) | Sub-millisecond similarity search |
| **Query Reformulation** | Groq · Llama 3 8b | Generates 2 alternative queries per input |
| **Answer Generation** | Groq · Llama 3 70b | Narrative answer + IS code extraction |
| **Key Management** | `llm_client.py` | Round-robin across 3 Groq API keys |
| **Evaluation** | `eval_script.py` | Hit@3, MRR@5, latency benchmarking |

---

## Environment Setup

> ⚠️ **Complete this before running anything.** BISfit uses **3 separate Groq API keys** in round-robin rotation to stay within rate limits during batch inference.

### Step 1 — Create `.env` in the project root

```dotenv
# ──────────────────────────────────────────────────────
#  BISfit — Environment Configuration
#  ⚠️  This file is in .gitignore — NEVER commit it
# ──────────────────────────────────────────────────────

GROQ_API_KEY_1=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GROQ_API_KEY_2=gsk_yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy
GROQ_API_KEY_3=gsk_zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz
```

> 🔑 All three keys **must be different**. Using the same key three times defeats the rate-limit rotation entirely.

### Step 2 — Get your API keys

<div align="center">

### 📎 [**Access BISfit API Keys →**](https://docs.google.com/document/d/1AI26neJ9VIcLlg7ipCz2IZXJfdoCsod2B3bheHDo900/edit?usp=sharing)

*Open the Google Doc — all three Groq API keys are provided, ready to paste into your `.env`.*

</div>

### Step 3 — How key rotation works

`src/pipeline/llm_client.py` handles this automatically on every call:

```python
import os, itertools
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

_keys = [
    os.getenv("GROQ_API_KEY_1"),
    os.getenv("GROQ_API_KEY_2"),
    os.getenv("GROQ_API_KEY_3"),
]
_cycle = itertools.cycle(_keys)

def get_client() -> Groq:
    """Returns a Groq client on the next key in rotation."""
    return Groq(api_key=next(_cycle))
```

Each query uses the next key in sequence — **3× effective rate-limit headroom**, critical when `inference.py` runs 100+ queries in batch mode with only a 3-second sleep between them.

---

## 📁 Project Structure

```
BISfit/
│
├── 📁 data/
│   ├── chunk_metadata.json          ← Metadata for all 584 chunks (IS no., title, section)
│   ├── faiss_index.bin              ← Pre-built FAISS vector index (384-dim, 584 vectors)
│   ├── public_test_results.json     ← Output from evaluation inference run
│   ├── public_test_set.json         ← Benchmark test queries with ground truth
│   └── rag_chunks.json              ← Full RAG dataset (one IS standard per entry)
│
├── 📁 src/
│   │
│   ├── 📁 ingestion/                ◀─ PHASE 1: Offline pipeline (run once)
│   │   ├── chunker.py               ← Segments parsed content → 584 IS-standard chunks
│   │   ├── embedder.py              ← Embeds chunks via MiniLM-L6-v2 → builds FAISS index
│   │   └── parser.py                ← Extracts & structures text from BIS PDF (PyMuPDF)
│   │
│   └── 📁 pipeline/                 ◀─ PHASE 2: Online inference (per query)
│       ├── llm_client.py            ← Groq client with 3-key round-robin rotation
│       └── rag.py                   ← Full pipeline: reform → retrieve → rerank → generate
│
├── venv/                         ← Virtual environment (git-ignored)
│
├── .env                          ← API keys — NEVER commit this file
├── .gitignore                    ← Covers .env, venv/, __pycache__, *.bin
├── eval_script.py                ← Computes Hit@3, MRR@5, avg latency
├── inference.py                  ← Batch runner: queries public_test_set.json
├── presentation.pdf              ← Project presentation deck
└── requirements.txt              ← All Python dependencies
```

---

## 🚀 Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-org/BISfit.git
cd BISfit

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows

# 3. Install all dependencies
pip install -r requirements.txt
```

### `requirements.txt`

```txt
groq>=0.9.0
faiss-cpu>=1.8.0
numpy>=1.26.0
pymupdf>=1.24.0
sentence-transformers>=3.0.0
python-dotenv>=1.0.0
tqdm>=4.66.0
fastapi>=0.111.0
uvicorn>=0.30.0
```

---

## ⚙️ Running the Pipeline

### Phase 1 — Build the FAISS Index *(one-time only)*

Run the three ingestion scripts in sequence:

```bash
# Step 1: Parse SP21 PDF into structured section text
python -m src.ingestion.parser

# Step 2: Chunk parsed text → 584 IS-standard chunks → data/rag_chunks.json
python -m src.ingestion.chunker

# Step 3: Embed all chunks → build FAISS index → data/faiss_index.bin
python -m src.ingestion.embedder
```

Expected terminal output after `embedder.py`:

```
Loading: all-MiniLM-L6-v2
Embedding 584 chunks... ████████████████████ 100%  [584/584]
FAISS index built — 584 vectors @ 384 dims
Saved ──▶ data/faiss_index.bin
Saved ──▶ data/chunk_metadata.json
✓ Phase 1 complete
```

> Estimated time: ~2–4 minutes on CPU

---

### Phase 2 — Query the System

#### Single query

```python
from src.pipeline.rag import BISfitRAG

rag = BISfitRAG()  # auto-loads FAISS index + rotates Groq keys

result = rag.query("What are the compressive strength requirements for Portland cement?")

print(result["answer"])       # Narrative from Llama 3 70b
print(result["is_codes"])     # e.g. ["IS 269 : 1989", "IS 455 : 1989"]
print(result["latency_ms"])   # e.g. 1842
```

#### Batch inference (for evaluation)

```bash
# Runs all queries from data/public_test_set.json
# 3-second sleep between queries to respect Groq rate limits
python inference.py
```

Results written to `data/public_test_results.json`:

```json
{
  "id": "q_042",
  "query": "thermal insulation requirements for mineral wool",
  "predicted_standards": ["IS 8183 : 1993", "IS 3677 : 1985"],
  "latency_ms": 2341
}
```

---

## Evaluation

```bash
python eval_script.py
```

Computes three metrics against `data/public_test_set.json` ground truth:

| Metric | What it measures | Target |
|---|---|---|
| **Hit@3** | Correct IS standard appears in top-3 retrieved chunks | **> 80%** |
| **MRR@5** | Mean Reciprocal Rank of the first correct result in top-5 | **> 0.70** |
| **Latency** | Average end-to-end response time per query | **< 5s** |

Sample output:

```
──────────────────────────────────────
  BISfit — Evaluation Results
──────────────────────────────────────
  Hit@3    :  90%     ✅  (target > 80%)
  MRR@5    :  0.900   ✅  (target > 0.7)
  Avg Lat. :  1.86s   ✅  (target < 5.0s)
  Queries  :  10
──────────────────────────────────────
```

---

## 🧩 Chunk Schema

Every entry in `data/rag_chunks.json`:

```json
{
  "chunk_id":       "CHUNK_0004",
  "is_number":      "IS 269 : 1989",
  "title":          "ORDINARY PORTLAND CEMENT, 33 GRADE",
  "section_number": 1,
  "section_name":   "CEMENT AND CONCRETE",
  "source":         "SP 21 : 2005",
  "publisher":      "Bureau of Indian Standards (BIS)",
  "text_to_embed":  "IS Number: IS 269 : 1989\nTitle: ORDINARY PORTLAND CEMENT...\n\n1. Scope — ...",
  "content_only":   "1. Scope — This standard covers ordinary Portland cement..."
}
```

| Field | How it's used |
|---|---|
| `chunk_id` | Links `rag_chunks.json` ↔ `chunk_metadata.json` ↔ FAISS index row |
| `is_number` | BM25 / keyword-exact lookup — always include in hybrid search |
| `section_number` | Pre-filter metadata before vector search to improve precision |
| `text_to_embed` | **Feed to `embedder.py`** — metadata prefix boosts semantic recall |
| `content_only` | **Feed to Llama 70b** as the retrieved context window |

---

## 🗃️ BIS Sections Covered

| # | Section | # | Section |
|---|---|---|---|
| 1 | Cement and Concrete | 15 | Structural Steels |
| 2 | Building Limes | 16 | Light Metals and Their Alloys |
| 3 | Stones | 17 | Structural Shapes |
| 4 | Clay Products for Building | 18 | Welding Electrodes and Wires |
| 5 | Gypsum Building Materials | 19 | Threaded Fasteners and Rivets |
| 6 | Timber | 20 | Wire Ropes and Wire Products |
| 7 | Bitumen and Tar Products | 21 | Glass |
| 8 | Floor, Wall, Roof Coverings & Finishes | 22 | Fillers, Stoppers and Putties |
| 9 | Waterproofing & Damp-Proofing Materials | 23 | Thermal Insulation Materials |
| 10 | Sanitary Appliances & Water Fittings | 24 | Plastics |
| 11 | Builder's Hardware | 25 | Conductors and Cables |
| 12 | Wood Products | 26 | Wiring Accessories |
| 13 | Doors, Windows and Shutters | 27 | General |
| 14 | Concrete Reinforcement | | |

---

## ⚡ Why Groq?

BISfit uses **Groq's LPU (Language Processing Unit)** — dedicated inference silicon, not GPU clusters:

```
Standard GPU inference  ▓▓▓▓▓▓▓░░░░░░░░░░░░░   ~30–60 tokens/sec
Groq LPU                ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓   ~750–900 tokens/sec  ⚡
```

- **Llama 3 8b** → query reformulation (fast, low-cost, 2 alt queries per call)
- **Llama 3 70b** → generation (high quality, narrative + IS code extraction)
- **3-key rotation** → uninterrupted batch inference across 100+ queries

---

## 🔒 Security

```bash
# Confirm .gitignore is correctly set
cat .gitignore
```

```gitignore
.env
venv/
__pycache__/
*.pyc
*.pyc
data/faiss_index.bin
*.bin
```

- ❌ Never commit `.env` — exposed keys are immediately invalidated
- ❌ Never hardcode any key in `llm_client.py` or any source file
- ✅ Always load via `os.getenv()` with `python-dotenv`
- ✅ Rotate keys periodically at [console.groq.com](https://console.groq.com)

---

## 📄 Data Source

| Field | Value |
|---|---|
| **Document** | SP 21 : 2005 |
| **Full Title** | Summaries of Indian Standards for Building Materials *(First Revision)* |
| **Publisher** | Bureau of Indian Standards, Manak Bhavan, New Delhi 110002 |
| **Committee** | CED 13 — Building Construction Practices Sectional Committee |
| **Standards Covered** | 580 IS standards across 27 building material categories |
| **Chunks Generated** | 584 (metadata-prefixed, one standard per chunk) |
| **Embedding Model** | all-MiniLM-L6-v2 · 384-dimensional vectors |
| **Index File** | `data/faiss_index.bin` · IndexFlatIP with L2 normalization |

---

<div align="center">

**Built for the Indian construction and engineering community**

*BISfit is an independent RAG research tool. Not affiliated with or endorsed by the Bureau of Indian Standards.*

</div>