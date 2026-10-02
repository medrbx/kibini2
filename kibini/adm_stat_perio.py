import pandas as pd
from os.path import join

from kiblib.utils.db import DbConn
from kiblib.utils.conf import Config

db_conn = DbConn().create_engine()

# Exemplaires de périodiques (par notice et site)
query = """SELECT i.itemnumber, i.biblionumber, i.biblioitemnumber, i.barcode,
i.dateaccessioned, i.homebranch, i.notforloan, i.itemcallnumber, i.location, i.ccode, bi.itemtype, b.title
FROM koha_prod.items i
JOIN koha_prod.biblioitems bi ON bi.biblionumber = i.biblionumber
JOIN koha_prod.biblio b ON b.biblionumber = i.biblionumber
WHERE bi.itemtype = 'PE' AND i.notforloan = '0'"""
items = pd.read_sql(query, db_conn)
perios = items.groupby(['biblionumber', 'title', 'homebranch', 'ccode'])['itemnumber'].count().reset_index()

# Prêts sur les 12 derniers mois
query = """SELECT biblionumber, itemnumber, issue_id, borrowernumber, branch
FROM statdb.stat_issues
WHERE itemtype = 'PE'
AND DATE(issuedate) >= CURDATE() - INTERVAL 1 YEAR"""
prets = pd.read_sql(query, db_conn)
prets_titre_nb = prets.groupby(['biblionumber', 'branch'])['issue_id'].count().reset_index()
prets_titre_emprunteurs_distincts = prets.groupby(['biblionumber', 'branch'])['borrowernumber'].nunique().reset_index()

perios = perios.merge(prets_titre_nb, left_on=['biblionumber', 'homebranch'], right_on=['biblionumber', 'branch'], how='left')
perios = perios[['biblionumber', 'title', 'homebranch', 'ccode', 'itemnumber', 'issue_id']]
perios = perios.merge(prets_titre_emprunteurs_distincts, left_on=['biblionumber', 'homebranch'], right_on=['biblionumber', 'branch'], how='left')
perios = perios[['biblionumber', 'title', 'homebranch', 'ccode', 'itemnumber', 'issue_id', 'borrowernumber']]

# Libellé des collections
query = """SELECT av.authorised_value, av.lib
FROM koha_prod.authorised_values av
WHERE category = 'collection'"""
va_collection = pd.read_sql(query, db_conn)
perios = perios.merge(va_collection, left_on='ccode', right_on='authorised_value', how='left')

perios = perios[['biblionumber', 'title', 'ccode', 'lib', 'homebranch', 'itemnumber',
                 'issue_id', 'borrowernumber']].copy()
perios.columns = ['notice', 'titre', 'ccode', 'collection', 'site', 'nb exemplaires',
                  'nb prêts', 'emprunteurs distincts']

perios['nb prêts'] = perios['nb prêts'].fillna(0).astype(int)
perios['emprunteurs distincts'] = perios['emprunteurs distincts'].fillna(0).astype(int)

perios.loc[perios['ccode'] == 'JPRZZZZ', 'collection'] = 'Jeunesse - presse'
perios.loc[perios['ccode'] == 'AMVZZ', 'collection'] = 'AMV - Musique Généralités'
perios = perios.sort_values(by='ccode')
perios = perios[['notice', 'titre', 'collection', 'site', 'nb exemplaires',
                 'nb prêts', 'emprunteurs distincts']]

# Prêts de l'année précédente (n-1)
query = """SELECT biblionumber, itemnumber, issue_id, borrowernumber, branch
FROM statdb.stat_issues
WHERE itemtype = 'PE'
AND DATE(issuedate) >= CURDATE() - INTERVAL 2 YEAR
AND DATE(issuedate) <= CURDATE() - INTERVAL 1 YEAR"""
prets2 = pd.read_sql(query, db_conn)
prets_titre_nb2 = prets2.groupby(['biblionumber', 'branch'])['issue_id'].count().reset_index()
prets_titre_emprunteurs_distincts2 = prets2.groupby(['biblionumber', 'branch'])['borrowernumber'].nunique().reset_index()

prets_titre_nb2.columns = ['notice', 'site', 'nb prêts n-1']
prets_titre_emprunteurs_distincts2.columns = ['notice', 'site', 'emprunteurs distincts n-1']
perios = perios.merge(prets_titre_nb2, on=['notice', 'site'], how='left')
perios = perios.merge(prets_titre_emprunteurs_distincts2, on=['notice', 'site'], how='left')

perios['nb prêts n-1'] = perios['nb prêts n-1'].fillna(0).astype(int)
perios['emprunteurs distincts n-1'] = perios['emprunteurs distincts n-1'].fillna(0).astype(int)

# Évolutions (inf/NaN quand n-1 vaut 0)
perios['évolution prêts'] = round((perios['nb prêts'] - perios['nb prêts n-1']) / perios['nb prêts n-1'] * 100, 1)
perios['évolution emprunteurs distincts'] = round(
    (perios['emprunteurs distincts'] - perios['emprunteurs distincts n-1']) / perios['emprunteurs distincts n-1'] * 100, 1)

dir_data = Config().get_config_data()
perios.to_excel(join(dir_data, "perios.xlsx"), index=False)
