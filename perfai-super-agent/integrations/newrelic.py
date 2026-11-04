from __future__ import annotations
import requests
from datetime import datetime, timezone
from typing import Any

class NewRelicError(RuntimeError): pass

class NewRelicClient:
    """Read-only New Relic NerdGraph client. Uses a User API key."""
    def __init__(self, api_key: str, account_id: str | int, region="US", timeout=30):
        if not api_key: raise NewRelicError("A New Relic User API key is required.")
        if not str(account_id).isdigit(): raise NewRelicError("New Relic account ID must be numeric.")
        region=region.upper()
        if region not in {"US","EU"}: raise NewRelicError("Region must be US or EU.")
        self.url="https://api.newrelic.com/graphql" if region=="US" else "https://api.eu.newrelic.com/graphql"
        self.account_id=int(account_id); self.timeout=timeout
        self.session=requests.Session()
        self.session.headers.update({"API-Key":api_key,"Content-Type":"application/json","Accept":"application/json"})
    def _graphql(self, query: str) -> dict[str,Any]:
        try:
            response=self.session.post(self.url,json={"query":query},timeout=self.timeout)
            if response.status_code in (401,403): raise NewRelicError("New Relic authentication/permission failed. Verify the User API key and account access.")
            if response.status_code==429: raise NewRelicError("New Relic rate limit reached. Wait before retrying.")
            response.raise_for_status()
            payload=response.json()
        except requests.RequestException as exc: raise NewRelicError(f"New Relic request failed: {exc}") from exc
        if payload.get("errors"): raise NewRelicError("; ".join(e.get("message","GraphQL error") for e in payload["errors"]))
        return payload.get("data",{})
    def test_connection(self) -> dict:
        data=self._graphql("{ actor { user { id } } }")
        user=data.get("actor",{}).get("user")
        if not user: raise NewRelicError("New Relic did not return an authenticated user.")
        return {"connected":True,"user_id":user.get("id"),"account_id":self.account_id,"region":self.url}
    def discover_entities(self, search_text: str, limit=25) -> list[dict]:
        safe=search_text.replace("\\","\\\\").replace('"','\\"').replace("\n"," ")
        query=f'''{{ actor {{ entitySearch(query: "name LIKE \"%{safe}%\"") {{ results {{ entities {{ guid name type domain accountId }} }} }} }} }}'''
        data=self._graphql(query)
        return data.get("actor",{}).get("entitySearch",{}).get("results",{}).get("entities",[])[:limit]
    def run_nrql(self, nrql: str) -> list[dict]:
        if not nrql.strip().lower().startswith("select "):
            raise NewRelicError("Only read-only SELECT NRQL queries are allowed.")
        forbidden=("insert ","update ","delete ","drop ","create ","alter ")
        if any(token in nrql.lower() for token in forbidden):
            raise NewRelicError("Mutating query syntax is not allowed.")
        escaped=nrql.replace("\\","\\\\").replace('"','\\"').replace("\n"," ")
        query=f'''{{ actor {{ account(id: {self.account_id}) {{ nrql(query: "{escaped}") {{ results }} }} }} }}'''
        data=self._graphql(query)
        return data.get("actor",{}).get("account",{}).get("nrql",{}).get("results",[])
    @staticmethod
    def results_to_timeseries(results: list[dict]) -> list[dict]:
        rows=[]
        for item in results:
            row=dict(item)
            stamp=row.pop("beginTimeSeconds",None) or row.pop("timestamp",None)
            if stamp is not None:
                try: row["timestamp"]=datetime.fromtimestamp(float(stamp),tz=timezone.utc).isoformat()
                except (ValueError,TypeError,OverflowError): continue
            elif row.get("beginTime") is not None:
                row["timestamp"]=row.pop("beginTime")
            if "timestamp" in row: rows.append(row)
        return rows
