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

## `kibini/conf/crontab.txt` — crontab système

Fichier source de la crontab installée en prod sur le compte `kibini` (`crontab conf/crontab.txt`, resynchronisation manuelle — aucun mécanisme n'applique automatiquement ce fichier au `crontab` système, à vérifier/réinstaller après modification). `MAILTO=fpichenot@ville-roubaix.fr` : la sortie/erreur de chaque job est envoyée par mail à cette adresse.

| Horaire | Commande | Rôle |
|---|---|---|
| Tous les jours à 03h00 | `bash crontab_lanceur.sh` | Orchestration quotidienne du pipeline data (détail ci-dessous) |
| Tous les jours à 08h00 | `python data_entrees_opteio.py --last 1` | Intégration des entrées Opteio (fréquentation) de la veille — job dédié, **sorti de `crontab_lanceur.sh`** (voir note ci-dessous) |
| Chaque mardi à 13h36 | `bash notebook2html.sh` | Régénération et publication HTML des notebooks |
| *(commenté, désactivé)* | `adm_vendangeur_auth2dedupl.py` à 08h30 | Dédoublonnage d'autorités |
| *(commenté, désactivé)* | `ADM_update_address.pl` à 19h30 | Mise à jour des adresses adhérents (script Perl historique de `kibini_prod`) |

### Opteio sorti de `crontab_lanceur.sh`

`data_entrees_opteio.py --last 1` n'est plus appelé depuis `crontab_lanceur.sh` : la ligne y est présente mais **commentée** (`crontab_lanceur.sh:52-54`) et remplacée par l'entrée dédiée de `crontab.txt` à 08h00 (voir tableau ci-dessus). Raison indiquée en commentaire dans le script : le service Opteio est indisponible la nuit et le week-end, ce qui rendait son appel peu fiable dans l'enchaînement de 03h00 — il est donc lancé séparément, plus tard dans la matinée.

## `kibini/crontab_lanceur.sh` — orchestration cron

Lancé quotidiennement à 03h00 par la crontab système (voir ci-dessus). Active l'environnement conda `kibini`, puis exécute une série de scripts selon un calendrier codé en dur avec des tests sur `date +%u`/`date +%d` :

| Fréquence | Scripts exécutés | Rôle |
|---|---|---|
| **Chaque jour** | `data_load_koha_prod.py` | Copie + décompression + chargement du dump `koha_prod` du jour |
| **Chaque jour** | `data_issues.py`, `data_reserves.py`, `data_freq_etude.py`, `data_exemplaires.py`, `data_ano.py`, `data_prets.py` | Incorporation quotidienne dans `statdb` : prêts/retours, réservations, fréquentation salle d'étude, exemplaires, anonymisation, prêts (schéma récent) |
| **Dernier mercredi du mois** (`dayofweek==3` ET `dayofmonthnextweek < dayofmonth`) | `data_adherents.py` | Cliché mensuel des données adhérents |
| **Chaque vendredi** | `adm_itemsNonRestituesPlus.py` | Liste les documents à passer en "non restitués plus" |
| **Le 1er du mois** | `adm_itemsPerdusPretendusRendus2acquereurs.py` | Envoie aux acquéreurs la liste des documents sortis des collections (perdus/prétendus rendus/non restitués) |
| **Chaque mercredi** | `adm_items2del2adm.py`, `adm_items2delb2adm.py`, `adm_itemsRetards2adm.py`, `adm_itemsPerdus2adm.py`, `adm_itemsPretendusRendus2adm.py`, `adm_itemsNonRestituesPlus.py`, `data_sauv_bdd.py` | Listes de gestion des exemplaires à traiter (à supprimer, en retard, perdus...) + sauvegarde `mysqldump` hebdomadaire de `statdb` |
| **Chaque jour** | `find ... -ctime +30 -exec rm` | Purge des logs cron de plus de 30 jours (`log/crontab/lanceur_*.log`) |

Chaque script est autonome, invocable indépendamment (`python kibini/data_issues.py`) pour du rattrapage ou du débogage. Le job `adm_itemsNonRestituesPlus_retours.py` du quotidien est présent dans le script mais **commenté** (désactivé), de même que `data_entrees_opteio.py` (voir note ci-dessus).

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

### Modifier le menu et les intitulés d'un tableau de bord

Deux fichiers à éditer, indépendants l'un de l'autre (rien ne les garde synchronisés automatiquement) :

1. **`webapp/dashboards.py`** — dictionnaire `DASHBOARDS`, une entrée par route (clé = chemin de l'URL). `label1`/`label2`/`label3` forment le fil d'Ariane affiché en haut de la page, `dashboard.src`/`height` pointent vers le HTML du notebook exporté (ou l'URL Kibana pour les dashboards encore actifs) et sa hauteur d'iframe. `app.py` boucle sur ce dict pour enregistrer les routes : ajouter une entrée suffit à créer la page, pas besoin de toucher `app.py`.
2. **`webapp/templates/includes/sidebar.html`** — le menu latéral lui-même, un `<a href>` par entrée regroupé par section (Grand-Plage, Médiathèque, Zèbre, Collectivités, poldoc, synthèses). Fichier HTML statique à éditer à la main : ajouter/renommer/retirer un lien n'a aucun effet sur `DASHBOARDS` et réciproquement — une page peut exister dans l'un sans être présente dans l'autre (cas déjà vu lors du retrait des dashboards Kibana, voir `ARCHIVED_KIBANA_DASHBOARDS` dans `dashboards.py`).

Pour ajouter une nouvelle page de tableau de bord : ajouter l'entrée dans `DASHBOARDS` **et** le lien dans `sidebar.html`, dans les deux cas avec le même chemin d'URL. Pour renommer un intitulé de menu, éditer le texte du `<a>` dans `sidebar.html` ; pour renommer le fil d'Ariane d'une page, éditer `label1`/`label2`/`label3` dans `dashboards.py`. Les templates Jinja2 sont rechargés à la volée en `flask run --debug` (voir plus bas), mais pas sous Gunicorn : en production, un changement nécessite un `git pull` + `sudo systemctl restart kibini-web`.

### Consolidation des rapports Koha derrière `/liste` (dispos/traitement/mise de côté/expirées/perdus)

`/liste` (voir `services.get_list_data`) affichait à l'origine ~30 rapports SQL Koha quasi-identiques (un par étage/site/public-personnel), chacun avec ses propres littéraux codés en dur. Ils ont été consolidés en quelques rapports paramétrés via les paramètres runtime Koha (`<<Label>>`, `<<Label|list>>`, voir `svc/report` : `sql_params`/`param_names`) : `_DISPO_PARAMS`/`_DISPO_BUS_PARAMS`, `_TRAIT_PARAMS`/`_TRAIT_BUS_PARAMS`, `_MISECOTE_PARAMS`, `_EXPIREES_PARAMS`, `_PERDUS_PARAMS` dans `services.py`. Restent non consolidés (établis comme des requêtes métier réellement différentes) : contentieux (`aazzz`/`bbzzz`, ids 207/208) et `tzzzz` (307).

**Bug corrigé au passage** : les clés `p_et0_s1` à `p_et3_s1` ("documents perdus depuis une semaine") pointaient par erreur vers les rapports Koha "cinq semaines" (152-155) au lieu des rapports "une semaine" (140-143). Les rapports "trois"/"cinq" semaines existaient bien côté Koha mais n'étaient jamais câblés dans `_LISTE_RAPPORTS` (ce qui ressemblait à un simple rapport manquant). Les 15 anciens rapports `WS_perdus_*_semaine_et*` (+ variante Bus) sont remplacés par un unique rapport paramétré (`_RAPPORT_PERDUS_ID`, `<<Localisation|list>>` + `<<Semaines>>`) — pas de risque de fan-out titre ici (jointure directe sur `items`, pas sur `reserves`/`biblionumber`).

**Rapports Koha devenus orphelins**, à supprimer manuellement dans Koha une fois les consolidations confirmées en usage réel (non fait automatiquement, aucun outil ne le permet depuis ce dépôt) : 140-143, 173, 148-151, 174, 152-155, 175 (anciens `WS_perdus_*_semaine_et*`), ainsi que 136-139, 171 (`Reservations_WS_perdues_*`, une génération encore antérieure, déjà orpheline avant même cette consolidation — jamais référencée dans `_LISTE_RAPPORTS`/`_LISTE_TITRES`).

**Bug d'échappement HTML corrigé** : Koha renvoyait la colonne "Code-barres" déjà sous forme de lien HTML tout fait (`<a href="...">code</a>), que Template Toolkit (Perl d'origine) affichait tel quel mais que Jinja2 échappe par défaut. Plutôt que de démarquer ce HTML avec `| safe` (recevoir du HTML pré-construit depuis un rapport SQL externe est fragile), le SQL de chaque rapport consolidé a été changé pour renvoyer barcode et itemnumber en colonnes séparées, le lien étant reconstruit dans le template (`liste_reservations.html`, `liste_misecote.html`, `liste_expirees.html`, `liste_perdus.html`). `liste_contentieux.html`/`liste_contentieuxb.html` n'ont pas de champ équivalent et ne sont pas concernés.

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

### Publier un nouveau notebook, du `.ipynb` à la page web

Chaîne complète pour ajouter un nouveau tableau de bord, du notebook jusqu'à la page accessible dans le site :

1. **Écrire le notebook** — `kibini/notebook_<nom>.ipynb`, dans l'env conda `kibini` (pas `kibini-web`, voir plus bas). Le notebook doit pouvoir s'exécuter de bout en bout sans cellule interactive (il sera lancé via `jupyter nbconvert --execute`) et ne pas afficher de code en sortie utile (`--no-input` masque le code mais pas les éventuels `print` de debug).
2. **Ajouter son nom à la liste des trois scripts de publication** — `notebook2html.sh`, `notebook2html_flask.sh` et `test_notebook2html.sh` (voir section précédente) : ajouter `notebook_<nom>` (sans l'extension `.ipynb`) dans le `for filename in ...` de chacun. Les trois listes doivent rester identiques.
3. **Générer le HTML en dev** — depuis `kibini2/`, env `kibini` activé : `./notebook2html_flask.sh` (ou `test_notebook2html.sh` après y avoir mis temporairement le seul nouveau notebook, pour ne pas tout relancer). Le fichier produit atterrit dans `kibini/webapp/static/data/notebook_<nom>.html` — rappel : ce dossier est gitignoré, donc en prod il faut lancer `notebook2html.sh` séparément sur le serveur (ou transférer le HTML manuellement, voir "Topologie").
4. **Brancher la route dans `webapp/dashboards.py`** — ajouter une entrée dans `DASHBOARDS` avec le chemin d'URL souhaité, les `label1`/`label2`/`label3` du fil d'Ariane, et `dashboard.src` pointant vers `/static/data/notebook_<nom>.html` (+ `height` ajusté à la taille du rendu).
5. **Ajouter le lien dans le menu** — un nouveau `<a href="...">` dans `webapp/templates/includes/sidebar.html`, dans la section appropriée, avec le même chemin d'URL qu'à l'étape 4.
6. **Recharger l'appli** — en dev (`flask run --debug`), les templates et `dashboards.py` sont repris à la prochaine requête sans redémarrage. En prod, `git pull` + `sudo systemctl restart kibini-web` (Gunicorn ne recharge rien à chaud).

Pour une mise à jour périodique d'un notebook déjà publié (pas un nouveau tableau de bord), seule l'étape 3 est à rejouer. **`crontab_lanceur.sh` n'appelle aucun des trois scripts `notebook2html*.sh`** : leur exécution n'est donc pas automatisée par le cron actuel et doit être déclenchée manuellement (ou via un cron séparé à mettre en place si une régénération périodique est souhaitée).

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
| `opteio` | `login`/`password` — API de comptage de fréquentation par capteurs | `data_entrees_opteio.py`, `kiblib.utils.opteio.OpteioClient` |
| `salt` | sel de hachage | `kiblib.utils.hashid` (anonymisation des identifiants adhérents) |
| `dir_log` | répertoire des logs | `kiblib.utils.log.Log` (scripts cron uniquement) |
| `dir_data` | répertoire de données | scripts d'administration ponctuels |
| `dir_webdav` | chemin des dumps Koha à charger | `adm_vendangeur_auth2dedupl.py` (script d'admin ponctuel — `data_load_koha_prod.py` calcule son propre chemin en dur, sans passer par cette clé) |
| `smtp` | serveur SMTP (adresse IP) | `kiblib.utils.email_sender.send_email`, utilisé par la webapp pour les notifications de suggestions |
| `acquereurs` | liste `borrowernumber`/`nom`/`courriel` des acquéreurs | webapp (`/suggestions` : liste déroulante d'attribution + email de notification) |

Cette configuration est **par machine** (dev et prod ont chacune leur propre `kibini_conf.yml`, non synchronisé par git) — les identifiants ou hôtes peuvent différer entre les deux (ex. `webservice.base` doit être joignable depuis la machine, ce qui n'est pas le cas depuis toutes les machines de dev).
