import pandas as pd
from datetime import datetime, time
import argparse
import os

def process_file(file_path):
    """Lit un fichier Excel, transforme la colonne 'datetime' et retourne un DataFrame consolidé."""
    try:
        # Charger le fichier Excel
        xls = pd.ExcelFile(file_path)
        
        all_data = []  # Stocker les données de chaque feuille
        
        for sheet_name in xls.sheet_names:
            try:
                # Vérifier si le nom de la feuille est une date (format JJ-MM-YYYY)
                date_obj = datetime.strptime(sheet_name, "%d-%m-%Y")
                
                # Lire la feuille
                df = xls.parse(sheet_name)
                
                # Vérifier si la colonne 'datetime' existe
                if 'datetime' not in df.columns:
                    print(f"?? La feuille '{sheet_name}' dans '{file_path}' ne contient pas de colonne 'datetime'. Ignorée.")
                    continue

                # Séparer heure et minute
                df[['heure', 'minute']] = df['datetime'].str.split('h', expand=True).astype(int)
                
                # Construire la colonne datetime complète
                df['datetime'] = df.apply(lambda row: datetime(
                    year=date_obj.year,
                    month=date_obj.month,
                    day=date_obj.day,
                    hour=row['heure'],
                    minute=row['minute'],
                    second=0
                ), axis=1)

                # Supprimer les colonnes intermédiaires
                df.drop(columns=['heure', 'minute'], inplace=True)

                # Ajouter au stockage global
                all_data.append(df)

            except ValueError:
                print(f"?? Feuille '{sheet_name}' ignorée (nom invalide, pas une date JJ-MM-YYYY).")
        
        # Concaténer toutes les feuilles
        if all_data:
            final_df = pd.concat(all_data, ignore_index=True)
            return final_df
        else:
            print(f"? Aucun relevé valide dans '{file_path}'.")
            return None

    except Exception as e:
        print(f"? Erreur lors du traitement de {file_path} : {e}")
        return None

def main():
    """Gère les arguments en ligne de commande et exécute la conversion."""
    parser = argparse.ArgumentParser(description="Fusionne les feuilles Excel et génère une colonne datetime complète.")
    parser.add_argument("files", nargs="+", help="Un ou plusieurs fichiers Excel à traiter.")
    
    args = parser.parse_args()
    
    all_results = []  # Stocker les résultats de tous les fichiers
    
    for file_path in args.files:
        df = process_file(file_path)
        if df is not None:
            all_results.append(df)
    
    # Fusionner tous les fichiers traités
    if all_results:
        final_df = pd.concat(all_results, ignore_index=True)
        output_file = "test_import_presence.csv"
        final_df.to_csv(output_file, index=False)
        print(f"? Fichier consolidé enregistré sous : {output_file}")
    else:
        print("? Aucun fichier valide traité.")

#if __name__ == "__main__":
#    main()
