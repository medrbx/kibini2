import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime as dt, date


#V2

class EvolutionActivite:
    def __init__(self,df,df_subject,text):
        self.df = df
        self.column = df.iloc[:,1]
        self.df_subject = df_subject
        self.text = text
    
    def add_columns(self):
        self.df[f'nombre_{self.df_subject}'] = 1
        self.df['semaine'] = pd.DatetimeIndex(self.df[self.df.columns[0]]).week
        self.df['annee'] = pd.DatetimeIndex(self.df[self.df.columns[0]]).year
        self.df = self.df[self.df['annee'].isin([2023,2024,2025])]
        #return(self.df)
    
    def evolution_byweek_thisyear(self):
        stats_2025 = self.df[self.df['annee']==2025]
        stat_2025 = stats_2025.groupby('semaine')[self.df.columns[2]].sum().reset_index()
        return(stat_2025)
        
    
    def evolution_hebdo_resume(self):
        stats_2025_resume = self.df[self.df['annee']==2025]
        stats_2025_resume = stats_2025_resume.groupby('semaine')[self.df.columns[2]].sum().reset_index()
        mean_2025 = np.int64(round(stats_2025_resume.iloc[:,1].mean(),0))
        sum_2025 = stats_2025_resume.iloc[:,1].sum()
        return(f"Depuis le debut de l annee, on compte au total {sum_2025} {self.text} avec en moyenne {mean_2025} {self.text} par semaine")
        #return(stat_2025_resume)
    
    def evolution_4lastweek(self):
        semaine_max = date.today().isocalendar()[1] - 1
        semaine_min = semaine_max - 4
        stats_4lastweek = self.df[self.df['annee'].isin([2023,2024,2025])]
        stats_4lastweek = self.df[self.df['semaine'].between(semaine_min,semaine_max)]
        stats_4lastweek = stats_4lastweek.groupby(['annee','semaine'])[self.df.columns[2]].sum().reset_index()
        return(stats_4lastweek)
    
    def evolution_by_year(self):
        #stats_year = self.df[self.df['annee'].isin([2023,2024,2025])]
        stats_year = self.df.groupby('annee')[self.df.columns[2]].sum().reset_index()
        return(stats_year)
        
    def distinct_evolution_byweek_thisyear(self):
        distinct_stats_2025 = self.df[self.df['annee']==2025]
        distinct_stats_2025 = distinct_stats_2025.groupby('semaine')[self.df.columns[1]].nunique().reset_index()
        distinct_stats_2025 = distinct_stats_2025.rename(columns={self.df.columns[1]:f"nombre_usagers_distincts_{self.df_subject}"})
        return(distinct_stats_2025)
        
        
        
    def distinct_evolution_4lastweek(self):
        semaine_max = date.today().isocalendar()[1] - 1
        semaine_min = semaine_max - 4
        distinct_stats_4lastweek =  self.df[self.df['annee'].isin([2023,2024,2025])]
        distinct_stats_4lastweek = self.df[self.df['semaine'].between(semaine_min,semaine_max)]
        distinct_stats_4lastweek = distinct_stats_4lastweek.groupby(['annee','semaine'])[self.df.columns[1]].nunique().reset_index()
        distinct_stats_4lastweek = distinct_stats_4lastweek.rename(columns={self.df.columns[1]:f"nombre_usagers_distincts_{self.df_subject}"})
        return(distinct_stats_4lastweek)
        
    def distinct_evolution_by_year(self):
        #distinct_stats_year =  self.df[self.df['annee'].isin([2023,2024,2025])]
        distinct_stats_year = self.df.groupby('annee')[self.df.columns[1]].nunique().reset_index()
        distinct_stats_year = distinct_stats_year.rename(columns={self.df.columns[1]:f"nombre_usagers_distincts_{self.df_subject}"})
        return(distinct_stats_year)


    def titre_graph1(self):
        return(f"Evolution du nombre de {self.text} par semaine en 2025")
    

    def titre_graph2(self):
        return(f"Evolution du nombre de {self.text} des 4 dernieres semaines\nComparatif annuel")
        
    
    def titre_graph3(self):
        return(f"Evolution du nombre de {self.text} par an depuis 2019")  
        
    def titre_graph4(self):
      return("Evolution du nombre de personnes distinctes utilisant le service par semaine en 2025")
      
    def titre_graph5(self):
      return("Evolution du nombre de personnes distinctes sur les 4 dernieres semaines\nComparatif annuel")
      
    def titre_graph6(self):
      return("Evolution du nombre de personnes distinctes utilisant le service par an depuis 2019")
