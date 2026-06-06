"""Markdown formatter — converts a OnePager model into a clean, citation-tagged document."""
from __future__ import annotations
from ..models import OnePager, CitedClaim, ConfidenceLevel

_BADGE = {
    ConfidenceLevel.HIGH:   "🟢 HIGH",
    ConfidenceLevel.MEDIUM: "🟡 MED",
    ConfidenceLevel.LOW:    "🔴 LOW",
}


class _Footnotes:
    def __init__(self) -> None:
        self._entries: list[str] = []
        self._idx = 1

    def add(self, claim: CitedClaim) -> str:
        """Register a claim and return its inline reference marker like [1]."""
        badge = _BADGE[claim.confidence]
        entry = (
            f"[{self._idx}] {badge} · **{claim.source_title}**  \n"
            f"   URL: {claim.source_url}  \n"
            f"   > \"{claim.snippet[:200]}\""
        )
        self._entries.append(entry)
        ref = f"[{self._idx}]"
        self._idx += 1
        return ref

    def render(self) -> str:
        if not self._entries:
            return ""
        lines = ["---", "## Citations & Confidence", ""]
        lines += [
            "| Badge | Meaning |",
            "|---|---|",
            "| 🟢 HIGH | Official source — company website, annual report, or exchange filing |",
            "| 🟡 MED  | Reputable third-party — news, analyst report, financial database |",
            "| 🔴 LOW  | Inferred or loosely supported |",
            "",
        ]
        for e in self._entries:
            lines.append(e)
            lines.append("")
        return "\n".join(lines)


def format_onepager(op: OnePager) -> str:
    fn = _Footnotes()
    c = op.company
    lines: list[str] = []

    # ── Header ────────────────────────────────────────────────────────────────
    lines += [f"# {c.canonical_name}", f"*One-Pager · Generated {op.generated_at}*", ""]

    meta: list[str] = []
    if c.ticker:   meta.append(f"**Ticker:** {c.ticker}")
    if c.exchange: meta.append(f"**Exchange:** {c.exchange}")
    if c.sector:   meta.append(f"**Sector:** {c.sector}")
    if c.industry: meta.append(f"**Industry:** {c.industry}")
    if c.hq:       meta.append(f"**HQ:** {c.hq}")
    if c.website:  meta.append(f"**Website:** [{c.website}]({c.website})")
    if meta:
        lines.append("  |  ".join(meta))
        lines.append("")

    # ── Section 1: Company Overview ───────────────────────────────────────────
    lines += ["---", "## 1. Company Overview", ""]
    if op.overview_claims:
        for claim in op.overview_claims:
            ref = fn.add(claim)
            lines.append(f"- {claim.value} {ref}")
    else:
        lines.append("*Overview — not found in available sources.*")
    lines.append("")

    # ── Section 2: Financial Snapshot ─────────────────────────────────────────
    lines += ["---", "## 2. Financial Snapshot", ""]
    snap = op.financial_snapshot
    lines.append(f"*Data source: {snap.data_source}*")
    lines.append("")

    if snap.rows and snap.years:
        years = snap.years
        lines.append("| Metric | " + " | ".join(years) + " |")
        lines.append("|---" + "|---" * len(years) + "|")
        for row in snap.rows:
            cells = [row.metric]
            for yr in years:
                v = row.values.get(yr)
                cells.append(v if v is not None else "—")
            lines.append("| " + " | ".join(cells) + " |")
            if row.note:
                lines.append(f"  *{row.note}*")
        lines.append("")
        # Single footnote for the whole financial table
        if snap.rows[0].source_url:
            r = snap.rows[0]
            ref = fn.add(CitedClaim(
                value="Financial table",
                source_url=r.source_url or "",
                source_title=r.source_title or snap.data_source,
                snippet=f"Annual financial data for {c.canonical_name}",
                confidence=ConfidenceLevel.HIGH if c.is_listed else ConfidenceLevel.MEDIUM,
            ))
            lines.append(f"*Source for all financial figures: {ref}*")
            lines.append("")
    else:
        lines.append("*Financial data not available in public sources for this company.*")
        lines.append("")

    for note in snap.notes:
        lines.append(f"> ⚠️  {note}")
    if snap.notes:
        lines.append("")

    # ── Section 3: Products ───────────────────────────────────────────────────
    lines += ["---", "## 3. Products", ""]
    if op.products:
        for prod in op.products:
            ref = fn.add(prod.description)
            lines.append(f"**{prod.name}** — {prod.description.value} {ref}")
            if prod.image_url:
                lines.append(f"![{prod.name}]({prod.image_url})")
            lines.append("")
    else:
        lines.append("*Products — no verified product information found in available sources.*")
        lines.append("")

    # ── Section 4: Select Clients ─────────────────────────────────────────────
    lines += ["---", "## 4. Select Clients", ""]
    if op.clients:
        for client in op.clients:
            ref = fn.add(client.relationship)
            lines.append(f"- **{client.name}** — {client.relationship.value} {ref}")
            if client.logo_url:
                lines.append(f"  ![{client.name}]({client.logo_url})")
    else:
        lines.append("*Select Clients — no verified client names found in available sources.*")
    lines.append("")

    # ── Not Found ─────────────────────────────────────────────────────────────
    if op.not_found_fields:
        lines += ["---", "## ⚠️  Data Gaps (Not Found — Not Invented)", ""]
        lines.append(
            "The following could not be verified from publicly available sources "
            "and are therefore omitted rather than estimated:"
        )
        lines.append("")
        for field in op.not_found_fields:
            lines.append(f"- {field}")
        lines.append("")

    # ── Citations block ───────────────────────────────────────────────────────
    lines.append(fn.render())

    return "\n".join(lines)
