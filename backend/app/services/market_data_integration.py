"""Market data integration placeholders for analytics benchmarks."""

from typing import Optional
from app.services.market_data_service import MarketDataService


class MarketDataIntegration:
    def __init__(self, market_data_service: MarketDataService | None = None):
        self.market_data_service = market_data_service

    def _get_market_payload(self, property_id: int) -> Optional[dict]:
        if not self.market_data_service:
            return None
        try:
            return self.market_data_service.get_market_intelligence(property_id)
        except Exception:
            return None

    @staticmethod
    def _extract_data(payload: Optional[dict], key: str) -> Optional[dict]:
        if not payload:
            return None
        value = payload.get(key)
        if isinstance(value, dict) and "data" in value:
            return value.get("data") or {}
        return value

    def get_market_rent_per_sf(self, property_id: int) -> Optional[float]:
        data = self._get_market_payload(property_id)
        if not data:
            return None
        comparables = self._extract_data(data, "comparables") or {}
        estimate = comparables.get("market_rent_estimate", {})
        if isinstance(estimate, dict):
            return estimate.get("mean_rent_psf") or estimate.get("median_rent_psf")
        return None

    def get_market_opex_per_sf(self, property_id: int) -> Optional[float]:
        data = self._get_market_payload(property_id)
        if not data:
            return None
        competitive = self._extract_data(data, "competitive_analysis") or {}
        return competitive.get("submarket_avg_opex_psf")

    def get_market_occupancy(self, property_id: int) -> Optional[float]:
        data = self._get_market_payload(property_id)
        if not data:
            return None
        competitive = self._extract_data(data, "competitive_analysis") or {}
        value = competitive.get("submarket_avg_occupancy")
        if value is not None:
            return float(value)
        comparables = self._extract_data(data, "comparables") or {}
        comps = comparables.get("comparables", []) if isinstance(comparables, dict) else []
        if comps:
            values = [c.get("occupancy_rate") for c in comps if c.get("occupancy_rate") is not None]
            if values:
                return float(sum(values) / len(values)) / 100.0 if max(values) > 1 else float(sum(values) / len(values))
        return None

    def get_market_cap_rate(self, property_id: int) -> Optional[float]:
        data = self._get_market_payload(property_id)
        if not data:
            return None
        competitive = self._extract_data(data, "competitive_analysis") or {}
        value = competitive.get("submarket_avg_cap_rate")
        if value is not None:
            return float(value)
        comparables = self._extract_data(data, "comparables") or {}
        comps = comparables.get("comparables", []) if isinstance(comparables, dict) else []
        if comps:
            values = [c.get("cap_rate") for c in comps if c.get("cap_rate") is not None]
            if values:
                avg = float(sum(values) / len(values))
                return avg / 100.0 if avg > 1 else avg
        return None
