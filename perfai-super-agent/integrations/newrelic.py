"""Read-only New Relic NerdGraph connector."""
from __future__ import annotations
import re
import time
import requests

class NewRelicError(RuntimeError):
    pass

class NewRelicClient:
    ENDPOINTS = {"US": "https://api.newrelic.com/graphql", "EU": "https://api.eu.newrelic.com/graphql"}

    def __init__(self, api_key: str, region: str = "US", timeout: int = 30,
                 session: requests.Session | None = None):
        region = region.upper()
        if region not in self.ENDPOINTS:
            raise ValueError("New Relic region must be US or EU")
        if not api_key or not api_key.strip():
            raise ValueError("New Relic User API key is required")
        self._api_key = api_key.strip()
        self.region = region
        self.endpoint = self.ENDPOINTS[region]
        self.timeout = timeout
        self.session = session or requests.Session()

    def _graphql(self, query: str, variables: dict | None = None) -> dict:
        for attempt in range(3):
            try:
                response = self.session.post(
                    self.endpoint,
                    headers={"API-Key": self._api_key, "Content-Type": "application/json"},
                    json={"query": query, "variables": variables or {}}, timeout=self.timeout)
                if (response.status_code == 429 or response.status_code >= 500) and attempt < 2:
                    time.sleep(min(2 ** attempt, 4))
                    continue
                response.raise_for_status()
                payload = response.json()
            except requests.RequestException as exc:
                raise NewRelicError(f"New Relic request failed: {exc}") from exc
            except ValueError as exc:
                raise NewRelicError("New Relic returned invalid JSON") from exc
            if payload.get("errors"):
                raise NewRelicError("; ".join(x.get("message", "GraphQL error") for x in payload["errors"]))
            return payload.get("data") or {}
        raise NewRelicError("New Relic request failed after retries")

    def test_connection(self) -> dict:
        data = self._graphql("query PerfAIPing { actor { user { email } } }")
        actor = data.get("actor") or {}
        return {"connected": bool(actor), "region": self.region,
                "user": (actor.get("user") or {}).get("email")}

    def discover_entities(self, search_term: str = "", limit: int = 50) -> list[dict]:
        term = search_term.strip().replace('"', r'\"')
        expression = f'name LIKE "{term}%"' if term else "domain IN ('APM','INFRA','BROWSER','MOBILE')"
        query = """query PerfAIEntitySearch($search: String!) {
          actor { entitySearch(query: $search) {
            results { entities { guid name type domain reporting } }
          } }
        }"""
        data = self._graphql(query, {"search": expression})
        entities = (((data.get("actor") or {}).get("entitySearch") or {})
                    .get("results") or {}).get("entities") or []
        return entities[:max(1, min(int(limit), 200))]

    def discover_metric_keys(self, account_id: int, entity_guid: str,
                             since: str = "1 hour ago") -> list[dict]:
        guid = self._safe_guid(entity_guid)
        query = """query PerfAIMetricKeys($accountId: Int!, $nrql: Nrql!) {
          actor { account(id: $accountId) { nrql(query: $nrql) { results } } }
        }"""
        nrql = f"FROM Metric SELECT keyset() WHERE entity.guid = '{guid}' SINCE {self._safe_since(since)}"
        data = self._graphql(query, {"accountId": int(account_id), "nrql": nrql})
        account = (data.get("actor") or {}).get("account") or {}
        return (account.get("nrql") or {}).get("results") or []

    def run_nrql(self, account_id: int, nrql: str) -> list[dict]:
        normalized = nrql.strip()
        if not re.match(r"(?is)^FROM\s+[A-Za-z_][A-Za-z0-9_]*\s+SELECT\s+", normalized):
            raise ValueError("Only read-only NRQL FROM ... SELECT queries are allowed")
        if ";" in normalized or re.search(r"(?i)\b(INSERT|DELETE|UPDATE|DROP|CREATE|ALTER)\b", normalized):
            raise ValueError("Only a single read-only NRQL query is allowed")
        query = """query PerfAINRQL($accountId: Int!, $nrql: Nrql!) {
          actor { account(id: $accountId) { nrql(query: $nrql) { results } } }
        }"""
        data = self._graphql(query, {"accountId": int(account_id), "nrql": normalized})
        account = (data.get("actor") or {}).get("account") or {}
        return (account.get("nrql") or {}).get("results") or []

    @staticmethod
    def _safe_guid(value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_-]{4,160}", value or ""):
            raise ValueError("Invalid New Relic entity GUID format")
        return value

    @staticmethod
    def _safe_since(value: str) -> str:
        if not re.fullmatch(r"(?:\d+\s+(?:minutes?|hours?|days?)\s+ago|\d{4}-\d{2}-\d{2}(?:T[0-9:.+-]+Z?)?)", value.strip(), re.I):
            raise ValueError("Use relative time such as '60 minutes ago' or an ISO date/time")
        return value.strip()
