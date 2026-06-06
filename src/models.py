from __future__ import annotations
from pydantic import BaseModel, field_validator
from typing import Optional
from enum import Enum


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"      # Official source or direct quote from primary document
    MEDIUM = "MEDIUM"  # Reliable third-party source
    LOW = "LOW"        # Inferred or indirectly supported


class CitedClaim(BaseModel):
    """A single verifiable fact with mandatory source attribution."""
    value: str
    source_url: str
    source_title: str
    snippet: str        # Exact text from source that supports this claim
    confidence: ConfidenceLevel

    @field_validator("value")
    @classmethod
    def value_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Claim value cannot be empty")
        return v.strip()

    @field_validator("source_url")
    @classmethod
    def url_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("source_url is mandatory — every claim must have a source")
        return v.strip()


class FinancialRow(BaseModel):
    """One row in the financial table (e.g., Revenue across years)."""
    metric: str
    values: dict[str, Optional[str]]   # {year_label: formatted_value_or_None}
    source_url: Optional[str] = None
    source_title: Optional[str] = None
    note: Optional[str] = None


class ProductInfo(BaseModel):
    name: str
    description: CitedClaim
    image_url: Optional[str] = None    # Only if found and verifiable


class ClientInfo(BaseModel):
    name: str
    relationship: CitedClaim           # Describes what they buy / how they're a client
    logo_url: Optional[str] = None     # Only if found and verifiable


class CompanyIdentity(BaseModel):
    name: str                          # Input name
    canonical_name: str                # Confirmed official name
    website: Optional[str] = None
    ticker: Optional[str] = None       # e.g. "BHARATFORG.NS"
    exchange: Optional[str] = None     # e.g. "NSE/BSE"
    sector: Optional[str] = None
    industry: Optional[str] = None
    hq: Optional[str] = None
    is_listed: bool = False
    search_source: str = ""


class FinancialSnapshot(BaseModel):
    rows: list[FinancialRow]
    data_source: str                   # e.g. "yfinance (NSE)" or "web search"
    years: list[str]
    notes: list[str] = []              # Honest notes about data gaps


class OnePager(BaseModel):
    company: CompanyIdentity
    overview_claims: list[CitedClaim]  # Each is a sourced statement
    financial_snapshot: FinancialSnapshot
    products: list[ProductInfo]
    clients: list[ClientInfo]
    not_found_fields: list[str] = []   # Fields we couldn't verify (never invented)
    generated_at: str
