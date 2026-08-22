"""
Portage Flask du site web Kibini (kibini_prod/lib/website/dancer.pm, Dancer2).

Tourne dans son propre environnement conda "kibini-web" (voir webapp/environment.yml),
distinct de l'env "kibini" utilisé par le pipeline de notebooks/scripts cron :
Flask exige Jinja2 >= 3.1, qui casse jupyter nbconvert (encore sur Jinja2 3.0.2
dans "kibini"). Ne jamais réinstaller flask dans l'env "kibini".

Lancement en développement (depuis kibini2/kibini, env "kibini-web" activé) :
    FLASK_APP=webapp.app:create_app FLASK_DEBUG=1 flask run
"""
from flask import Flask, redirect, render_template, request

from webapp import services
from webapp.dashboards import DASHBOARDS

APPNAME = "Kibini - les tableaux de bord de la Grand-Plage"


def create_app():
    app = Flask(__name__)

    @app.context_processor
    def inject_appname():
        return {"appname": APPNAME}

    def _kibana_view(page):
        def view():
            return render_template("kibana.html", **page)
        return view

    for path, page in DASHBOARDS.items():
        endpoint = f"dashboard{path}"
        app.add_url_rule(path, endpoint, _kibana_view(page), strict_slashes=False)

    # PARTIE 5 - La poldoc de La Grand-Plage

    @app.route("/grand-plage/collections/ensemble")
    def collections_grand_plage():
        return render_template(
            "collections2.html",
            label1="La Grand-Plage", label2="Collections", label3="Principaux indicateurs",
            file_2016="/static/data/poldoc/Statistiques_collections_2016_v20170506.xlsx",
            file_2017="/static/data/poldoc/Statistiques_collections_2017.xlsx",
            file_2018="/static/data/poldoc/Statistiques_collections_2018.xlsx",
            file_2019="/static/data/poldoc/Statistiques_collections_2019_VM.xlsx",
            file_2020="/static/data/poldoc/Statistiques_collections_2020_VM.xlsx",
            file_2021="/static/data/poldoc/Statistiques_collections_2021.xlsx",
            file_2022="/static/data/poldoc/Statistiques_collections_2022_20230128.xlsx",
            file_2023="/static/data/poldoc/Statistiques_collections_2023_v20240113.xlsx",
            file_2024="/static/data/poldoc/Statistiques_collections_2024.xlsx",
            file_2025="/static/data/poldoc/Statistiques_collections_2025.xlsx",
        )

    # NB : ces 3 routes appellent, côté Perl, une fonction GetDataCollections()
    # qui n'existe nulle part dans le code source (bug préexistant : `use data;`
    # est commenté dans dancer.pm et data.pm ne définit pas cette fonction).
    # Elles ne sont d'ailleurs jamais atteignables depuis la sidebar (liens
    # commentés). On les porte donc avec des indicateurs vides plutôt que de
    # planter, pour rester fonctionnellement équivalent au comportement réel.
    for path, label1 in (
        ("/mediatheque/collections/ensemble", "Médiathèque"),
        ("/zebre/collections/ensemble", "Le Zèbre"),
        ("/collectivites/collections/ensemble", "Collectivités"),
    ):
        def _view(label1=label1):
            return render_template(
                "collections.html",
                label1=label1, label2="Collections", label3="Principaux indicateurs sur 12 mois",
                indicateurs={},
            )
        app.add_url_rule(path, f"collections{path}", _view)

    # OUTILS

    @app.route("/qa/inscrits")
    def qa_inscrits():
        return render_template(
            "qa_borrowers.html",
            label1="Qualité du fichier adhérents",
            borrowers=services.get_borrowers_for_qa(),
        )

    @app.route("/suggestions")
    def suggestions_view():
        return render_template(
            "suggestions.html",
            label1="Suggestions",
            suggestions=services.suggestions3(),
            acquereurs=services.acquereurs(),
        )

    @app.route("/suggestions/mod", methods=["POST"])
    def suggestions_mod():
        suggestionid = request.form["suggestionid"]
        managedby = request.form["borrnummanagedby"]
        title = request.form["title"]
        services.mod_suggestion2(suggestionid, managedby)

        from_, to, subject, msg = services.construction_courriel(managedby, title)
        services.send_email(from_, to, subject, msg)

        return redirect("/suggestions")

    @app.route("/frequentation/etude")
    def frequentation_etude():
        return render_template(
            "frequentation.html",
            label1="Fréquentation de la salle d'étude",
            lecteurs_presents=services.get_today_entrance(),
            jours=services.get_past_entrances(),
        )

    @app.route("/frequentation/etude/post", methods=["POST"])
    def frequentation_etude_post():
        cardnumber = request.form.get("cardnumber")
        action = "Attention : aucun code-barre n'a été saisi."
        if cardnumber:
            entree = services.is_entrance(cardnumber)
            action = "sortie" if entree == 0 else "entrée"

        return render_template(
            "frequentation.html",
            label1="Fréquentation de la salle d'étude",
            entree=action,
            cardnumber=cardnumber,
            lecteurs_presents=services.get_today_entrance(),
            jours=services.get_past_entrances(),
        )

    @app.route("/form/action_culturelle")
    def form_action_culturelle():
        return render_template(
            "action_culturelle.html",
            label1="Action culturelle",
            actions=services.list_actions_culturelle(),
        )

    @app.route("/form/action_culturelle/post", methods=["POST"])
    def form_action_culturelle_post():
        f = request.form
        services.insert_action_culturelle(
            f.get("date"), f.get("action"), f.get("lieu"), f.get("type"),
            f.get("public"), f.get("partenariat"), f.get("participants"),
        )
        return render_template(
            "action_culturelle.html",
            label1="Action culturelle",
            actions=services.list_actions_culturelle(),
        )

    @app.route("/form/action_coop")
    def form_action_coop():
        return render_template(
            "action_coop.html",
            label1="Action de coopération",
            actions=services.get_list_actions_cooperation(),
        )

    @app.route("/form/action_coop/post", methods=["POST"])
    def form_action_coop_post():
        f = request.form
        services.add_action_cooperation(
            f.get("date"), f.get("lieu"), f.get("type_action"), f.get("nom_action"),
            f.get("type_structure"), f.get("nom_structure"), f.get("participants"),
            f.get("referent_action"),
        )
        return render_template(
            "action_coop.html",
            label1="Action de coopération",
            actions=services.get_list_actions_cooperation(),
        )

    # Listes de réservations et de perdus
    @app.route("/liste")
    def liste():
        params = request.args.to_dict()
        list_data = services.get_list_data(params)
        return render_template(
            f"{list_data['template']}.html",
            label1=list_data["titre"],
            rows=list_data["rows"],
        )

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("500.html"), 500

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
