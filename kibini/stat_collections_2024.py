import pandas as pd
import numpy as np

from datetime import datetime

from kiblib.utils.db import DbConn
from kiblib.utils.code2libelle import Code2Libelle
from kiblib.document import Document
from kiblib.pret import Pret

def get_location(code_site):
    if code_site == "GPL":
        location = "i.location != 'MUS1A'"
    elif code_site == "MED":
        location = "i.location NOT IN ('MUS1A', 'BUS1A', 'MED0A')"
    elif code_site == "BUS":
        location = "i.location = 'BUS1A'"
    elif code_site == "COL":
        location = "i.location = 'MED0A'"
    return location


def pivot_table_w_subtotals(df, values, indices, columns, aggfunc, fill_value):
    '''
    https://towardsdatascience.com/tabulating-subtotals-dynamically-in-python-pandas-pivot-tables-6efadbb79be2
    Adds tabulated subtotals to pandas pivot tables with multiple hierarchical indices.
    
    Args:
    - df - dataframe used in pivot table
    - values - values used to aggregrate
    - indices - ordered list of indices to aggregrate by
    - columns - columns to aggregrate by
    - aggfunc - function used to aggregrate (np.max, np.mean, np.sum, etc)
    - fill_value - value used to in place of empty cells
    
    Returns:
    -flat table with data aggregrated and tabulated
    
    '''
    listOfTable = []
    for indexNumber in range(len(indices)):
        n = indexNumber+1
        if n == 1:
            table = pd.pivot_table(df,values=values,index=indices[:n],columns=columns,aggfunc=aggfunc,fill_value=fill_value,margins=True)
        else:
            table = pd.pivot_table(df,values=values,index=indices[:n],columns=columns,aggfunc=aggfunc,fill_value=fill_value)
        table = table.reset_index()
        for column in indices[n:]:
            table[column] = ''
        listOfTable.append(table)
    concatTable = pd.concat(listOfTable).sort_index()
    concatTable = concatTable.set_index(keys=indices)
    return concatTable.sort_index(axis=0,ascending=True)


def get_items(annee, location, db_conn, c2lDict, indices):
    query = f""" SELECT
        i.itemnumber,
        i.biblionumber,
        i.ccode,
        bi.itemtype,
        i.dateaccessioned,
        i.notforloan,
        i.itemlost,
        i.damaged,
        i.location,
        i.onloan,
        i.datelastborrowed
    FROM koha{annee}.items i
    JOIN koha{annee}.biblioitems bi ON bi.biblionumber = i.biblionumber
    WHERE i.notforloan NOT IN (3, 4) AND {location}"""
    data = pd.read_sql(query, con=db_conn)
    exemplaires = Document(df=data, con=db_conn, c2l=c2l.dict_codes_lib)
    exemplaires.get_doc_statdb_data()
    exemplaires.get_doc_es_data()
    
    for c in indices:
       exemplaires.df[c] = exemplaires.df[c].fillna('#1#2#3#4#5#')
    
    # nb exemplaires
    exemplaires.df['nb_exemplaires'] = 1
    
    # exemplaires empruntables
    exemplaires.df['nb_exemplaires_empruntables'] = 0
    exemplaires.df.loc[  (exemplaires.df['doc_statut_code'] == 0)
                       & (exemplaires.df['doc_statut_abime_code'] == 0)
                       & (exemplaires.df['doc_statut_perdu_code'] == 0), 'nb_exemplaires_empruntables'] = 1
    
    # exemplaires consultables sur place uniquement
    exemplaires.df['exemplaires_consultables_sur_place'] = 0
    exemplaires.df.loc[  (exemplaires.df['doc_statut_code'] == 2)
                       & (exemplaires.df['doc_statut_abime_code'] == 0)
                       & (exemplaires.df['doc_statut_perdu_code'] == 0), 'exemplaires_consultables_sur_place'] = 1
                       
    # exemplaires en libre accès
    exemplaires.df['nb_exemplaires_en_acces_libre'] = 0
    mag_location = ['MED0A', 'MED2C', 'MED2D', 'MED3C', 'MED3D', 'MED3E', 'MED3F', 'MED3G', 'MED3H', 'MED3I', 'MED3J', 'MED3K', 'MED3L', 'MED3M', 'MED3N', 'MED3O', 'MED3P', 'MED3Q', 'MED3R', 'MED3S', 'MED3T']
    exemplaires.df.loc[  (exemplaires.df['doc_statut_code'].isin([0, 2]))
                       & (exemplaires.df['doc_statut_abime_code'] == 0)
                       & (exemplaires.df['doc_statut_perdu_code'] == 0)
                       & (~exemplaires.df['doc_item_localisation_code'].isin(mag_location)), 'nb_exemplaires_en_acces_libre'] = 1
                       
    # exemplaires en accès indirect
    exemplaires.df['nb_exemplaires_en_acces_indirect'] = 0
    mag_location = ['MED0A', 'MED2C', 'MED2D', 'MED3C', 'MED3D', 'MED3E', 'MED3F', 'MED3G', 'MED3H', 'MED3I', 'MED3J', 'MED3K', 'MED3L', 'MED3M', 'MED3N', 'MED3O', 'MED3P', 'MED3Q', 'MED3R', 'MED3S', 'MED3T']
    exemplaires.df.loc[  (exemplaires.df['doc_statut_code'].isin([0, 2]))
                       & (exemplaires.df['doc_statut_abime_code'] == 0)
                       & (exemplaires.df['doc_statut_perdu_code'] == 0)
                       & (exemplaires.df['doc_item_localisation_code'].isin(mag_location)), 'nb_exemplaires_en_acces_indirect'] = 1
    
    # exemplaires en commande
    exemplaires.df['nb_exemplaires_en_commande'] = 0
    exemplaires.df.loc[  (exemplaires.df['doc_statut_code'] == -1)
                       & (exemplaires.df['doc_statut_abime_code'] == 0)
                       & (exemplaires.df['doc_statut_perdu_code'] == 0), 'nb_exemplaires_en_commande'] = 1

    # exemplaires en traitement
    exemplaires.df['nb_exemplaires_en_traitement'] = 0
    exemplaires.df.loc[  (exemplaires.df['doc_statut_code'] == -2)
                       & (exemplaires.df['doc_statut_abime_code'] == 0)
                       & (exemplaires.df['doc_statut_perdu_code'] == 0), 'nb_exemplaires_en_traitement'] = 1
                       
    # exemplaires en abîmé
    # COUNT(IF(i.notforloan != -4 AND i.damaged = 1 AND i.itemlost = 0, i.itemnumber, NULL)) AS 'nb_exemplaires_en_abîmés',
    exemplaires.df['nb_exemplaires_en_abîmés'] = 0
    exemplaires.df.loc[  (exemplaires.df['doc_statut_code'] != -4)
                       & (exemplaires.df['doc_statut_abime_code'] == 1)
                       & (exemplaires.df['doc_statut_perdu_code'] == 0), 'nb_exemplaires_en_abîmés'] = 1
    
    # exemplaires en réparation
    # COUNT(IF(i.notforloan = -4 AND i.itemlost = 0, i.itemnumber, NULL)) AS 'nb_exemplaires_en_réparation',
    exemplaires.df['nb_exemplaires_en_réparation'] = 0
    exemplaires.df.loc[  (exemplaires.df['doc_statut_code'] == -4)
                       & (exemplaires.df['doc_statut_abime_code'] == 1)
                       & (exemplaires.df['doc_statut_perdu_code'] == 0), 'nb_exemplaires_en_réparation'] = 1
    
    # exemplaires en retrait
    # COUNT(IF(i.notforloan = -3 AND i.damaged = 0 AND i.itemlost = 0, i.itemnumber, NULL)) AS 'nb_exemplaires_en_retrait',
    exemplaires.df['nb_exemplaires_en_retrait'] = 0
    exemplaires.df.loc[  (exemplaires.df['doc_statut_code'] == -3)
                       & (exemplaires.df['doc_statut_abime_code'] == 0)
                       & (exemplaires.df['doc_statut_perdu_code'] == 0), 'nb_exemplaires_en_retrait'] = 1    
    
    # exemplaires en reliure
    # COUNT(IF(i.notforloan = 5 AND i.damaged = 0 AND i.itemlost = 0, i.itemnumber, NULL)) AS 'nb_exemplaires_en_reliure',
    exemplaires.df['nb_exemplaires_en_reliure'] = 0
    exemplaires.df.loc[  (exemplaires.df['doc_statut_code'] == 5)
                       & (exemplaires.df['doc_statut_abime_code'] == 0)
                       & (exemplaires.df['doc_statut_perdu_code'] == 0), 'nb_exemplaires_en_reliure'] = 1    
    
    # exemplaires perdus
    # COUNT(IF(i.itemlost = 2, i.itemnumber, NULL)) AS 'nb_exemplaires_perdus',
    exemplaires.df['nb_exemplaires_perdus'] = 0
    exemplaires.df.loc[  (exemplaires.df['doc_statut_perdu_code'] == 2), 'nb_exemplaires_perdus'] = 1    
    
    # exemplaires non restitués
    # COUNT(IF(i.itemlost = 1, i.itemnumber, NULL)) AS 'nb_exemplaires_non_restitués',',
    exemplaires.df['nb_exemplaires_non_restitués'] = 0
    exemplaires.df.loc[  (exemplaires.df['doc_statut_perdu_code'].isin([1, 3])), 'nb_exemplaires_non_restitués'] = 1    
    
    # exemplaires créés dans l'année
    # COUNT(IF(i.dateaccessioned > ('2024-01-01' - INTERVAL 1 YEAR), i.itemnumber, NULL)) AS 'nb_exemplaires_créés_dans_annee'               
    exemplaires.df['doc_item_date_creation'] = pd.to_datetime(exemplaires.df['doc_item_date_creation'])       
    exemplaires.df['nb_exemplaires_créés_dans_annee'] = 0               
    exemplaires.df.loc[  (exemplaires.df['doc_item_date_creation'] >= datetime(int(annee), 1, 1)), 'nb_exemplaires_créés_dans_annee'] = 1

    # exemplaires nb_exemplaires_empruntables_pas_empruntés_1_an
    #COUNT(IF(i.notforloan NOT IN (-2, -1, 2) AND i.datelastborrowed <= ('2024-01-01' - INTERVAL 1 YEAR), i.itemnumber, NULL)) AS 'nb_exemplaires_empruntables_pas_empruntés_1_an',
    exemplaires.df['doc_usage_date_dernier_pret'] = pd.to_datetime(exemplaires.df['doc_usage_date_dernier_pret'])       
    exemplaires.df['nb_exemplaires_empruntables_pas_empruntés_1_an'] = 0               
    exemplaires.df.loc[  (exemplaires.df['doc_usage_date_dernier_pret'] <= datetime(int(annee), 1, 1)), 'nb_exemplaires_empruntables_pas_empruntés_1_an'] = 1
    
    # exemplaires nb_exemplaires_empruntables_pas_empruntés_3_an
    #COUNT(IF(i.notforloan NOT IN (-2, -1, 2) AND i.datelastborrowed <= ('2024-01-01' - INTERVAL 3 YEAR), i.itemnumber, NULL)) AS 'nb_exemplaires_empruntables_pas_empruntés_3_ans',
    exemplaires.df['nb_exemplaires_empruntables_pas_empruntés_3_an'] = 0               
    exemplaires.df.loc[  (exemplaires.df['doc_usage_date_dernier_pret'] <= datetime(int(annee) - 2, 1, 1)), 'nb_exemplaires_empruntables_pas_empruntés_3_an'] = 1
    
    # exemplaires en prêt
    #COUNT(IF(i.onloan IS NOT NULL OR i.itemlost = 1, i.itemnumber, NULL)) AS 'nb_exemplaires_en_pret'    
    exemplaires.df['nb_exemplaires_en_pret'] = 0               
    exemplaires.df.loc[  (exemplaires.df['doc_usage_emprunt_date'].notna()) | (exemplaires.df['doc_statut_perdu_code'].isin([1, 3])), 'nb_exemplaires_en_pret'] = 1                   

    values = ['nb_exemplaires', 'nb_exemplaires_empruntables', 'exemplaires_consultables_sur_place',
              'nb_exemplaires_en_acces_libre', 'nb_exemplaires_en_acces_indirect', 'nb_exemplaires_en_commande',
              'nb_exemplaires_en_traitement', 'nb_exemplaires_en_abîmés', 'nb_exemplaires_en_réparation',
              'nb_exemplaires_en_retrait', 'nb_exemplaires_en_reliure', 'nb_exemplaires_perdus',
              'nb_exemplaires_non_restitués', 'nb_exemplaires_créés_dans_annee',
              'nb_exemplaires_empruntables_pas_empruntés_1_an', 'nb_exemplaires_empruntables_pas_empruntés_3_an', 'nb_exemplaires_en_pret']
              
    exemplaires_gr_nb = pivot_table_w_subtotals(df=exemplaires.df,
                                             values = values,
                                             indices = indices,
                                             columns=[],
                                             aggfunc='sum',
                                             fill_value=0)
                             
    return exemplaires_gr_nb


def get_issues(annee, location, db_conn, c2lDict, indices):
    query = f"""SELECT
        i.issuedate,
        i.borrowernumber, 
        i.itemnumber,
        i.location,
        i.ccode, 
        i.itemtype,
        i.biblionumber
    FROM statdb.stat_issues i
    WHERE YEAR(i.issuedate) >= {int(annee) - 3}
    AND YEAR(i.issuedate) <= {int(annee)}
    AND {location}"""
    
    data = pd.read_sql(query, con=db_conn)
    prets = Pret(df=data, con=db_conn, c2l=c2l.dict_codes_lib)
    prets.get_doc_statdb_data()
    prets.get_pret_date_pret()
    prets.get_doc_es_data()
    
    for c in indices:
       prets.df[c] = prets.df[c].fillna('#1#2#3#4#5#')
    
    prets.df['nb_prets'] = 1
    
    prets.df['pret_date_pret'] = pd.to_datetime(prets.df['pret_date_pret'])
    prets.df['pret_date_pret_annee'] = prets.df['pret_date_pret'].dt.year.astype(str)
    prets.df['annnee_pret'] = 1
    
    idx_gr = [idx for idx in indices]
    idx_gr.append('pret_date_pret_annee')
    prets_gr = prets.df.groupby(idx_gr).agg({"nb_prets": np.sum, "borrowernumber": pd.Series.nunique, "itemnumber": pd.Series.nunique}).reset_index().rename(columns={'borrowernumber':'nb_emprunteurs_distincts', 'itemnumber':'nb_prets_exemplaires_distincts'})
    
    prets_pv = pivot_table_w_subtotals(df=prets_gr,
                                       values = ['nb_prets'],
                                       indices = indices,
                                       columns=['pret_date_pret_annee'],
                                       aggfunc='sum',
                                       fill_value=0)
    prets_pv.columns = ['_'.join(col) for col in prets_pv.columns.values]
    
    idxx = []
    emprunteurs_2024 = []
    emprunteurs_2023 = []
    emprunteurs_2022 = []
    exemplaires_2024 = []
    exemplaires_2023 = []
    exemplaires_2022 = []
    
    print("-------- distincts")
    p = prets.df
    for idx in prets_pv.index:
        print(f"-------- distincts : {idx}")
        if idx[4] != '':
            e2024 = p['borrowernumber'][(p['pret_date_pret_annee'] == '2024')
                                      & (p['doc_item_collection_lib1'] == idx[0])
                                      & (p['doc_item_collection_lib2'] == idx[1])
                                      & (p['doc_item_collection_lib3'] == idx[2])
                                      & (p['doc_item_collection_lib4'] == idx[3])
                                      & (p['doc_biblio_support'] == idx[4])].nunique()
            e2023 = p['borrowernumber'][(p['pret_date_pret_annee'] == '2023')
                                      & (p['doc_item_collection_lib1'] == idx[0])
                                      & (p['doc_item_collection_lib2'] == idx[1])
                                      & (p['doc_item_collection_lib3'] == idx[2])
                                      & (p['doc_item_collection_lib4'] == idx[3])
                                      & (p['doc_biblio_support'] == idx[4])].nunique()
            e2022 = p['borrowernumber'][(p['pret_date_pret_annee'] == '2022')
                                      & (p['doc_item_collection_lib1'] == idx[0])
                                      & (p['doc_item_collection_lib2'] == idx[1])
                                      & (p['doc_item_collection_lib3'] == idx[2])
                                      & (p['doc_item_collection_lib4'] == idx[3])
                                      & (p['doc_biblio_support'] == idx[4])].nunique()
            ex2024 = p['itemnumber'][(p['pret_date_pret_annee'] == '2024')
                                      & (p['doc_item_collection_lib1'] == idx[0])
                                      & (p['doc_item_collection_lib2'] == idx[1])
                                      & (p['doc_item_collection_lib3'] == idx[2])
                                      & (p['doc_item_collection_lib4'] == idx[3])
                                      & (p['doc_biblio_support'] == idx[4])].nunique()
            ex2023 = p['itemnumber'][(p['pret_date_pret_annee'] == '2023')
                                      & (p['doc_item_collection_lib1'] == idx[0])
                                      & (p['doc_item_collection_lib2'] == idx[1])
                                      & (p['doc_item_collection_lib3'] == idx[2])
                                      & (p['doc_item_collection_lib4'] == idx[3])
                                      & (p['doc_biblio_support'] == idx[4])].nunique()
            ex2022 = p['itemnumber'][(p['pret_date_pret_annee'] == '2022')
                                      & (p['doc_item_collection_lib1'] == idx[0])
                                      & (p['doc_item_collection_lib2'] == idx[1])
                                      & (p['doc_item_collection_lib3'] == idx[2])
                                      & (p['doc_item_collection_lib4'] == idx[3])
                                      & (p['doc_biblio_support'] == idx[4])].nunique()                                      
                                      
        elif idx[4] == '' and idx[3] != '':
            e2024 = p['borrowernumber'][(p['pret_date_pret_annee'] == '2024')
                                      & (p['doc_item_collection_lib1'] == idx[0])
                                      & (p['doc_item_collection_lib2'] == idx[1])
                                      & (p['doc_item_collection_lib3'] == idx[2])
                                      & (p['doc_item_collection_lib4'] == idx[3])].nunique()
            e2023 = p['borrowernumber'][(p['pret_date_pret_annee'] == '2023')
                                      & (p['doc_item_collection_lib1'] == idx[0])
                                      & (p['doc_item_collection_lib2'] == idx[1])
                                      & (p['doc_item_collection_lib3'] == idx[2])
                                      & (p['doc_item_collection_lib4'] == idx[3])].nunique()
            e2022 = p['borrowernumber'][(p['pret_date_pret_annee'] == '2022')
                                      & (p['doc_item_collection_lib1'] == idx[0])
                                      & (p['doc_item_collection_lib2'] == idx[1])
                                      & (p['doc_item_collection_lib3'] == idx[2])
                                      & (p['doc_item_collection_lib4'] == idx[3])].nunique()
            ex2024 = p['itemnumber'][(p['pret_date_pret_annee'] == '2024')
                                      & (p['doc_item_collection_lib1'] == idx[0])
                                      & (p['doc_item_collection_lib2'] == idx[1])
                                      & (p['doc_item_collection_lib3'] == idx[2])
                                      & (p['doc_item_collection_lib4'] == idx[3])].nunique()
            ex2023 = p['itemnumber'][(p['pret_date_pret_annee'] == '2023')
                                      & (p['doc_item_collection_lib1'] == idx[0])
                                      & (p['doc_item_collection_lib2'] == idx[1])
                                      & (p['doc_item_collection_lib3'] == idx[2])
                                      & (p['doc_item_collection_lib4'] == idx[3])].nunique()
            ex2022 = p['itemnumber'][(p['pret_date_pret_annee'] == '2022')
                                      & (p['doc_item_collection_lib1'] == idx[0])
                                      & (p['doc_item_collection_lib2'] == idx[1])
                                      & (p['doc_item_collection_lib3'] == idx[2])
                                      & (p['doc_item_collection_lib4'] == idx[3])].nunique()
        elif idx[3] == '' and idx[2] != '':
            e2024 = p['borrowernumber'][(p['pret_date_pret_annee'] == '2024')
                                      & (p['doc_item_collection_lib1'] == idx[0])
                                      & (p['doc_item_collection_lib2'] == idx[1])
                                      & (p['doc_item_collection_lib3'] == idx[2])].nunique()
            e2023 = p['borrowernumber'][(p['pret_date_pret_annee'] == '2023')
                                      & (p['doc_item_collection_lib1'] == idx[0])
                                      & (p['doc_item_collection_lib2'] == idx[1])
                                      & (p['doc_item_collection_lib3'] == idx[2])].nunique()
            e2022 = p['borrowernumber'][(p['pret_date_pret_annee'] == '2022')
                                      & (p['doc_item_collection_lib1'] == idx[0])
                                      & (p['doc_item_collection_lib2'] == idx[1])
                                      & (p['doc_item_collection_lib3'] == idx[2])].nunique()
            ex2024 = p['itemnumber'][(p['pret_date_pret_annee'] == '2024')
                                      & (p['doc_item_collection_lib1'] == idx[0])
                                      & (p['doc_item_collection_lib2'] == idx[1])
                                      & (p['doc_item_collection_lib3'] == idx[2])].nunique()
            ex2023 = p['itemnumber'][(p['pret_date_pret_annee'] == '2023')
                                      & (p['doc_item_collection_lib1'] == idx[0])
                                      & (p['doc_item_collection_lib2'] == idx[1])
                                      & (p['doc_item_collection_lib3'] == idx[2])].nunique()
            ex2022 = p['itemnumber'][(p['pret_date_pret_annee'] == '2022')
                                      & (p['doc_item_collection_lib1'] == idx[0])
                                      & (p['doc_item_collection_lib2'] == idx[1])
                                      & (p['doc_item_collection_lib3'] == idx[2])].nunique()
        elif idx[2] == '' and idx[1] != '':
            e2024 = p['borrowernumber'][(p['pret_date_pret_annee'] == '2024')
                                      & (p['doc_item_collection_lib1'] == idx[0])
                                      & (p['doc_item_collection_lib2'] == idx[1])].nunique()
            e2023 = p['borrowernumber'][(p['pret_date_pret_annee'] == '2023')
                                      & (p['doc_item_collection_lib1'] == idx[0])
                                      & (p['doc_item_collection_lib2'] == idx[1])].nunique()
            e2022 = p['borrowernumber'][(p['pret_date_pret_annee'] == '2022')
                                      & (p['doc_item_collection_lib1'] == idx[0])
                                      & (p['doc_item_collection_lib2'] == idx[1])].nunique()
            ex2024 = p['itemnumber'][(p['pret_date_pret_annee'] == '2024')
                                      & (p['doc_item_collection_lib1'] == idx[0])
                                      & (p['doc_item_collection_lib2'] == idx[1])].nunique()
            ex2023 = p['itemnumber'][(p['pret_date_pret_annee'] == '2023')
                                      & (p['doc_item_collection_lib1'] == idx[0])
                                      & (p['doc_item_collection_lib2'] == idx[1])].nunique()
            ex2022 = p['itemnumber'][(p['pret_date_pret_annee'] == '2022')
                                      & (p['doc_item_collection_lib1'] == idx[0])
                                      & (p['doc_item_collection_lib2'] == idx[1])].nunique()
        elif idx[1] == '' and idx[0] != '' and idx[0] != 'All':
            e2024 = p['borrowernumber'][(p['pret_date_pret_annee'] == '2024')
                                      & (p['doc_item_collection_lib1'] == idx[0])].nunique()
            e2023 = p['borrowernumber'][(p['pret_date_pret_annee'] == '2023')
                                      & (p['doc_item_collection_lib1'] == idx[0])].nunique()
            e2022 = p['borrowernumber'][(p['pret_date_pret_annee'] == '2022')
                                      & (p['doc_item_collection_lib1'] == idx[0])].nunique()
            ex2024 = p['itemnumber'][(p['pret_date_pret_annee'] == '2024')
                                      & (p['doc_item_collection_lib1'] == idx[0])].nunique()
            ex2023 = p['itemnumber'][(p['pret_date_pret_annee'] == '2023')
                                      & (p['doc_item_collection_lib1'] == idx[0])].nunique()
            ex2022 = p['itemnumber'][(p['pret_date_pret_annee'] == '2022')
                                      & (p['doc_item_collection_lib1'] == idx[0])].nunique()
        elif idx[0] == 'All':
            e2024 = p['borrowernumber'][(p['pret_date_pret_annee'] == '2024')].nunique()
            e2023 = p['borrowernumber'][(p['pret_date_pret_annee'] == '2023')].nunique()
            e2022 = p['borrowernumber'][(p['pret_date_pret_annee'] == '2022')].nunique()
            ex2024 = p['itemnumber'][(p['pret_date_pret_annee'] == '2024')].nunique()
            ex2023 = p['itemnumber'][(p['pret_date_pret_annee'] == '2023')].nunique()
            ex2022 = p['itemnumber'][(p['pret_date_pret_annee'] == '2022')].nunique()
                                      
        idxx.append(idx)
        emprunteurs_2024.append(e2024)
        emprunteurs_2023.append(e2023)
        emprunteurs_2022.append(e2022)
        exemplaires_2024.append(ex2024)
        exemplaires_2023.append(ex2023)
        exemplaires_2022.append(ex2022)
    
    prets_pv['nb_prets_exemplaires_distincts_2022'] = exemplaires_2022
    prets_pv['nb_prets_exemplaires_distincts_2023'] = exemplaires_2023
    prets_pv['nb_prets_exemplaires_distincts_2024'] = exemplaires_2024
    
    prets_pv['nb_emprunteurs_distincts_2022'] = emprunteurs_2022
    prets_pv['nb_emprunteurs_distincts_2023'] = emprunteurs_2023
    prets_pv['nb_emprunteurs_distincts_2024'] = emprunteurs_2024    
    
    res = prets_pv
    return res
    
def get_eliminations(annee, location, db_conn, c2lDict, indices):
    query = f""" SELECT
        i.itemnumber,
        i.biblionumber,
        i.ccode,
        i.itemtype,
        i.dateaccessioned,
        i.notforloan,
        i.itemlost,
        i.damaged,
        i.location,
        i.onloan,
        i.datelastborrowed,
        i.motif
    FROM statdb.stat_eliminations i
    WHERE i.annee_mise_pilon = '2024' AND {location}"""

    data = pd.read_sql(query, con=db_conn)
    eliminations = Document(df=data, con=db_conn, c2l=c2l.dict_codes_lib)
    eliminations.get_doc_statdb_data()
    eliminations.get_doc_es_data()

    for c in indices:
       eliminations.df[c] = eliminations.df[c].fillna('#1#2#3#4#5#')
       
    # nb exemplaires éliminés
    eliminations.df['nb_exemplaires_elimines'] = 1
    
    # nb_exemplaires_elimines_non_restitues
    eliminations.df['nb_exemplaires_elimines_non_restitues'] = 0
    eliminations.df.loc[  (eliminations.df['motif'] == 'non restitué'), 'nb_exemplaires_elimines_non_restitues'] = 1

    # nb_exemplaires_elimines_perdus
    eliminations.df['nb_exemplaires_elimines_perdus'] = 0
    eliminations.df.loc[  (eliminations.df['motif'] == 'perdu'), 'nb_exemplaires_elimines_perdus'] = 1

    # nb_exemplaires_elimines_abimes
    eliminations.df['nb_exemplaires_elimines_abimes'] = 0
    eliminations.df.loc[  (eliminations.df['motif'] == 'abîmé'), 'nb_exemplaires_elimines_abimes'] = 1

    # nb_exemplaires_elimines_desherbes
    eliminations.df['nb_exemplaires_elimines_desherbes'] = 0
    eliminations.df.loc[  (eliminations.df['motif'] == 'désherbé'), 'nb_exemplaires_elimines_desherbes'] = 1
    
    
    values = ['nb_exemplaires_elimines', 'nb_exemplaires_elimines_non_restitues', 'nb_exemplaires_elimines_perdus', 'nb_exemplaires_elimines_abimes', 'nb_exemplaires_elimines_desherbes']
    
    eliminations_gr = pivot_table_w_subtotals(df=eliminations.df,
                                             values = values,
                                             indices = indices,
                                             columns=[],
                                             aggfunc='sum',
                                             fill_value=0)
    
    return eliminations_gr

    
annee = '2024'

sites = [
    {
        'nom': 'Grand-Plage',
        'code': 'GPL'
    },
    {
        'nom': 'Médiathèque',
        'code': 'MED'
    },
    {
        'nom': 'Collectivités',
        'code': 'COL'
    },
    {
        'nom': 'Zèbre',
        'code': 'BUS'
    }
]


test = [{
        'nom': 'Zèbre',
        'code': 'BUS'
    }]


db_conn = DbConn().create_engine()

c2l = Code2Libelle(db_conn)
c2l.get_val()

writer = pd.ExcelWriter('../data/Statistiques_collections_2024.xlsx', engine='xlsxwriter')
workbook = writer.book
fmt_rate = workbook.add_format({
 "num_format" : "0.0 %" , "bold" : False
})

for site in sites:
    print(site['code'])
    location = get_location(site['code'])
    indices = ['doc_item_collection_lib1', 'doc_item_collection_lib2', 'doc_item_collection_lib3', 'doc_item_collection_lib4', 'doc_biblio_support']
    print("---- items")
    ex = get_items(annee, location, db_conn, c2l.dict_codes_lib, indices)
    print("---- issues")
    pts = get_issues(annee, location, db_conn, c2l.dict_codes_lib, indices)
    print("---- eliminations")
    el = get_eliminations(annee, location, db_conn, c2l.dict_codes_lib, indices)
    stats = pd.merge(ex, pts, how='left', on=indices)
    stats = pd.merge(stats, el, how='left', on=indices)
    
    stats.to_csv(f"../data/Statistiques_collections_2024_TMP2_{site['code']}.csv")
    
    print("---- tx")
    stats['evolution_prets_2022-2023'] = (stats['nb_prets_2023'] - stats['nb_prets_2022']) / stats['nb_prets_2022']
    stats['evolution_prets_2022-2024'] = (stats['nb_prets_2024'] - stats['nb_prets_2022']) / stats['nb_prets_2022']
    stats['evolution_prets_2023-2024'] = (stats['nb_prets_2024'] - stats['nb_prets_2023']) / stats['nb_prets_2023']
    
    stats['evolution_prets_exemplaires_distincts_2022-2023'] = (stats['nb_prets_exemplaires_distincts_2023'] - stats['nb_prets_exemplaires_distincts_2022']) / stats['nb_prets_exemplaires_distincts_2022']
    stats['evolution_prets_exemplaires_distincts_2022-2024'] = (stats['nb_prets_exemplaires_distincts_2024'] - stats['nb_prets_exemplaires_distincts_2022']) / stats['nb_prets_exemplaires_distincts_2022']
    stats['evolution_prets_exemplaires_distincts_2023-2024'] = (stats['nb_prets_exemplaires_distincts_2024'] - stats['nb_prets_exemplaires_distincts_2023']) / stats['nb_prets_exemplaires_distincts_2023']
    
    stats['tx_rotation'] = round( stats['nb_prets_2024'] / stats['nb_exemplaires_empruntables'], 1)
    stats['tx_fond_actif'] =  stats['nb_prets_exemplaires_distincts_2024'] / stats['nb_exemplaires_empruntables']
    stats['tx_collection_non_empruntee_3_ans'] =  stats['nb_exemplaires_empruntables_pas_empruntés_3_an'] / stats['nb_exemplaires_empruntables']
    stats['tx_sortie'] =  stats['nb_exemplaires_en_pret'] / stats['nb_exemplaires_empruntables']
    stats['tx_non_restitues'] =  stats['nb_exemplaires_non_restitués'] / stats['nb_exemplaires_empruntables']
    stats['tx_renouvellement'] =  stats['nb_exemplaires_créés_dans_annee'] / stats['nb_exemplaires']
    stats['tx_accroissement'] =  (stats['nb_exemplaires_créés_dans_annee'] - stats['nb_exemplaires_elimines'] ) / stats['nb_exemplaires']

    stats['evolution_emprunteurs_distincts_2022-2023'] = (stats['nb_emprunteurs_distincts_2023'] - stats['nb_emprunteurs_distincts_2022']) / stats['nb_emprunteurs_distincts_2022']
    stats['evolution_emprunteurs_distincts_2022-2024'] = (stats['nb_emprunteurs_distincts_2024'] - stats['nb_emprunteurs_distincts_2022']) / stats['nb_emprunteurs_distincts_2022']
    stats['evolution_emprunteurs_distincts_2023-2024'] = (stats['nb_emprunteurs_distincts_2024'] - stats['nb_emprunteurs_distincts_2023']) / stats['nb_emprunteurs_distincts_2023']
    
    stats = stats[stats['nb_exemplaires'] >= 10]
    
    stats = stats.replace(0, np.nan)
       
    stats = stats[['nb_exemplaires', 'nb_exemplaires_empruntables', 'exemplaires_consultables_sur_place',
                   'nb_exemplaires_en_acces_libre', 'nb_exemplaires_en_acces_indirect', 'nb_exemplaires_en_commande',
                   'nb_exemplaires_en_traitement', 'nb_exemplaires_en_abîmés', 'nb_exemplaires_en_réparation', 'nb_exemplaires_en_retrait',
                   'nb_exemplaires_en_reliure', 'nb_exemplaires_perdus', 'nb_exemplaires_non_restitués', 'nb_exemplaires_créés_dans_annee',
                   'nb_exemplaires_elimines', 'nb_exemplaires_elimines_non_restitues', 'nb_exemplaires_elimines_perdus',
                   'nb_exemplaires_elimines_abimes', 'nb_exemplaires_elimines_desherbes', 'nb_prets_2022',
                   'nb_prets_exemplaires_distincts_2022', 'nb_prets_2023', 'nb_prets_exemplaires_distincts_2023', 'nb_prets_2024',
                   'nb_prets_exemplaires_distincts_2024', 'nb_exemplaires_empruntables_pas_empruntés_1_an',
                   'nb_exemplaires_empruntables_pas_empruntés_3_an', 'nb_exemplaires_en_pret', 'evolution_prets_2022-2023',
                   'evolution_prets_2022-2024', 'evolution_prets_2023-2024', 'evolution_prets_exemplaires_distincts_2022-2023',
                   'evolution_prets_exemplaires_distincts_2022-2024', 'evolution_prets_exemplaires_distincts_2023-2024', 'tx_rotation',
                   'tx_fond_actif', 'tx_collection_non_empruntee_3_ans', 'tx_sortie', 'tx_non_restitues', 'tx_renouvellement',
                   'tx_accroissement', 'nb_emprunteurs_distincts_2022', 'nb_emprunteurs_distincts_2023', 'nb_emprunteurs_distincts_2024',
                   'evolution_emprunteurs_distincts_2022-2023', 'evolution_emprunteurs_distincts_2022-2024',
                   'evolution_emprunteurs_distincts_2023-2024']]
                   
    stats.columns = ["exemplaires", "exemplaires empruntables", "exemplaires consultables sur place uniquement", "exemplaires en accès libre",
                     "exemplaires en accès indirect", "exemplaires en commande", "exemplaires en traitement", "exemplaires en abîmés", "exemplaires en réparation",
                     "exemplaires en retrait", "exemplaires en reliure", "exemplaires perdus", "exemplaires non restitués", "exemplaires créés dans annee", "exemplaires éliminés",
                     "exemplaires éliminés non restitués", "exemplaires éliminés perdus", "exemplaires éliminés abîmés", "exemplaires éliminés désherbés", "prêts 2022",
                     "prêts 2022 exemplaires distincts", "prêts 2023", "prêts 2023 exemplaires distincts", "prêts 2024", "prêts 2024 exemplaires distincts",
                     "exemplaires empruntables pas empruntés 1 an", "exemplaires empruntables pas empruntés 3 ans", "exemplaires en prêt", "évolution prêts 2022-2023",
                     "évolution prêts 2022-2024", "évolution prêts 2023-2024", "évolution exemplaires distincts prêtés 2022-2023", "évolution exemplaires distincts prêtés 2022-2024",
                     "évolution exemplaires distincts prêtés 2023-2024", "taux de rotation", "taux de fonds actif", "part collection non empruntée depuis 3 ans", "taux de sortie",
                     "taux de non restitués", "taux renouvellement", "taux d'accroissement", "emprunteurs distincts 2022", "emprunteurs distincts 2023", "emprunteurs distincts 2024",
                     "évolution emprunteurs distincts 2022-2023", "évolution emprunteurs distincts 2022-2024", "évolution emprunteurs distincts 2023-2024"]
 
    
    stats.to_excel(writer, sheet_name=site['nom'])
    worksheet = writer.sheets[site['nom']]
    worksheet.set_column("AH:AM", 10, fmt_rate)
    worksheet.set_column("AO:AT", 10, fmt_rate)
    worksheet.set_column("AX:AZ", 10, fmt_rate)
        
    
writer.close()
    