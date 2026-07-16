"""
Gestion de la base de données MySQL (compatible XAMPP).

Trois tables :
- utilisateurs : les personnes (nom affiché sur le ticket)
- badges       : chaque badge physique, lié à un utilisateur
- scans        : chaque tentative de scan (autorisée ou refusée)

Règle métier appliquée dans enregistrer_scan() :
- si le badge n'est lié à aucun utilisateur -> refusé, "Badge inconnu"
- si ce badge a déjà eu un scan autorisé (à n'importe quel moment,
  n'importe quel jour) -> refusé, "Déjà utilisé"
- sinon -> autorisé, on enregistre le scan et on retourne le nom de
  l'utilisateur (pour l'affichage et le ticket imprimé)

Cette classe ne connaît rien de Tkinter : en cas d'échec de connexion, elle
retourne simplement False / une liste vide / None, à charge de l'appelant
(l'UI) de continuer à fonctionner correctement.
"""

import mysql.connector
from mysql.connector import errorcode

import config


class BaseDeDonnees:
    def __init__(self, db_config: dict = None):
        self.db_config = db_config or config.DB_CONFIG
        self.connexion = None
        self.derniere_erreur = None

    def est_connectee(self) -> bool:
        return self.connexion is not None and self.connexion.is_connected()

    # ---------------- CONNEXION ----------------

    def connecter(self) -> bool:
        """
        Se connecte au serveur MySQL. Crée la base de données si elle
        n'existe pas encore, puis les tables si nécessaire.
        """
        try:
            connexion_serveur = mysql.connector.connect(
                host=self.db_config["host"],
                port=self.db_config["port"],
                user=self.db_config["user"],
                password=self.db_config["password"],
            )
            curseur = connexion_serveur.cursor()
            curseur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{self.db_config['database']}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            curseur.close()
            connexion_serveur.close()

            self.connexion = mysql.connector.connect(**self.db_config)
            self._creer_tables()

            self.derniere_erreur = None
            return True

        except mysql.connector.Error as e:
            self.derniere_erreur = self._message_lisible(e)
            self.connexion = None
            return False

    def _creer_tables(self):
        curseur = self.connexion.cursor()

        curseur.execute(
            """
            CREATE TABLE IF NOT EXISTS utilisateurs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nom VARCHAR(128) NOT NULL,
                prenom VARCHAR(128) NOT NULL DEFAULT '',
                cree_le TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )

        curseur.execute(
            """
            CREATE TABLE IF NOT EXISTS badges (
                id INT AUTO_INCREMENT PRIMARY KEY,
                numero_badge VARCHAR(64) NOT NULL UNIQUE,
                utilisateur_id INT NOT NULL,
                cree_le TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_badges_utilisateur
                    FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id)
                    ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )

        curseur.execute(
            """
            CREATE TABLE IF NOT EXISTS scans (
                id INT AUTO_INCREMENT PRIMARY KEY,
                badge_id INT NULL,
                numero_badge VARCHAR(64) NOT NULL,
                date_heure DATETIME NOT NULL,
                autorise TINYINT(1) NOT NULL,
                cree_le TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_numero_badge (numero_badge),
                INDEX idx_date_heure (date_heure),
                CONSTRAINT fk_scans_badge
                    FOREIGN KEY (badge_id) REFERENCES badges(id)
                    ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )

        curseur.close()
        self.connexion.commit()

        # Le numéro de ticket imprimé = id auto-incrémenté de la table
        # "scans" (une ligne scans = un ticket imprimé). Pour les bases
        # créées avec une version antérieure de l'appli (sans prénom),
        # on ajoute la colonne manquante si besoin (migration douce).
        self._migrer_colonne_prenom()

    def _migrer_colonne_prenom(self):
        """Ajoute la colonne 'prenom' à 'utilisateurs' si elle n'existe pas déjà
        (cas d'une base créée avant l'ajout du prénom sur le ticket)."""
        try:
            curseur = self.connexion.cursor()
            curseur.execute(
                """
                SELECT COUNT(*) FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'utilisateurs'
                  AND COLUMN_NAME = 'prenom'
                """,
                (self.db_config["database"],),
            )
            (existe,) = curseur.fetchone()
            if not existe:
                curseur.execute(
                    "ALTER TABLE utilisateurs ADD COLUMN prenom VARCHAR(128) "
                    "NOT NULL DEFAULT '' AFTER nom"
                )
                self.connexion.commit()
            curseur.close()
        except mysql.connector.Error as e:
            self.derniere_erreur = self._message_lisible(e)

    def deconnecter(self):
        if self.connexion:
            try:
                self.connexion.close()
            except mysql.connector.Error:
                pass
            self.connexion = None

    @staticmethod
    def _message_lisible(erreur: mysql.connector.Error) -> str:
        if erreur.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            return "Accès refusé (identifiants incorrects)"
        if erreur.errno == errorcode.ER_BAD_DB_ERROR:
            return "Base de données introuvable"
        if erreur.errno == 2003:
            return "Serveur MySQL injoignable (XAMPP démarré ?)"
        return str(erreur)

    # ---------------- UTILISATEURS / BADGES ----------------

    def ajouter_utilisateur(self, nom: str, prenom: str = "") -> int | None:
        """Crée un utilisateur et retourne son id, ou None en cas d'échec."""
        if not self.est_connectee():
            return None
        try:
            curseur = self.connexion.cursor()
            curseur.execute(
                "INSERT INTO utilisateurs (nom, prenom) VALUES (%s, %s)",
                (nom, prenom),
            )
            self.connexion.commit()
            nouvel_id = curseur.lastrowid
            curseur.close()
            return nouvel_id
        except mysql.connector.Error as e:
            self.derniere_erreur = self._message_lisible(e)
            return None

    def associer_badge(self, numero_badge: str, utilisateur_id: int) -> bool:
        """Lie un numéro de badge à un utilisateur existant."""
        if not self.est_connectee():
            return False
        try:
            curseur = self.connexion.cursor()
            curseur.execute(
                "INSERT INTO badges (numero_badge, utilisateur_id) VALUES (%s, %s)",
                (numero_badge, utilisateur_id),
            )
            self.connexion.commit()
            curseur.close()
            return True
        except mysql.connector.Error as e:
            self.derniere_erreur = self._message_lisible(e)
            return False

    def lister_utilisateurs(self) -> list:
        """Retourne [(id, nom, prenom), ...] triés par nom."""
        if not self.est_connectee():
            return []
        try:
            curseur = self.connexion.cursor()
            curseur.execute("SELECT id, nom, prenom FROM utilisateurs ORDER BY nom")
            lignes = curseur.fetchall()
            curseur.close()
            return lignes
        except mysql.connector.Error as e:
            self.derniere_erreur = self._message_lisible(e)
            return []

    def lister_badges(self) -> list:
        """Retourne [(numero_badge, nom_utilisateur, prenom_utilisateur), ...] triés par nom."""
        if not self.est_connectee():
            return []
        try:
            curseur = self.connexion.cursor()
            curseur.execute(
                """
                SELECT b.numero_badge, u.nom, u.prenom
                FROM badges b
                JOIN utilisateurs u ON u.id = b.utilisateur_id
                ORDER BY u.nom
                """
            )
            lignes = curseur.fetchall()
            curseur.close()
            return lignes
        except mysql.connector.Error as e:
            self.derniere_erreur = self._message_lisible(e)
            return []

    def _trouver_badge(self, numero_badge: str):
        """Retourne (badge_id, nom_utilisateur, prenom_utilisateur) ou None si le badge est inconnu."""
        curseur = self.connexion.cursor()
        curseur.execute(
            """
            SELECT b.id, u.nom, u.prenom
            FROM badges b
            JOIN utilisateurs u ON u.id = b.utilisateur_id
            WHERE b.numero_badge = %s
            """,
            (numero_badge,),
        )
        ligne = curseur.fetchone()
        curseur.close()
        return ligne  # (badge_id, nom, prenom) ou None

    def _badge_deja_utilise(self, badge_id: int) -> bool:
        curseur = self.connexion.cursor()
        curseur.execute(
            "SELECT COUNT(*) FROM scans WHERE badge_id = %s AND autorise = 1",
            (badge_id,),
        )
        (nombre,) = curseur.fetchone()
        curseur.close()
        return nombre > 0

    # ---------------- SCAN ----------------

    def enregistrer_scan(self, numero_badge: str, date_heure) -> dict:
        """
        Applique la règle métier et enregistre la tentative de scan.

        Le numéro de ticket imprimé correspond à l'id auto-incrémenté de la
        ligne insérée dans "scans" : il augmente donc automatiquement à
        chaque scan/impression, sans jamais revenir en arrière.

        Retourne :
        {numero_badge, nom, prenom, numero_ticket, autorise (bool), message}
        """
        if not self.est_connectee():
            return {
                "numero_badge": numero_badge,
                "nom": None,
                "prenom": None,
                "numero_ticket": None,
                "autorise": False,
                "message": "Base de données indisponible",
            }

        try:
            badge = self._trouver_badge(numero_badge)

            if badge is None:
                ticket_id = self._inserer_scan(None, numero_badge, date_heure, autorise=False)
                return {
                    "numero_badge": numero_badge,
                    "nom": None,
                    "prenom": None,
                    "numero_ticket": ticket_id,
                    "autorise": False,
                    "message": "Badge inconnu",
                }

            badge_id, nom, prenom = badge

            if self._badge_deja_utilise(badge_id):
                ticket_id = self._inserer_scan(badge_id, numero_badge, date_heure, autorise=False)
                return {
                    "numero_badge": numero_badge,
                    "nom": nom,
                    "prenom": prenom,
                    "numero_ticket": ticket_id,
                    "autorise": False,
                    "message": "Déjà utilisé",
                }

            ticket_id = self._inserer_scan(badge_id, numero_badge, date_heure, autorise=True)
            return {
                "numero_badge": numero_badge,
                "nom": nom,
                "prenom": prenom,
                "numero_ticket": ticket_id,
                "autorise": True,
                "message": "Accès autorisé",
            }

        except mysql.connector.Error as e:
            self.derniere_erreur = self._message_lisible(e)
            return {
                "numero_badge": numero_badge,
                "nom": None,
                "prenom": None,
                "numero_ticket": None,
                "autorise": False,
                "message": "Erreur base de données",
            }

    def _inserer_scan(self, badge_id, numero_badge, date_heure, autorise: bool) -> int:
        """Insère la ligne de scan et retourne son id (= numéro de ticket)."""
        curseur = self.connexion.cursor()
        curseur.execute(
            """
            INSERT INTO scans (badge_id, numero_badge, date_heure, autorise)
            VALUES (%s, %s, %s, %s)
            """,
            (badge_id, numero_badge, date_heure, int(autorise)),
        )
        self.connexion.commit()
        ticket_id = curseur.lastrowid
        curseur.close()
        return ticket_id

    # ---------------- LECTURE HISTORIQUE ----------------

    def charger_historique(self, limite: int = 500) -> list:
        """
        Retourne les derniers scans, du plus récent au plus ancien :
        liste de tuples (numero_ticket, numero_badge, nom, prenom, date_heure_str, autorise).
        """
        if not self.est_connectee():
            return []

        try:
            curseur = self.connexion.cursor()
            curseur.execute(
                """
                SELECT s.id, s.numero_badge, u.nom, u.prenom, s.date_heure, s.autorise
                FROM scans s
                LEFT JOIN badges b ON b.id = s.badge_id
                LEFT JOIN utilisateurs u ON u.id = b.utilisateur_id
                ORDER BY s.date_heure DESC, s.id DESC
                LIMIT %s
                """,
                (limite,),
            )
            lignes = curseur.fetchall()
            curseur.close()

            resultat = []
            for numero_ticket, numero_badge, nom, prenom, date_heure, autorise in lignes:
                resultat.append((
                    numero_ticket,
                    numero_badge,
                    nom,
                    prenom,
                    date_heure.strftime("%d/%m/%Y %H:%M:%S"),
                    bool(autorise),
                ))
            return resultat
        except mysql.connector.Error as e:
            self.derniere_erreur = self._message_lisible(e)
            return []

    def statistiques_globales(self) -> dict:
        """Retourne les compteurs pour le tableau de bord (aujourd'hui + total)."""
        vide = {
            "aujourdhui_autorise": 0, "aujourdhui_refuse": 0,
            "total_autorise": 0, "total_refuse": 0,
        }
        if not self.est_connectee():
            return vide
        try:
            curseur = self.connexion.cursor()
            curseur.execute(
                """
                SELECT
                    SUM(autorise = 1 AND DATE(date_heure) = CURDATE()),
                    SUM(autorise = 0 AND DATE(date_heure) = CURDATE()),
                    SUM(autorise = 1),
                    SUM(autorise = 0)
                FROM scans
                """
            )
            auj_a, auj_r, tot_a, tot_r = curseur.fetchone()
            curseur.close()
            return {
                "aujourdhui_autorise": int(auj_a or 0),
                "aujourdhui_refuse": int(auj_r or 0),
                "total_autorise": int(tot_a or 0),
                "total_refuse": int(tot_r or 0),
            }
        except mysql.connector.Error as e:
            self.derniere_erreur = self._message_lisible(e)
            return vide

    def statistiques_par_jour(self, nb_jours: int = 7) -> list:
        """
        Retourne [(jour_str, nb_autorise, nb_refuse), ...] pour les
        `nb_jours` derniers jours, en ordre chronologique. Utilisé pour le
        petit graphique du tableau de bord.
        """
        if not self.est_connectee():
            return []
        try:
            curseur = self.connexion.cursor()
            curseur.execute(
                """
                SELECT DATE(date_heure) AS jour,
                       SUM(autorise = 1) AS nb_autorise,
                       SUM(autorise = 0) AS nb_refuse
                FROM scans
                WHERE date_heure >= (CURDATE() - INTERVAL %s DAY)
                GROUP BY jour
                ORDER BY jour
                """,
                (nb_jours - 1,),
            )
            lignes = curseur.fetchall()
            curseur.close()
            return [
                (jour.strftime("%d/%m"), int(a or 0), int(r or 0))
                for jour, a, r in lignes
            ]
        except mysql.connector.Error as e:
            self.derniere_erreur = self._message_lisible(e)
            return []
