import numpy as np
import pandas as pd

from datetime import datetime as dt

data_filepath = "../vacances_scolaires_fr.csv"
#data_filepath_2 = "/home/kibini/kibini2/kibini/kiblib/vacances_scolaires_fr.csv"

class Vacances():

  def __init__(self):
    self.df_vacances = pd.read_csv(data_filepath)
    
    
    
  def get_VacancesScolaires(input_data = None, merge_on=None,how='left',keep_zone=None):
  
    input_data = self.input_data
    
    # Filtrage de la zone vacance à retenir
    if keep_zone not None:
    
      self.bloc_info_vacances = self.df_vacances[['date',f'vacances_zone_{keep_zone}','nom_vacances']]
      
    #Ajout d'une colonne au dataframe à enrichir
    self.input_data['date_to_merge'] = self.input_data[merge_on].dt.date
      
    # Ajout de l'info_vacance
    self.df_resultat = self.input_data.merge(self.bloc_info_vacances,left_on='date_to_merge',right_on='date',how=how)
    
