import string
import pandas as pd
import numpy as np
import seaborn as sns
import re
from datetime import datetime as dt
from matplotlib import pyplot as plt
import warnings
warnings.filterwarnings("ignore")

class AECS():
    def __init__(self,set_sll_columns=False):    
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
                      
        alphabet = list(string.ascii_lowercase)
        
        data_date = '20250917'
        filepath_data = f'../data/aecs/tableaux_suivi_AECS_{data_date}.xlsx'
        
        self.aecs = pd.read_excel(filepath_data,sheet_name=sheets2keep)
        self.aecs = pd.concat(self.aecs)
        self.aecs = self.aecs.droplevel(level=1).reset_index()        
        self.aecs.loc[self.aecs['Nb adultes touchés']>100,'ANOMALIE Nb adultes touchés']='oui'
        self.aecs.loc[self.aecs['Nb enfants touchés']>100,'ANOMALIE Nb enfants touchés']='oui'
        
        self.aecs['Nb actions'] = 1
        
        # Pour toutes les feuilles
        self.aecs['Total personnes distinctes touchées'] = self.aecs['Nb enfants touchés'] + self.aecs['Nb adultes touchés']
        
        #Pour Action Culturelle uniquement on copie dans la colonne "Total" les données de la colonne"Nb personnes touchées"
        self.aecs.loc[self.aecs['index']=="Mathilde M","Total personnes distinctes touchées"] = self.aecs['Nb personnes touchées']
        
        self.aecs_collectivites = self.aecs[self.aecs["index"]=='Laetitia D']
        self.effectifs_scolaires = pd.read_excel(filepath_data,sheet_name='Effectifs')
        self.aecs_collectivites = self.aecs_collectivites.merge(self.effectifs_scolaires,left_on="Nom d'équipement",right_on="Nom",how='left')
        self.list_SchoolNames = list(self.aecs_collectivites[self.aecs_collectivites['Type de structure']=="Ecole"]["Nom d'équipement"].unique())
        
        self.ac = self.aecs[self.aecs["index"]=='Mathilde M']
        self.aes = self.aecs[self.aecs["index"]!='Mathilde M']
        

        if set_sll_columns==True:
            
            # Ajout des colonnes SLL pour le DataFrame Action Culturelle (ac)
            self.ac.loc[self.ac["Type d'action"]=="Exposition",
                        "H4 - Actions au sein de l'établissement"] = "H4 - Exposition"

            self.ac.loc[self.ac["Type d'action"].isin(['Conférence','Rencontre','Lecture']),
                        "H4 - Actions au sein de l'établissement"] = "H4 - Conférences, rencontres, lectures"

            self.ac.loc[self.ac["Type d'action"].isin(['Concert','Projection']),
                        "H4 - Actions au sein de l'établissement"] = "H4 - Concerts, projections"

            self.ac.loc[self.ac["Type d'action"]=="Séance de contes",
                        "H4 - Actions au sein de l'établissement"] = "H4 - Séances de contes"

            self.ac.loc[self.ac["Type d'action"].isin(["Club lecture","Atelier d'écriture"]),
                        "H4 - Actions au sein de l'établissement"] = "H4 - Clubs de lecteurs, ateliers d'écriture"

            #ac.loc[ac["Type d'action"].isin(["Journée festive","Salon du livre","Festival"]),['sll-type_action']] = "H4 - Fêtes, salons du livre, festivals" 
            #ac.loc[ac["Evénement"].notna(),["H4 - Actions au sein de l'établissement"]] = "H4 - Fêtes, salons du livre, festivals"


            self.ac.loc[~self.ac["H4 - Actions au sein de l'établissement"].isin(["H4 - Exposition",
                                                          "H4 - Conférences, rencontres, lectures",
                                                          "H4 - Concerts, projections",
                                                          "H4 - Séances de contes",
                                                          "H4 - Clubs de lecteurs, ateliers d'écriture",
                                                          #"H4 - Fêtes, salons du livre, festivals"
                                                         ]),
                        "H4 - Actions au sein de l'établissement"] = "H4 - Autres"
            
            self.ac.loc[self.ac["Type de public"].isin(['Enfants','Petite enfance','Adolescents']),'sll_type_public'] = 'a/ Enfants'
            self.ac.loc[~self.ac['Type de public'].isin(['Enfants','Petite enfance','Adolescents']),'sll_type_public'] = 'b/ Tout public'
    
            
            
            # Création d'un dictionnaire
            dict_TypeDeStructure = {'Ecole':'Écoles',
                                    'Collège':'Collèges',
                                    'Lycée':'Lycées',
                                    'Supérieur':'Supérieur',
                                    'Maison_de_retraite':'Maisons de retraite',
                                    'Centre_social':'Centres sociaux',
                                    'Centre_de_loisirs':'Centres de loisirs',
                                    'Structure_de_la_petite_enfance':'Services de la petite enfance',
                                    'Service_emploi_et_formation':'Services de l\'emploi',
                                    'Equipement_medicosocial':'Équipements médico-sociaux'
                                   }
            
            # Création d'une liste de clés et de valeurs
            keys = dict_TypeDeStructure.keys()
            values = dict_TypeDeStructure.values()
            column_to_parse = 'Type de structure'
            column_to_add = 'H1 - Partenariats avec des institutions'
            
            # Pour chaque paire clé/valeurs, 
            # si Type de structure contient clé
            # Pour nouvelle colonne H1 - Partenariat avec les institutions, utilisé valeurs associée
            for key,value,letter in zip(keys,values,alphabet):
                self.aecs.loc[self.aecs[column_to_parse]==key,column_to_add] = f'{letter}/ {value}'

        
            dict_TypeDePublic = {"Personnes âgées (65 ans et plus)":"Personnes âgées",
                                 "Personnes en situation de handicap":"Personnes en situation de hancidap",
                                 "Jeunes (18-25 ans)":"Jeunes",
                                 "Petite enfance (0-3 ans)":"Petite enfance",
                                 "Personnes en recherche d'emploi":"Personnes en recherche d'emploi",
                                 "Personnes en situation d'illettrisme":"Personnes en situation d'illétrisme",
                                 "Populations allophones":"Population non-francophone",
                                 "Populations en situation d'insertion sociale":"Population en situation d'insertion sociale"
                                }

            keys = dict_TypeDePublic.keys()
            values = dict_TypeDePublic.values()
            for key,value,letter in zip(keys,values,alphabet):
                self.aecs.loc[self.aecs["Type de public"]==key,
                             'H7 - Actions et services à destination de publics à besoins spécifiques'] = f'{letter}/ {value}'

    
    def get_SLL_datas(self):
        self.get_SLL_H1_PartenariatsAvecDesInstitutions()
        self.get_SLL_H2_PartenariatsAvecDesEquipementsCulturels()
        self.get_SLL_H4_ActionsAuSeinDelEtablissement()
        self.get_SLL_H5_ActionsHorsDelEtablissement()
        self.get_SLL_H7_PublicsSpecifiques()
    
    
    def get_SLL_H1_PartenariatsAvecDesInstitutions(self):
        
        self.aecs_H1XX_df = self.aecs.groupby('H1 - Partenariats avec des institutions')['Total personnes distinctes touchées'].sum().to_frame()
        return(self.aecs_H1XX_df)

        
        
    def get_SLL_H2_PartenariatsAvecDesEquipementsCulturels(self):
        
        self.aecs_H2XX_df = self.aecs[self.aecs["Type de structure"]=="Centre_culturel"].groupby("Nom d'équipement")['Total personnes distinctes touchées'].sum().to_frame()
        return(self.aecs_H2XX_df)
    
    
    def get_SLL_H3_PartenariatsAvecDesAssociations(self):
        return("Travaux en cours")    
        
        
    
    
    def get_SLL_H4_ActionsAuSeinDelEtablissement(self):
        
        self.aecs_H4XX_df= self.ac.pivot_table(index="H4 - Actions au sein de l'établissement",
                                      columns='sll_type_public',
                                      values=['Nb actions','Nb personnes touchées'],
                                      aggfunc=sum,
                                      margins=True,
                                      fill_value=0,
                                      margins_name='Total'
                                     )
        
        return(self.aecs_H4XX_df)
        
    
    def get_SLL_H5_ActionsHorsDelEtablissement(self,print_result=False):
        
        self.aecs_H5XX_df_HorsLesMurs = self.aecs[(self.aecs['Lieu']=='Hors les murs') &
                                                  (self.aecs['index']!='Laetitia D')]
        
        self.aecs_H5XX_NbActionsHorsLesMursMed = self.aecs_H5XX_df_HorsLesMurs['Nb actions'].sum()
        self.aecs_H5XX_NbActionsHorsLesMursCol = len(self.aecs_collectivites)
        self.aecs_H502_NbActionsHorsLesMurs = self.aecs_H5XX_NbActionsHorsLesMursCol + self.aecs_H5XX_NbActionsHorsLesMursMed
            
        
        for name in self.list_SchoolNames:
            aecs_collectivites_school = self.aecs_collectivites[self.aecs_collectivites["Nom d'équipement"]==name]
            Total_actions_BCD = len(aecs_collectivites_school[aecs_collectivites_school["Nom action ou projet"]=="BCD"])
            Total_actions_MARM = len(aecs_collectivites_school[aecs_collectivites_school["Nom action ou projet"]=="MARMOTHEQUE"])
            Total_emprunteurs_distincts = aecs_collectivites_school["Nom emprunteur"].nunique()
            self.aecs_collectivites.loc[self.aecs_collectivites["Nom d'équipement"]==name,'Total_actions_BCD']=Total_actions_BCD
            self.aecs_collectivites.loc[self.aecs_collectivites["Nom d'équipement"]==name,'Total_actions_Marmothèque'] = Total_actions_MARM
            self.aecs_collectivites.loc[self.aecs_collectivites["Nom d'équipement"]==name,'Total_emprunteurs_distincts'] = Total_emprunteurs_distincts
            
        effectif_moyen_classe = 25    
        self.aecs_collectivites.loc[self.aecs_collectivites["Total_actions_BCD"]>0,'Nb enfants touchés'] = self.aecs_collectivites['Total Ecole']
        self.aecs_collectivites.loc[self.aecs_collectivites["Total_actions_Marmothèque"]>0,'Nb enfants touchés'] = self.aecs_collectivites['Total Maternelle']
        self.aecs_collectivites.loc[(self.aecs_collectivites["Total_actions_BCD"]==0) &
                                    (self.aecs_collectivites["Total_actions_Marmothèque"]==0),
                                    'Nb enfants touchés'] = self.aecs_collectivites['Total_emprunteurs_distincts'] * effectif_moyen_classe

        # Suppression des noms doublons pour les noms d'école
        self.aecs_collectivites.drop_duplicates(subset="Nom",
                                                inplace=True)
        
        self.aecs_collectivites_schools = self.aecs_collectivites[["index","Nom","Nb enfants touchés"]]
        
        self.aecs_H5XX_PopulationToucheeCol = self.aecs_collectivites_schools["Nb enfants touchés"].sum()
        self.aecs_H5XX_PopulationToucheeMed = self.aecs_H5XX_df_HorsLesMurs['Total personnes distinctes touchées'].sum()
        self.aecs_H503_PopulationTouchee = self.aecs_H5XX_NbActionsHorsLesMursMed + self.aecs_H5XX_PopulationToucheeCol
        
        
    def get_SLL_H7_PublicsSpecifiques(self):
        
        self.aecs_H7XX_df = self.aecs.groupby('H7 - Actions et services à destination de publics à besoins spécifiques')['Nb actions','Total personnes distinctes touchées'].sum()
        return(self.aecs_H7XX_df)
        
    def get_Statistiques(self,
                         print_result=False,
                         filter_on=None,
                         method = None,
                         group_by_what = [],
                         total_on = [],
                         count_actions_numbers=False):
        
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


"""
# V1

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
"""