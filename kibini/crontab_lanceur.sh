#! /bin/bash

dayofweek=`date +%u`
dayofmonth=`date +%d`
dayofmonthnextweek=`date +%d -d "7 day"`

dir_log='/home/kibini/kibini2/log/crontab/'
dir_kib='/home/kibini/kibini2'

# on acative l'environnement conda kibini
conda activate kibini

# CHAQUE JOUR
# On charge sur preprod la version de koha_prod du jour (copie + décompression intégrées au script)
python $dir_kib/kibini/data_load_koha_prod.py

# CHAQUE DERNIER MERCREDI DU MOIS
if [ $dayofweek -eq 3 ] && [ $dayofmonthnextweek -lt $dayofmonth ]
then
    # On fait un cliché des données adhérents
    python $dir_kib/kibini/data_adherents.py
fi

# CHAQUE VENDREDI
if [ $dayofweek -eq 5 ]
then
	# On liste les documents à passer en non restitués plus
	python $dir_kib/kibini/adm_itemsNonRestituesPlus.py

fi

# CHAQUE PREMIER DU MOIS
if [ `date +%d` == "01" ]
then
    # On envoie aux acquereurs la liste des documents sortis des collections car perdus, pretendus rendus ou non restitués
	python $dir_kib/kibini/adm_itemsPerdusPretendusRendus2acquereurs.py
fi

# CHAQUE JOUR
# On liste les documents en non restitués plus rendu la veille
#python $dir_kib/kibini/adm_itemsNonRestituesPlus_retours.py

# On incorpore dans statdb les prêts et retours de la veille
python $dir_kib/kibini/data_issues.py

# On incorpore dans statdb les réservations de la veille
python $dir_kib/kibini/data_reserves.py

# On traite les données liées à la fréquentation de la salle d'étude
python $dir_kib/kibini/data_freq_etude.py

# On incorpore les entrées
python $dir_kib/kibini/data_entrees_opteio.py --last 1

# NOUVELLE VERSION
# On met à jour les données exemplaires
python $dir_kib/kibini/data_exemplaires.py

# On anonymise statdb
python $dir_kib/kibini/data_ano.py

# KIBINI2
python $dir_kib/kibini/data_prets.py

# CHAQUE MERCREDI
if [ $dayofweek -eq 3 ]
then
    # On liste les exemplaires sortis des collections non abîmés, non perdus, non restitués à supprimer
    python $dir_kib/kibini/adm_items2del2adm.py

    # On liste les exemplaires sortis des collections abîmés, perdus, non restitués à supprimer
    python $dir_kib/kibini/adm_items2delb2adm.py

    # On liste les exemplaires non restitués depuis plus de 180 jours
    python $dir_kib/kibini/adm_itemsRetards2adm.py

	# On liste les exemplaires perdus ou prétendus rendus à sortir des collections
	python $dir_kib/kibini/adm_itemsPerdus2adm.py

    # On liste les prétendus rendus à traiter
    python $dir_kib/kibini/adm_itemsPretendusRendus2adm.py

	# On liste les documents à passer en retard supérieur à 90 jours
	python $dir_kib/kibini/adm_itemsNonRestituesPlus.py

    # On réalise un dump de statdb
    python $dir_kib/kibini/data_sauv_bdd.py
fi

# CHAQUE JOUR
# On supprime les logs crontab de plus de 30 jours
find $dir_log/lanceur_*.log  -ctime +30 -exec rm "{}" \;
