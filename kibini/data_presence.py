import pandas as pd
from datetime import datetime, time
import argparse
import os

def process_file(file_path):
    """Lit un fichier Excel, transforme la colonne 'datetime' et retourne un DataFrame consolid�."""
    try:
        # Charger le fichier Excel
        xls = pd.ExcelFile(file_path)
        
        all_data = []  # Stocker les donn�es de chaque feuille
        
        for sheet_name in xls.sheet_names:
            try:
                # V�rifier si le nom de la feuille est une date (format JJ-MM-YYYY)
                date_obj = datetime.strptime(sheet_name, "%d-%m-%Y")
                
                # Lire la feuille
                df = xls.parse(sheet_name)
                
                # V�rifier si la colonne 'datetime' existe
                if 'datetime' not in df.columns:
                    print(f"?? La feuille '{sheet_name}' dans '{file_path}' ne contient pas de colonne 'datetime'. Ignor�e.")
                    continue

                # S�parer heure et minute
                df[['heure', 'minute']] = df['datetime'].str.split('h', expand=True).astype(int)
                
                # Construire la colonne datetime compl�te
                df['datetime'] = df.apply(lambda row: datetime(
                    year=date_obj.year,
                    month=date_obj.month,
                    day=date_obj.day,
                    hour=row['heure'],
                    minute=row['minute'],
                    second=0
                ), axis=1)

                # Supprimer les colonnes interm�diaires
                df.drop(columns=['heure', 'minute'], inplace=True)

                # Ajouter au stockage global
                all_data.append(df)

            except ValueError:
                print(f"?? Feuille '{sheet_name}' ignor�e (nom invalide, pas une date JJ-MM-YYYY).")
        
        # Concat�ner toutes les feuilles
        if all_data:
            final_df = pd.concat(all_data, ignore_index=True)
            return final_df
        else:
            print(f"? Aucun relev� valide dans '{file_path}'.")
            return None

    except Exception as e:
        print(f"? Erreur lors du traitement de {file_path} : {e}")
        return None

def main():
    """G�re les arguments en ligne de commande et ex�cute la conversion."""
    parser = argparse.ArgumentParser(description="Fusionne les feuilles Excel et g�n�re une colonne datetime compl�te.")
    parser.add_argument("files", nargs="+", help="Un ou plusieurs fichiers Excel � traiter.")
    
    args = parser.parse_args()
    
    all_results = []  # Stocker les r�sultats de tous les fichiers
    
    for file_path in args.files:
        df = process_file(file_path)
        if df is not None:
            all_results.append(df)
    
    # Fusionner tous les fichiers trait�s
    if all_results:
        final_df = pd.concat(all_results, ignore_index=True)
        output_file = "test_import_presence.csv"
        final_df.to_csv(output_file, index=False)
        print(f"? Fichier consolid� enregistr� sous : {output_file}")
    else:
        print("? Aucun fichier valide trait�.")

#if __name__ == "__main__":
#    main()
