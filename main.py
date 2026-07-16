"""
Point d'entrée de l'application.

Ne contient aucune logique métier : se contente d'importer et de lancer
l'interface graphique.

Lancer avec : python main.py
"""

import sys

from ui.interface_scan import InterfaceScan
from license_manager import check_license


def main():

    sys.stdout.reconfigure(encoding="utf-8")

    # Vérification de la licence hardware
    if not check_license():
        print("Licence invalide : cette application n'est pas autorisée sur ce PC.")
        return

    # Lancement de l'application
    app = InterfaceScan()
    app.mainloop()


if __name__ == "__main__":
    main()