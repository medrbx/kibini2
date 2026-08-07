import argparse
from datetime import date, timedelta

from sqlalchemy import text

from kiblib.utils.db import DbConn
from kiblib.utils.log import Log

RESERVES_INSERT_COLUMNS = """
    reserve_id, borrowernumber, reservedate, biblionumber, branchcode,
    notificationdate, cancellationdate, priority, found, timestamp,
    itemnumber, waitingdate, expirationdate, age, sexe, ville, iris,
    branchcode_borrower, categorycode, fidelite, mobile, courriel
"""

# on insère les réservations nouvelles depuis `since` (non encore présentes
# dans stat_reserves) : borne basse ouverte, comme dans le script Perl
# d'origine - ça permet de rattraper naturellement un jour manqué
RESERVES_NEW_QUERY = f"""
    INSERT INTO statdb.stat_reserves ({RESERVES_INSERT_COLUMNS})
    SELECT
        r.reserve_id, r.borrowernumber, r.reservedate, r.biblionumber, r.branchcode,
        r.notificationdate, r.cancellationdate, r.priority, r.found, r.timestamp,
        r.itemnumber, r.waitingdate, r.expirationdate,
        CASE
            WHEN b.categorycode NOT IN ('BIBL', 'CSLT', 'CSVT', 'MEDA', 'MEDB', 'MEDC', 'MEDP')
            THEN 'NP'
            ELSE YEAR(r.reservedate) - YEAR(b.dateofbirth)
        END,
        b.sex, b.city, b.altcontactcountry, b.branchcode, b.categorycode,
        YEAR(r.reservedate) - YEAR(b.dateenrolled),
        CASE WHEN b.mobile LIKE '0%' THEN 'oui' ELSE 'non' END,
        CASE WHEN b.email LIKE '%@%' THEN 'oui' ELSE 'non' END
    FROM koha_prod.{{table}} r
    JOIN koha_prod.borrowers b ON b.borrowernumber = r.borrowernumber
    WHERE r.reservedate >= :since
      AND r.reserve_id NOT IN (SELECT reserve_id FROM statdb.stat_reserves)
"""

# on répercute les champs modifiés le jour traité (hors créations du jour,
# déjà couvertes par RESERVES_NEW_QUERY) ; converti en UPDATE...JOIN unique
# au lieu de la boucle ligne à ligne du script Perl d'origine
RESERVES_MAJ_QUERY = """
    UPDATE statdb.stat_reserves s
    JOIN koha_prod.{table} r ON r.reserve_id = s.reserve_id
    SET
        s.notificationdate = r.notificationdate,
        s.cancellationdate = r.cancellationdate,
        s.priority = r.priority,
        s.found = r.found,
        s.timestamp = r.timestamp,
        s.itemnumber = r.itemnumber,
        s.waitingdate = r.waitingdate,
        s.expirationdate = r.expirationdate,
        s.annulation = CASE WHEN s.cancellationdate IS NULL THEN 'non' ELSE 'oui' END,
        s.document_mis_cote = CASE WHEN s.waitingdate IS NULL THEN 'non' ELSE 'oui' END
    WHERE r.timestamp >= :day AND r.timestamp < :day_end
      AND r.reservedate != :day
"""


def ex_reservables(conn, branch, biblionumber):
    """Exemplaires réservables pour une notice, sur une branche donnée."""
    if branch == "MED":
        notloc_sql = "location NOT IN ('BUS1A', 'MED0A')"
    elif branch == "BUS":
        notloc_sql = "location != 'MED0A'"
    else:
        raise ValueError(f"branche non gérée pour ex_reservables : {branch!r}")

    result = conn.execute(
        text(
            f"""
            SELECT itemnumber FROM koha_prod.items
            WHERE biblionumber = :biblionumber
              AND notforloan IN (0, -1, -2, -3, -4)
              AND itemlost = 0
              AND {notloc_sql}
            """
        ),
        {"biblionumber": biblionumber},
    )
    return [row[0] for row in result]


def ex_pas_trait(conn, branch, itemnumber):
    """L'exemplaire n'est pas en traitement."""
    if branch == "MED":
        notloc_sql = "('BUS1A', 'MED0A')"
    elif branch == "BUS":
        notloc_sql = "('MED0A')"
    else:
        raise ValueError(f"branche non gérée pour ex_pas_trait : {branch!r}")

    count = conn.execute(
        text(
            f"""
            SELECT COUNT(*) FROM koha_prod.items
            WHERE itemnumber = :itemnumber
              AND location NOT IN {notloc_sql}
              AND notforloan = 0
              AND itemlost = 0
            """
        ),
        {"itemnumber": itemnumber},
    ).scalar()
    return count > 0


def ex_trait(conn, branch, itemnumber):
    """L'exemplaire est en traitement."""
    if branch == "MED":
        notloc_sql = "('BUS1A', 'MED0A')"
    elif branch == "BUS":
        notloc_sql = "('MED0A')"
    else:
        raise ValueError(f"branche non gérée pour ex_trait : {branch!r}")

    count = conn.execute(
        text(
            f"""
            SELECT COUNT(*) FROM koha_prod.items
            WHERE itemnumber = :itemnumber
              AND location NOT IN {notloc_sql}
              AND notforloan IN (-1, -2, -3, -4)
              AND itemlost = 0
            """
        ),
        {"itemnumber": itemnumber},
    ).scalar()
    return count > 0


def test_ex_empruntes(conn, itemnumber):
    """L'exemplaire est actuellement emprunté."""
    count = conn.execute(
        text("SELECT COUNT(*) FROM koha_prod.issues WHERE itemnumber = :itemnumber"),
        {"itemnumber": itemnumber},
    ).scalar()
    return count > 0


def test_ex_attente_retrait(conn, itemnumber):
    """L'exemplaire est en attente de retrait après réservation."""
    count = conn.execute(
        text("SELECT COUNT(*) FROM koha_prod.reserves WHERE found = 'W' AND itemnumber = :itemnumber"),
        {"itemnumber": itemnumber},
    ).scalar()
    return count > 0


def localisation_label(location):
    location = location or ""
    if "MED0" in location:
        return "RDC"
    if "MED1" in location:
        return "Etage 1"
    if "MED2" in location:
        return "Etage 2"
    if location == "MED3A":
        return "Etage 3"
    if location == "BUS1A":
        return "Zèbre"
    return "Magasins"


def localisation_de(conn, itemnumber):
    location = conn.execute(
        text("SELECT location FROM koha_prod.items WHERE itemnumber = :itemnumber"),
        {"itemnumber": itemnumber},
    ).scalar()
    return localisation_label(location)


def statut_reservation(conn, branch, biblionumber):
    """
    Statut d'une réservation, dans l'ordre de priorité du script Perl d'origine :
    disponible > en traitement > emprunté > en attente de retrait > indéterminé.
    S'arrête au premier exemplaire qui satisfait chaque condition.
    """
    itemnumbers = ex_reservables(conn, branch, biblionumber)

    for itemnumber in itemnumbers:
        if (
            ex_pas_trait(conn, branch, itemnumber)
            and not test_ex_empruntes(conn, itemnumber)
            and not test_ex_attente_retrait(conn, itemnumber)
        ):
            return "disp", localisation_de(conn, itemnumber)

    for itemnumber in itemnumbers:
        if (
            ex_trait(conn, branch, itemnumber)
            and not test_ex_empruntes(conn, itemnumber)
            and not test_ex_attente_retrait(conn, itemnumber)
        ):
            return "trait", localisation_de(conn, itemnumber)

    for itemnumber in itemnumbers:
        if test_ex_empruntes(conn, itemnumber) and not test_ex_attente_retrait(conn, itemnumber):
            return "empr", localisation_de(conn, itemnumber)

    for itemnumber in itemnumbers:
        if test_ex_attente_retrait(conn, itemnumber):
            return "rese", localisation_de(conn, itemnumber)

    return "ind", "indéterminé"


def new_reserve_ids(conn, day):
    result = conn.execute(
        text("SELECT reserve_id FROM statdb.stat_reserves WHERE reservedate = :day"),
        {"day": day},
    )
    return [row[0] for row in result]


def reserve_infos(conn, reserve_id):
    branchcode, biblionumber = conn.execute(
        text("SELECT branchcode, biblionumber FROM statdb.stat_reserves WHERE reserve_id = :reserve_id"),
        {"reserve_id": reserve_id},
    ).one()
    return branchcode, biblionumber


def update_statut_loc_reservation(conn, reserve_id, statut, localisation):
    conn.execute(
        text(
            "UPDATE statdb.stat_reserves SET etat = :etat, espace = :espace WHERE reserve_id = :reserve_id"
        ),
        {"etat": statut, "espace": localisation, "reserve_id": reserve_id},
    )


def reserve_issue_date(engine):
    """
    Complète, pour les réservations retirées (found='F') dont la date de
    retrait effectif n'est pas encore connue, la date de prêt correspondante
    et le nombre de jours d'attente. Traitement global, non daté (comme dans
    le script Perl d'origine).
    """
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT reserve_id, itemnumber, borrowernumber, waitingdate
                FROM statdb.stat_reserves
                WHERE found = 'F' AND waitingdate IS NOT NULL AND issuedate IS NULL AND itemnumber IS NOT NULL
                """
            )
        ).mappings().all()

    for res in rows:
        with engine.begin() as conn:
            issuedate = conn.execute(
                text(
                    """
                    SELECT issuedate FROM statdb.stat_issues
                    WHERE itemnumber = :itemnumber
                      AND borrowernumber = :borrowernumber
                      AND issuedate >= :waitingdate AND issuedate < :waitingdate + INTERVAL 11 DAY
                    """
                ),
                {
                    "itemnumber": res["itemnumber"],
                    "borrowernumber": res["borrowernumber"],
                    "waitingdate": res["waitingdate"],
                },
            ).scalar()

            waiting_duration = (issuedate.date() - res["waitingdate"]).days if issuedate else None

            conn.execute(
                text(
                    """
                    UPDATE statdb.stat_reserves
                    SET issuedate = :issuedate, waiting_duration = :waiting_duration
                    WHERE reserve_id = :reserve_id
                    """
                ),
                {
                    "issuedate": issuedate,
                    "waiting_duration": waiting_duration,
                    "reserve_id": res["reserve_id"],
                },
            )
        log.add_info(
            f"reserve_issue_date reserve_id={res['reserve_id']} "
            f"issuedate={issuedate} waiting_duration={waiting_duration}"
        )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Incorpore dans statdb.stat_reserves les réservations d'une date (par défaut : hier)."
    )
    parser.add_argument("--date", help="Date à traiter (YYYY-MM-DD). Par défaut : hier.")
    args = parser.parse_args()
    if args.date:
        return date.fromisoformat(args.date)
    return date.today() - timedelta(days=1)


day = parse_args()
day_end = day + timedelta(days=1)

log = Log()
log.add_info('Lancement')
log.add_info(f"date traitée : {day}")

engine = DbConn().create_engine()

for table in ("reserves", "old_reserves"):
    with engine.begin() as conn:
        result = conn.execute(text(RESERVES_NEW_QUERY.format(table=table)), {"since": day})
    log.add_info(f"reserves_new {table} : {result.rowcount} lignes")

for table in ("reserves", "old_reserves"):
    with engine.begin() as conn:
        result = conn.execute(
            text(RESERVES_MAJ_QUERY.format(table=table)),
            {"day": day, "day_end": day_end},
        )
    log.add_info(f"reserves_maj {table} : {result.rowcount} lignes")

reserve_issue_date(engine)

with engine.begin() as conn:
    reserve_ids = new_reserve_ids(conn, day)
log.add_info(f"{len(reserve_ids)} nouvelles réservations à qualifier")

for reserve_id in reserve_ids:
    with engine.begin() as conn:
        branch, biblionumber = reserve_infos(conn, reserve_id)
        statut, loc = statut_reservation(conn, branch, biblionumber)
        update_statut_loc_reservation(conn, reserve_id, statut, loc)
    log.add_info(f"reserve_id={reserve_id} statut={statut} espace={loc}")

log.add_info("Fin traitement\n\n")
