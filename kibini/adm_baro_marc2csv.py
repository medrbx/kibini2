import pandas as pd
import gzip

from os.path import join

import kiblib.marc2table_baro as mc
from pymarc import MARCReader

filename = "2024-01-14-notices_total"
marc_file = join("..", "data", f"{filename}.mrc.gz")
print(marc_file)

print("lecture du fichier")
with gzip.open(marc_file, "rb") as f:
    data = f.read()
    marc_data = MARCReader(data, to_unicode=True, force_utf8=True)

metadatas = []
i = 0

print("extraction des données")
for record in marc_data:
    i += 1
    if i % 20000 == 0:
        print(i)
    metadata = {}
    metadata['biblionumber'] = mc.get_record_id(record)
    metadata['Titre'] = mc.get_mc_values(record, ["200a"])
    metadata['SousTitre'] = mc.get_mc_values(record, ["200e"])
    metadata['TitreVolume'] = mc.get_mc_values(record, ["200i"])
    metadata['TitreSerie'] = mc.get_mc_values(record, ["461t"])
    metadata['ISBN'] = mc.get_isbn(record)
    if metadata['ISBN'] == '':
        metadata['ISBN'] = mc.get_ean(record)
    metadata['DateEdition'] =  mc.get_publication_date(record)
    metadata['NumeroVolume'] = mc.get_numero_tome(record)
    metadata['Collection'] = mc.get_collection(record)
    metadata['Dewey'] = mc.get_mc_values(record, ["676a"])
    metadata['NomAuteur'] = mc.get_mc_values(record, ["700a"])
    metadata['PrenomAuteur'] = mc.get_mc_values(record, ["700b"])
    metadata['DatesAuteur'] = mc.get_mc_values(record, ["700f"])
    metadata['CollectiviteAuteur'] = mc.get_mc_values(record, ["710a"])
    metadata['ArkBnF'] = mc.get_mc_values(record, ["033a"])
    metadatas.append(metadata)

print("création du fichier de résultats")
metadatas_df = pd.DataFrame.from_records(metadatas)
metadatas_df.to_csv(join("..", "data", f"{filename}.csv"), index=False)
