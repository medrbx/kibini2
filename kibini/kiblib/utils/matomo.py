"""
Client pour l'API Matomo (statistiques de fréquentation web).

Remplace l'export CSV manuel ("Visiteurs > Aperçu") utilisé jusqu'ici par
data_web_interne.py / data_web_externe.py : les mêmes métriques (Visites,
Vues, Utilisateurs, Taux de conversion) sont récupérées directement via
l'API Matomo (modules VisitsSummary, Actions, Goals).

API documentée : https://developer.matomo.org/api-reference/reporting-api

Identifiants lus depuis kibini_conf.yml (section 'matomo: base/token_auth'),
via kiblib.utils.conf.Config.get_config_matomo().
"""
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import timedelta

from kiblib.utils.conf import Config


def _parse_percent(value):
    """Convertit '12.5%' (chaîne renvoyée par l'API Goals) en float. Renvoie
    None si la valeur est vide/absente."""
    if value is None or value == "":
        return None
    if isinstance(value, str):
        value = value.replace("%", "").replace(",", ".").strip()
        if value == "":
            return None
    return float(value)


# Heuristique de repérage d'un pool de bots constaté sur les logs BN-R
# (analyse du 2026-09-10 sur bnr_visites_detail.csv) : 646 IP toutes
# localisées en Chine, résolution figée à BOT_RESOLUTIONS et aucun plugin
# navigateur détecté. Ce pool représentait 21% des visites mais 30% des
# pages vues et 62% des accès au gabarit "Notice/Resultat" -> à exclure
# des analyses de comportement/contenu si on veut des chiffres représentatifs
# d'un usage humain. Non constaté sur bokeh au moment de l'analyse.
#
# Heuristique empirique (pas une détection de bot officielle Matomo) : à
# revalider si le pattern évolue, et à étendre si d'autres pools apparaissent
# sur d'autres pays/résolutions.
BOT_COUNTRY = "Chine"
BOT_RESOLUTIONS = {"1600x1600", "375x667"}


def is_probable_bot(visit):
    """Heuristique : la visite correspond au pool de bots identifié sur BN-R
    (pays Chine + résolution figée + aucun plugin navigateur détecté).

    `visit` peut être une entrée brute de Live.getLastVisitsDetails (dict
    avec les clés 'country', 'resolution', 'plugins') ou une ligne de CSV
    issue de flatten_visit (mêmes noms de colonnes) : les deux exposent ces
    trois champs de la même façon.
    """
    return (
        visit.get("country") == BOT_COUNTRY
        and visit.get("resolution") in BOT_RESOLUTIONS
        and not visit.get("plugins")
    )


# Heuristique de repérage des visites trackées côté serveur (et non par le
# navigateur) constatée sur bokeh (analyse du 2026-09-17) : deux plages
# /24 identifiées (195.154.187.0/24 "Online S.a.s.", 38,6% des visites sur
# 163 jours ; 135.125.109.0/24 "Avaya Inc.", 2,2% par rafales sur 15 jours),
# avec exactement la même signature -> vraisemblablement le même serveur
# d'authentification/CAS, dont l'IP de sortie a changé sur certaines
# périodes. Signature retenue car indépendante de l'IP/provider (donc plus
# robuste qu'une liste de mots-clés d'hébergeur) : resolution/plugins jamais
# renseignés (pas de JS exécuté) et 100% des hits de la visite sont des
# 'event' (aucune vraie pageview).
#
# ATTENTION : contrairement à is_probable_bot, ceci NE détecte PAS des bots.
# Ce sont de vraies visites d'usagers authentifiés (userId renseigné sur
# ~87% des cas dans l'analyse) : la connexion/réservation est trackée par le
# back-end plutôt que par le navigateur de l'usager. Cette instance Matomo
# tourne SANS cookie (vérifié le 2026-09-17 : la réponse de matomo.php ne
# contient aucun Set-Cookie, configuration serveur volontaire, pas un
# blocage navigateur) -> l'identification des visiteurs repose uniquement
# sur le fallback 'config_id' (empreinte IP + navigateur + plugins), pour
# TOUT le trafic du site, pas seulement ce cluster. L'appel serveur n'ayant
# ni la même IP (le serveur applicatif, pas l'usager) ni la même empreinte
# (pas de JS exécuté -> plugins vides) que le vrai navigateur, son
# config_id diverge nécessairement -> Matomo crée une nouvelle visite au
# lieu de rattacher l'événement à la visite de navigation déjà en cours.
# Le risque associé est donc la SUR-COMPTABILISATION : une même visite
# réelle comptée deux fois. Piste de correctif la plus réaliste (puisqu'il
# n'existe pas de cookie à transmettre) : appeler setUserId() côté client
# dès l'authentification (aujourd'hui seul l'appel serveur le fait) combiné
# au réglage serveur Matomo enable_userid_overwrites_visitorid, qui permet
# de rattacher deux visites au même userId même avec des identifiants
# différents (cf. https://fr.matomo.org/faq/general/how-are-requests-with-a-user-id-tracked/) —
# nécessite une intervention chez Biblibre, qui héberge l'instance.
#
# Estimation du taux de doublons (analyse du 2026-09-17, bokeh,
# 136 321 visites) par recoupement temporel avec une autre visite (autre
# IP) de la même notice consultée :
#   - recoupement direct (notice commune, fenêtre ±5 min) : 8 034 visites
#     confirmées, soit 5,9% du total des visites du fichier ;
#   - + bootstrap (une fois l'IP réelle d'un compte confirmée une première
#     fois par contenu, on la réutilise pour retrouver ses autres visites
#     trackées serveur le même jour, à ±5 min) : 21 005 visites confirmées
#     au total, soit 15,4% du total.
#   Le solde (34 591 visites, ~25% des visites du fichier) reste
#   indéterminé : 13 305 comptes n'ont jamais de correspondance par contenu
#   (aucune IP réelle connue), 15 247 ont une IP réelle connue mais aucune
#   visite proche trouvée ce jour-là (délai >300s ou changement d'IP
#   intra-journalier), et 6 039 visites n'ont même pas de userId. 15,4% est
#   donc un plancher, pas une borne haute (le plafond extrapolé monte à
#   21,8%). Méthodologie complète et reproductible :
#   kibini/adm_analyse_estimation_doublons_bokeh.py et .ipynb.
#
# Heuristique et estimation empiriques, à revalider si le mécanisme de
# tracking du portail évolue.
def is_server_tracked_visit(visit):
    """Heuristique : la visite a été trackée côté serveur (authentification
    /réservation) plutôt que par le navigateur de l'usager -> resolution et
    plugins jamais renseignés, referrer toujours 'direct', et uniquement des
    hits de type 'event' (aucune vraie pageview de type 'action').

    `visit` peut être une entrée brute de Live.getLastVisitsDetails (dict
    avec 'actionDetails' déjà sous forme de liste) ou une ligne de CSV issue
    de flatten_visit ('actionDetails' sérialisé en JSON dans une chaîne).

    Ne pas confondre avec is_probable_bot() : ceci désigne de vrais usagers,
    pas du trafic à exclure d'une analyse de fréquentation humaine (mais à
    dédupliquer si on veut éviter de compter deux fois la même visite).
    """
    if visit.get("resolution") != "unknown" or visit.get("plugins"):
        return False
    if visit.get("referrerType") != "direct":
        return False

    action_details = visit.get("actionDetails") or []
    if isinstance(action_details, str):
        try:
            action_details = json.loads(action_details) if action_details else []
        except json.JSONDecodeError:
            return False
    if not action_details:
        return False
    return all(a.get("type") == "event" for a in action_details)


class MatomoClient:
    def __init__(self, base=None, token_auth=None):
        if base is None or token_auth is None:
            conf = Config().get_config_matomo()
            base = base or conf["base"]
            token_auth = token_auth or conf["token_auth"]
        base = base.rstrip("/")
        if base.endswith("/index.php"):
            base = base[: -len("/index.php")]
        self.base = base
        self.token_auth = token_auth

    def _call(self, method, id_site, date, period="day", segment=None, extra=None):
        params = {
            "module": "API",
            "method": method,
            "idSite": id_site,
            "period": period,
            "date": date,
            "format": "JSON",
            "token_auth": self.token_auth,
        }
        if segment:
            params["segment"] = segment
        if extra:
            params.update(extra)

        # token_auth est envoyé en POST (jamais dans l'URL) : Matomo refuse
        # (HTTP 401) le token passé en paramètre GET dès que l'option "Only
        # allow secure requests" est active côté serveur.
        url = f"{self.base}/index.php"
        data = urllib.parse.urlencode(params).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            raise RuntimeError(f"API Matomo {method} -> HTTP {exc.code}\n{detail[:500]}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Connexion impossible à l'API Matomo : {exc.reason}") from exc

        parsed = json.loads(raw) if raw.strip() else {}
        if isinstance(parsed, dict) and parsed.get("result") == "error":
            raise RuntimeError(f"API Matomo {method} -> {parsed.get('message')}")
        return parsed

    def get_daily_stats(self, id_site, start, end, segment=None):
        """
        Récupère, pour le site id_site et la période [start, end] (objets
        date), les métriques journalières correspondant aux colonnes de
        statdb.stat_web2 : visites, pages_vues, utilisateurs, taux_conversion.

        segment permet de restreindre l'appel à un sous-ensemble de visites
        du même site (ex: 'visitIp==1.2.3.4' pour isoler le trafic interne
        d'un site Matomo qui ne distingue pas interne/externe par id_site).

        Renvoie un dict {date (str AAAA-MM-JJ): {visites, pages_vues,
        utilisateurs, taux_conversion}}.

        Astuce API Matomo : avec period=day et date="debut,fin", l'API
        renvoie directement un objet indexé par jour (pas besoin de boucler
        jour par jour ni de gérer period=range).
        """
        date_range = f"{start.isoformat()},{end.isoformat()}"

        visits = self._call("VisitsSummary.get", id_site, date_range, segment=segment)
        actions = self._call("Actions.get", id_site, date_range, segment=segment)
        goals = self._call("Goals.get", id_site, date_range, segment=segment, extra={"idGoal": 0})

        days = {}
        for day, values in visits.items():
            values = values or {}
            days.setdefault(day, {})["visites"] = values.get("nb_visits", 0)
            days[day]["utilisateurs"] = values.get("nb_uniq_visitors", 0)
        for day, values in actions.items():
            values = values or {}
            days.setdefault(day, {})["pages_vues"] = values.get("nb_pageviews", 0)
        for day, values in goals.items():
            values = values or {}
            days.setdefault(day, {})["taux_conversion"] = _parse_percent(values.get("conversion_rate"))

        return days

    def get_visits_details(self, id_site, day, filter_limit=100, filter_offset=0, segment=None):
        """
        Une page de logs de visite bruts (module Live.getLastVisitsDetails)
        pour le jour `day` (objet date) : une entrée par visite (referrer,
        device, pays, durée, nombre d'actions, variables personnalisées...).

        Le serveur Matomo plafonne la réponse à 100 visites par appel quel
        que soit filter_limit demandé au-delà de 100 : pour un jour complet,
        paginer avec filter_offset (0, 100, 200, ...) jusqu'à une page vide.

        Ce n'est disponible que sur une fenêtre récente : Matomo purge en
        général ces logs détaillés après quelques mois/années, alors que les
        agrégats (get_daily_stats) restent consultables sur toute l'historique.
        """
        return self._call(
            "Live.getLastVisitsDetails", id_site, day.isoformat(), period="day",
            segment=segment,
            extra={"filter_limit": filter_limit, "filter_offset": filter_offset},
        )

    def get_daily_stats_deduped(self, id_site, start, end, segment=None, filter_limit=100):
        """
        Variante de get_daily_stats() qui exclut is_server_tracked_visit()
        avant de calculer les métriques journalières, pour ne pas compter
        deux fois une même visite réelle (cf. analyse bokeh du
        2026-09-17 : ~46% des visites trackées côté serveur qui référencent
        une notice précise ont une visite concurrente déjà trackée
        normalement par le navigateur -> environ 4,5% du total des visites
        bokeh sont ainsi comptées en double).

        Contrairement à get_daily_stats(), qui interroge les endpoints
        agrégés de l'API (VisitsSummary/Actions/Goals, disponibles sur tout
        l'historique du site), cette méthode reconstruit les métriques jour
        par jour à partir des visites brutes (Live.getLastVisitsDetails,
        paginé) : elle est donc limitée à la fenêtre de rétention des logs
        détaillés côté serveur Matomo (quelques mois à ~2 ans selon le site,
        cf. data_matomo_logs_*.py). Pour un backfill au-delà de cette
        fenêtre, utiliser get_daily_stats() (sans déduplication possible,
        faute de granularité par visite dans les endpoints agrégés).

        Renvoie le même format que get_daily_stats() : dict {date (str
        AAAA-MM-JJ): {visites, pages_vues, utilisateurs, taux_conversion}}.
        """
        days = {}
        cur = start
        while cur <= end:
            visits = []
            offset = 0
            while True:
                page = self.get_visits_details(
                    id_site, cur, filter_limit=filter_limit, filter_offset=offset, segment=segment,
                )
                if not page:
                    break
                visits.extend(page)
                offset += len(page)
                if len(page) < filter_limit:
                    break

            kept = [v for v in visits if not is_server_tracked_visit(v)]
            n_visits = len(kept)
            n_pageviews = sum(
                1
                for v in kept
                for a in (v.get("actionDetails") or [])
                if a.get("type") == "action"
            )
            n_visitors = len({v.get("visitorId") for v in kept if v.get("visitorId")})
            n_converted = sum(1 for v in kept if str(v.get("visitConverted")) == "1")
            conversion_rate = (100 * n_converted / n_visits) if n_visits else 0.0

            days[cur.isoformat()] = {
                "visites": n_visits,
                "pages_vues": n_pageviews,
                "utilisateurs": n_visitors,
                "taux_conversion": conversion_rate,
            }
            cur += timedelta(days=1)

        return days
