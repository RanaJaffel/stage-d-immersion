"""
Point d'entrée de l'application.

Ne contient aucune logique métier : se contente d'importer et de lancer
l'interface graphique.

Lancer avec : python main.py
"""

import sys

from ui.interface_scan import InterfaceScan


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    app = InterfaceScan()
    app.mainloop()


if __name__ == "__main__":
    main()
