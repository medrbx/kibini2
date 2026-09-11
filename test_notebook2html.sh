#! /bin/bash


date=$(date '+%Y-%m-%d')
kibini2="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
data_dir="$kibini2/kibini/webapp/static/data"
mkdir -p "$data_dir"
cd "$kibini2"

# Execution et publication d'un notebook en particulier
for filename in notebook_kibini2_med_evolution_prets


do
    newfilename="$filename"_"$date"
    jupyter nbconvert --to notebook --execute kibini/$filename.ipynb --output $newfilename
    jupyter nbconvert --to html --no-input kibini/$newfilename.ipynb
    cp kibini/$newfilename.html $data_dir/$filename.html
    rm kibini/$newfilename*
done
