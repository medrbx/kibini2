import pandas as pd

from kiblib.utils.db import DbConn
from kiblib.utils.code2libelle import Code2Libelle
from kiblib.utils.date import get_date_and_time
from kiblib.pret import Pret

date = "2020-10-01"#get_date_and_time('yesterday')
datelim = "2020-11-01"

db_conn = DbConn().create_db_con()

c2l = Code2Libelle(db_conn)
c2l.get_val()

query = """
    SELECT
        iss.issue_id, -- pret_koha_id,
        iss.issuedate, -- pret_date,
        iss.returndate, -- pret_date_retour_effectif,
        iss.date_due, -- pret_date_retour_prevue,
        iss.renewals, -- pret_nb_renouvellement,
        iss.branchcode as issue_branchcode, -- pret_site_pret_code
        iss.arret_bus as pret_bus_arret_code,
        iss.returnbranch,
        iss.borrowernumber, -- adh_id,
        iss.sexe as adh_sexe_code, -- adh_sexe_code,
        iss.age as adh_age_code, -- adh_age_code,
        iss.ville as city,
        iss.iris as adh_geo_rbx_iris_code,
        iss.categorycode,
        iss.branchcode as adh_inscription_site_code,
        iss.fidelite as adh_inscription_nb_annees_adhesion,
        iss.biblionumber,
        iss.itemtype,
        iss.publicationyear as doc_biblio_annee_publication,
        iss.itemnumber,
        iss.ccode,
        iss.homebranch,
        iss.location,
        iss.itemcallnumber,
        iss.dateaccessioned
    FROM borrowers_20201031.stat_issues_1 iss
    JOIN statdb.stat_prets_1 sp ON sp.pret_koha_id = iss.issue_id
"""

df = pd.read_sql(query, con=db_conn)
#df = pd.read_sql(query, params=(date, datelim), con=db_conn)
#df = pd.read_sql(query, params={date}, con=db_conn)
pret = Pret(df=df, con=db_conn, c2l=c2l.dict_codes_lib)
pret.get_pret_statdb_data()
pret.get_pret_statdb_data_columns()
pret.add_statdb_pret_data('update')
print(pret.pret_statdb_data)
