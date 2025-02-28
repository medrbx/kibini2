#! /bin/bash


date=$(date '+%Y-%m-%d')
kibini2='/home/kibini/kibini2'
kibini='/home/kibini/kibini_prod'

for filename in notebook_dimanche24 notebook_kibini2_lgp_activite30j notebook_kibini2_lgp_qui_sont_les_inscrits notebook_kibini2_lgp_que_font_les_inscrits notebook_kibini2_lgp_evolution_prets notebook_kibini2_lgp_evolution_retours notebook_kibini2_lgp_evolution_resas notebook_kibini2_lgp_quels_usages_resas notebook_kibini2_lgp_quels_usages_portail notebook_kibini2_med_evolution_prets notebook_kibini2_med_evolution_retours notebook_kibini2_med_evolution_resas notebook_kibini2_med_evolution_webkiosk notebook_kibini2_med_evolution_frequentation_etude notebook_kibini2_med_evolution_entrees notebook_kibini2_zebre_evolution_prets notebook_kibini2_zebre_evolution_retours notebook_kibini2_zebre_evolution_resas notebook_kibini2_0_presentation notebook_kibini2_med_quels_publics_action_culturelle notebook_kibini2_med_activite_hebdo notebook_kibini2_0_presentation notebook_kibini2_lgp_syntheses_pluriannuelles notebook_kibini2_med_evolution_impressions notebook_kibini2_med_quelle_repartition_des_prets

#for filename in notebook_kibini2_lgp_evolution_prets


do
    newfilename="$filename"_"$date"
    jupyter nbconvert --to notebook --execute kibini/$filename.ipynb --output $newfilename
    jupyter nbconvert --to html --no-input kibini/$newfilename.ipynb
    cp kibini/$newfilename.html /home/kibini/kibini_prod/public/data/$filename.html
    rm kibini/$newfilename*
done