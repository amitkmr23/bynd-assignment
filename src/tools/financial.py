"""yfinance financial data fetcher — free, no API key needed."""
from __future__ import annotations
from typing import Optional
import pandas as pd


def get_yfinance_data(ticker: str) -> dict:
    """
    Fetch income statement, balance sheet, and info for a listed company.
    Returns a dict; 'error' key is set if something goes wrong.
    """
    import yfinance as yf

    result: dict = {
        "info": {},
        "income_statement": {},
        "balance_sheet": {},
        "cash_flow": {},
        "source": f"https://finance.yahoo.com/quote/{ticker}/financials",
        "error": None,
    }

    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        result["info"] = {k: v for k, v in info.items() if v is not None}

        # Income statement (annual)
        try:
            stmt = t.income_stmt        # preferred in newer yfinance
        except AttributeError:
            stmt = t.financials         # fallback for older versions
        if stmt is not None and not stmt.empty:
            result["income_statement"] = stmt.to_dict()

        # Balance sheet
        try:
            bs = t.balance_sheet
            if bs is not None and not bs.empty:
                result["balance_sheet"] = bs.to_dict()
        except Exception:
            pass

        # Cash flow (for D&A → EBITDA)
        try:
            cf = t.cash_flow
            if cf is not None and not cf.empty:
                result["cash_flow"] = cf.to_dict()
        except Exception:
            pass

    except Exception as e:
        result["error"] = str(e)

    return result


def format_crore(value: float) -> str:
    """Convert raw INR value to Indian Crore string."""
    crore = value / 1e7
    if abs(crore) >= 1000:
        return f"₹{crore/100:.1f}k Cr"
    return f"₹{crore:.0f} Cr"


def extract_annual_rows(
    income_raw: dict,
    cash_flow_raw: dict,
    source_url: str,
    source_title: str,
) -> tuple[list, list[str]]:
    """
    Build FinancialRow list from raw yfinance income_statement + cash_flow dicts.
    Returns (rows, years_list).
    """
    from ..models import FinancialRow

    if not income_raw:
        return [], []

    # Collect all timestamps, sort most-recent-first, take up to 4 years
    all_ts: set = set()
    for metric_vals in income_raw.values():
        all_ts.update(metric_vals.keys())
    sorted_ts = sorted(all_ts, reverse=True)[:4]

    def ts_label(ts) -> str:
        yr = ts.year if hasattr(ts, "year") else int(str(ts)[:4])
        return f"FY{str(yr)[2:]}"   # e.g. FY24

    years = [ts_label(ts) for ts in sorted_ts]

    def row_for(metric_key: str, display: str, divisor: float = 1e7) -> Optional[dict]:
        data = income_raw.get(metric_key, {})
        if not data:
            return None
        vals: dict[str, Optional[str]] = {}
        for ts, yr in zip(sorted_ts, years):
            v = data.get(ts)
            if v is not None and not pd.isna(v):
                vals[yr] = format_crore(float(v))
            else:
                vals[yr] = None
        if not any(v is not None for v in vals.values()):
            return None
        return dict(metric=display, values=vals, source_url=source_url, source_title=source_title)

    rows = []
    for key, label in [
        ("Total Revenue", "Revenue"),
        ("Gross Profit", "Gross Profit"),
        ("Operating Income", "EBIT"),
        ("Net Income", "Net Income / PAT"),
    ]:
        r = row_for(key, label)
        if r:
            rows.append(FinancialRow(**r))

    # Net margin
    rev_d = income_raw.get("Total Revenue", {})
    net_d = income_raw.get("Net Income", {})
    if rev_d and net_d:
        margin_vals: dict[str, Optional[str]] = {}
        for ts, yr in zip(sorted_ts, years):
            rev = rev_d.get(ts)
            net = net_d.get(ts)
            if rev and net and not pd.isna(rev) and not pd.isna(net) and float(rev) != 0:
                margin_vals[yr] = f"{float(net)/float(rev)*100:.1f}%"
            else:
                margin_vals[yr] = None
        if any(v is not None for v in margin_vals.values()):
            rows.append(FinancialRow(
                metric="Net Margin",
                values=margin_vals,
                source_url=source_url,
                source_title=source_title,
            ))

    # EBITDA = Operating Income + D&A (from cash flow)
    oi_d = income_raw.get("Operating Income", {})
    da_d = cash_flow_raw.get("Depreciation And Amortization", {})
    if oi_d and da_d:
        ebitda_vals: dict[str, Optional[str]] = {}
        for ts, yr in zip(sorted_ts, years):
            oi = oi_d.get(ts)
            da = da_d.get(ts)
            if oi and da and not pd.isna(oi) and not pd.isna(da):
                ebitda_vals[yr] = format_crore(float(oi) + abs(float(da)))
            else:
                ebitda_vals[yr] = None
        if any(v is not None for v in ebitda_vals.values()):
            rows.append(FinancialRow(
                metric="EBITDA (approx.)",
                values=ebitda_vals,
                source_url=source_url,
                source_title=source_title,
                note="Calculated as EBIT + D&A from cash flow statement",
            ))

    return rows, years
