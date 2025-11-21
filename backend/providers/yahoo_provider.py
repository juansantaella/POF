from datetime import datetime
from typing import List

import yfinance as yf

from . import OptionContract


def get_option_chain(ticker: str, expiry: str) -> List[OptionContract]:
    """
    Fetch and normalize Yahoo Finance option chain using yfinance.

    - expiry must be "YYYY-MM-DD" and match one of ts.options.
    - Requires yfinance and pandas as dependencies.
    """

    ts = yf.Ticker(ticker)

    if expiry not in ts.options:
        raise ValueError(f"Expiration {expiry} not in Yahoo options list for {ticker}")

    chain = ts.option_chain(expiry)
    calls_df = chain.calls
    puts_df = chain.puts

    results: List[OptionContract] = []
    expiry_dt = datetime.strptime(expiry, "%Y-%m-%d").date()

    def _maybe_int(x):
        if x != x:  # NaN
            return None
        try:
            return int(x)
        except Exception:
            return None

    # Calls
    for _, row in calls_df.iterrows():
        iv = row.get("impliedVolatility")
        results.append(
            OptionContract(
                underlying=ticker.upper(),
                option_ticker=str(row.get("contractSymbol")),
                option_type="call",
                expiry=expiry_dt,
                strike=float(row.get("strike")),
                bid=row.get("bid"),
                ask=row.get("ask"),
                last=row.get("lastPrice"),
                volume=_maybe_int(row.get("volume")),
                open_interest=_maybe_int(row.get("openInterest")),
                implied_vol=iv,
                greeks_source="vendor" if iv == iv else "none",
            )
        )

    # Puts
    for _, row in puts_df.iterrows():
        iv = row.get("impliedVolatility")
        results.append(
            OptionContract(
                underlying=ticker.upper(),
                option_ticker=str(row.get("contractSymbol")),
                option_type="put",
                expiry=expiry_dt,
                strike=float(row.get("strike")),
                bid=row.get("bid"),
                ask=row.get("ask"),
                last=row.get("lastPrice"),
                volume=_maybe_int(row.get("volume")),
                open_interest=_maybe_int(row.get("openInterest")),
                implied_vol=iv,
                greeks_source="vendor" if iv == iv else "none",
            )
        )

    return results
