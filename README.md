# 🛡️ Sentinels of Truth

A multi-agent fact-checking and knowledge-base system: ingest an unverified claim, have one agent research it against live web evidence, and have a second agent decide whether that finding actually belongs in a persistent "ground truth" store.

<p align="center">
  <a href="https://sentinels-of-truth-aman-basu.streamlit.app">
    <img src="https://img.shields.io/badge/Live_Demo-Streamlit-FF4B4B?style=for-the-badge" alt="Live Demo"/>
  </a>
</p>

<p align="center">
  <img src="./assets/workflow_graph.png" alt="LangGraph agent workflow: Start → Scout → Librarian → End" width="108"/>
</p>

Claims come in through a single on-demand endpoint — you submit one, the pipeline runs, you get a verdict back. There's no background feed poller here; it's a direct submit-and-verify loop, which is enough to exercise the full agent pipeline end to end.

## Architecture

Two agents, each with a narrow job and its own toolset, wired together as a LangGraph state machine: `START → Scout → Librarian → END`.

### Agent Alpha — "The Scout"
Takes the raw claim, runs a Tavily web search for supporting/contradicting evidence, and hands both to a Groq-hosted Llama 3.1 8B model constrained with `.with_structured_output()`. The output is a Pydantic-validated `VerificationReport`: a verdict (`VERIFIED` / `FALSE` / `UNVERIFIED`), a confidence score, a summary, and a normalized `subject` string used later for deduplication. Alpha never touches the database — its only responsibility is producing a report.

The claim-triage reasoning (deciding what's missing / what needs checking) happens implicitly inside that structured-output call rather than as a separate explicit step — the model is prompted to weigh the search evidence and land on `UNVERIFIED` when it can't resolve the claim, rather than Alpha first enumerating missing information before searching. Worth knowing going in if you're looking for a distinct "what am I missing" phase.

### Agent Beta — "The Librarian"
The only component with database write access. It takes Alpha's report and queries the `claims` table by `subject` before doing anything:

| Scenario | Action |
|---|---|
| Claim is `UNVERIFIED` | Discard immediately — database is never touched |
| No existing record for the subject | Insert (`VERIFIED` or `FALSE`) |
| Existing record already agrees, or is `FLAGGED` | Discard (redundant) |
| Existing record contradicts the new verdict | Flag for review — appends a timestamped conflict note, merges source lists |
| Two requests insert the same new subject concurrently | Caught via `sqlite3.IntegrityError` on the unique constraint, second one discarded |

### The Orchestrator
LangGraph passes a shared `AgentState` TypedDict between the two nodes. `trace` uses an `operator.add` reducer, so each agent appends to a running log instead of overwriting it — that log is what the frontend shows as the investigation history.

## Tech Stack

- **FastAPI** — REST layer exposing `POST /api/verify`
- **Streamlit** — claim submission UI + verdict/trace display
- **LangGraph** — orchestration, manually-defined state schema
- **Groq + Llama 3.1 8B Instant** — structured-output inference for Alpha
- **Tavily** — web search evidence
- **SQLite** — ground-truth store
- **Pydantic** — schema validation for both the LLM output and the API contract

## Local Setup

```bash
git clone https://github.com/<your-username>/sentinels-of-truth.git
cd sentinels-of-truth
python -m venv venv
source venv/bin/activate   # venv\Scripts\activate on Windows
pip install -r requirements.txt
```

Create a `.env` file:
```env
GROQ_API_KEY=your_groq_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
```

Run it as two processes:

```bash
# terminal 1 — backend, also initializes ground_truth.db on first run
uvicorn main:api --reload

# terminal 2 — frontend
streamlit run frontend.py
```

Open the Streamlit URL (usually `http://localhost:8501`) and submit a claim.

## Known limitations

The real architectural tension here: a probabilistic layer (Alpha's LLM-generated `subject` field) writing into a deterministic layer (Beta's exact-match `WHERE subject = ?` against a SQL unique constraint). Because LLM generation isn't deterministic across calls, the same underlying fact can get normalized to different strings on different runs. Concretely: "Jupiter is the largest planet" can produce the subject `"largest planet"`, while "Saturn is the largest planet in our solar system" produces `"largest planet in our solar system"` — same fact-space to a human, two unrelated rows to SQLite. That silently breaks the conflict-detection logic Beta depends on. It's not a prompting bug, it's a ceiling on what exact-match relational lookups can do with generated text.

The fix is replacing (or augmenting) the SQLite lookup with a vector store — ChromaDB, say — embedding each `subject` and retrieving near-duplicates by cosine similarity above a threshold, instead of string equality. That would let Beta correctly cluster `"largest planet"` and `"largest planet in our solar system"` as the same subject, while SQLite (or a hybrid store) still handles the structured fields — status, confidence, timestamps, sources.

## Repository Structure

```
sentinels-of-truth/
├── main.py             # FastAPI app — POST /api/verify, invokes the LangGraph orchestrator
├── orchestrator.py     # LangGraph StateGraph — Scout → Librarian → END
├── alpha_agent.py       # Agent Alpha — Tavily search + Groq structured-output verification
├── beta_agent.py        # Agent Beta — SQL conflict resolution (Insert / Flag / Discard)
├── database.py          # SQLite schema + init
├── frontend.py           # Streamlit UI
└── requirements.txt
```