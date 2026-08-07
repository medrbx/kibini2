from sqlalchemy import text

from kiblib.utils.db import DbConn
from kiblib.utils.log import Log

# on récupère le borrowernumber, le sexe, l'âge, la ville, l'iris et la
# catégorie du titulaire d'une carte
BORROWER_QUERY = text(
    """
    SELECT
        borrowernumber,
        CASE
            WHEN title = 'Madame' THEN 'Femme'
            WHEN title = 'Monsieur' THEN 'Homme'
            WHEN categorycode NOT IN ('BIBL', 'CSLT', 'CSVT', 'MEDA', 'MEDB', 'MEDC', 'MEDP') THEN 'NP'
        END,
        YEAR(CURDATE()) - YEAR(dateofbirth),
        city,
        altcontactcountry,
        categorycode
    FROM koha_prod.borrowers
    WHERE cardnumber = :cardnumber
    """
)

# on ne touche pas aux entrées du jour même (pas encore "closes")
UPDATE_QUERY = text(
    """
    UPDATE statdb.stat_freq_etude
    SET
        borrowernumber = :borrowernumber,
        sexe = :sexe,
        age = :age,
        ville = :ville,
        iris = :iris,
        categorycode = :categorycode
    WHERE cardnumber = :cardnumber AND datetime_entree < CURDATE()
    """
)


def mod_entrance_adding_data(engine):
    """
    Rafraîchit les données socio-démographiques des fréquentants de la salle
    d'étude des 7 derniers jours, sur l'ensemble de leur historique d'entrées
    (hors entrées du jour même).
    """
    with engine.begin() as conn:
        cardnumbers = [
            row[0]
            for row in conn.execute(
                text(
                    "SELECT DISTINCT cardnumber FROM statdb.stat_freq_etude "
                    "WHERE datetime_entree >= CURDATE() - INTERVAL 7 DAY"
                )
            )
        ]

    nb_lignes_maj = 0
    for cardnumber in cardnumbers:
        with engine.begin() as conn:
            row = conn.execute(BORROWER_QUERY, {"cardnumber": cardnumber}).fetchone()
            if row is None:
                continue
            borrowernumber, sexe, age, ville, iris, categorycode = row
            if borrowernumber is None:
                continue

            result = conn.execute(
                UPDATE_QUERY,
                {
                    "borrowernumber": borrowernumber,
                    "sexe": sexe if sexe is not None else "INC",
                    "age": age if age is not None else "INC",
                    "ville": ville if ville is not None else "INC",
                    "iris": iris if iris is not None else "INC",
                    "categorycode": categorycode if categorycode is not None else "INC",
                    "cardnumber": cardnumber,
                },
            )
        nb_lignes_maj += result.rowcount

    return len(cardnumbers), nb_lignes_maj


log = Log()
log.add_info('Lancement')

engine = DbConn().create_engine()
nb_cardnumbers, nb_lignes_maj = mod_entrance_adding_data(engine)

log.add_info(f"{nb_cardnumbers} cardnumbers examinés, {nb_lignes_maj} lignes mises à jour")
log.add_info("Fin traitement\n\n")
