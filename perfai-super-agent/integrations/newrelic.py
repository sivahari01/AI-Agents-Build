import requests

class NewRelicError(RuntimeError): pass

class NewRelicClient:
    def __init__(self,api_key,account_id,region="US",timeout=30):
        if not api_key: raise NewRelicError("New Relic User API key is required.")
        if not str(account_id).isdigit(): raise NewRelicError("Account ID must be numeric.")
        region=region.upper()
        if region not in ("US","EU"): raise NewRelicError("Region must be US or EU.")
        self.account_id=int(account_id); self.timeout=timeout
        self.url="https://api.newrelic.com/graphql" if region=="US" else "https://api.eu.newrelic.com/graphql"
        self.session=requests.Session()
        self.session.headers.update({"API-Key":api_key,"Content-Type":"application/json"})
    def _query(self,query):
        try:
            response=self.session.post(self.url,json={"query":query},timeout=self.timeout)
            if response.status_code in (401,403): raise NewRelicError("Authentication or permission denied.")
            if response.status_code==429: raise NewRelicError("New Relic rate limit reached.")
            response.raise_for_status(); payload=response.json()
        except requests.RequestException as exc: raise NewRelicError(f"New Relic request failed: {exc}") from exc
        if payload.get("errors"): raise NewRelicError("; ".join(x.get("message","GraphQL error") for x in payload["errors"]))
        return payload.get("data",{})
    def test_connection(self):
        data=self._query("{ actor { user { id } } }")
        user=data.get("actor",{}).get("user")
        if not user: raise NewRelicError("No authenticated user returned.")
        return {"connected":True,"user_id":user.get("id"),"account_id":self.account_id}
    def discover_entities(self,name="",limit=25):
        term=name.replace("\\","").replace('"','\\"').replace("\n"," ")
        q=f'''{{ actor {{ entitySearch(query: "name LIKE \"%{term}%\"") {{ results {{ entities {{ guid name type domain accountId }} }} }} }} }}'''
        return self._query(q).get("actor",{}).get("entitySearch",{}).get("results",{}).get("entities",[])[:limit]
    def run_nrql(self,nrql):
        if not nrql.strip().lower().startswith("select "): raise NewRelicError("Only SELECT NRQL is allowed.")
        if any(x in nrql.lower() for x in (" delete "," update "," insert "," drop "," create "," alter ")):
            raise NewRelicError("Mutating query syntax is not allowed.")
        safe=nrql.replace("\\","\\\\").replace('"','\\"').replace("\n"," ")
        q=f'''{{ actor {{ account(id: {self.account_id}) {{ nrql(query: "{safe}") {{ results }} }} }} }}'''
        return self._query(q).get("actor",{}).get("account",{}).get("nrql",{}).get("results",[])
