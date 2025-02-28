import pandas as pd
import datetime as dt

class ImportNoticeAdherents:
    def __init__(self,file_path,data_adherents,):
        self.data_adherents = data_adherents
        
    def get_notice_adherents(self):
        self.data_adherents = pd.read_excel(f'../data_lucas/{self.data_adherents}.xlsx')
        return(self.data_adherents)
    
    def rename_columns(self):
        data_adherents_ok = self.data_adherents.rename(columns={'numero de carte':'cardnumber',
                               'civilite':'title',
                               'nom de famille':'surname',
                               'prenom':'firstname',
                               'date de naissance':'dateofbirth',
                               'autre nom':'othernames',
                               'nom du garant':'contactname',
                               'prenom du garant':'contactfirstname',
                               'lieu naissance du garant':'altcontactsurname',
                               'relation avec le garant':'relationship',
                               'site de rattachement':'branchcode',
                               'type de carte':'categorycode',
                               'date de creation de carte':'dateenrolled',
                               'date expiration':'dateexpiry',
                               'identifiant':'userid',
                               'mot de passe':'password',
                               'parti sans laisser adresse':'gonenoadress',
                               'type action':'action'                               
                              })
        return(data_adherents_ok)
    
    def save_dataset(self):
        timestamp = dt.datetime.today().strftime('%Y-%m-%d')
        self.data_adherents.to_csv(f'../data_lucas/data_import_adherents_lot_du_{timestamp}.csv')
        
