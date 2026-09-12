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

## Export open data adhérents — jeu "caractéristiques des adhérents" sur data.lillemetropole.fr

Chaîne de scripts **manuelle** (pas de cron) qui alimente le jeu de données publié par la Ville de Roubaix sur data.lillemetropole.fr (`ville_roubaix:caracteristiques_des_adherents_a_la_mediatheque_la_grand_plage`), pas mis à jour depuis les extractions 2019/2020. Reconstituée en septembre 2026 en vue de remplacer ce jeu par un historique complet 2015-2025 ; qui fait quoi :

| Fichier | Rôle |
|---|---|
| `kiblib/adherent.py` | Classe `Adherent`, partagée avec le reste du pipeline (dashboards, formulaire SLL...). `get_adherent_statdb_data()`/`get_adherent_es_data()` existaient déjà (utilisées par les notebooks de restitution) ; `get_adherent_opendata_data()`/`get_adherent_opendata_data_columns()` ont été ajoutées pour dériver et renommer vers le schéma exact du jeu publié sur data MEL. |
| `stat_adh2oa.py` | Script à lancer **manuellement, une fois par extraction annuelle** (date en dur dans le fichier, à éditer avant chaque lancement) : interroge `statdb.stat_adherents` pour une `date_extraction` donnée, enrichit via `Adherent.get_adherent_opendata_data()`, écrit le CSV brut de l'année (colonnes internes `adh_*`, même format que `adherents_2015.csv`...`adherents_2022.csv`) dans `data/openData/data/adherents_<annee>.csv`. Ne récupère pas `borrowernumber` : les 4 colonnes d'attributs (action culturelle, arrêt Zèbre, structure collective, PCS) restent vides pour les nouvelles extractions - voir plus bas. |
| `data/openData/data/fusion_fichiers.ipynb` | Notebook historique (2015-2022 uniquement, pas à relancer tel quel) : concatène les exports annuels produits par `stat_adh2oa.py` puis **décode le JSON** alors stocké dans `statdb.stat_adherents.inscription_attribut` (`{"action":"...","zèbre":"...","PCS":"...","collectivités":"..."}`) en 4 colonnes propres. A produit `data/openData/data/adherents.csv`, source (après compression manuelle non scriptée) de `data/adherents_2015-2025.csv.gz`. |
| `stat_opendata_fusion.py` | Remplace `fusion_fichiers.ipynb` pour les mises à jour futures (plus d'étape JSON, devenue obsolète - voir plus bas) : concatène l'historique multi-années existant avec le CSV brut d'une nouvelle année (sortie de `stat_adh2oa.py`) et écrit le nouvel historique. Noms de fichiers en dur en tête de script, à éditer avant chaque lancement. |
| `data/openData/analyse_adh.ipynb` | Notebook d'exploration (ne produit pas de fichier réutilisé ailleurs) : lit `data/adherents.csv`, calcule des statistiques d'usage par année (exclut 2020). |
| `stat_opendata_publish.py` | Prend l'historique multi-années (colonnes internes `adh_*`) et le renomme vers un schéma grand public (table de correspondance dans le fichier), codes techniques conservés avec un préfixe `code_*`. Noms de fichiers en dur en tête de script, à éditer avant chaque lancement (en cohérence avec `FICHIER_SORTIE` de `stat_opendata_fusion.py`). Écrit le CSV candidat pour remplacer le jeu publié sur data MEL, accompagné du dictionnaire de données `data/openData/adherents_2015-2025_opendata_dictionnaire.csv` (à régénérer/vérifier à la main si de nouvelles valeurs apparaissent). |

### Ajouter une nouvelle année à l'historique (procédure annuelle)

1. Éditer la date dans `stat_adh2oa.py` (variable `date`, en tête de fichier) et le lancer : produit `data/openData/data/adherents_<annee>.csv`.
2. Éditer `FICHIER_HISTORIQUE`/`NOUVELLE_ANNEE`/`FICHIER_SORTIE` en tête de `stat_opendata_fusion.py` et le lancer : produit le nouvel historique fusionné (`data/adherents_2015-<annee>.csv.gz`).
3. Éditer `FICHIER_HISTORIQUE`/`FICHIER_SORTIE` en tête de `stat_opendata_publish.py` et le lancer : produit le CSV au format grand public, prêt à déposer sur data MEL.
4. Vérifier le dictionnaire de données (`adherents_2015-2025_opendata_dictionnaire.csv`) : les colonnes ne changent pas, mais une nouvelle valeur catégorielle (nouvelle action culturelle, nouvel arrêt Zèbre...) doit y être ajoutée à la main si elle apparaît.

Point de vigilance : les colonnes `code_action_culturelle`/`action_culturelle_associee`/`code_arret_bus_zebre`/`arret_bus_zebre`/`code_type_structure_collective`/`type_structure_collective` seront **vides pour toute année à partir de 2023** (voir section suivante) - ce n'est pas un bug de cette procédure, la donnée source ne le permet plus en l'état.
| `notebook_sll.ipynb` | Sans lien avec l'open data : alimente l'enquête annuelle SLL (ministère de la Culture). Réutilise `Adherent.get_adherent_statdb_data()`/`get_adherent_es_data()` pour une extraction ponctuelle. |
| `notebook_kibini2_lgp_que_font_les_inscrits.ipynb` | Dashboard de restitution interne, sans lien avec la publication open data : calcule indépendamment `nb_venues_prets` et une segmentation d'usage, logique proche de `get_opendata_activite()` mais implémentation séparée. |

### Bug historique retrouvé sur le jeu actuellement publié sur data MEL

Le CSV en ligne (extractions 2019/2020 uniquement) a été généré à partir de la sortie brute annuelle de `stat_adh2oa.py`, **sans** passer par l'étape de décodage JSON de `fusion_fichiers.ipynb`. Pour ces années-là, `stat_adherents.inscription_attribut` contenait du JSON (clés mojibake `zÃ¨bre`/`collectivitÃ©s`, vraisemblablement un aller-retour Latin-1/UTF-8 au moment de sa construction) : sur ~3 % des lignes publiées, les colonnes `attribut_inscription`/`inscription_personnalite`/`inscription_site_inscription`/`inscription_type_carte` affichent donc du JSON brut mal échappé (et des colonnes décalées) à la place de leur valeur. `stat_opendata_publish.py` ne reproduit pas ce bug puisqu'il part du fichier déjà fusionné/décodé par `fusion_fichiers.ipynb`.

### `inscription_attribut` a changé de format dans le temps

- Jusqu'à ~2022 (années couvertes par `fusion_fichiers.ipynb`) : JSON (`{"action": "...", "zèbre": "...", ...}`).
- Actuellement (`data_adherents.py`, `fetch_attributes_by_borrower`) : valeurs jointes par `'|'`, sans le code d'origine (ACTION/BUS/COLLECT/PCS perdu à l'écriture).

Aucun des deux formats ne permet de reconstruire les 4 colonnes séparément pour une extraction récente sans rejoindre `koha_prod.borrower_attributes` par `borrowernumber` (`get_inscription_attributs_code()` dans `adherent.py` - non utilisable depuis `stat_adh2oa.py`, qui ne récupère pas ce champ).

## Jeu open data "affluence horaire" - pas de script producteur dans ce dépôt

Second jeu de données publié par la Ville de Roubaix sur data.lillemetropole.fr : `ville_roubaix:affluence_et_activites_de_la_grand_plage_h_par_h_depuis_2014` (22 018 lignes, colonnes `date`/`annee`/`jour`/`mois`/`heure`/`retours`/`prets`/`connexions_postes`). Comme le jeu adhérents, plus mis à jour depuis 2020.

**Contrairement au jeu adhérents, aucun script ni notebook de ce dépôt ne produit ce fichier** - recherche large sans résultat (noms de colonnes exacts, requêtes SQL combinant `stat_issues`/`stat_prets` et `stat_webkiosk`/`stat_sessions_webkiosk` par heure). Les briques existent séparément (`data_issues.py`/`data_prets.py` pour les prêts-retours, `data_wk_pc.py` pour les connexions postes), mais rien ne les agrège par heure vers ce format. Pas de script `stat_*2oa.py` équivalent à `stat_adh2oa.py` pour ce jeu - à écrire si une mise à jour est décidée.

### Anomalie identifiée et vérifiée sur le jeu publié : connexions fantômes à 2h du matin

Sur les données 2014-2020 : exactement 9 lignes par mois, chaque mois de juillet 2014 à août 2016 (26 mois), toutes `heure=02:00:00`, `connexions_postes=1`, `retours`/`prets` vides, systématiquement sur les jours 1 à 9 du mois - une médiathèque n'ouvre pas à 2h. Le motif s'arrête net en septembre 2016 (3 occurrences ce mois-là puis plus rien de comparable).

Hypothèse initiale (tâche planifiée sur un poste, compte technique webkiosk) **infirmée par vérification directe en base** :
- `statdb.stat_webkiosk` (alimentée par `data_wk_pc.py` depuis les logs du logiciel webkiosk tiers) : aucune ligne à `HOUR(heure_deb)=2` sur les jours 1-9, ni même sur l'ensemble de la journée du 2014-07-02 vérifiée en détail (amplitude réelle du poste ce jour-là : 10h06-18h06).
- `statdb.stat_sessions_webkiosk` (anonymisée quotidiennement par `data_ano.py`) : également vide sur `HOUR(session_date_heure_debut)=2` et jours 1-9, sur toute la période.

Aucune donnée source actuelle n'explique ces lignes : l'artefact vient très probablement du pipeline qui a construit l'export historique à l'époque (l'ancien système Perl `kibini_prod`, antérieur à ce portage Python et absent de ce dépôt) - valeur sentinelle ou bug de jointure non reproductible avec le code actuel. **Recommandation pour une reconstruction de ce jeu** : exclure ces ~235 lignes comme données aberrantes plutôt que de chercher à les réexpliquer.

### Autres points relevés sur ce jeu (non vérifiés en base, à confirmer si reconstruction)

- `NaN` n'a pas un sens fiable : les 3 colonnes ont à la fois des zéros explicites et des valeurs manquantes (`connexions_postes` notamment : 43 zéros vs 6160 `NaN`, 28 % des lignes) - à clarifier/documenter avant toute republication plutôt que de laisser l'ambiguïté "non mesuré" vs "activité nulle".
- Pics extrêmes de `retours` le 2020-03-14 (veille du 1er confinement) et le 2020-10-29 (annonce du 2e) : cohérents avec le contexte (retours massifs avant fermeture), pas des erreurs à corriger.
- Couverture incomplète : démarre le 1er juillet 2014 (pas le 1er janvier, malgré le nom "depuis 2014") ; 261 jours sans aucune ligne sur toute la période (78 en 2020, cohérent avec les confinements ; 42 en 2014 et 57 en 2015, moins évidents - possibles trous de collecte au démarrage, à vérifier).

### `stat_affluence2oa.py` - script de mise à jour (nouveau)

Reconstitue ce jeu à partir de `statdb` pour prolonger l'historique après 2020-12-31 : `prets`/`retours` viennent de `statdb.stat_issues` (`issuedate`/`returndate`, filtré `branch='MED'`), `connexions_postes` de `statdb.stat_webkiosk` (`heure_deb`) - **par choix explicite**, malgré l'import CSV manuel via `data_wk_pc.py` (absent du cron) qui alimente cette table. En pratique, testé sur 2021-2025 : `stat_webkiosk` est bien réalimentée (62 % des lignes ont `connexions_postes > 0`, jusqu'à 108/h) - la réserve initiale (table possiblement à l'arrêt) ne s'est pas vérifiée. `stat_sessions_webkiosk`, elle, reste confirmée non alimentée en nouvelles lignes. Plage de dates en paramètres CLI (`--start-date`/`--end-date`, `YYYY-MM-DD`, bornes incluse/exclue - même convention que `data_issues.py`), pas en dur dans le fichier. Corrige au passage l'ambiguïté `NaN` du jeu publié (voir plus haut) : les créneaux sans activité sortent à `0` explicite, pas vides.

```bash
python stat_affluence2oa.py --start-date 2021-01-01 --end-date 2026-01-01
```

### Anomalie identifiée sur les données 2021-2025 : prêts groupés hors amplitude d'ouverture

Analyse du fichier produit par `stat_affluence2oa.py` sur 2021-2025 : 7 créneaux avec des `prets` en dehors de toute amplitude plausible (3h ou 21h), ex. **70 prêts en 17 secondes à 3h01 le 2021-02-04**, répartis sur 7 adhérents différents (jusqu'à 17 exemplaires pour un seul). Vérifié dans `statdb.stat_issues` : toujours `branch=MED`, catégories d'adhérent normales (BIBL/MEDA/MEDC/MEDP/CSVT, pas de code collectivité), plusieurs adhérents et exemplaires distincts par lot - donc de **vrais prêts**, pas un artefact du pipeline Kibini (`data_issues.py` copie `issuedate` tel quel depuis `koha_prod`, ne le réécrit jamais). La vitesse (des dizaines de prêts sur plusieurs comptes en quelques secondes) exclut une saisie manuelle : traitement automatisé côté Koha ou service de portage/prêt à distance préparé en lot, cause exacte non identifiée.

Ces prêts existent réellement mais ne représentent pas de la fréquentation physique sur le créneau publié : `stat_affluence2oa.py` exclut donc `HOUR(issuedate) NOT BETWEEN 9 AND 19` (amplitude d'ouverture) du comptage `prets`.

### Règle métier : le lundi, seuls les retours sont possibles

La médiathèque est fermée au public le lundi - seule la boîte de retour reste accessible. Tout `prets`/`connexions_postes` enregistré un lundi est donc un test, pas de la fréquentation réelle. `stat_affluence2oa.py` exclut `DAYOFWEEK(...) = 2` (lundi) des comptages `prets` et `connexions_postes` ; `retours` n'est pas filtré par jour de la semaine.

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

### Routes qui appellent un rapport Koha (`svc/report`)

Liste exhaustive des routes de `app.py` qui appellent en dernier ressort `svc/report` côté Koha (via `services._webservice_get`) — les autres routes (dashboards Kibana, `/frequentation/*`, `/form/*`, `/grand-plage/*`...) passent par la base SQL directe (`DbConn`) ou du contenu statique.

Routes à rapport fixe (pas de paramètre) :

| Route | Rapport Koha | Fonction |
|---|---|---|
| `GET /qa/inscrits` | `id=166` | `services.get_borrowers_for_qa` |
| `GET /suggestions` | `id=309` | `services.suggestions3` |

`GET /liste?type=...&loc=...&public=...&wk=...&resbranch=...` — route unique, dispatchée selon la clé `type+loc+public+wk+resbranch` (`services.get_list_data`) :

| Catégorie | Rapport Koha | Paramétrage runtime (`param_names`/`sql_params`) |
|---|---|---|
| Réservations disponibles (RDC→3e étage) | `id=333` | `Localisation\|list`, `Site`, `Cible est personnel` (`_DISPO_PARAMS`) |
| Réservations disponibles, Bus/Zèbre | `id=334` | `Cible est personnel` (`_DISPO_BUS_PARAMS`) |
| Réservations en traitement (RDC→3e étage) | `id=336` | `Localisation\|list`, `Site`, `Cible est personnel` (`_TRAIT_PARAMS`) |
| Réservations en traitement, Bus/Zèbre | `id=337` | `Cible est personnel` (`_TRAIT_BUS_PARAMS`) |
| Réservations mises de côté | `id=338` | `Est Bus` (`_MISECOTE_PARAMS`) |
| Réservations expirées | `id=339` | `Site`, `Cible est personnel`, `Ignorer categorie` (`_EXPIREES_PARAMS`) |
| Documents perdus (1/3/5 semaines, tous étages + Zèbre) | `id=340` | `Localisation\|list`, `Semaines` (`_PERDUS_PARAMS`) |
| Réservations dispo, Quarantaine (`d5azz`/`d5pzz`) | `id=205` / `id=206` | aucun (rapport figé, `_LISTE_RAPPORTS`) |
| Réservations annulées la veille (`e0zzz`) | `id=177` | aucun |
| Contentieux — personnes à appeler (`aazzz`) | `id=207` | aucun |
| Contentieux — titres de recettes (`bbzzz`) | `id=208` | aucun |
| Réservations reparties en rayons (`tzzzz`) | `id=307` | aucun — template dédié `liste_reservations_rayons.html` (voir plus bas) |

Si la clé ne correspond à aucune entrée, `/liste` renvoie une liste vide sans appeler Koha.

### Consolidation des rapports Koha derrière `/liste` (dispos/traitement/mise de côté/expirées/perdus)

`/liste` (voir `services.get_list_data`) affichait à l'origine ~30 rapports SQL Koha quasi-identiques (un par étage/site/public-personnel), chacun avec ses propres littéraux codés en dur. Ils ont été consolidés en quelques rapports paramétrés via les paramètres runtime Koha (`<<Label>>`, `<<Label|list>>`, voir `svc/report` : `sql_params`/`param_names`) : `_DISPO_PARAMS`/`_DISPO_BUS_PARAMS`, `_TRAIT_PARAMS`/`_TRAIT_BUS_PARAMS`, `_MISECOTE_PARAMS`, `_EXPIREES_PARAMS`, `_PERDUS_PARAMS` dans `services.py`. Restent non consolidés (établis comme des requêtes métier réellement différentes) : contentieux (`aazzz`/`bbzzz`, ids 207/208) et `tzzzz` (307).

**Bug corrigé au passage** : les clés `p_et0_s1` à `p_et3_s1` ("documents perdus depuis une semaine") pointaient par erreur vers les rapports Koha "cinq semaines" (152-155) au lieu des rapports "une semaine" (140-143). Les rapports "trois"/"cinq" semaines existaient bien côté Koha mais n'étaient jamais câblés dans `_LISTE_RAPPORTS` (ce qui ressemblait à un simple rapport manquant). Les 15 anciens rapports `WS_perdus_*_semaine_et*` (+ variante Bus) sont remplacés par un unique rapport paramétré (`_RAPPORT_PERDUS_ID`, `<<Localisation|list>>` + `<<Semaines>>`) — pas de risque de fan-out titre ici (jointure directe sur `items`, pas sur `reserves`/`biblionumber`).

**Rapports Koha devenus orphelins**, à supprimer manuellement dans Koha une fois les consolidations confirmées en usage réel (non fait automatiquement, aucun outil ne le permet depuis ce dépôt) : 140-143, 173, 148-151, 174, 152-155, 175 (anciens `WS_perdus_*_semaine_et*`), ainsi que 136-139, 171 (`Reservations_WS_perdues_*`, une génération encore antérieure, déjà orpheline avant même cette consolidation — jamais référencée dans `_LISTE_RAPPORTS`/`_LISTE_TITRES`).

**Bug d'échappement HTML corrigé** : Koha renvoyait la colonne "Code-barres" déjà sous forme de lien HTML tout fait (`<a href="...">code</a>), que Template Toolkit (Perl d'origine) affichait tel quel mais que Jinja2 échappe par défaut. Plutôt que de démarquer ce HTML avec `| safe` (recevoir du HTML pré-construit depuis un rapport SQL externe est fragile), le SQL de chaque rapport consolidé a été changé pour renvoyer barcode et itemnumber en colonnes séparées, le lien étant reconstruit dans le template (`liste_reservations.html`, `liste_misecote.html`, `liste_expirees.html`, `liste_perdus.html`). `liste_contentieux.html`/`liste_contentieuxb.html` n'ont pas de champ équivalent et ne sont pas concernés.

**Bug corrigé — colonnes décalées sur `tzzzz`** : `tzzzz` (id 307) partage le type `t` avec les rapports trait consolidés, mais son SQL n'a pas été modifié par la consolidation ci-dessus — ses 15 colonnes (`itemnumber`, `biblionumber`, `title`, `Vol.`, `Titre de partie`, espace, cote, code-barres, `reservedate`, nom adhérent, `biblionumber` dupliqué, `borrowernumber`, `author`, `dateaccessioned`, note) n'ont jamais correspondu à l'ordre désormais attendu par `liste_reservations.html` (barcode/itemnumber séparés pour les rapports consolidés). `tzzzz` affichait donc des colonnes décalées, et sa colonne code-barres — un `GROUP_CONCAT` de liens `<a>` déjà complets (un par exemplaire, séparés par `<br>`, générés directement par le SQL) — apparaissait échappée (littéralement `<a href="...">...</a>`) au lieu d'un lien cliquable. Un template dédié `liste_reservations_rayons.html` reprend le mapping réel des 15 colonnes, avec `| safe` uniquement sur cette colonne code-barres déjà prête à l'emploi (pas de reconstruction de lien, contrairement aux rapports consolidés) ; `_LISTE_TEMPLATES_OVERRIDE` dans `services.py` le sélectionne spécifiquement pour la clé `tzzzz`, sans toucher aux autres rapports de type `t`.

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
gunicorn "webapp.app:create_app()" --workers 3 --bind 0.0.0.0:1789
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
