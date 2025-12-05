import numpy as np
import pandas as pd

from datetime import datetime as dt

#data_filepath = "../vacances_scolaires_fr.csv"
data_filepath = "/home/kibini/kibini2/kibini/kiblib/vacances_scolaires_fr.csv"

class Vacances():
  """
  Cette classe permet de manipuler des données relatives aux vacances scolaires
  """

  def __init__(self):
    """
    Initialisation de l'instance
    """
    self.df_vacances = pd.read_csv(data_filepath)
    
    
    
  def get_PeriodesVacances(self,input_data=None, date_based_on=None,how='left',keep_zone=None):
    """
    Cette méthode permet de récupérer des informations sur les vacances scolaires et/ de les ajouter un DataFrame existant
    
      Args:
        
        input_data (DataFrame object) : Dataframe en entrée
        date_based_on = (string) : nom de la colonne à utiliser pour créer une colonne date
        how (string) : de quel côté fusionner
        
        
      Returns:
        DataFrame : DataFrame contenant des colonnes avec des informations relatives aux vacances scolaires"
    """

    if input_data is None:
      return("L'argument input_data est vide. Rentrez une variable de type DataFrame. ")
      
    else:
      self.input_data = input_data
      self.input_data.loc['datetime'] = pd.to_datetime(self.input_data[date_based_on])
      self.input_data['date'] = self.input_data['datetime'].date
      self.input_data.set_index('date',inplace=True)
      
      
      self.bloc_info_vacances = self.df_vacances
      
      # Filtrage de la zone vacance à retenir
      if keep_zone is not None:
        self.bloc_info_vacances = self.bloc_info_vacances[['date',f'vacances_zone_{keep_zone}','nom_vacances']]
      
      
      # Ajout de l'info_vacance
      self.df_resultat = pd.merge(left=self.input_data,
                                  right=self.bloc_info_vacances,
                                  left_on='date',
                                  right_on='date',
                                  how=how)