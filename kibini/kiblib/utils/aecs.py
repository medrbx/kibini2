import pandas as pd
import numpy as np
import seaborn as sns
import re
from datetime import datetime as dt
from matplotlib import pyplot as plt
import warnings
warnings.filterwarnings("ignore")

class AECS():
    def __init__(self):        
        sheets2keep = ['Baptiste',
                       'Bruno',
                       'Céline',
                       'Esther',
                       'Gwen',
                       'Hélène',
                       'Inès',
                       'Laetitia C',
                       'Laetitia D',
                       'Mathilde M',
                       'Pascale',
                       'Zina'
                      ]
        
        
        data_date = '20250917'
        filepath_data = f'../data/aecs/tableaux_suivi_AECS_{data_date}.xlsx'
        self.df = pd.read_excel(filepath_data,
                                sheet_name=sheets2keep,
                                #dtype={"Date début action":"Datetime64"}
                               )
        
        self.df = pd.concat(self.df)
        
        self.df.loc[self.df['Nb adultes touchés']>100,'ANOMALIE Nb adultes touchés']='oui'
        self.df.loc[self.df['Nb enfants touchés']>100,'ANOMALIE Nb enfants touchés']='oui'
        
        self.df['Nb actions'] = 1
        
        
    def get_Statistiques(self,
                         print_result=False,
                         filter_on=None,
                         method = None,
                         group_by_what = [],
                         total_on = [],
                         count_actions_numbers=False,
                        ):
        
        if filter_on == 'ac':
            self.stats = self.df[self.df.index.get_level_values(0)=='Mathilde M'] # On ne garde que le feuille Excel de Mathilde
            
        if filter_on == 'aecs':
            self.stats = self.df[self.df.index.get_level_values(0)!='Mathilde M'] # On exclut la feuille Excel de Mathilde
        
        self.stats['Date début action'] = pd.to_datetime(self.stats['Date début action'],
                                             errors='coerce',
                                             format='%Y-%m-%d %H:%M:%S')
        
        self.stats['annee'] = pd.DatetimeIndex(self.stats['Date début action']).year
        
            
        self.stats = self.stats.groupby(group_by_what)[total_on].sum()
        return(self.stats)
        