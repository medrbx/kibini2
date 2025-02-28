import pandas as pd

from kiblib.utils.db import DbConn
from kiblib.utils.code2libelle import Code2Libelle
from kiblib.utils.log import Log
from kiblib.pret import Pret

log = Log()
log.add_info('Lancement')

db_conn = DbConn().create_db_con()

c2l = Code2Libelle(db_conn)
c2l.get_val()

chunksize = 10000

#####################################################
# MaJ es prets2020
log.add_info('MaJ es prets2020')

query = """
    SELECT pret_id,
        pret_koha_id,
        pret_date_pret,
        pret_date_retour_effectif,
        pret_date_retour_prevue,
        pret_nb_renouvellement,
        pret_site_pret_code,
        pret_bus_arret_code,
        pret_site_retour_code,
        adh_id,
        adh_age_code,
        adh_sexe_code,
        adh_geo_ville,
        adh_geo_rbx_iris_code,
        adh_inscription_site_code,
        adh_inscription_carte_code,
        adh_inscription_carte_personnalite_code,
        adh_inscription_nb_annees_adhesion,
        adh_inscription_attribut_action_code,
        adh_inscription_attribut_bus_code,
        adh_inscription_attribut_collect_code,
        adh_inscription_attribut_pcs_code,
        doc_biblio_id,
        doc_biblio_titre,
        doc_biblio_support_code,
        doc_biblio_annee_publication,
        doc_item_id,
        doc_item_code_barre,
        doc_item_collection_ccode,
        doc_item_site_detenteur_code,
        doc_item_localisation_code,
        doc_item_cote,
        doc_item_date_creation,
        updated_on
    FROM stat_prets
    WHERE DATE(updated_on) = CURDATE()
"""

nb_lignes = 0
for df in pd.read_sql(query, con=db_conn, chunksize=chunksize):
    if df.empty:
        log.add_info("es : dataframe vide")
    else:
        pret = Pret(df=df, con=db_conn, c2l=c2l.dict_codes_lib)
        pret.get_pret_statdb_data()
        pret.get_pret_statdb_data_columns()
        pret.get_pret_es_data()
        pret.get_pret_es_data_columns()
        pret.add_es_pret_data()
        nb_lignes = nb_lignes + len(df.index)

log.add_info(f"{nb_lignes} ajoutées ou mises à jour")

log.add_info("Fin traitement\n\n")
