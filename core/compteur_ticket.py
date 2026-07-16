"""
Compteur de secours pour numéroter les tickets.

En temps normal, le numéro de ticket imprimé correspond à l'id
auto-incrémenté de la ligne "scans" en base de données (voir
database.py -> enregistrer_scan()).

Si la base de données MySQL est indisponible, ce module prend le relais :
il lit/écrit un simple fichier texte à côté du projet pour continuer à
numéroter les tickets de façon incrémentale, même en cas de redémarrage
de l'application.
"""

import os
import threading

CHEMIN_COMPTEUR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "ticket_compteur.txt",
)

_verrou = threading.Lock()


def prochain_numero() -> int:
    """Incrémente et retourne le prochain numéro de ticket (>= 1)."""
    with _verrou:
        valeur = 0
        try:
            if os.path.exists(CHEMIN_COMPTEUR):
                with open(CHEMIN_COMPTEUR, "r", encoding="utf-8") as f:
                    contenu = f.read().strip()
                    valeur = int(contenu) if contenu.isdigit() else 0
        except (ValueError, OSError):
            valeur = 0

        valeur += 1

        try:
            with open(CHEMIN_COMPTEUR, "w", encoding="utf-8") as f:
                f.write(str(valeur))
        except OSError:
            pass

        return valeur
