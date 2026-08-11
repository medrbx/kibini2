-- Schéma de statdb.stat_entrees_det, chargée par statdb_entrees_opteio.py.
-- Détail brut (par capteur et par minute) des comptages Opteio, dataset 'inout'.
CREATE TABLE statdb.stat_entrees_det (
    id INT AUTO_INCREMENT PRIMARY KEY,
    site_id INT NOT NULL,
    capteur INT NOT NULL,
    datetime DATETIME NOT NULL,
    jour DATE NOT NULL,
    heure TINYINT UNSIGNED NOT NULL,
    minute TINYINT UNSIGNED NOT NULL,
    entree INT NOT NULL,
    sortie INT NOT NULL,
    UNIQUE KEY uq_site_capteur_datetime (site_id, capteur, datetime),
    KEY idx_datetime (datetime)
);
