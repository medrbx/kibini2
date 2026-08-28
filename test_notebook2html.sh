#! /bin/bash


date=$(date '+%Y-%m-%d')
kibini2='/home/kibini/kibini2'
kibini='/home/kibini/kibini_prod'

# Execution et publication d'un notebook en particulier
for filename in notebook_kibini2_med_quels_publics_action_culturelle notebook_kibini2_med_activite_hebdo


do
    newfilename="$filename"_"$date"
    jupyter nbconvert --to notebook --execute kibini/$filename.ipynb --output $newfilename
    jupyter nbconvert --to html --no-input kibini/$newfilename.ipynb
    cp kibini/$newfilename.html /home/kibini/kibini_prod/public/data/$filename.html
    rm kibini/$newfilename*
done
