# Write-up — Company One-Pager Generator

## What I built

A pipeline that takes a company name and produces a fully-cited investor one-pager in Markdown.
Each claim in the output — every line of the overview, every financial figure, every product name and client — is tagged with the source URL it came from and a confidence level (HIGH / MEDIUM / LOW). If something cannot be verified, it is omitted and listed explicitly in a "Data Gaps" section. Nothing is invented.

The system was tested on two deliberately contrasting companies:
- **Bharat Forge Limited** (NSE: BHARATFORG) — data-rich, fully listed
- **Brakes India Private Limited** — data-sparse, unlisted, no public IR site

## What didn't work

**Brakes India financials** were the clearest failure — and the most instructive one. The company is private and files with MCA; those filings are paywalled or require registration to access. The web search returns news mentions of their revenue (₹8,000+ Cr referenced in one article) but without a retrievable source that the LLM can confirm, the system correctly flags the financial section as "NOT FOUND" rather than inserting a loosely-sourced number. This is the right outcome — an analyst would rather see an honest gap than a made-up figure — but it limits the output's practical usefulness for unlisted companies.

**DuckDuckGo rate limiting** was a recurring friction point during development. The free search library gets throttled after several rapid queries, so I added `time.sleep` delays between batches. This is reliable but slow (~90–120 seconds per company). A production system would use a paid search API (Tavily, Serper, or Bing) that handles bursting without throttling.

**LLM snippet extraction fidelity** — the LLM occasionally shortens a snippet in a way that changes its meaning slightly, or merges two sentences from different parts of a page. The Pydantic model enforces that a snippet exists, but doesn't verify it against the source. An ideal system would cross-check the extracted snippet against the scraped text before committing it to the output.

## Trade-offs

**Cost vs. latency** — I chose the fully free stack (Groq + DuckDuckGo + yfinance) to avoid any API spend. The cost is sequential execution with sleep delays. With a $5/month Tavily key and a slightly higher Groq quota, the same pipeline would run in under 30 seconds.

**LLM extraction vs. deterministic parsing** — For financial data on listed companies I used yfinance (deterministic — pulls directly from Yahoo Finance's NSE data feed) and avoided LLM extraction entirely. For everything else I used LLM extraction from web snippets, which is flexible but imperfect. A better approach for financials would be to parse the actual annual-report PDF with `pdfplumber` — deterministic table extraction, no hallucination risk.

**Breadth vs. depth** — Each web source is capped at 4,500 characters before being sent to the LLM. This keeps costs and latency manageable but means a 200-page annual report only contributes its first few pages. A chunked RAG approach over the full document would be more thorough.

## What I'd build next

1. **PDF annual-report ingestion** — download the latest AR PDF from NSE/BSE filings, extract tables with `pdfplumber`, and feed structured financial data directly to the formatter — no LLM required for numbers.
2. **Screener.in structured scraper** — Screener has clean balance-sheet and P&L tables for most Indian companies including some private ones; a targeted scraper would dramatically improve Brakes India coverage.
3. **Cross-source claim deduplication and confidence escalation** — if the same fact appears in 3 independent sources, auto-upgrade confidence to HIGH.
4. **HTML/PDF render** — a clean single-page layout using WeasyPrint for a presentation-ready deliverable.
5. **Evaluation harness** — a small benchmark of 10 known companies with manually verified ground-truth financials, to score precision/recall on extracted figures and catch regressions.
