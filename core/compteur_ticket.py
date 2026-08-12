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
import sys
import threading


def _dossier_application() -> str:
    """
    - En exécution normale (python main.py) : dossier racine du projet.
    - Une fois transformé en .exe : __file__ pointe vers un dossier
      temporaire recréé à chaque lancement, donc on utilise plutôt
      le dossier de l'exécutable (sys.executable) pour que le
      compteur soit bien conservé d'un lancement à l'autre.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


CHEMIN_COMPTEUR = os.path.join(_dossier_application(), "ticket_compteur.txt")

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