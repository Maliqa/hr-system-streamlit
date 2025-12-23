import requests

API_BASE = "http://127.0.0.1:8000"

_session = requests.Session()

def api_get(path, **kwargs):
    return _session.get(f"{API_BASE}{path}", **kwargs)

def api_post(path, **kwargs):
    return _session.post(f"{API_BASE}{path}", **kwargs)
