# Company One-Pager Generator — Bynd AI Engineering Intern Assignment

An AI system that produces a fully-sourced, investor-grade company one-pager from just a company name.  
Every claim carries a citation and a confidence level. When something cannot be verified, the system says so — it never invents.

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- A **free** Groq API key → sign up at [console.groq.com](https://console.groq.com) (no credit card needed)

### 2. Install

```bash
git clone https://github.com/amitkmr23/company-onepager
cd company-onepager
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
# Open .env and paste your Groq API key
```

### 4. Run

```bash
python main.py "Bharat Forge Limited"
python main.py "Brakes India Private Limited"
```

Output is saved to `outputs/<company_name>.md` and also printed to the terminal.

---

## Architecture

```
Input: company name
        │
        ▼
┌─────────────────────┐
│  Entity Resolver    │  DDG search → LLM → CompanyIdentity
│  (ticker, website,  │  (confirms it's the right company; finds
│   listed/unlisted)  │   NSE ticker if listed)
└────────┬────────────┘
         │
    ┌────┴─────────────────────────────────┐
    │              Parallel agents         │
    ▼                ▼                    ▼
Overview          Financial           Products &
Agent             Agent               Clients Agent
(DDG search       (yfinance for       (DDG search +
 + LLM extract    listed; web         scraping;
 cited claims)    search fallback     only named,
                  for unlisted)       verified items)
    │                │                    │
    └────────────────┼────────────────────┘
                     ▼
             Hallucination Guard
        (drop uncited → mark NOT FOUND)
                     │
                     ▼
            Markdown Formatter
        (inline [n] citations + badges)
                     │
                     ▼
            outputs/<name>.md
```

### Models / Services Used

| Component | Tool | Why |
|---|---|---|
| LLM | **Groq** — `llama-3.3-70b-versatile` | Free tier, fast, excellent JSON instruction-following |
| Web Search | **duckduckgo-search** Python lib | No API key, no signup, completely free |
| Financial Data | **yfinance** | Free, reliable NSE/BSE annual data for listed companies |
| Scraping | **httpx + BeautifulSoup4** | Lightweight, handles most financial news pages |
| Validation | **Pydantic v2** | `CitedClaim.source_url` is a required field — hallucination impossible at the model level |

### Key Design Decisions

- **No LangChain** — direct API calls are easier to audit, debug, and explain
- **Pydantic enforces citations** — `CitedClaim` has `source_url` as a required non-empty field; any claim without a URL fails validation before it can reach the output
- **Honest gaps > filled gaps** — the `not_found_fields` list in the output is a first-class feature, not an afterthought
- **yfinance for listed, web fallback for unlisted** — Brakes India is private/unlisted, so financial data is genuinely sparse; the system reports this correctly

---

## Sample Outputs

Pre-generated outputs are in [`outputs/`](outputs/):

- [`bharat_forge_limited.md`](outputs/bharat_forge_limited.md) — **data-rich** company (NSE-listed)
- [`brakes_india_private_limited.md`](outputs/brakes_india_private_limited.md) — **data-sparse** company (unlisted, TVS group)

The gap between the two outputs is intentional — it demonstrates the system's honesty under data scarcity.

---

## Self-Evaluation

### What works well

- Bharat Forge output is well-sourced: financial rows come directly from yfinance (NSE filings), and overview claims trace to company website / Moneycontrol / ET
- Brakes India correctly surfaces "NOT FOUND" for financials (company is unlisted; MCA data is paywalled) rather than hallucinating numbers
- The Pydantic `CitedClaim` model makes it structurally impossible to output an uncited claim

### Where it breaks

- **Brakes India products/clients are sparse** — the company has no investor-relations site and news coverage is thin; some products are named but client OEM relationships are mostly unverifiable
- **Image/logo retrieval is best-effort** — logo URLs are included only when a search result directly provides one; no dedicated logo API was used
- **DuckDuckGo rate limits** — under heavy use the search library gets throttled; the code has backoff logic but a paid search API would be more reliable
- **yfinance key mapping** — INR figures from NSE come back as raw numbers; the `format_crore` conversion is correct but needs validation against the actual filed PDF for exact figures

### Trade-offs

| Dimension | Trade-off made |
|---|---|
| Cost | 100% free stack (Groq + DDG + yfinance). Latency ~60–120s per company due to sequential LLM calls to stay within Groq free-tier rate limits |
| Latency | Agents run sequentially to respect free-tier API limits. Parallelising would cut this to ~20–30s but risks rate-limit errors |
| Accuracy | LLM extraction from web snippets is good but not perfect — financial figures are validated against yfinance (primary source), not re-verified against PDFs |
| Coverage | Unlisted companies with no IR site (Brakes India) will always produce sparse outputs — this is correct behaviour, not a bug |

### What I'd build next

1. **Annual report PDF ingestion** — parse the actual filing PDF with a tool like `pdfplumber` to extract tables directly, eliminating LLM hallucination risk on financials
2. **Screener.in structured scrape** — Screener has clean balance-sheet tables for many Indian companies; a dedicated scraper would improve Brakes India coverage
3. **Parallel agents** — safe to parallelise overview, financial, and products agents once on a paid API tier
4. **Confidence auto-escalation** — if a claim appears in 2+ independent sources, upgrade confidence from MEDIUM → HIGH automatically
5. **HTML / PDF render** — clean one-page layout using WeasyPrint or Playwright for a presentation-ready output

---

## Write-up

See [writeup.md](writeup.md) for the full ~1-page trade-off and retrospective write-up.
