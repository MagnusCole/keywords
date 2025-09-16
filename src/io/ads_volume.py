# mypy: ignore-errors
import json
import logging
import os
import time
from pathlib import Path

# Import quota management and environment config
from .ads_quota import check_quota_before_request, record_quota_usage
from .env_config import get_google_ads_credentials, load_dotenv_file


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
        self._cache: dict[str, dict] = self._load_cache()
        self._ttl_days: int = int(os.getenv("ADS_CACHE_TTL_DAYS", "0") or 0)
        # Load environment configuration
        load_dotenv_file()

        # Lazy import of google-ads
        self.googleads = None
        try:
            from google.ads.googleads.client import GoogleAdsClient

            self.GoogleAdsClient = GoogleAdsClient
            self.googleads = True
        except Exception:
            self.logger.warning("google-ads library not available; Ads volume disabled")

        # Get credentials from environment config
        creds = get_google_ads_credentials()
        self.developer_token = creds["developer_token"]
        self.client_id = creds["client_id"]
        self.client_secret = creds["client_secret"]
        self.refresh_token = creds["refresh_token"]
        self.customer_id = creds["customer_id"]
        self.login_customer_id = creds["login_customer_id"]

    def _load_cache(self) -> dict:
        try:
            if self.cache_file.exists():
                data = json.loads(self.cache_file.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    now = int(time.time())
                    # migrate legacy int cache to new schema
                    migrated: dict[str, dict] = {}
                    for k, v in data.items():
                        if isinstance(v, int):
                            migrated[k] = {"v": int(v), "ts": now}
                        elif isinstance(v, dict) and "v" in v:
                            # ensure ts exists
                            migrated[k] = {"v": int(v.get("v", 0)), "ts": int(v.get("ts", now))}
                        else:
                            # skip invalid
                            continue
                    return migrated
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

    def _get_cached(self, key: str) -> int | None:
        item = self._cache.get(key)
        if not item:
            return None
        if isinstance(item, int):
            return int(item)
        # TTL enforcement
        if self._ttl_days > 0:
            ttl_sec = self._ttl_days * 86400
            if int(time.time()) - int(item.get("ts", 0)) > ttl_sec:
                # expired
                self._cache.pop(key, None)
                return None
        return int(item.get("v", 0) or 0)

    def _set_cache(self, key: str, value: int) -> None:
        self._cache[key] = {"v": int(value), "ts": int(time.time())}

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

    def get_volumes(  # noqa: C901
        self, keywords: list[str], geo: str = "PE", language: str = "es"
    ) -> dict[str, int]:
        if not self.googleads or not self._have_credentials():
            self.logger.warning("Google Ads not configured; returning empty volume mapping")
            return {}

        # Guard misconfigured customer_id (must be digits with dashes removed)
        try:
            cid = (self.customer_id or "").replace("-", "")
            if not cid.isdigit() or len(cid) < 8:
                self.logger.warning("Invalid GOOGLE_ADS_CUSTOMER_ID; skipping Ads volume")
                return {}
        except Exception:
            return {}

        # Filter cached
        to_query = []
        result: dict[str, int] = {}
        for kw in keywords:
            k = f"{kw}|{geo}|{language}"
            cached = self._get_cached(k)
            if cached is None:
                to_query.append(kw)
            else:
                result[kw] = cached
        if not to_query:
            return result

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

            # Batch in chunks with quota management
            batch_size = 20  # Smaller batches for better quota control
            for i in range(0, len(to_query), batch_size):
                batch = to_query[i : i + batch_size]

                # Check quota before making request
                if not check_quota_before_request(operation_count=1):
                    self.logger.warning("Google Ads quota exhausted, skipping remaining keywords")
                    break

                request = client.get_type("GenerateKeywordIdeasRequest")
                request.customer_id = self.customer_id  # type: ignore
                request.language = language_constant  # type: ignore
                request.geo_target_constants.extend(location_ids)  # type: ignore
                request.include_adult_keywords = False  # type: ignore
                request.keyword_plan_network = (  # type: ignore
                    client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH  # type: ignore
                )
                request.keyword_seed.keywords.extend(batch)  # type: ignore

                # Simple retry with backoff
                retries = 0
                backoff = 1.0
                request_successful = False
                response = None  # Initialize response variable

                while retries <= 3:
                    try:
                        self.logger.info(
                            f"Fetching volume data for batch {i//batch_size + 1} ({len(batch)} keywords)"
                        )
                        response = idea_svc.generate_keyword_ideas(request=request)

                        # Record successful quota usage
                        record_quota_usage(operation_count=1)
                        request_successful = True
                        break

                    except Exception as e:
                        retries += 1
                        if retries > 3:
                            self.logger.error(
                                f"Failed to fetch volume data after {retries} retries: {e}"
                            )
                            break

                        self.logger.warning(f"API request failed (retry {retries}/3): {e}")
                        time.sleep(backoff)
                        backoff *= 2

                # Only process response if request was successful
                if request_successful and response is not None:
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
                            self._set_cache(key, avg)

                # Rate limiting between batches
                time.sleep(2)  # 2 second delay between batches

            # Save cache and build mapping
            self._save_cache()
            # Merge cached new results
            for kw in to_query:
                k = f"{kw}|{geo}|{language}"
                v = self._get_cached(k)
                if v:
                    result[kw] = v
            return result

        except Exception as e:
            self.logger.error(f"Google Ads volume fetch failed: {e}")
            return {}
