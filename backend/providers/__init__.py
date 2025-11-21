import os
from datetime import date
from pathlib import Path
from typing import Optional, Callable, List, Tuple

from dotenv import load_dotenv
from pydantic import BaseModel


class OptionContract(BaseModel):
    """
    Normalized internal representation of an option contract,
    regardless of which external data provider we use.
    """

    underlying: str
    option_ticker: str
    option_type: str  # "call" or "put"

    expiry: date
    strike: float

    bid: Optional[float] = None
    ask: Optional[float] = None
    last: Optional[float] = None

    volume: Optional[int] = None
    open_interest: Optional[int] = None

    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    implied_vol: Optional[float] = None

    greeks_source: str = "none"  # "vendor" | "model" | "none"


def resolve_get_option_chain() -> Tuple[Callable[[str, str], List[OptionContract]], str]:
    """
    Decide which provider to use based on DATA_PROVIDER env var and
    return (get_option_chain_function, provider_mode).

    Allowed values:
      - "tradier_sandbox"
      - "tradier_production"
      - "massive"
      - "yahoo"
    """
    base_dir = Path(__file__).resolve().parent.parent
    load_dotenv(base_dir / "provider.env")

    provider_mode = os.getenv("DATA_PROVIDER", "tradier_sandbox").lower()

    if provider_mode.startswith("tradier"):
        from .tradier_provider import get_option_chain
    elif provider_mode == "massive":
        from .massive_provider import get_option_chain
    elif provider_mode == "yahoo":
        from .yahoo_provider import get_option_chain
    else:
        raise RuntimeError(
            f"Unknown DATA_PROVIDER={provider_mode}. "
            "Expected one of: tradier_sandbox, tradier_production, massive, yahoo."
        )

    return get_option_chain, provider_mode
