import os
import requests

try:
    from dados_gov_sdk import ApiClient, Settings
except Exception:
    ApiClient = None
    Settings = None

def build_dados_gov_client():
    if ApiClient is None or Settings is None:
        return None
    api_key = os.getenv("DADOS_GOV_API_KEY", "")
    settings = Settings(api_key=api_key) if api_key else Settings()
    return ApiClient(settings=settings)

def transparency_headers():
    key = os.getenv("PORTAL_TRANSPARENCIA_API_KEY", "")
    hdr = {"Accept": "application/json"}
    if key:
        hdr["chave-api-dados"] = key
    return hdr

def transparencia_get(path, params=None):
    base = "https://www.portaldatransparencia.gov.br"
    url = f"{base}{path}"
    r = requests.get(url, headers=transparency_headers(), params=params or {}, timeout=60)
    r.raise_for_status()
    return r.json()

def brasilapi_get(endpoint, params=None):
    base = os.getenv("BRASILAPI_BASE", "https://brasilapi.com.br/api")
    url = f"{base.rstrip('/')}/{endpoint.lstrip('/')}"
    r = requests.get(url, params=params or {}, timeout=30)
    r.raise_for_status()
    return r.json()
