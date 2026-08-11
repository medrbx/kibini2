"""
Client pour l'API Opteio (comptage de fréquentation par capteurs).
Intégré depuis dev/opteio-export/export_opteio_api.py.

API documentée (Swagger) : https://api.opteio.com/api-docs/
  - POST /users/authenticate        -> token JWT (body {user_login, user_pass})
  - GET  /users/opteio-associations -> liste des sites de l'utilisateur
  - GET  /sensor-data/period        -> comptages d'un site (max 100 jours / requête)

Identifiants lus depuis kibini_conf.yml (section 'opteio: login/password'),
pas depuis un fichier .env comme dans l'outil d'origine.
"""
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import timedelta

from kiblib.utils.conf import Config

API_BASE = "https://api.opteio.com"
MAX_DAYS_PER_REQUEST = 100  # limite imposée par l'API sur /sensor-data/period
DATASETS = ["inout", "presence_data", "worked_hours", "site_data", "parasitic_counts"]


def daterange_chunks(start, end, max_days=MAX_DAYS_PER_REQUEST):
    """Découpe [start, end] en tranches <= max_days (limite API)."""
    cur = start
    while cur <= end:
        chunk_end = min(cur + timedelta(days=max_days - 1), end)
        yield cur, chunk_end
        cur = chunk_end + timedelta(days=1)


def enrich_inout(row):
    """Ajoute une colonne datetime ISO pratique aux comptages minute (jour/heure/minute)."""
    if {"jour", "heure", "minute"} <= row.keys():
        try:
            row = {
                "datetime": f"{row['jour']} {int(row['heure']):02d}:{int(row['minute']):02d}",
                **row,
            }
        except (TypeError, ValueError):
            pass
    return row


def site_label(site):
    for k in ("site-name", "site_name", "name", "label", "nom", "site"):
        if site.get(k):
            return str(site[k])
    return "?"


def site_id_of(site):
    for k in ("site-id", "site_id", "id", "siteId", "id_site"):
        if site.get(k) is not None:
            return site[k]
    return None


class OpteioClient:
    def __init__(self, login=None, password=None):
        if login is None or password is None:
            conf = Config().get_config_opteio()
            login = login or conf["login"]
            password = password or conf["password"]
        self.login = login
        self.password = password
        self._token = None

    @property
    def token(self):
        if self._token is None:
            self._token = self._authenticate()
        return self._token

    def _api_request(self, method, path, params=None, body=None, auth=True):
        url = f"{API_BASE}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)

        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        if auth:
            headers["Authorization"] = f"Bearer {self.token}"

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode("utf-8")
                auth_header = resp.headers.get("Authorization")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            raise RuntimeError(f"API {method} {path} -> HTTP {exc.code}\n{detail[:500]}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Connexion impossible à l'API Opteio : {exc.reason}") from exc

        parsed = None
        if raw.strip():
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = raw.strip()
        return parsed, auth_header

    def _authenticate(self):
        """Renvoie le token JWT. S'adapte au format de réponse (string / JSON / header)."""
        parsed, auth_header = self._api_request(
            "POST", "/users/authenticate",
            body={"user_login": self.login, "user_pass": self.password},
            auth=False,
        )

        if isinstance(parsed, str) and parsed:
            return parsed.replace("Bearer ", "").strip()

        if isinstance(parsed, dict):
            for key in ("token", "access_token", "accessToken", "jwt", "bearer", "id_token", "data"):
                val = parsed.get(key)
                if isinstance(val, str) and val:
                    return val.replace("Bearer ", "").strip()
                if isinstance(val, dict):
                    for k2 in ("token", "access_token", "accessToken", "jwt"):
                        if isinstance(val.get(k2), str):
                            return val[k2].replace("Bearer ", "").strip()

        if auth_header:
            return auth_header.replace("Bearer ", "").strip()

        raise RuntimeError(
            "Connexion réussie mais token Opteio introuvable dans la réponse "
            f"(réponse reçue : {json.dumps(parsed)[:300]})"
        )

    def get_sites(self):
        parsed, _ = self._api_request("GET", "/users/opteio-associations")
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            for key in ("data", "sites", "associations", "results"):
                if isinstance(parsed.get(key), list):
                    return parsed[key]
        return [parsed] if parsed else []

    def fetch_period(self, site_id, start, end, datasets=None):
        """
        Récupère un ou plusieurs jeux de données du site sur la période
        (la limite de 100 jours/requête de l'API est gérée automatiquement).
        datasets=None -> tous les jeux disponibles.
        """
        result = {}
        for c_start, c_end in daterange_chunks(start, end):
            parsed, _ = self._api_request(
                "GET", "/sensor-data/period",
                params={"site_id": site_id, "start": c_start.isoformat(), "end": c_end.isoformat()},
            )
            if isinstance(parsed, dict):
                for key, value in parsed.items():
                    if datasets and key not in datasets:
                        continue
                    if isinstance(value, list):
                        result.setdefault(key, []).extend(value)
            elif isinstance(parsed, list):
                result.setdefault("data", []).extend(parsed)
        return result
