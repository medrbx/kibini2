import pandas as pd

def issues_without_merged(df, df2):
    df = pd.merge(df,
                               df2[['issue_id', 'borrowernumber', 'itemnumber', 'issuedate',]],
                               how='outer',
                               on='issue_id',
                               indicator=True)
    df = df[df._merge == 'left_only'].drop('_merge', axis=1)
    df = df.rename(columns={'borrowernumber_x':'borrowernumber',
                            'itemnumber_x':'itemnumber',
                            'issuedate_x':'issuedate'})
    return df.drop(columns=['borrowernumber_y', 'itemnumber_y', 'issuedate_y'])

def prets_without_merged(df, df2):
    df = pd.merge(df,
                           df2[['pret_id', 'borrowernumber', 'itemnumber', 'issuedate',]],
                           how='outer',
                           on='pret_id',
                           indicator=True)
    df = df[df._merge == 'left_only'].drop('_merge', axis=1)
    df = df.rename(columns={'borrowernumber_x':'borrowernumber',
                                                 'itemnumber_x':'itemnumber',
                                                 'issuedate_x':'issuedate'})
    return df.drop(columns=['borrowernumber_y', 'itemnumber_y', 'issuedate_y'])

prets = pd.read_csv("data/stat_prets_202004271042.csv")
prets = prets.drop(columns=['pret_koha_id'])
prets = prets.rename(columns={'pret_date':'issuedate', 'doc_item_id':'itemnumber'})
prets['issuedate'] = pd.to_datetime(prets['issuedate'])
prets['issuedate_key'] = prets['issuedate'].dt.strftime('%Y_%m_%d_%H_%M')

issues = pd.read_csv("data/issues_all.csv")
issues['issuedate'] = pd.to_datetime(issues['issuedate'])
issues['issuedate_key'] = issues['issuedate'].dt.strftime('%Y_%m_%d_%H_%M')

issues_to_merge = issues
prets_to_merge = prets

### Etape 1
merged_1 = issues_to_merge.merge(prets_to_merge, how='inner', on=['issuedate', 'itemnumber', 'borrowernumber'])
merged = merged_1
# On retire les éléments fusionnés de issues
issues_to_merge = issues_without_merged(issues_to_merge, merged)
# On retire les éléments fusionnés de prets
prets_to_merge = prets_without_merged(prets_to_merge, merged)



### Etape 2
merged_2 = issues_to_merge.merge(prets_to_merge, how='inner', on=['issuedate', 'itemnumber'])
merged = pd.concat([merged, merged_2])
## On retire les éléments fusionnés de issues
issues_to_merge = issues_without_merged(issues_to_merge, merged)
# On retire les éléments fusionnés de prets
prets_to_merge = prets_without_merged(prets_to_merge, merged)



### Etape 3
merged_3 = issues_to_merge.merge(prets_to_merge, how='inner', on=['issuedate_key', 'itemnumber'])
merged = pd.concat([merged, merged_3])
# On retire les éléments fusionnés de issues
issues_to_merge = issues_without_merged(issues_to_merge, merged)
# On retire les éléments fusionnés de prets
prets_to_merge = prets_without_merged(prets_to_merge, merged)
