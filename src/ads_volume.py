# mypy: ignore-errors
import json
import logging
import os
from pathlib import Path


class GoogleAdsVolumeProvider:
    """Fetches average monthly searches from Google Ads Keyword Planner.

    - Requires GOOGLE ADS credentials via environment variables (see .env.example).
    - Gracefully returns {} when credentials or library are missing.
    - Caches results to avoid repeated calls (cache/ads_volume.json).
    """

    def __init__(self, cache_dir: str = "cache") -> None:
        self.logger = logging.getLogger(__name__)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_file = self.cache_dir / "ads_volume.json"
        self._cache: dict[str, int] = self._load_cache()

        # Lazy import of google-ads
        self.googleads = None
        try:
            from google.ads.googleads.client import GoogleAdsClient

            self.GoogleAdsClient = GoogleAdsClient
            self.googleads = True
        except Exception:
            self.logger.warning("google-ads library not available; Ads volume disabled")

        # Credentials from env
        self.developer_token = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN")
        self.client_id = os.getenv("GOOGLE_ADS_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_ADS_CLIENT_SECRET")
        self.refresh_token = os.getenv("GOOGLE_ADS_REFRESH_TOKEN")
        self.customer_id = os.getenv("GOOGLE_ADS_CUSTOMER_ID")
        self.login_customer_id = os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID")

    def _load_cache(self) -> dict[str, int]:
        try:
            if self.cache_file.exists():
                return json.loads(self.cache_file.read_text(encoding="utf-8"))
        except Exception as e:
            self.logger.warning(f"Failed to load Ads cache: {e}")
        return {}

    def _save_cache(self) -> None:
        try:
            self.cache_file.write_text(
                json.dumps(self._cache, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as e:
            self.logger.warning(f"Failed to save Ads cache: {e}")

    def _have_credentials(self) -> bool:
        return all(
            [
                self.developer_token,
                self.client_id,
                self.client_secret,
                self.refresh_token,
                self.customer_id,
            ]
        )

    def _build_client(self):
        # Build client from dict config; avoids external yaml
        config = {
            "developer_token": self.developer_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "login_customer_id": self.login_customer_id,
        }
        return self.GoogleAdsClient.load_from_dict(config)

    def _resolve_geo_ids(self, client, geo: str) -> list[str]:
        # Try SuggestGeoTargetConstants for the country code/name
        try:
            svc = client.get_service("GeoTargetConstantService")
            request = client.get_type("SuggestGeoTargetConstantsRequest")
            request.locale = "es"
            request.country_code = geo.upper()
            response = svc.suggest_geo_target_constants(request=request)
            ids = []
            for res in response.geo_target_constant_suggestions:
                const = res.geo_target_constant
                if const.resource_name:
                    ids.append(const.resource_name)
            return ids
        except Exception as e:
            self.logger.warning(f"Failed to resolve geo IDs for {geo}: {e}")
            return []

    def _resolve_language_constant(self, client, language: str) -> str | None:
        # Common mappings fallback
        lang = language.lower()
        mapping = {"es": "languageConstants/1003", "en": "languageConstants/1000"}
        if lang in mapping:
            return mapping[lang]
        # Could lookup via Google Ads API if needed
        return mapping.get("es")

    def get_volumes(
        self, keywords: list[str], geo: str = "PE", language: str = "es"
    ) -> dict[str, int]:
        if not self.googleads or not self._have_credentials():
            self.logger.warning("Google Ads not configured; returning empty volume mapping")
            return {}

        # Filter cached
        to_query = [kw for kw in keywords if f"{kw}|{geo}|{language}" not in self._cache]
        if not to_query:
            return {kw: int(self._cache.get(f"{kw}|{geo}|{language}", 0)) for kw in keywords}

        try:
            client = self._build_client()
            idea_svc = client.get_service("KeywordPlanIdeaService")

            # Locations
            location_ids = self._resolve_geo_ids(client, geo)
            if not location_ids:
                self.logger.warning(f"No geo IDs resolved for {geo}; skipping Ads volume")
                return {}

            # Language
            language_constant = self._resolve_language_constant(client, language)
            if not language_constant:
                self.logger.warning(f"No language constant for {language}; skipping Ads volume")
                return {}

            # Batch in chunks to avoid overloading
            batch_size = 700
            for i in range(0, len(to_query), batch_size):
                batch = to_query[i : i + batch_size]

                request = client.get_type("GenerateKeywordIdeasRequest")
                request.customer_id = self.customer_id  # type: ignore
                request.language = language_constant  # type: ignore
                request.geo_target_constants.extend(location_ids)  # type: ignore
                request.include_adult_keywords = False  # type: ignore
                request.keyword_plan_network = (  # type: ignore
                    client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH  # type: ignore
                )
                request.keyword_seed.keywords.extend(batch)  # type: ignore

                response = idea_svc.generate_keyword_ideas(request=request)

                for idea in response:
                    text = idea.text
                    metrics = idea.keyword_idea_metrics
                    avg = (
                        int(metrics.avg_monthly_searches)
                        if metrics and metrics.avg_monthly_searches
                        else 0
                    )
                    key = f"{text}|{geo}|{language}"
                    # Cache only non-zero values
                    if avg > 0:
                        self._cache[key] = avg

            # Save cache and build mapping
            self._save_cache()
            return {kw: int(self._cache.get(f"{kw}|{geo}|{language}", 0)) for kw in keywords}

        except Exception as e:
            self.logger.error(f"Google Ads volume fetch failed: {e}")
            return {}
