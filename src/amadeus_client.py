from __future__ import annotations

from typing import Any, Dict, List, Optional
from amadeus import Client, ResponseError  # type: ignore

from .config import get_settings


class AmadeusService:
    def __init__(self) -> None:
        settings = get_settings()
        self.client = Client(
            client_id=settings.amadeus_api_key,
            client_secret=settings.amadeus_api_secret,
            hostname="test" if settings.amadeus_env.lower() == "test" else "production",
        )

    def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None,
        adults: int = 1,
        currency: Optional[str] = None,
        non_stop: Optional[bool] = None,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {
            "originLocationCode": origin.upper(),
            "destinationLocationCode": destination.upper(),
            "departureDate": departure_date,
            "adults": str(max(1, adults)),
            "max": str(max_results),
        }

        if return_date:
            params["returnDate"] = return_date
        if currency:
            params["currencyCode"] = currency
        if non_stop is not None:
            params["nonStop"] = "true" if non_stop else "false"

        try:
            response = self.client.shopping.flight_offers_search.get(**params)
            data = response.data or []
        except ResponseError as e:  # pragma: no cover - network/credentials errors
            raise RuntimeError(f"Amadeus API error: {e}") from e

        return data


