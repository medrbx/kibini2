import pandas as pd
from datetime import date
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

# Coût de l'abonnement 2026 (fichier de correspondance biblionumber / tableau des abonnements)
dir_data = Config().get_config_data()
couts = pd.read_excel(join(dir_data, "periodiques_titres_couts.xlsx"),
                      usecols=['biblionumber', 'coût 2026'])
couts.columns = ['notice', 'coût abonnement 2026']
perios = perios.merge(couts.drop_duplicates('notice'), on='notice', how='left')


def ajoute_periode(perios, suffixe, debut, fin):
    """Ajoute les colonnes de prêts et d'emprunteurs distincts d'une période passée.
    debut et fin sont des intervalles SQL (ex. '2 YEAR') relatifs à CURDATE()."""
    query = f"""SELECT biblionumber, itemnumber, issue_id, borrowernumber, branch
    FROM statdb.stat_issues
    WHERE itemtype = 'PE'
    AND DATE(issuedate) >= CURDATE() - INTERVAL {debut}
    AND DATE(issuedate) < CURDATE() - INTERVAL {fin}"""
    prets_p = pd.read_sql(query, db_conn)
    nb = prets_p.groupby(['biblionumber', 'branch'])['issue_id'].count().reset_index()
    emprunteurs = prets_p.groupby(['biblionumber', 'branch'])['borrowernumber'].nunique().reset_index()
    nb.columns = ['notice', 'site', f'nb prêts {suffixe}']
    emprunteurs.columns = ['notice', 'site', f'emprunteurs distincts {suffixe}']
    perios = perios.merge(nb, on=['notice', 'site'], how='left')
    perios = perios.merge(emprunteurs, on=['notice', 'site'], how='left')
    for col in (f'nb prêts {suffixe}', f'emprunteurs distincts {suffixe}'):
        perios[col] = perios[col].fillna(0).astype(int)
    return perios


# Prêts des années précédentes (n-1 : entre 2 ans et 1 an ; n-2 : entre 3 ans et 2 ans)
perios = ajoute_periode(perios, 'n-1', '2 YEAR', '1 YEAR')
perios = ajoute_periode(perios, 'n-2', '3 YEAR', '2 YEAR')

# Évolutions n vs n-1, n-1 vs n-2 et n vs n-2 (inf/NaN quand la valeur de référence vaut 0)
perios['évolution prêts'] = round((perios['nb prêts'] - perios['nb prêts n-1']) / perios['nb prêts n-1'] * 100, 1)
perios['évolution emprunteurs distincts'] = round(
    (perios['emprunteurs distincts'] - perios['emprunteurs distincts n-1']) / perios['emprunteurs distincts n-1'] * 100, 1)
perios['évolution prêts n-1/n-2'] = round(
    (perios['nb prêts n-1'] - perios['nb prêts n-2']) / perios['nb prêts n-2'] * 100, 1)
perios['évolution emprunteurs distincts n-1/n-2'] = round(
    (perios['emprunteurs distincts n-1'] - perios['emprunteurs distincts n-2']) / perios['emprunteurs distincts n-2'] * 100, 1)
perios['évolution prêts n/n-2'] = round((perios['nb prêts'] - perios['nb prêts n-2']) / perios['nb prêts n-2'] * 100, 1)
perios['évolution emprunteurs distincts n/n-2'] = round(
    (perios['emprunteurs distincts'] - perios['emprunteurs distincts n-2']) / perios['emprunteurs distincts n-2'] * 100, 1)

file_out = join(dir_data, f"stats_periodiques_{date.today():%Y%m%d}.xlsx")
with pd.ExcelWriter(file_out, engine='openpyxl') as writer:
    perios.to_excel(writer, index=False, sheet_name='périodiques')
    ws = writer.sheets['périodiques']
    # largeur de chaque colonne adaptée à son contenu (en-tête compris), plafonnée à 50
    for col in ws.columns:
        largeur = max(len(str(cell.value)) if cell.value is not None else 0 for cell in col)
        ws.column_dimensions[col[0].column_letter].width = min(largeur + 2, 50)
