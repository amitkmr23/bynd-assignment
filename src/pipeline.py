"""Pipeline: orchestrates all agents and assembles the final OnePager."""
from __future__ import annotations
from datetime import datetime
from .models import OnePager
from .agents.entity_resolver import resolve_entity
from .agents.overview_agent import gather_overview
from .agents.financial_agent import gather_financials
from .agents.products_agent import gather_products_and_clients


def run_pipeline(company_name: str) -> OnePager:
    sep = "=" * 54
    print(f"\n{sep}")
    print(f"  Company One-Pager Pipeline")
    print(f"  Input: {company_name}")
    print(f"{sep}\n")

    # ── Step 1: Identify the company ──────────────────────────────────────────
    identity = resolve_entity(company_name)
    print(
        f"  Resolved → {identity.canonical_name} | "
        f"Listed: {identity.is_listed} | Ticker: {identity.ticker or 'N/A'}"
    )

    # ── Step 2: Gather data in sequence (avoids overwhelming free-tier APIs) ──
    overview_claims = gather_overview(identity)
    financial_snapshot = gather_financials(identity)
    products, clients = gather_products_and_clients(identity)

    # ── Step 3: Assess honest gaps — never invent ─────────────────────────────
    not_found: list[str] = []
    if not overview_claims:
        not_found.append("Company overview — no verifiable claims found in available sources")
    if not financial_snapshot.rows:
        not_found.append("Financial data — not available in publicly accessible sources")
    if not products:
        not_found.append("Products — no named products verified from available sources")
    if not clients:
        not_found.append("Select Clients — no named clients verified from available sources")

    print(f"\n{sep}")
    print(f"  Summary")
    print(f"  Overview claims : {len(overview_claims)}")
    print(f"  Financial rows  : {len(financial_snapshot.rows)}")
    print(f"  Products        : {len(products)}")
    print(f"  Clients         : {len(clients)}")
    if not_found:
        print(f"  Data gaps       : {len(not_found)} field(s) not found")
    print(f"{sep}\n")

    return OnePager(
        company=identity,
        overview_claims=overview_claims,
        financial_snapshot=financial_snapshot,
        products=products,
        clients=clients,
        not_found_fields=not_found,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )
