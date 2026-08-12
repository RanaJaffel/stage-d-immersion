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

    if sys.stdout is not None:
        sys.stdout.reconfigure(encoding="utf-8")

    # Vérification de la licence hardware
    if not check_license():
        import tkinter as tk
        from tkinter import messagebox
        racine = tk.Tk()
        racine.withdraw()
        messagebox.showerror(
            "Licence invalide",
            "Cette application n'est pas autorisée sur ce PC.\n"
            "Vérifiez que license.key est présent et correspond à ce PC.",
        )
        return

    # Lancement de l'application
    app = InterfaceScan()
    app.mainloop()


if __name__ == "__main__":
    main()