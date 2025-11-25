import numpy as np
import pandas as pd

data_filepath = "../vacances_scolaires_fr.csv"
data_filepath_2 = "/home/kibini/kibini2/kibini/kiblib/vacances_scolaires_fr.csv"

class Vacances():

  def __init__(self):
    self.df = pd.read_csv(data_filepath_2)