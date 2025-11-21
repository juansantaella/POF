import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

import requests
from dotenv import load_dotenv

from . import OptionContract

BASE_DIR = Path(__file__).resolve().parent.parent

# Load Massive keys (local files; in production use env vars)
load_dotenv(BASE_DIR / "Massive_API_Key.env")
# Legacy compatibility if you still have Polygon_API_Key.env
load_dotenv(BASE_DIR / "Polygon_API_Key.env")

API_KEY = os.getenv("MASSIVE_API_KEY") or os.getenv("POLYGON_API_KEY")

BASE_URL = "https://api.massive.com"


def _massive_get(path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Helper to call Massive's REST API with the API key and handle errors.
    """
    if not API_KEY:
        raise RuntimeError(
            "MASSIVE_API_KEY (or POLYGON_API_KEY) is not set. Massive provider cannot be used."
        )

    full_params: Dict[str, Any] = dict(params or {})
    full_params["apiKey"] = API_KEY

    url = f"{BASE_URL}{path}"
    headers = {"accept": "application/json"}

    response = requests.get(url, headers=headers, params=full_params, timeout=10)
    response.raise_for_status()
    return response.json()


def _fetch_side(
    ticker: str, expiration_date: str, contract_type: str, limit: int = 200
) -> List[OptionContract]:
    """
    Fetch one side (CALL or PUT) of the Massive option chain
    and normalize it into a list[OptionContract].
    """
    params = {
        "contract_type": contract_type,       # "put" or "call"
        "expiration_date": expiration_date,   # "YYYY-MM-DD"
        "limit": limit,
        "sort": "strike_price",
        "order": "asc",
    }

    path = f"/v3/snapshot/options/{ticker.upper()}"
    data = _massive_get(path, params)

    results: List[OptionContract] = []

    for opt in data.get("results", []):
        details = opt.get("details") or {}
        underlying_asset = opt.get("underlying_asset") or {}

        underlying = (
            underlying_asset.get("ticker")
            or details.get("underlying_ticker")
            or ticker.upper()
        )
        option_ticker = details.get("ticker") or details.get("symbol")

        expiration = details.get("expiration_date") or expiration_date
        try:
            expiry = datetime.strptime(expiration, "%Y-%m-%d").date()
        except Exception:
            expiry = datetime.strptime(expiration_date, "%Y-%m-%d").date()

        strike = details.get("strike_price")

        day = opt.get("day") or {}
        volume = day.get("volume") or day.get("v")
        oi = opt.get("open_interest")

        greeks = opt.get("greeks") or {}
        delta = greeks.get("delta")
        gamma = greeks.get("gamma")
        theta = greeks.get("theta")
        vega = greeks.get("vega")

        iv = opt.get("implied_volatility") or greeks.get("iv")

        last_quote = opt.get("last_quote") or {}
        bid = last_quote.get("bid") or last_quote.get("bid_price")
        ask = last_quote.get("ask") or last_quote.get("ask_price")

        last_trade = opt.get("last_trade") or {}
        last = last_trade.get("price") or last_trade.get("p")

        greeks_source = "vendor" if (delta is not None and iv is not None) else "none"

        if strike is None:
            continue

        results.append(
            OptionContract(
                underlying=underlying,
                option_ticker=option_ticker,
                option_type=contract_type,
                expiry=expiry,
                strike=float(strike),
                bid=bid,
                ask=ask,
                last=last,
                volume=volume,
                open_interest=oi,
                delta=delta,
                gamma=gamma,
                theta=theta,
                vega=vega,
                implied_vol=iv,
                greeks_source=greeks_source,
            )
        )

    return results


def get_option_chain(ticker: str, expiry: str) -> List[OptionContract]:
    """
    Public provider API: fetch full chain (calls + puts) for one expiration
    from Massive and return it in normalized OptionContract format.
    """
    calls = _fetch_side(ticker, expiry, "call")
    puts = _fetch_side(ticker, expiry, "put")
    return calls + puts
