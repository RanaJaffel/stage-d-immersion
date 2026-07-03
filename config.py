"""
Paramètres de configuration du projet.

Centraliser ces valeurs ici évite de les répéter dans plusieurs fichiers
et facilite les futurs ajustements.
"""

import serial

# ---------------------------------------------------------------------------
# Paramètres série du convertisseur Wie232 (mode SW6 = ON)
# ---------------------------------------------------------------------------
BAUDRATE = 9600
BYTESIZE = serial.EIGHTBITS
PARITY = serial.PARITY_NONE
STOPBITS = serial.STOPBITS_ONE
TIMEOUT = 1  # secondes

# Délai avant tentative de reconnexion automatique (secondes)
RECONNECT_DELAY = 3

# ---------------------------------------------------------------------------
# Imprimante
# ---------------------------------------------------------------------------
PRINTER_NAME = "POS80 Printer(6)"

# ---------------------------------------------------------------------------
# Thème visuel
# ---------------------------------------------------------------------------
# Palette "moderne" sobre, inspirée d'un dashboard clair.
THEME = {
    "bg": "#F4F6FB",              # fond général
    "bg_card": "#FFFFFF",         # fond des cartes / panneaux
    "bg_header": "#1F2A44",       # bandeau supérieur
    "text_primary": "#1F2937",
    "text_secondary": "#6B7280",
    "text_on_dark": "#F9FAFB",

    "accent": "#4F6BFF",          # couleur principale (boutons, focus)
    "accent_hover": "#3D57E0",

    "success": "#16A34A",
    "success_bg": "#DCFCE7",
    "error": "#DC2626",
    "error_bg": "#FEE2E2",
    "warning": "#D97706",
    "warning_bg": "#FEF3C7",
    "neutral": "#6B7280",

    "border": "#E5E7EB",
    "row_alt": "#F9FAFB",

    "font_family": "Segoe UI",
    "font_family_mono": "Consolas",
}

# Dossier d'export par défaut (CSV / Excel)
EXPORT_DIR_NAME = "exports"

# ---------------------------------------------------------------------------
# Base de données MySQL (XAMPP)
# ---------------------------------------------------------------------------
# Valeurs par défaut d'une installation XAMPP standard :
# host=localhost, port=3306, user=root, password="" (vide)
# Pensez à créer la base au préalable, par exemple via phpMyAdmin,
# ou laissez l'appli la créer automatiquement (voir database.py).
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "",
    "database": "scan_pointeuse",
}

# Si True, l'appli tente une connexion MySQL au démarrage et recharge
# l'historique. Si False, elle fonctionne uniquement en mémoire (comme avant).
DB_ACTIVEE = True
