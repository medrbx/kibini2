import argparse
import re
from datetime import date, timedelta

from sqlalchemy import text

from kiblib.utils.db import DbConn
from kiblib.utils.log import Log

KOHA_FIELDS = [
    "bi.publicationyear", "i.biblionumber", "i.price", "bi.itemtype", "b.title",
    "i.barcode", "i.ccode", "i.itemcallnumber", "i.dateaccessioned", "i.itemnumber",
    "i.location", "i.homebranch", "i.holdingbranch", "i.notforloan", "i.damaged",
    "i.withdrawn", "i.withdrawn_on", "i.itemlost", "i.itemlost_on", "i.onloan",
    "i.datelastborrowed",
]
KOHA_SELECT = ", ".join(KOHA_FIELDS)

INSERT_QUERY = text(
    """
    INSERT INTO statdb.data_exemplaires (
        ex_item_id, ex_biblio_annee_publication, ex_biblio_id, ex_biblio_prix,
        ex_biblio_support_code, ex_biblio_titre, ex_item_annee_mise_pilon,
        ex_item_code_barre, ex_item_collection_ccode, ex_item_cote,
        ex_item_date_creation, ex_item_localisation_code, ex_item_site_detenteur_code,
        ex_item_site_rattachement_code, ex_statut_code, ex_statut_abime_code,
        ex_statut_desherbe_code, ex_statut_desherbe_date, ex_statut_perdu_code,
        ex_statut_perdu_date, ex_usage_emprunt_code, ex_usage_date_dernier_pret,
        ex_item_deleted
    ) VALUES (
        :ex_item_id, :ex_biblio_annee_publication, :ex_biblio_id, :ex_biblio_prix,
        :ex_biblio_support_code, :ex_biblio_titre, :ex_item_annee_mise_pilon,
        :ex_item_code_barre, :ex_item_collection_ccode, :ex_item_cote,
        :ex_item_date_creation, :ex_item_localisation_code, :ex_item_site_detenteur_code,
        :ex_item_site_rattachement_code, :ex_statut_code, :ex_statut_abime_code,
        :ex_statut_desherbe_code, :ex_statut_desherbe_date, :ex_statut_perdu_code,
        :ex_statut_perdu_date, :ex_usage_emprunt_code, :ex_usage_date_dernier_pret,
        :ex_item_deleted
    )
    """
)

UPDATE_QUERY = text(
    """
    UPDATE statdb.data_exemplaires
    SET
        ex_biblio_annee_publication = :ex_biblio_annee_publication,
        ex_biblio_id = :ex_biblio_id,
        ex_biblio_prix = :ex_biblio_prix,
        ex_biblio_support_code = :ex_biblio_support_code,
        ex_biblio_titre = :ex_biblio_titre,
        ex_item_annee_mise_pilon = :ex_item_annee_mise_pilon,
        ex_item_code_barre = :ex_item_code_barre,
        ex_item_collection_ccode = :ex_item_collection_ccode,
        ex_item_cote = :ex_item_cote,
        ex_item_date_creation = :ex_item_date_creation,
        ex_item_localisation_code = :ex_item_localisation_code,
        ex_item_site_detenteur_code = :ex_item_site_detenteur_code,
        ex_item_site_rattachement_code = :ex_item_site_rattachement_code,
        ex_statut_code = :ex_statut_code,
        ex_statut_abime_code = :ex_statut_abime_code,
        ex_statut_desherbe_code = :ex_statut_desherbe_code,
        ex_statut_desherbe_date = :ex_statut_desherbe_date,
        ex_statut_perdu_code = :ex_statut_perdu_code,
        ex_statut_perdu_date = :ex_statut_perdu_date,
        ex_usage_emprunt_code = :ex_usage_emprunt_code,
        ex_usage_date_dernier_pret = :ex_usage_date_dernier_pret,
        ex_item_deleted = :ex_item_deleted,
        updated_on = NOW()
    WHERE ex_item_id = :ex_item_id
    """
)


def fetch_koha_item(conn, itemnumber):
    """
    Reproduit la cascade de recherche de l'exemplaire dans koha_prod : items,
    puis deleteditems (+ biblio si la notice existe encore, sinon +
    deletedbiblio). Retourne (champs koha, supprimé:bool), ou (None, None) si
    l'exemplaire n'existe nulle part (ne devrait pas arriver : les
    itemnumbers traités proviennent toujours de items ou deleteditems).
    """
    in_items = conn.execute(
        text("SELECT COUNT(*) FROM koha_prod.items WHERE itemnumber = :itemnumber"),
        {"itemnumber": itemnumber},
    ).scalar()

    if in_items:
        row = conn.execute(
            text(
                f"""
                SELECT {KOHA_SELECT}
                FROM koha_prod.items i
                LEFT JOIN koha_prod.biblioitems bi ON bi.biblionumber = i.biblionumber
                LEFT JOIN koha_prod.biblio b ON b.biblionumber = i.biblionumber
                WHERE i.itemnumber = :itemnumber
                """
            ),
            {"itemnumber": itemnumber},
        ).mappings().first()
        return row, False

    in_deleted = conn.execute(
        text("SELECT COUNT(*) FROM koha_prod.deleteditems WHERE itemnumber = :itemnumber"),
        {"itemnumber": itemnumber},
    ).scalar()
    if not in_deleted:
        return None, None

    biblio_exists = conn.execute(
        text(
            """
            SELECT COUNT(*) FROM koha_prod.deleteditems i
            JOIN koha_prod.biblio b ON b.biblionumber = i.biblionumber
            WHERE i.itemnumber = :itemnumber
            """
        ),
        {"itemnumber": itemnumber},
    ).scalar()

    if biblio_exists:
        row = conn.execute(
            text(
                f"""
                SELECT {KOHA_SELECT}
                FROM koha_prod.deleteditems i
                LEFT JOIN koha_prod.biblioitems bi ON bi.biblionumber = i.biblionumber
                LEFT JOIN koha_prod.biblio b ON b.biblionumber = i.biblionumber
                WHERE i.itemnumber = :itemnumber
                """
            ),
            {"itemnumber": itemnumber},
        ).mappings().first()
    else:
        row = conn.execute(
            text(
                f"""
                SELECT {KOHA_SELECT}
                FROM koha_prod.deleteditems i
                LEFT JOIN koha_prod.deletedbiblioitems bi ON bi.biblionumber = i.biblionumber
                LEFT JOIN koha_prod.deletedbiblio b ON b.biblionumber = i.biblionumber
                WHERE i.itemnumber = :itemnumber
                """
            ),
            {"itemnumber": itemnumber},
        ).mappings().first()
    return row, True


def compute_statdb_fields(conn, koha, deleted, existing_pilon_year):
    """
    Équivalent de get_statdb_document_generic_data, avec les 3 corrections
    validées par rapport au Perl d'origine :
    - ex_item_collection_ccode : la correction pour les périodiques (via
      statdb.lib_periodiques) est réellement appliquée, plus écrasée juste
      après par le ccode brut ;
    - ex_item_annee_mise_pilon : la valeur déjà en base est préservée lors
      d'une mise à jour, au lieu d'être systématiquement remise à NULL ;
    - ex_statut_code / ex_statut_abime_code / ex_statut_desherbe_code /
      ex_statut_perdu_code : la valeur 0 (cas normal) est bien écrite telle
      quelle, au lieu d'être perdue par un test de vérité façon Perl.
    """
    ccode = koha["ccode"]
    if koha["ccode"] and koha["itemtype"] == "PE":
        perio_ccode = conn.execute(
            text("SELECT ccode FROM statdb.lib_periodiques WHERE biblionumber = :biblionumber"),
            {"biblionumber": koha["biblionumber"]},
        ).scalar()
        if perio_ccode:
            ccode = perio_ccode

    if koha["onloan"] is None:
        usage_emprunt_code = 0
    elif re.match(r"^\d{4}-\d{2}-\d{2}", str(koha["onloan"])):
        usage_emprunt_code = 1
    else:
        usage_emprunt_code = None

    return {
        "ex_biblio_annee_publication": koha["publicationyear"],
        "ex_biblio_id": koha["biblionumber"],
        "ex_biblio_prix": koha["price"],
        "ex_biblio_support_code": koha["itemtype"],
        "ex_biblio_titre": koha["title"],
        "ex_item_annee_mise_pilon": existing_pilon_year,
        "ex_item_code_barre": koha["barcode"],
        "ex_item_collection_ccode": ccode,
        "ex_item_cote": koha["itemcallnumber"],
        "ex_item_date_creation": koha["dateaccessioned"],
        "ex_item_localisation_code": koha["location"],
        "ex_item_site_detenteur_code": koha["homebranch"],
        "ex_item_site_rattachement_code": koha["holdingbranch"],
        "ex_statut_code": koha["notforloan"],
        "ex_statut_abime_code": koha["damaged"],
        "ex_statut_desherbe_code": koha["withdrawn"],
        "ex_statut_desherbe_date": koha["withdrawn_on"],
        "ex_statut_perdu_code": koha["itemlost"],
        "ex_statut_perdu_date": koha["itemlost_on"],
        "ex_usage_emprunt_code": usage_emprunt_code,
        "ex_usage_date_dernier_pret": koha["datelastborrowed"],
        "ex_item_deleted": 1 if deleted else 0,
    }


def process_item(engine, itemnumber):
    """Traite un exemplaire, retourne 'inserted', 'updated' ou 'skipped'."""
    with engine.begin() as conn:
        koha, deleted = fetch_koha_item(conn, itemnumber)
        if koha is None:
            return "skipped"

        existing = conn.execute(
            text("SELECT ex_item_annee_mise_pilon FROM statdb.data_exemplaires WHERE ex_item_id = :item_id"),
            {"item_id": itemnumber},
        ).fetchone()

        fields = compute_statdb_fields(conn, koha, deleted, existing[0] if existing else None)
        fields["ex_item_id"] = itemnumber

        if existing is not None:
            conn.execute(UPDATE_QUERY, fields)
            return "updated"

        conn.execute(INSERT_QUERY, fields)
        return "inserted"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Incorpore dans statdb.data_exemplaires les exemplaires modifiés "
                     "depuis une date (par défaut : hier)."
    )
    parser.add_argument("--since", help="Traiter depuis cette date (YYYY-MM-DD). Par défaut : hier.")
    args = parser.parse_args()
    if args.since:
        return date.fromisoformat(args.since)
    return date.today() - timedelta(days=1)


since = parse_args()

log = Log()
log.add_info('Lancement')
log.add_info(f"depuis : {since}")

engine = DbConn().create_engine()

with engine.begin() as conn:
    itemnumbers = set()
    for table in ("items", "deleteditems"):
        result = conn.execute(
            text(f"SELECT itemnumber FROM koha_prod.{table} WHERE timestamp >= :since"),
            {"since": since},
        )
        itemnumbers.update(row[0] for row in result)

nb_inserted = 0
nb_updated = 0
nb_skipped = 0
for itemnumber in itemnumbers:
    outcome = process_item(engine, itemnumber)
    if outcome == "inserted":
        nb_inserted += 1
    elif outcome == "updated":
        nb_updated += 1
    else:
        nb_skipped += 1
        log.add_info(f"itemnumber={itemnumber} introuvable dans koha_prod (ignoré)")

log.add_info(f"{nb_inserted} lignes ajoutées, {nb_updated} lignes mises à jour, {nb_skipped} ignorées")
log.add_info("Fin traitement\n\n")
