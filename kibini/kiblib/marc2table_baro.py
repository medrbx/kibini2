from pymarc import MARCReader
import pandas as pd
from os.path import join

def get_files(path):
    for file in os.listdir(path):
        if os.path.isfile(os.path.join(path, file)):
            yield file

def get_type_notice(record):
    result = get_mc_values(record, ["LDR"])
    result = result[6]
    type_notice_codes = {
        "a": "texte",
        "b": "manuscrit",
        "c": "partition",
        "d": "partition manuscrite",
        "e": "carte",
        "f": "carte manuscrite",
        "g": "video",
        "i": "son - non musical",
        "j": "son - musique",
        "k": "image, dessin",
        "l": "ressource électronique",
        "m": "multimedia",
        "r": "objet"
    }
    if result in type_notice_codes.keys():
        result = type_notice_codes[result]
    return result

def get_niveau_bib(record):
    result = get_mc_values(record, ["LDR"])
    result = result[7]
    niveau_bib_codes = {
        "a": "analytique",
        "i": "ressource intégratrice",
        "m": "monographie",
        "s": "périodique",
        "c": "collection"
    }
    if result in niveau_bib_codes.keys():
        result = niveau_bib_codes[result]
    return result

def get_record_id(record):
    result = get_mc_values(record, ["001"])
    return result

def get_isbn(record):
    result = get_mc_values(record, ["010a"])
    return result

def get_ark(record):
    result = get_mc_values(record, ["033a"])
    return result

def get_alignement_bnf(metadata):
    result = False
    if 'ark:/12148' in metadata['ark']:
        result = True
    return result

def get_frbnf(record):
    result = ''
    data = get_mc_values(record, ["035a"])
    if 'FRBNF' in data:
        result = data
    return result

def get_refcom(record):
    result = get_mc_values(record, ["071ba"])
    return result

def get_ean(record):
    result = get_mc_values(record, ["073a"])
    return result

def get_rbx_vdg(record):
    result = get_mc_values(record, ["091a"])
    vdg_codes = {'0': 'rien', '1': 'aut', '2': 'bib & aut'}
    if result in vdg_codes.keys():
        result = vdg_codes[result]
    return result

def get_support(record):
    result = get_mc_values(record, ["099t"])
    support_codes = {
            'AP': 'périodique - article',
            'CA': 'carte routière',
            'CR': 'cd-rom',
            'DC': 'disque compact',
            'DG': 'disque gomme-laque',
            'DV': 'disque microsillon',
            'IC': 'document iconographique',
            'JE': 'jeu',
            'K7': 'cassette audio',
            'LG': 'livre en gros caractères',
            'LI': 'livre',
            'LN': 'livre numérique',
            'LS': 'livre audio',
            'ML': 'méthode de langue',
            'MT': 'matériel',
            'PA': 'partition',
            'PE': 'périodique',
            'VD': 'dvd',
            'VI': 'vhs, umatic ou film'
        }
    if result in support_codes.keys():
        result = support_codes[result]
    return result

def get_scale(record):
    result = get_mc_values(record, ["123b"])
    if result == '':
        result = get_mc_values(record, ["206b"])
    return result

def get_title(record, global_titre=None):
    if global_titre:
        result = get_mc_values(record, ["200a"])
        result2 = get_mc_values(record, ["200ae"])
        if (result == global_titre) | (result2 == global_titre):
            result = get_mc_values(record, ["200i"])
    else:
        result = get_mc_values(record, ["200ae"])
    return result

def get_key_title(record):
    result = get_mc_values(record, ["530a"])
    if result == '':
        result = get_mc_values(record, ["200ae"])
    return result

def get_global_title(record):
    result = get_mc_values(record, ["225a"])
    if result == '':
        result = get_mc_values(record, [""])
    return result

def get_collection(record):
    result = get_mc_values(record, ["410t", "225a"])
    result_list = result.split(" ; ")
    result_list = set(list(result_list))
    result = " ; ".join(result_list)
    return result

def get_part_title(record):
    result = get_mc_values(record, ["464t"])
    if result == '':
        result = get_mc_values(record, ["200ae"])
    return result

def get_numero_tome(record):
    result = get_mc_values(record, ["200h"])
    if result == '':
        result = get_mc_values(record, ["461v"])
    return result

def get_responsability(record):
    result = get_mc_values(record, ["700ab", "710ab", "701ab", "711ab", "702ab", "712ab"])
    if result == '':
        get_mc_values(record, ["200f"])
    return result

def get_subject(record):
    result = get_mc_values(record, ["600abcdefghijklmnopqrstuvwxyz",
                                    "601abcdefghijklmnopqrstuvwxyz",
                                    "602abcdefghijklmnopqrstuvwxyz",
                                    "604abcdefghijklmnopqrstuvwxyz",
                                    "605abcdefghijklmnopqrstuvwxyz",
                                    "606abcdefghijklmnopqrstuvwxyz",
                                    "607abcdefghijklmnopqrstuvwxyz",
                                    "608abcdefghijklmnopqrstuvwxyz",
                                    "609abcdefghijklmnopqrstuvwxyz"])
    return result

def get_publication_date(record):
    result = get_mc_values(record, ["100a"])
    result = result[9:13]
    if result == '':
        result = get_mc_values(record, ["214d"])
    if result == '':
        result = get_mc_values(record, ["210d"])
    if result == '':
        result = get_mc_values(record, ["219d"])
    return result

def get_publisher(record):
    result = get_mc_values(record, ["214c"])
    if result == '':
        result = get_mc_values(record, ["210c"])
    if result == '':
        result = get_mc_values(record, ["219c"])
    return result

def get_publication_place(record):
    result = get_mc_values(record, ["214a"])
    if result == '':
        result = get_mc_values(record, ["210a"])
    if result == '':
        result = get_mc_values(record, ["219a"])
    return result

def get_agence_cat(record):
    result = get_mc_values(record, ["801b"])
    return result

def get_pat(record):
    result = False
    ccodes = get_mc_values(record, ["995h"])
    ccodes = ccodes.split(" ; ")
    for ccode in ccodes:
        if ccode in ['PENPDZZ', 'PENRSZZ', 'PENACZZ', 'PENCVZZ',
                     'PENDEZZ', 'PENHPZZ', 'PPAFIZZ', 'PPEFGZZ',
                     'PPELGZZ', 'PPEPMZZ', 'PPEPRZZ', 'PPIPIZZ', 'PRRFIZZ']:
            result = True
            break
    return result

def get_nb_items(record):
    fields = record.get_fields('995')
    return len(fields)

def get_links(record):
    bnf_authnumbers = []
    koha_authnumbers = []

    tags = [tag for tag in range(600, 610)]
    for tag in range(700, 704):
        tags.append(tag)
    for tag in range(710, 714):
        tags.append(tag)

    for tag in tags:
        tag = str(tag)
        fields = record.get_fields(tag)
        for field in fields:
            numbers = field.get_subfields('3')
            for number in numbers:
                bnf_authnumbers.append(number)
            numbers = field.get_subfields('9')
            for number in numbers:
                koha_authnumbers.append(number)
    return [";".join(bnf_authnumbers), ";".join(koha_authnumbers)]

def get_mc_values(record, tags):
    result = []
    for tag in tags:
        if tag == 'LDR':
            result.append(record.leader)
        else:
            fields = record.get_fields(tag[:3])
            for field in fields:
                field_value = []
                # controlfield
                if tag[:2] == '00':
                    field_value.append(field.data)
                # datafield
                else:
                    for s in tag[3:]:
                        values = field.get_subfields(s)
                        for value in values:
                            field_value.append(value)
                result.append(" ".join(field_value))
    return " ; ".join(result)


# if __name__ == "__main__":
#     dir_path = 'data'
#     file = "2023-04-02-destombes"
#     marc_file = join(dir_path, 'marc', f"{file}.mrc.gz")
#     csv_file = join(dir_path, 'csv', f"{file}.csv.gz")
#
#     metadatas = []
#     i = 0
#     with open(marc_file, 'rb') as fh:
#         reader = MARCReader(fh, to_unicode=True, force_utf8=True)
#         for record in reader:
#             i += 1
#             if i % 20000 == 0:
#                 print(i)
#             metadata = {}
#     #, , , , , , ,
#     #, , NomAuteur, PrenomAuteur, DatesAuteur, CollectiviteAuteur, , Dewey
#             metadata['biblionumber'] = get_record_id(record)
#             metadata['ISBN'] = get_isbn(record)
#             if metadata['ISBN'] == None:
#                 metadata['ISBN'] = get_ean(record)
#             metadata['DateEdition'] =  get_publication_date(record)
#             metadata['global_title'] = get_global_title(record)
#             metadata['Titre'] = get_title(record, global_titre=None)
#             #metadata['key_title'] = get_key_title(record)
#             #metadata['part_title'] = get_part_title(record)
#             #if metadata['global_title'] == metadata['part_title']:
#             #    metadata['part_title'] = ''
#             metadata['NumeroVolume'] = get_numero_tome(rec
#
#             metadata['responsability'] = get_responsability(record)
#             #metadata['subject'] = get_subject(record)
#             metadata['publisher'] = get_publisher(record)
#             metadata['publication_place'] = get_publication_place(record)
#             metadata['agence_cat'] = get_agence_cat(record)
#             metadata['pat'] = get_pat(record)
#             metadata['alignement_bnf'] = get_alignement_bnf(metadata)
#             metadata['nb_items'] = get_nb_items(record)
#             #metadata['bnf_authnumbers'], metadata['koha_authnumbers'] = get_links(record)
#             metadatas.append(metadata)
#
#     metadatas_df = pd.DataFrame.from_records(metadatas)
#     metadatas_df.to_csv(csv_file, index=False)
