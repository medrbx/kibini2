# kibini2

Portage Python de [kibini_prod](../kibini_prod) (à l'origine en Perl : scripts de collecte/consolidation statistique + site web Dancer2). kibini2 est la cible active de ce portage.

## Vue d'ensemble

kibini2 a trois usages distincts, qui se recoupent dans le code mais tournent séparément :

1. **Collecte et consolidation des données** — scripts `data_*.py` lancés quotidiennement par cron, qui alimentent la base MySQL `statdb` à partir de `koha_prod` (SIGB Koha), du service Opteio (comptage de fréquentation) et de fichiers CSV.
2. **Analyse et restitution** — notebooks Jupyter (`notebook_*.ipynb`) qui produisent les tableaux de bord, exportés en HTML par les scripts `notebook2html*.sh` et affichés en iframe par le site web.
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
│   └── frequentation/          # relevés de fréquentation par espace (Excel)
├── log/                      # logs (cron, application) — non suivi par git
├── referentiels/             # fichiers de référence (communes/département/région, acquéreurs)
├── environment.yml           # environnement conda "kibini" (pipeline data + notebooks)
└── notebook2html*.sh         # exécutent les notebooks et publient leur rendu HTML (3 variantes, voir plus bas)
```

## `kibini/crontab_lanceur.sh` — orchestration cron

Point d'entrée unique lancé par une tâche cron (fréquence non fixée dans le script lui-même — à vérifier dans la crontab système, mais conçu pour tourner une fois par jour). Active l'environnement conda `kibini`, puis exécute une série de scripts selon un calendrier codé en dur avec des tests sur `date +%u`/`date +%d` :

| Fréquence | Scripts exécutés | Rôle |
|---|---|---|
| **Chaque jour** | `data_load_koha_prod.py` | Copie + décompression + chargement du dump `koha_prod` du jour |
| **Chaque jour** | `data_issues.py`, `data_reserves.py`, `data_freq_etude.py`, `data_entrees_opteio.py --last 1`, `data_exemplaires.py`, `data_ano.py`, `data_prets.py` | Incorporation quotidienne dans `statdb` : prêts/retours, réservations, fréquentation salle d'étude, entrées (capteurs Opteio), exemplaires, anonymisation, prêts (schéma récent) |
| **Dernier mercredi du mois** (`dayofweek==3` ET `dayofmonthnextweek < dayofmonth`) | `data_adherents.py` | Cliché mensuel des données adhérents |
| **Chaque vendredi** | `adm_itemsNonRestituesPlus.py` | Liste les documents à passer en "non restitués plus" |
| **Le 1er du mois** | `adm_itemsPerdusPretendusRendus2acquereurs.py` | Envoie aux acquéreurs la liste des documents sortis des collections (perdus/prétendus rendus/non restitués) |
| **Chaque mercredi** | `adm_items2del2adm.py`, `adm_items2delb2adm.py`, `adm_itemsRetards2adm.py`, `adm_itemsPerdus2adm.py`, `adm_itemsPretendusRendus2adm.py`, `adm_itemsNonRestituesPlus.py`, `data_sauv_bdd.py` | Listes de gestion des exemplaires à traiter (à supprimer, en retard, perdus...) + sauvegarde `mysqldump` hebdomadaire de `statdb` |
| **Chaque jour** | `find ... -ctime +30 -exec rm` | Purge des logs cron de plus de 30 jours (`log/crontab/lanceur_*.log`) |

Chaque script est autonome, invocable indépendamment (`python kibini/data_issues.py`) pour du rattrapage ou du débogage. Le job `adm_itemsNonRestituesPlus_retours.py` du quotidien est présent dans le script mais **commenté** (désactivé).

## `kibini/data_*.py` — collecte cron

Portage des scripts Perl `kibini_prod/bin/statdb_*.pl` et `bin/data_*.pl`, renommés uniformément en `data_*.py`. Chacun alimente une ou plusieurs tables de `statdb` : `data_load_koha_prod.py` (dump quotidien de koha_prod), `data_issues.py`/`data_prets.py`, `data_reserves.py`, `data_adherents.py`, `data_exemplaires.py`, `data_freq_etude.py`, `data_entrees_opteio.py`, `data_ano.py` (anonymisation), `data_wk_pc.py`/`data_wk_wifi.py` (webkiosk/wifi), `data_sauv_bdd.py` (sauvegarde mysqldump).

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
│   └── data/            # HTML des notebooks publié par notebook2html_flask.sh, + poldoc/*.xlsx
└── environment.yml     # environnement conda "kibini-web", dédié (voir ci-dessous)
```

Routes principales : les tableaux de bord (iframe pointant vers un notebook exporté en `/static/data/*.html`, ou vers Kibana pour les quelques dashboards encore actifs), les pages poldoc (`/*/collections/ensemble`), et les outils (`/qa/inscrits`, `/suggestions`, `/frequentation/etude`, `/form/action_culturelle`, `/form/action_coop`, `/liste`).

### Lancement en développement

Depuis `kibini2/kibini`, env `kibini-web` activé :
```bash
FLASK_APP=webapp.app:create_app FLASK_DEBUG=1 flask run --port 5055
```
En session Claude Code, `preview_start` avec la config `kibini-webapp` de `.claude/launch.json` fait la même chose.

### Déploiement en production

La webapp tourne en production sur une machine distincte de l'environnement de développement (voir "Topologie" ci-dessous), via **Gunicorn** (pas `flask run`) :

```bash
# depuis kibini2/kibini, env kibini-web activé
gunicorn "webapp.app:create_app()" --workers 3 --bind 0.0.0.0:1793
```

Géré par un service **systemd nommé `kibini-web`** (redémarrage automatique en cas de crash) :
```bash
sudo systemctl restart kibini-web   # après un git pull, pour recharger le code
sudo systemctl status kibini-web
sudo journalctl -u kibini-web -f    # suivre les logs
```
Les templates Jinja2 sont rechargés à la volée en mode `flask run --debug`, mais **pas** sous Gunicorn (pas de rechargement automatique en prod) : tout changement de code ou de template nécessite un `git pull` + redémarrage du service.

### Topologie (dev ≠ prod, à ne pas confondre)

Le développement se fait sur une machine distincte du serveur de production. Le code circule entre les deux via `git pull`/`push`. **Point important : `data/` (et tout dossier nommé `data`, y compris `webapp/static/data/`) est gitignoré** — les fichiers de données qu'il contient (notebooks HTML exportés, fonds de carte `.geojson`, fichiers Excel poldoc/AECS/fréquentation) ne sont donc **jamais synchronisés par git** et doivent être transférés séparément (scp ou équivalent) vers chaque machine qui doit les servir.

## Scripts de publication des tableaux de bord

Trois scripts à la racine de `kibini2/`, tous exécutent une liste de notebooks (`jupyter nbconvert --execute`) et les exportent en HTML sans le code (`--no-input`) — mais divergent sur le chemin de destination :

- **`notebook2html.sh`** — chemins **prod en dur** (`kibini2='/home/kibini/kibini2'`, copie vers `/home/kibini/kibini_prod/public/data/<nom>.html`). C'est la version utilisée sur le serveur de production, où ces chemins sont réels.
- **`notebook2html_flask.sh`** — variante avec **chemin calculé depuis l'emplacement du script** (`$(dirname "${BASH_SOURCE[0]}")`), copie vers `kibini/webapp/static/data/<nom>.html`. Fonctionne quel que soit l'endroit où le dépôt est cloné (dev comme prod) ; c'est celle-ci qui alimente la webapp Flask.
- **`test_notebook2html.sh`** — même logique que `notebook2html.sh` (chemins prod en dur) mais restreinte à un seul notebook, pour tester une régénération ciblée sans relancer tout le lot.

Ces trois scripts embarquent la même liste de notebooks en dur dans une boucle `for` — **à maintenir manuellement à l'identique entre les trois** quand un notebook est ajouté ou retiré (déjà source d'un oubli constaté : `notebook2html_flask.sh` a dû être rattrapé après coup pour deux notebooks présents dans `notebook2html.sh` mais absents de sa propre liste).

Certains notebooks dépendent de fichiers déposés dans `data/` (AECS, fréquentation, fonds de carte géojson) ou de partages réseau internes à la Médiathèque — non fournis par git (voir "Topologie" plus haut).

## Deux environnements conda, volontairement séparés

- **`kibini`** (Python 3.8, voir `environment.yml`) — pipeline data + notebooks (pandas, sqlalchemy, matplotlib, seaborn, geopandas, jupyter...).
- **`kibini-web`** (Python 3.8, voir `kibini/webapp/environment.yml`) — site web Flask uniquement (flask, sqlalchemy, pymysql, mysql-connector-python, pyyaml, requests).

Séparation nécessaire : Flask exige Jinja2 ≥ 3.1, incompatible avec `jupyter nbconvert` dans l'env `kibini` (resté sur Jinja2 3.0.2). **Ne jamais installer Flask (ou toute dépendance web) dans l'env `kibini`.**

## Configuration

`kibini/conf/kibini_conf.yml` — gitignoré (contient des identifiants réels), à créer à partir du modèle `kibini/conf/kibini_conf_empty.yml`. Lu via `kiblib.utils.conf.Config` (une méthode `get_config_*` par section). Sections :

| Clé | Contenu | Utilisé par |
|---|---|---|
| `database` | `db`/`user`/`pwd` — connexion MySQL à `statdb` | `kiblib.utils.db.DbConn`, quasiment tout le pipeline et la webapp |
| `webservice` | `base` (hôte du rapport Koha `ws-koha.*`) + `user`/`pwd` (auth basique de l'API REST Koha) | `webapp/services.py` (rapports `/liste`, `/qa/inscrits`, `/suggestions`, et `mod_suggestion2`) |
| `elasticsearch` | `node` (URL du nœud ES) | scripts de synchro ES du pipeline cron (pas la webapp) |
| `opteio` | `login`/`password` — API de comptage de fréquentation par capteurs | `data_entrees_opteio.py`, `kiblib.utils.opteio.OpteioClient` |
| `salt` | sel de hachage | `kiblib.utils.hashid` (anonymisation des identifiants adhérents) |
| `dir_log` | répertoire des logs | `kiblib.utils.log.Log` (scripts cron uniquement) |
| `dir_data` | répertoire de données | scripts d'administration ponctuels |
| `dir_webdav` | chemin des dumps Koha à charger | `data_load_koha_prod.py` |
| `smtp` | serveur SMTP (adresse IP) | `kiblib.utils.email_sender.send_email`, utilisé par la webapp pour les notifications de suggestions |
| `acquereurs` | liste `borrowernumber`/`nom`/`courriel` des acquéreurs | webapp (`/suggestions` : liste déroulante d'attribution + email de notification) |
| `stat_sugg` | mapping `borrowernumber → nom` (jeu de données plus large, historique) | scripts d'analyse ponctuels |

Cette configuration est **par machine** (dev et prod ont chacune leur propre `kibini_conf.yml`, non synchronisé par git) — les identifiants ou hôtes peuvent différer entre les deux (ex. `webservice.base` doit être joignable depuis la machine, ce qui n'est pas le cas depuis toutes les machines de dev).
