import pandas as pd
from kiblib.utils.db import DbConn
from kiblib.utils.code2libelle import Code2Libelle
from kiblib.pret import Pret

engine = DbConn().create_engine()
c2l = Code2Libelle(engine)
c2l.get_val()

for i, chunk in enumerate(pd.read_csv("../../data/stat_issues_20200128.tsv",
                                      sep="\t", low_memory=False,
                                      chunksize= 10000)):
    print(i)
    chunk = chunk.drop(columns=['issue_id'])
    chunk = chunk.rename(columns={
                                       'branch': 'issue_branchcode',
                                       'sexe': 'adh_sexe_code',
                                       'arret_bus': 'pret_bus_arret_code',
                                       'ville': 'city',
                                       'iris': 'adh_geo_rbx_iris_code',
                                       'fidelite': 'adh_inscription_nb_annees_adhesion'
                                 })
    pret = Pret(df=chunk, engine=engine, c2l=c2l.dict_codes_lib)
    pret.get_pret_statdb_data()
    #print(pret.df['borrowernumber'])
    pret.pret_statdb_columns.to_sql('stat_prets', index=False, con=engine, if_exists='append')
    #print(pret.df['adh_age_code'])
    #print(pret.c2l['age'])
    #pret.pret_statdb_columns.to_csv(f"data/test_prets/chunk_{i:03d}.csv", header=True, index=False)
