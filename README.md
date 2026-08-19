# kibini2

Portage Python de [kibini_prod](../kibini_prod) (à l'origine en Perl : scripts de collecte/consolidation statistique + site web Dancer2). kibini2 est la cible active de ce portage.

## Vue d'ensemble

kibini2 a trois usages distincts, qui se recoupent dans le code mais tournent séparément :

1. **Collecte et consolidation des données** — scripts `data_*.py` lancés quotidiennement par cron, qui alimentent la base MySQL `statdb` à partir de `koha_prod` (SIGB Koha), du service Opteio (comptage de fréquentation) et de fichiers CSV.
2. **Analyse et restitution** — notebooks Jupyter (`notebook_*.ipynb`) qui produisent les tableaux de bord, exportés en HTML par `notebook2html.sh` et affichés en iframe par le site web.
3. **Site web** — application Flask (`kibini/webapp/`), portage du site Dancer2/Perl d'origine (`kibini_prod/lib/website/dancer.pm`), qui sert de porte d'entrée aux tableaux de bord et à quelques outils de saisie (fréquentation salle d'étude, actions culturelles/coopération, suggestions, contrôle qualité des inscrits).

## Arborescence

```
kibini2/
├── kibini/                  # tout le code Python et les notebooks
│   ├── kiblib/               # bibliothèque interne partagée
│   │   ├── adherent.py, document.py, pret.py, webkiosk.py, poldoc.py
│   │   └── utils/             # conf, db, email_sender, date, log, opteio, code2libelle,
│   │                           # aecs, charte_graphique_lgp, hashid, vacances_scolaires...
│   ├── webapp/                # application web Flask (voir plus bas)
│   ├── conf/                  # kibini_conf.yml (identifiants — gitignoré) + modèle vide + conf ES
│   ├── archives/               # anciens scripts de migration, non utilisés en prod
│   ├── data_*.py              # scripts cron de collecte/consolidation (voir plus bas)
│   ├── adm_*.py / adm_*.ipynb # scripts et notebooks d'administration ponctuels (qualité de données,
│   │                           # listes à traiter manuellement, envois aux acquéreurs...)
│   ├── notebook_*.ipynb       # notebooks de restitution (tableaux de bord)
│   └── crontab_lanceur.sh     # point d'entrée cron, orchestre les data_*.py selon le jour
├── data/                     # données d'entrée/sortie locales (gitignoré, jamais vide en prod)
│   ├── aecs/                  # tableaux de suivi AECS (Excel)
│   ├── frequentation/          # relevés de fréquentation par espace (Excel)
│   └── poldoc/                 # statistiques de collections annuelles (Excel) — copie dupliquée sous
│                                 # webapp/static/data/poldoc/, c'est cette dernière qui est servie
├── log/                      # logs (cron, application) — non suivi par git
├── referentiels/             # fichiers de référence (communes/département/région, acquéreurs)
├── environment.yml           # environnement conda "kibini" (pipeline data + notebooks)
└── notebook2html.sh          # exécute les notebooks et publie leur rendu HTML pour le site web
```

## `kibini/data_*.py` — collecte cron

Portage des scripts Perl `kibini_prod/bin/statdb_*.pl` et `bin/data_*.pl`, renommés uniformément en `data_*.py`. Orchestrés par `crontab_lanceur.sh`, qui active l'environnement conda `kibini` puis appelle chaque script selon un calendrier (quotidien, hebdomadaire, dernier mercredi du mois, premier du mois...). Chacun alimente une ou plusieurs tables de `statdb` : `data_load_koha_prod.py` (dump quotidien de koha_prod), `data_issues.py`/`data_prets.py`, `data_reserves.py`, `data_adherents.py`, `data_exemplaires.py`, `data_freq_etude.py`, `data_entrees_opteio.py`, `data_ano.py` (anonymisation), `data_wk_pc.py`/`data_wk_wifi.py` (webkiosk/wifi), `data_sauv_bdd.py` (sauvegarde mysqldump).

## `kibini/webapp/` — site web Flask

Portage de `kibini_prod/lib/website/dancer.pm` (Dancer2/Perl) et des modules qu'il appelle (`adherents.pm`, `collections/suggestions.pm`, `salleEtude/form.pm`, `action_culturelle.pm`, `action_coop/form.pm`, `liste.pm`).

```
webapp/
├── app.py            # factory create_app(), toutes les routes
├── dashboards.py      # table de données des tableaux de bord Kibana/notebooks (DASHBOARDS actif,
│                       # ARCHIVED_KIBANA_DASHBOARDS pour les anciens dashboards Kibana désormais
│                       # indisponibles, conservés comme référence)
├── services.py         # logique métier : webservice Koha, requêtes statdb, envoi d'email
├── templates/          # gabarits Jinja2 (portage des .tt Template Toolkit d'origine)
├── static/             # assets (css/js/fonts/images copiés de kibini_prod/public/) +
│   └── data/            # HTML des notebooks publié par notebook2html.sh, + poldoc/*.xlsx
└── environment.yml     # environnement conda "kibini-web", dédié (voir ci-dessous)
```

Routes principales : les tableaux de bord (iframe pointant vers un notebook exporté en `/static/data/*.html`, ou vers Kibana pour les quelques dashboards encore actifs), les pages poldoc (`/*/collections/ensemble`), et les outils (`/qa/inscrits`, `/suggestions`, `/frequentation/etude`, `/form/action_culturelle`, `/form/action_coop`, `/liste`).

Lancement en dev : `preview_start` avec la config `kibini-webapp` de `.claude/launch.json` (port 5055), ou manuellement depuis `kibini2/kibini` avec l'env `kibini-web` activé : `FLASK_APP=webapp.app:create_app FLASK_DEBUG=1 flask run`.

## `notebook2html.sh` — publication des tableaux de bord

Exécute une liste de notebooks (`jupyter nbconvert --execute`), les exporte en HTML sans le code (`--no-input`), et copie le résultat dans `kibini/webapp/static/data/<nom>.html`. Le chemin de destination est calculé depuis l'emplacement du script (fonctionne aussi bien en dev qu'en prod). Certains notebooks dépendent de fichiers déposés dans `data/` (AECS, fréquentation, fonds de carte géojson) ou de partages réseau internes à la Médiathèque.

## Deux environnements conda, volontairement séparés

- **`kibini`** (Python 3.8, voir `environment.yml`) — pipeline data + notebooks (pandas, sqlalchemy, matplotlib, seaborn, geopandas, jupyter...).
- **`kibini-web`** (Python 3.8, voir `kibini/webapp/environment.yml`) — site web Flask uniquement (flask, sqlalchemy, pymysql, mysql-connector-python, pyyaml, requests).

Séparation nécessaire : Flask exige Jinja2 ≥ 3.1, incompatible avec `jupyter nbconvert` dans l'env `kibini` (resté sur Jinja2 3.0.2). **Ne jamais installer Flask (ou toute dépendance web) dans l'env `kibini`.**

## Configuration

`kibini/conf/kibini_conf.yml` contient les identifiants (base `statdb`, webservice Koha, Opteio, SMTP, sel de hachage) — gitignoré, à créer à partir du modèle `kibini_conf_empty.yml`. Lu via `kiblib.utils.conf.Config`.

## Ce qui n'est pas (encore) dans kibini2

- La synchronisation Elasticsearch déclenchée par les formulaires action culturelle/coopération (existait côté Perl).
- Certains tableaux de bord Kibana dont le serveur (`129.1.0.237:5601`) n'existe plus — conservés dans `ARCHIVED_KIBANA_DASHBOARDS` en attendant leur reconstruction en notebook.
