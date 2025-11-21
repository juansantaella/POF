import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

import requests
from dotenv import load_dotenv

from . import OptionContract

BASE_DIR = Path(__file__).resolve().parent.parent

# Load provider mode (tradier_sandbox vs tradier_production)
load_dotenv(BASE_DIR / "provider.env")
# Load Tradier keys (name as you prefer; we support one or two underscores)
load_dotenv(BASE_DIR / "Tradier_API_Key.env")
load_dotenv(BASE_DIR / "Tradier__API_Key.env")  # in case you used this name

DATA_PROVIDER = os.getenv("DATA_PROVIDER", "tradier_sandbox").lower()

if DATA_PROVIDER == "tradier_sandbox":
    BASE_URL = "https://sandbox.tradier.com/v1"
    TOKEN = os.getenv("TRADIER_SANDBOX_ACCESS_TOKEN")
elif DATA_PROVIDER == "tradier_production":
    BASE_URL = "https://api.tradier.com/v1"
    TOKEN = os.getenv("TRADIER_PRODUCTION_ACCESS_TOKEN")
else:
    # This module should only be used when provider is Tradier
    raise RuntimeError(
        f"Tradier provider imported, but DATA_PROVIDER={DATA_PROVIDER}. "
        "Expected tradier_sandbox or tradier_production."
    )

if not TOKEN:
    raise RuntimeError(
        f"Missing Tradier token for mode {DATA_PROVIDER}. "
        "Check Tradier_API_Key.env (TRADIER_SANDBOX_ACCESS_TOKEN / TRADIER_PRODUCTION_ACCESS_TOKEN)."
    )


def _tradier_get(path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{BASE_URL}{path}"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/json",
    }
    response = requests.get(url, headers=headers, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def get_option_chain(ticker: str, expiry: str) -> List[OptionContract]:
    """
    Fetch and normalize option chain from Tradier.

    Endpoint:
        GET /markets/options/chains
        Base URL:
          - https://sandbox.tradier.com/v1 (tradier_sandbox)
          - https://api.tradier.com/v1      (tradier_production)
    """

    params = {
        "symbol": ticker.upper(),
        "expiration": expiry,  # "YYYY-MM-DD"
        "greeks": "true",
    }

    data = _tradier_get("/markets/options/chains", params)

    options_root = data.get("options") or {}
    option_list = options_root.get("option") or []

    results: List[OptionContract] = []

    for opt in option_list:
        option_type = opt.get("option_type")
        if option_type not in ("call", "put"):
            continue

        strike = opt.get("strike")
        expiration = opt.get("expiration_date") or expiry
        try:
            expiry_dt = datetime.strptime(expiration, "%Y-%m-%d").date()
        except Exception:
            expiry_dt = datetime.strptime(expiry, "%Y-%m-%d").date()

        greeks = opt.get("greeks") or {}
        delta = greeks.get("delta")
        gamma = greeks.get("gamma")
        theta = greeks.get("theta")
        vega = greeks.get("vega")
        # Tradier/ORATS: mid_iv/bid_iv/ask_iv; use mid_iv if present.
        iv = greeks.get("mid_iv") or greeks.get("iv")

        greeks_source = "vendor" if (delta is not None and iv is not None) else "none"

        if strike is None:
            continue

        results.append(
            OptionContract(
                underlying=ticker.upper(),
                option_ticker=opt.get("symbol"),  # OCC option symbol
                option_type=option_type,
                expiry=expiry_dt,
                strike=float(strike),
                bid=opt.get("bid"),
                ask=opt.get("ask"),
                last=opt.get("last"),
                volume=opt.get("volume"),
                open_interest=opt.get("open_interest"),
                delta=delta,
                gamma=gamma,
                theta=theta,
                vega=vega,
                implied_vol=iv,
                greeks_source=greeks_source,
            )
        )

    return results
