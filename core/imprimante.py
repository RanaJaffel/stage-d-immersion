"""
Gestion de l'imprimante thermique (ticket restaurant).

Nécessite pywin32 (win32print) — Windows uniquement.

Format du ticket imprimé, de haut en bas :
    - Numéro de ticket (auto-incrémenté à chaque impression)
    - Titre "TICKET RESTAURANT"
    - Date et heure d'impression
    - Nom / Prénom
    - Matricule en grand (jamais "0" — voir extraire_matricule())
    - "Bon appétit"
"""

from datetime import datetime

import config
from core.utils import extraire_matricule

try:
    import win32print
    WIN32_DISPONIBLE = True
except ImportError:
    WIN32_DISPONIBLE = False


# ---------------------------------------------------------------------------
# Commandes ESC/POS (imprimantes thermiques compatibles, ex. POS80)
# ---------------------------------------------------------------------------
ESC = b"\x1b"
GS = b"\x1d"

INIT = ESC + b"@"
ALIGN_CENTER = ESC + b"a" + b"\x01"
ALIGN_LEFT = ESC + b"a" + b"\x00"
BOLD_ON = ESC + b"E" + b"\x01"
BOLD_OFF = ESC + b"E" + b"\x00"
TAILLE_NORMALE = GS + b"!" + b"\x00"
TAILLE_DOUBLE = GS + b"!" + b"\x11"      # double hauteur + double largeur
TAILLE_GEANTE = GS + b"!" + b"\x33"      # x4 hauteur + x4 largeur (matricule)
SAUT_LIGNE = b"\n"


class Imprimante:
    def __init__(self, nom_imprimante: str = None):
        self.PRINTER_NAME = nom_imprimante or config.PRINTER_NAME
        self.printer = None
        self.derniere_erreur = None

    def est_connectee(self) -> bool:
        return self.printer is not None

    def connecter(self) -> bool:
        if not WIN32_DISPONIBLE:
            self.derniere_erreur = "Module win32print indisponible (Windows requis)"
            return False

        try:
            self.printer = win32print.OpenPrinter(self.PRINTER_NAME)
            self.derniere_erreur = None
            return True
        except Exception as e:
            self.derniere_erreur = str(e)
            self.printer = None
            return False

    def imprimer_ticket(self, numero_badge: str, numero_ticket: int,
                         nom: str = None, prenom: str = None,
                         date_heure: datetime = None) -> bool:
        """
        Imprime le ticket restaurant.

        numero_badge  : valeur brute lue par le lecteur (ex: "0.2"), utilisée
                        pour retrouver le matricule affiché en grand.
        numero_ticket : numéro de ticket auto-incrémenté à afficher en haut.
        nom, prenom   : identité de la personne (peuvent être vides).
        date_heure    : date/heure d'impression (par défaut : maintenant).
        """
        if not self.printer:
            return False

        date_heure = date_heure or datetime.now()
        date_str = date_heure.strftime("%d/%m/%Y")
        heure_str = date_heure.strftime("%H:%M:%S")

        nom_affiche = (nom or "").strip().upper() or "-"
        prenom_affiche = (prenom or "").strip() or "-"
        matricule = extraire_matricule(numero_badge)
        ticket_str = f"{int(numero_ticket):06d}" if numero_ticket else "------"

        def enc(texte: str) -> bytes:
            # cp437 (jeu de caractères de l'imprimante thermique) ne connaît
            # pas tous les accents (ex: —, Ô, Î, Û, Œ, Ù). On remplace plutôt
            # que de planter, pour ne jamais bloquer l'impression du ticket.
            return texte.encode("cp437", errors="replace")

        try:
            data = bytearray()
            data += INIT
            data += ALIGN_CENTER

            # -- Numéro de ticket --
            data += TAILLE_NORMALE
            data += BOLD_ON
            data += enc(f"Ticket N. {ticket_str}") + SAUT_LIGNE
            data += BOLD_OFF

            data += b"--------------------------------" + SAUT_LIGNE

            # -- Titre --
            data += TAILLE_DOUBLE
            data += BOLD_ON
            data += enc("TICKET") + SAUT_LIGNE
            data += enc("RESTAURANT") + SAUT_LIGNE
            data += BOLD_OFF
            data += TAILLE_NORMALE

            data += b"--------------------------------" + SAUT_LIGNE
            data += SAUT_LIGNE

            # -- Date / heure d'impression --
            data += enc(f"Date  : {date_str}") + SAUT_LIGNE
            data += enc(f"Heure : {heure_str}") + SAUT_LIGNE
            data += SAUT_LIGNE

            # -- Nom / prénom --
            data += ALIGN_LEFT
            data += enc(f"Nom    : {nom_affiche}") + SAUT_LIGNE
            data += enc(f"Prenom : {prenom_affiche}") + SAUT_LIGNE
            data += ALIGN_CENTER
            data += SAUT_LIGNE

            # -- Matricule (grande police, jamais "0") --
            data += TAILLE_GEANTE
            data += BOLD_ON
            data += enc(matricule) + SAUT_LIGNE
            data += BOLD_OFF
            data += TAILLE_NORMALE
            data += SAUT_LIGNE

            data += b"--------------------------------" + SAUT_LIGNE
            data += SAUT_LIGNE

            # -- Pied de ticket --
            data += TAILLE_DOUBLE
            data += enc("Bon appetit") + SAUT_LIGNE
            data += TAILLE_NORMALE
            data += SAUT_LIGNE + SAUT_LIGNE + SAUT_LIGNE

            win32print.StartDocPrinter(self.printer, 1, ("Ticket restaurant", None, "RAW"))
            win32print.StartPagePrinter(self.printer)

            win32print.WritePrinter(self.printer, bytes(data))

            win32print.EndPagePrinter(self.printer)
            win32print.EndDocPrinter(self.printer)
            return True

        except Exception as e:
            self.derniere_erreur = str(e)
            return False

    def fermer(self):
        if self.printer:
            try:
                win32print.ClosePrinter(self.printer)
            except Exception:
                pass
            self.printer = None
