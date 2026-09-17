"""
Estimation du taux de visites bokeh comptées en double à cause des
visites trackées côté serveur (cf. kiblib.utils.matomo.is_server_tracked_visit).

Contexte : quand une action nécessite d'être authentifié (ex. réserver un
document), le portail déclenche un appel de tracking Matomo côté serveur qui
ne transmet pas le cookie visiteur (_pk_id) du navigateur -> Matomo crée une
nouvelle visite au lieu de rattacher l'événement à la visite de navigation
déjà en cours. Ce script mesure combien de ces visites "serveur" sont en
fait des doublons d'une visite déjà trackée normalement, par deux passes :

  1. Recoupement par contenu : la visite serveur référence une notice
     précise (URL contenant /id/<n> ou /record_id/<n>) -> on cherche une
     autre visite (autre IP) qui consulte la même notice à quelques minutes
     d'écart (fenêtre GAP).
  2. Bootstrap : une fois l'IP réelle d'un compte (userId) confirmée une
     première fois par contenu, on la réutilise pour retrouver ses autres
     visites serveur du même jour (sans notice à recouper), à quelques
     minutes d'écart sur cette même IP.

Puis un test null (Monte-Carlo) évalue le taux de faux positifs des deux
méthodes en cassant volontairement la vraie correspondance (ids mélangés
entre visites pour la méthode 1, IP d'ancrage tirée au hasard chez un autre
compte pour la méthode 2) et en comptant combien de "confirmations" surgissent
quand même par pur hasard -> permet de donner une fourchette de confiance
plutôt qu'un chiffre ponctuel.

Résultats de référence (analyse du 2026-09-17, 136 321 visites bokeh) :
  - brut (contenu + bootstrap)         : 20 975 visites = 15,4% du total
  - faux positifs estimés (test null)  : ~0,3-0,4% des visites testées
  - ajusté (2 écarts-types)            : [15,2% ; 15,3%] du total
Le bruit statistique est négligeable : la limite n'est pas la fiabilité de
la méthode mais son plancher structurel (cf. kiblib/utils/matomo.py pour le
détail du solde indéterminé - comptes sans aucune IP réelle connue). À
relancer sur un CSV à jour si besoin d'un chiffre récent.

Usage :
    python adm_analyse_estimation_doublons_bokeh.py [chemin_csv] [n_iter]
    (par défaut : kibini/data/bokeh_visites_detail.csv, n_iter=20)
"""
import csv
import json
import os
import random
import re
import statistics
import sys
from collections import defaultdict

csv.field_size_limit(sys.maxsize)

DEFAULT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "bokeh_visites_detail.csv"
)
ID_RE = re.compile(r"/(?:id|record_id)/(\d{5,})")
GAP = 300  # tolerance en secondes entre deux fenetres temporelles
N_ITER_DEFAULT = 20


def is_server_tracked_visit(row):
    """Copie autonome de kiblib.utils.matomo.is_server_tracked_visit,
    dupliquée ici pour que ce script tourne sans dépendance (pas besoin de
    l'environnement conda kibini/PyYAML) sur un simple CSV."""
    if row.get("resolution") != "unknown" or row.get("plugins"):
        return False
    if row.get("referrerType") != "direct":
        return False
    ad_raw = row.get("actionDetails") or "[]"
    try:
        ad = json.loads(ad_raw) if ad_raw else []
    except json.JSONDecodeError:
        return False
    if not ad:
        return False
    return all(a.get("type") == "event" for a in ad)


def extract_ids(action_details):
    ids = set()
    for a in action_details:
        url = a.get("url") or ""
        for m in ID_RE.finditer(url):
            ids.add(m.group(1))
    return ids


def overlap_gap(fa, la, tf, tl):
    """0 si les deux fenetres [fa,la] et [tf,tl] se chevauchent, sinon
    l'ecart en secondes entre elles."""
    return 0 if (fa <= tl and tf <= la) else min(abs(fa - tl), abs(tf - la))


def stats(values):
    return statistics.mean(values), (statistics.stdev(values) if len(values) > 1 else 0.0)


def main(path, n_iter):
    # ---------- Passe 1 : visites cibles (trackées côté serveur) ----------
    targets = []
    id_occurrences = defaultdict(list)  # notice_id -> [(ip, first, last), ...] (trafic NON cible)
    ip_date_index = defaultdict(list)   # (ip, date) -> [(first, last), ...] (trafic NON cible)

    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            try:
                fa = int(row.get("firstActionTimestamp") or 0)
                la = int(row.get("lastActionTimestamp") or 0)
            except ValueError:
                continue
            if is_server_tracked_visit(row):
                ad = json.loads(row.get("actionDetails") or "[]")
                targets.append({
                    "userId": row.get("userId") or None, "date": row.get("serverDate"),
                    "first": fa, "last": la, "ids": extract_ids(ad), "confirmed_ip": None,
                })
            else:
                ip_date_index[(row.get("visitIp"), row.get("serverDate"))].append((fa, la))
                for m in ID_RE.finditer(row.get("actionDetails") or "[]"):
                    id_occurrences[m.group(1)].append((row.get("visitIp"), fa, la))

    print(f"Total visites cibles (is_server_tracked_visit) : {len(targets)}")

    def content_match(ids, tf, tl):
        for _id in ids:
            for ip, fa, la in id_occurrences.get(_id, []):
                if overlap_gap(fa, la, tf, tl) <= GAP:
                    return ip
        return None

    def bootstrap_match(ip, date, tf, tl):
        return any(overlap_gap(fa, la, tf, tl) <= GAP for fa, la in ip_date_index.get((ip, date), []))

    # ---------- Passe 2 (réelle) : recoupement par contenu ----------
    for tv in targets:
        if tv["ids"]:
            tv["confirmed_ip"] = content_match(tv["ids"], tv["first"], tv["last"])

    n_content_real = sum(1 for tv in targets if tv["confirmed_ip"])
    print(f"Confirmees par contenu (notice commune) : {n_content_real}")

    # ---------- Passe 3 (réelle) : bootstrap ----------
    anchors_by_user = defaultdict(list)
    for tv in targets:
        if tv["confirmed_ip"] and tv["userId"]:
            anchors_by_user[tv["userId"]].append((tv["first"], tv["confirmed_ip"]))
    for anchors in anchors_by_user.values():
        anchors.sort()

    unconfirmed_with_userid = [
        tv for tv in targets if not tv["confirmed_ip"] and tv["userId"] and anchors_by_user.get(tv["userId"])
    ]
    n_no_anchor = sum(1 for tv in targets if not tv["confirmed_ip"] and tv["userId"] and not anchors_by_user.get(tv["userId"]))
    n_no_userid = sum(1 for tv in targets if not tv["confirmed_ip"] and not tv["userId"])

    n_bootstrap_real = 0
    for tv in unconfirmed_with_userid:
        candidate_ip = min(anchors_by_user[tv["userId"]], key=lambda a: abs(a[0] - tv["first"]))[1]
        tv["bootstrap_ip"] = candidate_ip
        if bootstrap_match(candidate_ip, tv["date"], tv["first"], tv["last"]):
            tv["confirmed_ip"] = candidate_ip
            n_bootstrap_real += 1

    n_total_real = n_content_real + n_bootstrap_real
    n_total_targets = len(targets)

    print()
    print(f"Confirmees par bootstrap (IP reelle deja connue pour ce compte) : {n_bootstrap_real}")
    print(f"  dont : sans ancre disponible pour ce compte = {n_no_anchor}")
    print(f"         ancre disponible mais aucune visite proche trouvee = {len(unconfirmed_with_userid) - n_bootstrap_real}")
    print(f"         sans userId du tout (compte non identifiable) = {n_no_userid}")
    print()
    print(f"TOTAL confirme (contenu + bootstrap) : {n_total_real} / {n_total_targets} = {100*n_total_real/n_total_targets:.1f}%")

    with open(path, newline="") as f:
        total_file_visits = sum(1 for _ in csv.DictReader(f))
    print(f"Total visites du fichier : {total_file_visits}")
    print(f"Doublons confirmes / total fichier : {100*n_total_real/total_file_visits:.1f}%")

    # ---------- Test null A : shuffle des ids (méthode contenu) ----------
    id_bearing = [tv for tv in targets if tv["ids"]]
    null_content_counts = []
    for _ in range(n_iter):
        shuffled = [tv["ids"] for tv in id_bearing]
        random.shuffle(shuffled)
        spurious = sum(
            1 for tv, fake_ids in zip(id_bearing, shuffled)
            if fake_ids is not tv["ids"] and content_match(fake_ids, tv["first"], tv["last"])
        )
        null_content_counts.append(spurious)

    # ---------- Test null B : IP d'ancrage aléatoire (méthode bootstrap) ----------
    anchor_pool = sorted({ip for anchors in anchors_by_user.values() for _, ip in anchors})
    null_bootstrap_counts = []
    for _ in range(n_iter):
        spurious = 0
        for tv in unconfirmed_with_userid:
            own_ips = {ip for _, ip in anchors_by_user[tv["userId"]]}
            candidates = [ip for ip in anchor_pool if ip not in own_ips]
            if candidates and bootstrap_match(random.choice(candidates), tv["date"], tv["first"], tv["last"]):
                spurious += 1
        null_bootstrap_counts.append(spurious)

    mean_a, std_a = stats(null_content_counts)
    mean_b, std_b = stats(null_bootstrap_counts)

    print()
    print(f"=== Test null A (contenu), {n_iter} tirages sur {len(id_bearing)} visites ===")
    print(f"  Faux positifs simules : moyenne={mean_a:.1f}  ecart-type={std_a:.1f}  ({100*mean_a/len(id_bearing):.2f}%)")
    print(f"=== Test null B (bootstrap), {n_iter} tirages sur {len(unconfirmed_with_userid)} visites ===")
    print(f"  Faux positifs simules : moyenne={mean_b:.1f}  ecart-type={std_b:.1f}  ({100*mean_b/len(unconfirmed_with_userid):.2f}%)")

    adj_total = (n_content_real - mean_a) + (n_bootstrap_real - mean_b)
    adj_lo = (n_content_real - (mean_a + 2*std_a)) + (n_bootstrap_real - (mean_b + 2*std_b))
    adj_hi = (n_content_real - max(mean_a - 2*std_a, 0)) + (n_bootstrap_real - max(mean_b - 2*std_b, 0))

    print()
    print("=== Estimation ajustee (brut - faux positifs attendus) ===")
    print(f"  Brut                           : {100*n_total_real/total_file_visits:.1f}% du total")
    print(f"  Ajuste (point central)         : {100*adj_total/total_file_visits:.1f}% du total")
    print(f"  Fourchette (+/- 2 ecarts-type) : [{100*adj_lo/total_file_visits:.1f}% ; {100*adj_hi/total_file_visits:.1f}%]")

    # ---------- Plafond extrapole ----------
    # Le plancher (ci-dessus) ne peut pas verifier : (a) les comptes avec
    # userId mais sans aucune ancre confirmee, (b) les visites sans userId
    # du tout. Plutot que de supposer 100% de doublons pour ces deux
    # populations (hors-sol), on extrapole le taux de confirmation observe
    # sur la population comparable la plus proche :
    #   (a) taux de confirmation des comptes qui ONT une ancre (bootstrap)
    #       applique aux comptes qui n'en ont pas -> meme population
    #       (usagers identifies), seule differe la disponibilite d'une ancre.
    #   (b) taux de confirmation global parmi tous les comptes identifies
    #       (contenu + bootstrap) applique aux visites sans userId -> proxy
    #       plus faible (population differente), faute de mieux.
    rate_anchor = n_bootstrap_real / len(unconfirmed_with_userid) if unconfirmed_with_userid else 0.0
    rate_identified = n_total_real / (n_total_targets - n_no_userid) if (n_total_targets - n_no_userid) else 0.0

    extra_no_anchor = n_no_anchor * rate_anchor
    extra_no_userid = n_no_userid * rate_identified
    ceiling_total = n_total_real + extra_no_anchor + extra_no_userid

    print()
    print("=== Plafond extrapole ===")
    print(f"  Taux de confirmation chez les comptes avec ancre : {100*rate_anchor:.1f}%  (applique a {n_no_anchor} visites sans ancre -> +{extra_no_anchor:.0f})")
    print(f"  Taux de confirmation global (comptes identifies) : {100*rate_identified:.1f}%  (applique a {n_no_userid} visites sans userId -> +{extra_no_userid:.0f})")
    print(f"  Plafond extrapole : {ceiling_total:.0f} / {total_file_visits} = {100*ceiling_total/total_file_visits:.1f}% du total")
    print(f"  (contre {100*n_total_real/total_file_visits:.1f}% pour le plancher brut, et 100% hors-sol = {100*n_total_targets/total_file_visits:.1f}%)")


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATH
    iterations = int(sys.argv[2]) if len(sys.argv) > 2 else N_ITER_DEFAULT
    main(csv_path, iterations)
