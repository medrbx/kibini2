"""
Table des tableaux de bord Kibana affichés en iframe, portée depuis les
routes `get '...' => sub { template 'kibana', {...} }` de
kibini_prod/lib/website/dancer.pm.

NB : deux routes du fichier Perl d'origine ("grand-plage/dimanche24" et
"grand-plage/dimanche25") étaient déclarées sans le "/" initial requis par
Dancer2 pour matcher une requête HTTP réelle (le lien de la sidebar, lui,
pointe bien vers "/grand-plage/dimanche24") ; elles sont donc corrigées
ici avec le "/" initial.
"""

DASHBOARDS = {
    "/": {
        "label1": "Bienvenue sur Kibini",
        "label2": "Les tableaux de bord de La Grand-Plage",
        "label3": "Quels sont les services proposés ?",
        "dashboard": {
            "src": "/static/data/notebook_kibini2_0_presentation.html",
            "height": "1400px",
        },
    },

    # PARTIE 1 - La Grand-Plage
    "/grand-plage/activites": {
        "label1": "La Grand-Plage", "label2": "Quelle activité ces 30 derniers jours ?", "label3": "Quelques chiffres",
        "dashboard": {"src": "/static/data/notebook_kibini2_lgp_activite30j.html", "height": "1400px"},
    },
    "/grand-plage/inscrits/profils": {
        "label1": "La Grand-Plage", "label2": "Inscrits", "label3": "Profils des inscrits",
        "dashboard": {"src": "/static/data/notebook_kibini2_lgp_qui_sont_les_inscrits.html", "height": "1400px"},
    },
    "/grand-plage/inscrits/usages": {
        "label1": "La Grand-Plage", "label2": "Inscrits", "label3": "Usages des inscrits",
        "dashboard": {"src": "/static/data/notebook_kibini2_lgp_que_font_les_inscrits.html", "height": "1400px"},
    },
    "/grand-plage/collections/prets": {
        "label1": "La Grand-Plage", "label2": "Collections", "label3": "Prêts",
        "dashboard": {"src": "/static/data/notebook_kibini2_lgp_evolution_prets.html", "height": "1400px"},
    },
    "/grand-plage/collections/retours": {
        "label1": "La Grand-Plage", "label2": "Collections", "label3": "Retours",
        "dashboard": {"src": "/static/data/notebook_kibini2_lgp_evolution_retours.html", "height": "1400px"},
    },
    "/grand-plage/collections/reservations": {
        "label1": "La Grand-Plage", "label2": "Collections", "label3": "Réservations",
        "dashboard": {"src": "/static/data/notebook_kibini2_lgp_evolution_resas.html", "height": "1400px"},
    },
    "/grand-plage/collections/reservations_usages": {
        "label1": "La Grand-Plage", "label2": "Collections", "label3": "Usage des réservations",
        "dashboard": {"src": "/static/data/notebook_kibini2_lgp_quels_usages_resas.html", "height": "1400px"},
    },
    "/grand-plage/web/portail": {
        "label1": "La Grand-Plage", "label2": "Portail", "label3": "L'usage du portail",
        "dashboard": {"src": "/static/data/notebook_kibini2_lgp_quels_usages_portail.html", "height": "1400px"},
    },
    "/grand-plage/dimanche22": {
        "label1": "La Grand-Plage", "label2": "Activité", "label3": "Dimanches 2022-2023",
        "dashboard": {"src": "/static/data/notebook_dimanche22.html", "height": "2600px"},
    },
    "/grand-plage/dimanche23": {
        "label1": "La Grand-Plage", "label2": "Activité", "label3": "Dimanches 2023-2024",
        "dashboard": {"src": "/static/data/notebook_dimanche23.html", "height": "2600px"},
    },
    "/grand-plage/dimanche24": {
        "label1": "La Grand-Plage", "label2": "Activité", "label3": "Dimanches 2024-2025",
        "dashboard": {"src": "/static/data/notebook_dimanche24.html", "height": "2600px"},
    },
    "/grand-plage/dimanche25": {
        "label1": "La Grand-Plage", "label2": "Activité", "label3": "Dimanches 2025-2026",
        "dashboard": {"src": "/static/data/notebook_dimanche25.html", "height": "2600px"},
    },
    "/grand-plage/dimanche26": {
        "label1": "La Grand-Plage", "label2": "Activité", "label3": "Dimanches 2026-2027",
        "dashboard": {"src": "/static/data/notebook_dimanche26.html", "height": "2600px"},
    },
    "/grand-plage/synthese_pluriannuelle": {
        "label1": "La Grand-Plage", "label2": "Activité", "label3": "Synthèse pluriannuelle",
        "dashboard": {"src": "/static/data/notebook_kibini2_lgp_syntheses_pluriannuelles.html", "height": "1500px"},
    },

    # PARTIE 2 - La Médiathèque
    "/mediatheque/activites": {
        "label1": "La Médiathèque", "label2": "Activité",
        "dashboard": {"src": "/static/data/notebook_kibini2_med_activite_hebdo.html", "height": "1400px"},
    },
    "/mediatheque/entrees": {
        "label1": "La Médiathèque", "label2": "Entrées",
        "dashboard": {"src": "/static/data/notebook_kibini2_med_evolution_entrees.html", "height": "1400px"},
    },
    "/mediatheque/collections/prets_repartition": {
        "label1": "La Médiathèque", "label2": "Collections", "label3": "Répartition des prêts",
        "dashboard": {"src": "/static/data/notebook_kibini2_med_quelle_repartition_des_prets.html", "height": "1400px"},
    },
    "/mediatheque/collections/prets": {
        "label1": "La Médiathèque", "label2": "Collections", "label3": "Prêts",
        "dashboard": {"src": "/static/data/notebook_kibini2_med_evolution_prets.html", "height": "1400px"},
    },
    "/mediatheque/collections/retours": {
        "label1": "La Médiathèque", "label2": "Collections", "label3": "Retours",
        "dashboard": {"src": "/static/data/notebook_kibini2_med_evolution_retours.html", "height": "1400px"},
    },
    "/mediatheque/collections/reservations": {
        "label1": "La Médiathèque", "label2": "Collections", "label3": "Réservations",
        "dashboard": {"src": "/static/data/notebook_kibini2_med_evolution_resas.html", "height": "1400px"},
    },
    "/mediatheque/webkiosk/connexions": {
        "label1": "La Médiathèque", "label2": "Webkiosk", "label3": "Connexions",
        "dashboard": {"src": "/static/data/notebook_kibini2_med_evolution_webkiosk.html", "height": "1400px"},
    },
    "/mediatheque/webkiosk/impressions": {
        "label1": "La Médiathèque", "label2": "Quelle évolution des impressions ?",
        "dashboard": {"src": "/static/data/notebook_kibini2_med_evolution_impressions.html", "height": "1500px"},
    },
    "/mediatheque/collections/emprunteurs": {
        "label1": "La Médiathèque", "label2": "Collections", "label3": "Emprunteurs",
        "dashboard": {"src": "/static/data/notebook_kibini2_med_qui_sont_les_emprunteurs.html", "height": "1300px"},
    },
    "/mediatheque/collections/emprunteurs/details": {
        "label1": "La Médiathèque", "label2": "Collections", "label3": "Qui emprunte quoi ?",
        "dashboard": {"src": "...", "height": "1200px"},
    },
    "/mediatheque/suggestions/profils": {
        "label1": "La Médiathèque", "label2": "Qui fait des suggestions aux acquéreurs?",
        "dashboard": {"src": "...", "height": "1200px"},
    },
    "/mediatheque/etude/frequentation": {
        "label1": "La Médiathèque", "label2": "Fréquentation de la salle d'étude?",
        "dashboard": {"src": "/static/data/notebook_kibini2_med_evolution_frequentation_etude.html", "height": "1200px"},
    },
    "/mediatheque/action culturelle": {
        "label1": "La Médiathèque", "label2": "Quels publics pour l'action culturelle ?",
        "dashboard": {"src": "/static/data/notebook_kibini2_med_quels_publics_action_culturelle.html", "height": "1500px"},
    },

    # PARTIE 3 - Le Zèbre
    "/zebre/collections/prets": {
        "label1": "La Médiathèque", "label2": "Collections", "label3": "Prêts",
        "dashboard": {"src": "/static/data/notebook_kibini2_zebre_evolution_prets.html", "height": "1400px"},
    },
    "/zebre/collections/retours": {
        "label1": "La Médiathèquee", "label2": "Collections", "label3": "Retours",
        "dashboard": {"src": "/static/data/notebook_kibini2_zebre_evolution_retours.html", "height": "1400px"},
    },
    "/zebre/collections/reservations": {
        "label1": "La Médiathèque", "label2": "Collections", "label3": "Réservations",
        "dashboard": {"src": "/static/data/notebook_kibini2_zebre_evolution_resas.html", "height": "1400px"},
    },
    "/zebre/collections/emprunteurs/details": {
        "label1": "Le Zèbre", "label2": "Collections", "label3": "Qui emprunte quoi ?",
        "dashboard": {"src": "...", "height": "1200px"},
    },

    # PARTIE 4 - Les Collectivités
    "/collectivites/collections/prets": {
        "label1": "Collectivités", "label2": "Collections", "label3": "Prêts",
        "dashboard": {"src": "/static/data/notebook_kibini2_collectivites_evolution_prets.html", "height": "1400px"},
    },

    # PARTIE 5 - Les synthèses pluriannuelles de la Grand-Plage
    "/grand-plage/syntheses/prets": {
        "label1": "La Grand-Plage", "label2": "Synthèses", "label3": "Prêts",
        "dashboard": {"src": "/static/data/notebook_kibini2_synthese_prets.html", "height": "1500px"},
    },

}

# --------------------------------------------------------------------------
# Tableaux de bord Kibana archivés (2026-08-18) : le serveur Kibana
# (129.1.0.237:5601) n'existe plus, ces routes ont donc été retirées de
# DASHBOARDS (plus enregistrées par app.py, donnent 404) et de la sidebar.
# Conservés ici tels quels (labels, hauteur, URL d'embed Kibana d'origine
# avec ses filtres/colonnes) comme référence pour reconstruire l'équivalent
# sous forme de notebook Jupyter (cf. notebook2html.sh) le jour venu.
# --------------------------------------------------------------------------
ARCHIVED_KIBANA_DASHBOARDS = {
    "/mediatheque/webkiosk/profils": {
        "label1": "La Médiathèque", "label2": "Qui utilise le service webkiosk?",
        "dashboard": {"src": "http://129.1.0.237:5601/goto/e2054a9d9694884fe341c1580b50c75e?embed=true", "height": "1500px"},
    },
    "/zebre/collections/emprunteurs": {
        "label1": "Le Zèbre", "label2": "Collections", "label3": "Emprunteurs",
        "dashboard": {
            "src": "http://129.1.0.237:5601/app/kibana#/dashboard/Qui-sont-les-emprunteurs-du-Z%C3%A8bre-questionmark-?embed=true&_g=(refreshInterval:(display:Off,pause:!f,value:0),time:(from:now-1y,mode:quick,to:now))&_a=(filters:!(),options:(darkTheme:!f),panels:!((col:1,id:'Nombre-d!'emprunteurs-par-mois',panelIndex:1,row:1,size_x:8,size_y:2,type:visualization),(col:1,id:Nombre-de-pr%C3%AAts-par-mois,panelIndex:3,row:3,size_x:8,size_y:2,type:visualization),(col:9,id:Pr%C3%AAts,panelIndex:4,row:3,size_x:4,size_y:2,type:visualization),(col:1,id:Emprunteurs-distincts-par--de-Roubaix,panelIndex:6,row:5,size_x:6,size_y:3,type:visualization),(col:7,id:Emprunteurs-distincts-par-ville,panelIndex:7,row:5,size_x:6,size_y:3,type:visualization),(col:9,id:Emprunteurs-distincts-par-%C3%A2ge-m%C3%A9diath%C3%A8que,panelIndex:8,row:8,size_x:4,size_y:3,type:visualization),(col:1,id:Emprunteurs-distincts-par-type-de-carte,panelIndex:9,row:8,size_x:4,size_y:3,type:visualization),(col:5,id:Emprunteurs-distincts-par-sexe,panelIndex:10,row:8,size_x:4,size_y:3,type:visualization),(col:9,id:'Nombre-d!'emprunteurs-',panelIndex:11,row:1,size_x:4,size_y:2,type:visualization)),query:(query_string:(analyze_wildcard:!t,query:'pret_site%20:%20%22Z%C3%A8bre%22')),title:'Qui%20sont%20les%20emprunteurs%20du%20Z%C3%A8bre%20%3F',uiState:(P-1:(vis:(legendOpen:!f)),P-10:(vis:(legendOpen:!f)),P-3:(vis:(legendOpen:!f)),P-6:(vis:(legendOpen:!f)),P-7:(vis:(legendOpen:!f)),P-8:(vis:(legendOpen:!f)),P-9:(vis:(legendOpen:!f))))",
            "height": "1200px",
        },
    },
    "/collectivites/collections/documents": {
        "label1": "Collectivités", "label2": "Collections", "label3": "Documents",
        "dashboard": {
            "src": "http://129.1.0.237:5601/app/kibana#/dashboard/Quelles-collections-pour-les-collectivit%C3%A9s-questionmark-?embed=true&_g=(refreshInterval:(display:Off,pause:!f,value:0),time:(from:now-15y,mode:relative,to:now))&_a=(filters:!(),options:(darkTheme:!f),panels:!((col:7,id:Documents-collectivit%C3%A9s,panelIndex:5,row:1,size_x:6,size_y:3,type:visualization),(col:1,id:Documents-empruntables-collectivit%C3%A9s,panelIndex:6,row:1,size_x:6,size_y:3,type:visualization),(col:1,id:Nombre-de-documents-des-collectivit%C3%A9s-par-collection,panelIndex:7,row:4,size_x:12,size_y:8,type:visualization)),query:(query_string:(analyze_wildcard:!t,query:'localisation:%20%22Magasin%20collectivit%C3%A9s%22')),title:'Quelles%20collections%20pour%20les%20collectivit%C3%A9s%20%3F',uiState:())",
            "height": "1300px",
        },
    },
    "/grand-plage/syntheses/inscrits": {
        "label1": "La Grand-Plage", "label2": "Synthèses", "label3": "Inscrits",
        "dashboard": {
            "src": "http://129.1.0.237:5601/app/kibana#/dashboard/AWHc1TFtpw5wXLtt1uz1?embed=true&_g=(refreshInterval%3A(display%3AOff%2Cpause%3A!f%2Cvalue%3A0)%2Ctime%3A(from%3Anow-1y%2Fy%2Cmode%3Aquick%2Cto%3Anow-1y%2Fy))",
            "height": "1100px",
        },
    },
    "/grand-plage/syntheses/collections": {
        "label1": "La Grand-Plage", "label2": "Synthèses", "label3": "Collections",
        "dashboard": {
            "src": "http://129.1.0.237:5601/app/kibana#/dashboard/AWHc5g3Ppw5wXLtt1uz6?embed=true&_g=(refreshInterval%3A(display%3AOff%2Cpause%3A!f%2Cvalue%3A0)%2Ctime%3A(from%3Anow-1y%2Fy%2Cmode%3Aquick%2Cto%3Anow-1y%2Fy))",
            "height": "1100px",
        },
    },
}
