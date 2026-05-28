"""
Configuration for the Congress Trading Aggregator.
Set API keys via environment variables or a .env file.
"""
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    # --- Optional API keys (free tiers available without) ---
    finnhub_api_key: Optional[str] = field(default_factory=lambda: os.getenv("FINNHUB_API_KEY"))
    quiver_api_key: Optional[str] = field(default_factory=lambda: os.getenv("QUIVER_API_KEY"))
    unusual_whales_token: Optional[str] = field(default_factory=lambda: os.getenv("UNUSUAL_WHALES_TOKEN"))

    # --- Output ---
    reports_dir: str = field(default_factory=lambda: os.getenv("REPORTS_DIR", "congress_tracker/reports"))
    send_email: bool = field(default_factory=lambda: os.getenv("SEND_EMAIL", "false").lower() == "true")
    email_to: Optional[str] = field(default_factory=lambda: os.getenv("EMAIL_TO"))
    smtp_host: str = field(default_factory=lambda: os.getenv("SMTP_HOST", "smtp.gmail.com"))
    smtp_port: int = field(default_factory=lambda: int(os.getenv("SMTP_PORT", "587")))
    smtp_user: Optional[str] = field(default_factory=lambda: os.getenv("SMTP_USER"))
    smtp_password: Optional[str] = field(default_factory=lambda: os.getenv("SMTP_PASSWORD"))

    # --- Schedule ---
    run_hour: int = field(default_factory=lambda: int(os.getenv("RUN_HOUR", "7")))   # 7 AM daily
    run_minute: int = field(default_factory=lambda: int(os.getenv("RUN_MINUTE", "0")))
    lookback_days: int = field(default_factory=lambda: int(os.getenv("LOOKBACK_DAYS", "7")))


# --- Top-performing politicians to spotlight ---
SPOTLIGHT_POLITICIANS = [
    "Nancy Pelosi",
    "Paul Pelosi",
    "Dan Crenshaw",
    "Michael McCaul",
    "Ro Khanna",
    "Josh Gottheimer",
    "Brian Mast",
    "Tommy Tuberville",
    "David Perdue",
    "Virginia Foxx",
    "Shelley Moore Capito",
    "Austin Scott",
    "Greg Gianforte",
    "Susie Lee",
    "Mark Green",
]

# --- Key institutional investors tracked via SEC 13F ---
INSTITUTIONAL_INVESTORS = {
    "Berkshire Hathaway (Buffett)": "0001067983",
    "Scion Asset Management (Burry)": "0001649339",
    "Pershing Square (Ackman)": "0001336528",
    "Duquesne Family Office (Druckenmiller)": "0000802799",
    "Appaloosa Management (Tepper)": "0001691936",
    "Third Point (Loeb)": "0001040273",
    "Greenlight Capital (Einhorn)": "0001079114",
}

# --- ARK ETF tickers for Cathie Wood tracking ---
ARK_ETFS = {
    "ARKK": "ARK Innovation ETF",
    "ARKQ": "ARK Autonomous Technology & Robotics ETF",
    "ARKW": "ARK Next Generation Internet ETF",
    "ARKG": "ARK Genomic Revolution ETF",
    "ARKF": "ARK Fintech Innovation ETF",
    "ARKX": "ARK Space Exploration & Innovation ETF",
}
