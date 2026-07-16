"""
Interface graphique - Scan pointeuse (version améliorée)

Nouveautés par rapport à la version initiale :
- Thème visuel moderne (couleurs, cartes, badge de statut coloré) + mode sombre
- Barre de recherche filtrant la liste en direct
- Filtres avancés (période, statut)
- Tableau de bord avec statistiques et petit graphique
- Export CSV / Excel avec horodatage automatique
- Reconnexion automatique du port série
- Diagnostics techniques (port / imprimante / base de données) cachés,
  réservés à l'admin/technicien
"""

import os
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import ttk, filedialog, messagebox

from core.lecteur_serie import LecteurSerie
from core.imprimante import Imprimante
from core.database import BaseDeDonnees
from core import export
from core import compteur_ticket
from core.utils import extraire_matricule
import config

THEME = config.THEME


class InterfaceScan(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Scan Pointeuse")
        self.geometry("820x600")
        self.minsize(700, 520)
        self.configure(bg=THEME["bg"])

        # Données en mémoire : liste de tuples
        # (numero_ticket, numero_badge, nom_complet, date_heure_str, statut)
        self.badges_donnees = []
        self.nombre_badges = 0

        # Mémorise le dernier état affiché des badges de statut, pour
        # pouvoir les restaurer après un changement de thème (qui reconstruit
        # l'interface) sans avoir à relancer les connexions.
        self._etat_port = ("● Déconnecté", "neutral")
        self._etat_imprimante = ("🖨 Imprimante", "neutral")
        self._etat_db = ("🗄 Base de données", "neutral")
        self._mode_sombre = False

        self._configurer_styles()

        # Lecteur série
        self.lecteur = LecteurSerie(
            callback_badge=self._on_badge_recu,
            callback_erreur=self._on_erreur,
            callback_statut=self._on_statut_port,
        )

        # Imprimante thermique
        self.imprimante = Imprimante()
        imprimante_ok = self.imprimante.connecter()

        # Base de données MySQL (XAMPP)
        self.base_donnees = BaseDeDonnees()
        db_ok = self.base_donnees.connecter() if config.DB_ACTIVEE else False

        self._construire_header()
        self._construire_toolbar()
        self._construire_fenetre_diagnostics()
        self._construire_liste()
        self._construire_footer()

        self._rafraichir_ports()
        self._maj_statut_imprimante(imprimante_ok)
        self._maj_statut_db(db_ok)

        if db_ok:
            self._charger_historique_db()

        self.protocol("WM_DELETE_WINDOW", self._fermer)

    # ---------------- STYLE ----------------

    def _configurer_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        police = (THEME["font_family"], 10)
        police_titre = (THEME["font_family"], 14, "bold")

        style.configure("TFrame", background=THEME["bg"])
        style.configure("Card.TFrame", background=THEME["bg_card"])
        style.configure("Header.TFrame", background=THEME["bg_header"])

        style.configure("TLabel", background=THEME["bg"], foreground=THEME["text_primary"], font=police)
        style.configure("Card.TLabel", background=THEME["bg_card"], foreground=THEME["text_primary"], font=police)
        style.configure("Header.TLabel", background=THEME["bg_header"], foreground=THEME["text_on_dark"], font=police_titre)
        style.configure("Sub.TLabel", background=THEME["bg_header"], foreground="#C7D0E8", font=(THEME["font_family"], 9))
        style.configure("Secondary.TLabel", background=THEME["bg"], foreground=THEME["text_secondary"], font=(THEME["font_family"], 9))

        style.configure(
            "Accent.TButton",
            background=THEME["accent"],
            foreground="white",
            font=(THEME["font_family"], 10, "bold"),
            padding=(14, 8),
            borderwidth=0,
        )
        style.map("Accent.TButton", background=[("active", THEME["accent_hover"])])

        style.configure(
            "Ghost.TButton",
            background=THEME["bg_card"],
            foreground=THEME["text_primary"],
            font=(THEME["font_family"], 9),
            padding=(10, 6),
            borderwidth=1,
            relief="solid",
        )
        style.map("Ghost.TButton", background=[("active", THEME["row_alt"])])

        style.configure("TCombobox", padding=4)

        style.configure(
            "Treeview",
            background=THEME["bg_card"],
            fieldbackground=THEME["bg_card"],
            foreground=THEME["text_primary"],
            rowheight=28,
            font=police,
            borderwidth=0,
        )
        style.configure(
            "Treeview.Heading",
            background=THEME["bg_header"],
            foreground=THEME["text_on_dark"],
            font=(THEME["font_family"], 10, "bold"),
            relief="flat",
        )
        style.map("Treeview.Heading", background=[("active", THEME["bg_header"])])
        style.map("Treeview", background=[("selected", THEME["accent"])], foreground=[("selected", "white")])

    # ---------------- UI : HEADER ----------------

    def _construire_header(self):
        header = tk.Frame(self, bg=THEME["bg_header"])
        header.pack(fill="x")

        contenu = ttk.Frame(header, style="Header.TFrame", padding=(20, 14))
        contenu.pack(fill="x")

        ttk.Label(contenu, text="🕒  Scan Pointeuse", style="Header.TLabel").pack(anchor="w")
        ttk.Label(contenu, text="Suivi des badges scannés en temps réel", style="Sub.TLabel").pack(anchor="w")

        # Accès discret aux infos techniques (port / imprimante / base de
        # données), réservé à l'admin ou au technicien : rien d'autre ne
        # l'indique dans l'interface.
        bouton_diag = tk.Label(
            header, text="⋮", font=(THEME["font_family"], 18, "bold"),
            bg=THEME["bg_header"], fg=THEME["neutral"], cursor="hand2",
        )
        bouton_diag.place(relx=1.0, rely=0.5, anchor="e", x=-16)
        bouton_diag.bind("<Button-1>", lambda e: self._ouvrir_diagnostics())

    # ---------------- UI : TOOLBAR ----------------

    def _construire_toolbar(self):
        cadre = ttk.Frame(self, padding=(20, 14, 20, 6))
        cadre.pack(fill="x")

        # -- Ligne recherche + export --
        ligne_recherche = ttk.Frame(cadre)
        ligne_recherche.pack(fill="x", pady=(0, 8))

        ttk.Label(ligne_recherche, text="🔎").pack(side="left")

        self.var_recherche = tk.StringVar()
        self.var_recherche.trace_add("write", self._filtrer_liste)

        self.champ_recherche = ttk.Entry(ligne_recherche, textvariable=self.var_recherche, width=30)
        self.champ_recherche.pack(side="left", padx=(6, 16))

        ttk.Button(ligne_recherche, text="📄 Exporter CSV", style="Ghost.TButton",
                   command=self._exporter_csv).pack(side="right", padx=(6, 0))
        ttk.Button(ligne_recherche, text="📊 Exporter Excel", style="Ghost.TButton",
                   command=self._exporter_excel).pack(side="right")

        # -- Ligne filtres avancés + tableau de bord + thème --
        ligne_filtres = ttk.Frame(cadre)
        ligne_filtres.pack(fill="x")

        ttk.Label(ligne_filtres, text="Période :").pack(side="left")
        self.var_periode = tk.StringVar(value="Tout")
        combo_periode = ttk.Combobox(
            ligne_filtres, textvariable=self.var_periode, state="readonly", width=16,
            values=["Tout", "Aujourd'hui", "7 derniers jours", "30 derniers jours"],
        )
        combo_periode.pack(side="left", padx=(6, 16))
        combo_periode.bind("<<ComboboxSelected>>", self._filtrer_liste)

        ttk.Label(ligne_filtres, text="Statut :").pack(side="left")
        self.var_statut_filtre = tk.StringVar(value="Tous")
        combo_statut = ttk.Combobox(
            ligne_filtres, textvariable=self.var_statut_filtre, state="readonly", width=12,
            values=["Tous", "Autorisé", "Refusé"],
        )
        combo_statut.pack(side="left", padx=(6, 0))
        combo_statut.bind("<<ComboboxSelected>>", self._filtrer_liste)

        self.bouton_theme = ttk.Button(
            ligne_filtres, text="🌙 Mode sombre", style="Ghost.TButton",
            command=self._basculer_theme,
        )
        self.bouton_theme.pack(side="right")

        ttk.Button(ligne_filtres, text="📊 Tableau de bord", style="Ghost.TButton",
                   command=self._ouvrir_tableau_de_bord).pack(side="right", padx=(0, 8))

    def _construire_fenetre_diagnostics(self):
        """
        Fenêtre technique cachée par défaut (port série, imprimante, base de
        données). Accessible uniquement via le bouton discret "⋮" dans
        l'en-tête — pensée pour l'admin/technicien, pas pour l'utilisateur
        courant.
        """
        fen = tk.Toplevel(self)
        fen.title("Diagnostics techniques")
        fen.geometry("380x230")
        fen.configure(bg=THEME["bg"])
        fen.resizable(False, False)
        fen.protocol("WM_DELETE_WINDOW", fen.withdraw)

        cadre = ttk.Frame(fen, padding=16)
        cadre.pack(fill="both", expand=True)

        ttk.Label(cadre, text="Diagnostics techniques", style="Header.TLabel").pack(anchor="w", pady=(0, 12))

        ligne_port = ttk.Frame(cadre)
        ligne_port.pack(fill="x", pady=(0, 10))

        ttk.Label(ligne_port, text="Port série :").pack(side="left")

        self.combo_port = ttk.Combobox(ligne_port, width=14, state="readonly")
        self.combo_port.pack(side="left", padx=(6, 4))
        self.combo_port.bind("<<ComboboxSelected>>", self._connecter_port)

        ttk.Button(ligne_port, text="⟳ Actualiser", style="Ghost.TButton",
                   command=self._rafraichir_ports).pack(side="left", padx=(4, 0))

        self.badge_statut_port = self._creer_badge_statut(cadre, "● Déconnecté", "neutral")
        self.badge_statut_port.pack(anchor="w", pady=(0, 8))

        self.badge_statut_imprimante = self._creer_badge_statut(cadre, "🖨 Imprimante", "neutral")
        self.badge_statut_imprimante.pack(anchor="w", pady=(0, 8))

        self.badge_statut_db = self._creer_badge_statut(cadre, "🗄 Base de données", "neutral")
        self.badge_statut_db.pack(anchor="w")

        fen.withdraw()  # caché tant que l'admin ne clique pas sur "⋮"
        self.fenetre_diagnostics = fen

    def _ouvrir_diagnostics(self):
        self.fenetre_diagnostics.deiconify()
        self.fenetre_diagnostics.lift()
        self.fenetre_diagnostics.focus_force()

    def _creer_badge_statut(self, parent, texte, etat):
        """Crée une petite étiquette colorée type 'badge' (pill)."""
        couleurs = {
            "success": (THEME["success_bg"], THEME["success"]),
            "error": (THEME["error_bg"], THEME["error"]),
            "warning": (THEME["warning_bg"], THEME["warning"]),
            "neutral": (THEME["bg"], THEME["neutral"]),
        }
        bg, fg = couleurs.get(etat, couleurs["neutral"])
        lbl = tk.Label(
            parent, text=texte, bg=bg, fg=fg,
            font=(THEME["font_family"], 9, "bold"),
            padx=10, pady=3
        )
        return lbl

    def _maj_badge_statut(self, widget, texte, etat):
        couleurs = {
            "success": (THEME["success_bg"], THEME["success"]),
            "error": (THEME["error_bg"], THEME["error"]),
            "warning": (THEME["warning_bg"], THEME["warning"]),
            "neutral": (THEME["bg"], THEME["neutral"]),
        }
        bg, fg = couleurs.get(etat, couleurs["neutral"])
        widget.config(text=texte, bg=bg, fg=fg)

        # Mémorisation pour restauration après reconstruction de l'interface
        # (bascule de thème) : on identifie le badge par comparaison directe.
        if widget is getattr(self, "badge_statut_port", None):
            self._etat_port = (texte, etat)
        elif widget is getattr(self, "badge_statut_imprimante", None):
            self._etat_imprimante = (texte, etat)
        elif widget is getattr(self, "badge_statut_db", None):
            self._etat_db = (texte, etat)

    # ---------------- UI : LISTE ----------------

    def _construire_liste(self):
        cadre = ttk.Frame(self, padding=(20, 6, 20, 6))
        cadre.pack(fill="both", expand=True)

        carte = tk.Frame(cadre, bg=THEME["bg_card"], highlightbackground=THEME["border"], highlightthickness=1)
        carte.pack(fill="both", expand=True)

        colonnes = ("numero", "badge", "nom", "heure", "statut")
        self.arbre = ttk.Treeview(carte, columns=colonnes, show="headings", height=14)

        self.arbre.heading("numero", text="N° Ticket")
        self.arbre.heading("badge", text="Matricule")
        self.arbre.heading("nom", text="Utilisateur")
        self.arbre.heading("heure", text="Date / Heure")
        self.arbre.heading("statut", text="Statut")

        self.arbre.column("numero", width=75, anchor="center")
        self.arbre.column("badge", width=170, anchor="w")
        self.arbre.column("nom", width=190, anchor="w")
        self.arbre.column("heure", width=155, anchor="center")
        self.arbre.column("statut", width=150, anchor="w")

        self.arbre.tag_configure("pair", background=THEME["row_alt"])
        self.arbre.tag_configure("impair", background=THEME["bg_card"])
        self.arbre.tag_configure("refuse", foreground=THEME["error"])
        self.arbre.tag_configure("autorise", foreground=THEME["success"])

        scrollbar = ttk.Scrollbar(carte, orient="vertical", command=self.arbre.yview)
        self.arbre.configure(yscrollcommand=scrollbar.set)

        self.arbre.pack(side="left", fill="both", expand=True, padx=(1, 0), pady=1)
        scrollbar.pack(side="right", fill="y", pady=1)

    # ---------------- UI : FOOTER ----------------

    def _construire_footer(self):
        cadre = ttk.Frame(self, padding=(20, 6, 20, 16))
        cadre.pack(fill="x")

        ttk.Button(cadre, text="🗑 Effacer la liste", style="Ghost.TButton",
                   command=self._effacer_liste).pack(side="left")

        ttk.Button(cadre, text="👤 Gérer les utilisateurs", style="Ghost.TButton",
                   command=self._ouvrir_gestion_utilisateurs).pack(side="left", padx=(8, 0))

        self.label_compteur = ttk.Label(cadre, text="0 badge(s) scanné(s)", style="Secondary.TLabel")
        self.label_compteur.pack(side="right")

    # ---------------- PORT ----------------

    def _rafraichir_ports(self):
        ports = LecteurSerie.lister_ports()
        self.combo_port["values"] = ports

        if ports:
            self.combo_port.current(0)
            self._connecter_port()
        else:
            self._maj_badge_statut(self.badge_statut_port, "● Aucun port détecté", "warning")

    def _connecter_port(self, event=None):
        port = self.combo_port.get()

        if not port:
            self._maj_badge_statut(self.badge_statut_port, "● Aucun port", "warning")
            return

        if self.lecteur.est_connecte():
            self.lecteur.deconnecter()

        self.lecteur.reconnexion_auto = True
        if self.lecteur.connecter(port):
            self._maj_badge_statut(self.badge_statut_port, f"● Connecté ({port})", "success")
        else:
            self._maj_badge_statut(self.badge_statut_port, "● Échec connexion", "error")

    def _on_statut_port(self, statut: str):
        self.after(0, self._appliquer_statut_port, statut)

    def _appliquer_statut_port(self, statut: str):
        if statut == "connecte":
            port = self.lecteur.port_actuel or "?"
            self._maj_badge_statut(self.badge_statut_port, f"● Connecté ({port})", "success")
        elif statut == "reconnexion":
            self._maj_badge_statut(self.badge_statut_port, "● Reconnexion en cours…", "warning")
        elif statut == "deconnecte":
            self._maj_badge_statut(self.badge_statut_port, "● Déconnecté", "neutral")

    def _maj_statut_imprimante(self, connectee: bool):
        if connectee:
            self._maj_badge_statut(self.badge_statut_imprimante, "🖨 Imprimante OK", "success")
        else:
            msg = self.imprimante.derniere_erreur or "non connectée"
            self._maj_badge_statut(self.badge_statut_imprimante, f"🖨 Imprimante : {msg[:24]}", "error")

    def _maj_statut_db(self, connectee: bool):
        if not config.DB_ACTIVEE:
            self._maj_badge_statut(self.badge_statut_db, "🗄 DB désactivée", "neutral")
        elif connectee:
            self._maj_badge_statut(self.badge_statut_db, "🗄 Base connectée", "success")
        else:
            msg = self.base_donnees.derniere_erreur or "non connectée"
            self._maj_badge_statut(self.badge_statut_db, f"🗄 DB : {msg[:24]}", "error")

    def _charger_historique_db(self):
        """Recharge les scans déjà enregistrés en base au démarrage de l'appli."""
        historique = self.base_donnees.charger_historique()

        for numero_ticket, numero_badge, nom, prenom, date_heure_str, autorise in reversed(historique):
            self.nombre_badges += 1
            statut = "Autorisé" if autorise else "Refusé"
            nom_complet = f"{prenom or ''} {nom or ''}".strip() or "—"
            ligne = (numero_ticket, numero_badge, nom_complet, date_heure_str, statut)
            self.badges_donnees.append(ligne)
            self._inserer_ligne_arbre(ligne, autorise)

        self.label_compteur.config(text=f"{self.nombre_badges} badge(s) scanné(s)")

    # ---------------- CALLBACKS SÉRIE ----------------

    def _on_badge_recu(self, numero_badge: str):
        self.after(0, self._ajouter_badge, numero_badge)

    def _on_erreur(self, message: str):
        self.after(0, lambda: self._maj_badge_statut(self.badge_statut_port, f"● Erreur : {message[:20]}", "error"))

    # ---------------- AJOUT BADGE ----------------

    def _ajouter_badge(self, numero_badge_brut: str):
        # Le lecteur envoie parfois une valeur brute type "0.2" : on isole
        # tout de suite le matricule ("2"), utilisé partout ensuite (base
        # de données, liste, impression). C'est aussi ce matricule qu'il
        # faut saisir dans "Gérer les utilisateurs" pour lier un badge.
        numero_badge = extraire_matricule(numero_badge_brut)

        maintenant = datetime.now()
        horodatage = maintenant.strftime("%d/%m/%Y %H:%M:%S")

        if not self.base_donnees.est_connectee():
            # Pas de base : on ne peut pas vérifier l'autorisation, on
            # affiche quand même le passage brut pour ne rien perdre.
            resultat = {
                "numero_badge": numero_badge,
                "nom": None,
                "prenom": None,
                "numero_ticket": None,
                "autorise": False,
                "message": "Base de données indisponible",
            }
        else:
            resultat = self.base_donnees.enregistrer_scan(numero_badge, maintenant)

        # Le numéro de ticket vient normalement de la base (id auto-incrémenté
        # de la ligne "scans"). Si la base est indisponible, on retombe sur un
        # compteur local persistant pour continuer à numéroter les tickets.
        numero_ticket = resultat.get("numero_ticket") or compteur_ticket.prochain_numero()

        self.nombre_badges += 1
        nom_complet = f"{(resultat['prenom'] or '').strip()} {(resultat['nom'] or '').strip()}".strip() or "—"
        ligne = (numero_ticket, numero_badge, nom_complet, horodatage, resultat["message"])
        self.badges_donnees.append(ligne)

        self._inserer_ligne_arbre(ligne, resultat["autorise"])
        self.label_compteur.config(text=f"{self.nombre_badges} badge(s) scanné(s)")

        if resultat["autorise"] and self.imprimante.est_connectee():
            imprime = self.imprimante.imprimer_ticket(
                numero_badge,
                numero_ticket,
                nom=resultat["nom"],
                prenom=resultat["prenom"],
                date_heure=maintenant,
            )
            if not imprime:
                erreur = self.imprimante.derniere_erreur or "échec inconnu"
                self._maj_badge_statut(
                    self.badge_statut_imprimante, f"🖨 Erreur impression : {erreur[:22]}", "error"
                )

    def _inserer_ligne_arbre(self, ligne, autorise: bool = True):
        tag_parite = "pair" if ligne[0] % 2 == 0 else "impair"
        tag_statut = "autorise" if autorise else "refuse"
        self.arbre.insert("", 0, values=ligne, tags=(tag_parite, tag_statut))

    # ---------------- TABLEAU DE BORD ----------------

    def _ouvrir_tableau_de_bord(self):
        fen = tk.Toplevel(self)
        fen.title("Tableau de bord")
        fen.geometry("520x430")
        fen.configure(bg=THEME["bg"])
        fen.transient(self)

        cadre = ttk.Frame(fen, padding=16)
        cadre.pack(fill="both", expand=True)

        ttk.Label(cadre, text="📊 Tableau de bord", style="Header.TLabel").pack(anchor="w", pady=(0, 12))

        if not self.base_donnees.est_connectee():
            ttk.Label(
                cadre,
                text="Statistiques indisponibles : base de données non connectée.",
                style="Secondary.TLabel",
            ).pack(anchor="w")
            return

        stats = self.base_donnees.statistiques_globales()

        cartes = ttk.Frame(cadre)
        cartes.pack(fill="x", pady=(0, 16))

        self._creer_carte_stat(cartes, "Autorisés aujourd'hui", stats["aujourdhui_autorise"], THEME["success"])
        self._creer_carte_stat(cartes, "Refusés aujourd'hui", stats["aujourdhui_refuse"], THEME["error"])
        self._creer_carte_stat(cartes, "Total autorisés", stats["total_autorise"], THEME["accent"])
        self._creer_carte_stat(cartes, "Total refusés", stats["total_refuse"], THEME["neutral"])

        ttk.Label(
            cadre, text="7 derniers jours  (vert = autorisé, rouge = refusé)",
            style="Secondary.TLabel",
        ).pack(anchor="w", pady=(4, 6))

        canvas = tk.Canvas(
            cadre, width=470, height=210, bg=THEME["bg_card"],
            highlightbackground=THEME["border"], highlightthickness=1,
        )
        canvas.pack(fill="both", expand=True)

        donnees = self.base_donnees.statistiques_par_jour(7)
        self._dessiner_graphique(canvas, donnees, largeur=470, hauteur=210)

    def _creer_carte_stat(self, parent, titre, valeur, couleur):
        carte = tk.Frame(parent, bg=THEME["bg_card"], highlightbackground=THEME["border"], highlightthickness=1)
        carte.pack(side="left", expand=True, fill="both", padx=4)
        tk.Label(
            carte, text=str(valeur), bg=THEME["bg_card"], fg=couleur,
            font=(THEME["font_family"], 20, "bold"),
        ).pack(pady=(10, 0))
        tk.Label(
            carte, text=titre, bg=THEME["bg_card"], fg=THEME["text_secondary"],
            font=(THEME["font_family"], 8), wraplength=100, justify="center",
        ).pack(pady=(0, 10))
        return carte

    def _dessiner_graphique(self, canvas, donnees, largeur=470, hauteur=210):
        """Petit graphique en barres empilées (autorisé/refusé), dessiné en Canvas natif (pas de dépendance externe)."""
        canvas.delete("all")
        marge_gauche = 16
        marge_droite = 16
        marge_bas = 24
        marge_haut = 20

        if not donnees:
            canvas.create_text(
                largeur // 2, hauteur // 2, text="Pas encore de données",
                fill=THEME["text_secondary"], font=(THEME["font_family"], 10),
            )
            return

        maxi = max((a + r) for _, a, r in donnees) or 1
        zone_h = hauteur - marge_haut - marge_bas
        zone_w = largeur - marge_gauche - marge_droite
        largeur_barre = zone_w / len(donnees)
        y_base = hauteur - marge_bas

        canvas.create_line(marge_gauche, y_base, largeur - marge_droite, y_base, fill=THEME["border"])

        for i, (label, a, r) in enumerate(donnees):
            x0 = marge_gauche + i * largeur_barre + 6
            x1 = x0 + largeur_barre - 12
            h_a = zone_h * (a / maxi)
            h_r = zone_h * (r / maxi)

            if a:
                canvas.create_rectangle(x0, y_base - h_a, x1, y_base, fill=THEME["success"], width=0)
            if r:
                canvas.create_rectangle(x0, y_base - h_a - h_r, x1, y_base - h_a, fill=THEME["error"], width=0)

            canvas.create_text(
                (x0 + x1) / 2, y_base + 12, text=label,
                font=(THEME["font_family"], 8), fill=THEME["text_secondary"],
            )
            total = a + r
            if total:
                canvas.create_text(
                    (x0 + x1) / 2, y_base - h_a - h_r - 8, text=str(total),
                    font=(THEME["font_family"], 8, "bold"), fill=THEME["text_primary"],
                )

    # ---------------- THÈME (MODE SOMBRE) ----------------

    def _basculer_theme(self):
        self._mode_sombre = not self._mode_sombre
        nouvelle_palette = config.PALETTE_SOMBRE if self._mode_sombre else config.PALETTE_CLAIRE
        THEME.clear()
        THEME.update(nouvelle_palette)
        self._reconstruire_interface()

    def _reconstruire_interface(self):
        """
        Reconstruit entièrement l'interface avec le thème courant (THEME).
        Nécessaire car les couleurs des widgets tk "bruts" (Frame, Label,
        Canvas...) sont figées à la création : on ne peut pas les
        re-teinter a posteriori, il faut reconstruire.
        """
        terme_recherche = self.var_recherche.get() if hasattr(self, "var_recherche") else ""
        periode = self.var_periode.get() if hasattr(self, "var_periode") else "Tout"
        statut_filtre = self.var_statut_filtre.get() if hasattr(self, "var_statut_filtre") else "Tous"

        for enfant in self.winfo_children():
            enfant.destroy()

        self.configure(bg=THEME["bg"])
        self._configurer_styles()
        self._construire_header()
        self._construire_toolbar()
        self._construire_fenetre_diagnostics()
        self._construire_liste()
        self._construire_footer()

        self.var_periode.set(periode)
        self.var_statut_filtre.set(statut_filtre)
        self.var_recherche.set(terme_recherche)

        self.bouton_theme.config(text="☀️ Mode clair" if self._mode_sombre else "🌙 Mode sombre")

        self._restaurer_statuts_widgets()
        self._restaurer_liste_ports()
        self._filtrer_liste()
        self.label_compteur.config(text=f"{self.nombre_badges} badge(s) scanné(s)")

    def _restaurer_statuts_widgets(self):
        """Réapplique les derniers statuts connus aux badges fraîchement recréés."""
        self._maj_badge_statut(self.badge_statut_port, *self._etat_port)
        self._maj_badge_statut(self.badge_statut_imprimante, *self._etat_imprimante)
        self._maj_badge_statut(self.badge_statut_db, *self._etat_db)

    def _restaurer_liste_ports(self):
        """Réaffiche la liste des ports après reconstruction, sans relancer de connexion."""
        ports = LecteurSerie.lister_ports()
        self.combo_port["values"] = ports
        if self.lecteur.port_actuel and self.lecteur.port_actuel in ports:
            self.combo_port.set(self.lecteur.port_actuel)
        elif ports:
            self.combo_port.set(ports[0])

    # ---------------- RECHERCHE / FILTRES ----------------

    def _filtrer_liste(self, *args):
        terme = self.var_recherche.get().strip().lower()
        periode = self.var_periode.get() if hasattr(self, "var_periode") else "Tout"
        statut_filtre = self.var_statut_filtre.get() if hasattr(self, "var_statut_filtre") else "Tous"

        aujourdhui = datetime.now().date()
        seuils = {
            "Aujourd'hui": aujourdhui,
            "7 derniers jours": aujourdhui - timedelta(days=6),
            "30 derniers jours": aujourdhui - timedelta(days=29),
        }
        seuil = seuils.get(periode)

        for item in self.arbre.get_children():
            self.arbre.delete(item)

        for ligne in reversed(self.badges_donnees):
            numero, badge_id, nom, horodatage, statut = ligne
            autorise = statut in ("Autorisé", "Accès autorisé")

            if statut_filtre == "Autorisé" and not autorise:
                continue
            if statut_filtre == "Refusé" and autorise:
                continue

            if seuil is not None:
                try:
                    jour_ligne = datetime.strptime(str(horodatage)[:10], "%d/%m/%Y").date()
                except ValueError:
                    jour_ligne = None
                if jour_ligne is None or jour_ligne < seuil:
                    continue

            if (
                terme in str(badge_id).lower()
                or terme in str(nom).lower()
                or terme in str(numero)
                or terme in str(horodatage).lower()
            ):
                self._inserer_ligne_arbre(ligne, autorise=autorise)

    # ---------------- EXPORT ----------------

    def _exporter_csv(self):
        if not self.badges_donnees:
            messagebox.showinfo("Export CSV", "Aucun badge à exporter.")
            return

        nom_defaut = export.nom_fichier_horodate("badges", "csv")
        chemin = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=nom_defaut,
            filetypes=[("Fichier CSV", "*.csv")],
        )
        if not chemin:
            return

        if export.exporter_csv(self.badges_donnees, chemin):
            messagebox.showinfo("Export CSV", f"Export réussi :\n{chemin}")
        else:
            messagebox.showerror("Export CSV", "Échec de l'export CSV.")

    def _exporter_excel(self):
        if not self.badges_donnees:
            messagebox.showinfo("Export Excel", "Aucun badge à exporter.")
            return

        nom_defaut = export.nom_fichier_horodate("badges", "xlsx")
        chemin = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            initialfile=nom_defaut,
            filetypes=[("Classeur Excel", "*.xlsx")],
        )
        if not chemin:
            return

        if export.exporter_excel(self.badges_donnees, chemin):
            messagebox.showinfo("Export Excel", f"Export réussi :\n{chemin}")
        else:
            messagebox.showerror(
                "Export Excel",
                "Échec de l'export Excel.\nVérifiez que le module 'openpyxl' est installé\n"
                "(pip install openpyxl)."
            )

    # ---------------- RESET ----------------

    def _effacer_liste(self):
        if self.badges_donnees:
            confirmation = messagebox.askyesno(
                "Effacer la liste",
                "Voulez-vous vraiment effacer tous les badges scannés ?"
            )
            if not confirmation:
                return

        for item in self.arbre.get_children():
            self.arbre.delete(item)

        self.badges_donnees.clear()
        self.nombre_badges = 0
        self.label_compteur.config(text="0 badge(s) scanné(s)")

    # ---------------- GESTION UTILISATEURS / BADGES ----------------

    def _ouvrir_gestion_utilisateurs(self):
        if not self.base_donnees.est_connectee():
            messagebox.showerror(
                "Gestion des utilisateurs",
                "Base de données non connectée : impossible de gérer les utilisateurs."
            )
            return

        fenetre = tk.Toplevel(self)
        fenetre.title("Gérer les utilisateurs et leurs badges")
        fenetre.geometry("520x480")
        fenetre.configure(bg=THEME["bg"])
        fenetre.transient(self)
        fenetre.grab_set()

        # -- Formulaire nouvel utilisateur --
        cadre_user = ttk.LabelFrame(fenetre, text="Nouvel utilisateur", padding=10)
        cadre_user.pack(fill="x", padx=14, pady=(14, 8))

        ttk.Label(cadre_user, text="Nom :").grid(row=0, column=0, sticky="w")
        var_nom = tk.StringVar()
        ttk.Entry(cadre_user, textvariable=var_nom, width=22).grid(row=0, column=1, padx=6)

        ttk.Label(cadre_user, text="Prénom :").grid(row=1, column=0, sticky="w", pady=(6, 0))
        var_prenom = tk.StringVar()
        ttk.Entry(cadre_user, textvariable=var_prenom, width=22).grid(row=1, column=1, padx=6, pady=(6, 0))

        def ajouter_utilisateur():
            nom = var_nom.get().strip()
            prenom = var_prenom.get().strip()
            if not nom:
                messagebox.showwarning("Utilisateur", "Le nom ne peut pas être vide.")
                return
            uid = self.base_donnees.ajouter_utilisateur(nom, prenom)
            if uid:
                var_nom.set("")
                var_prenom.set("")
                rafraichir_combo_utilisateurs()
                rafraichir_liste()
            else:
                messagebox.showerror("Utilisateur", self.base_donnees.derniere_erreur or "Échec.")

        ttk.Button(cadre_user, text="➕ Ajouter", style="Accent.TButton",
                   command=ajouter_utilisateur).grid(row=0, column=2, rowspan=2, padx=6)

        # -- Formulaire association badge --
        cadre_badge = ttk.LabelFrame(fenetre, text="Associer un matricule à un utilisateur", padding=10)
        cadre_badge.pack(fill="x", padx=14, pady=8)

        ttk.Label(cadre_badge, text="Utilisateur :").grid(row=0, column=0, sticky="w")
        combo_utilisateur = ttk.Combobox(cadre_badge, width=26, state="readonly")
        combo_utilisateur.grid(row=0, column=1, padx=6, pady=(0, 6))

        ttk.Label(cadre_badge, text="Matricule :").grid(row=1, column=0, sticky="w")
        var_badge = tk.StringVar()
        ttk.Entry(cadre_badge, textvariable=var_badge, width=30).grid(row=1, column=1, padx=6)
        ttk.Label(
            cadre_badge,
            text="Le numéro affiché en grand sur le ticket lors du scan (ex: 11), pas la valeur brute du lecteur.",
            style="Secondary.TLabel",
            wraplength=440,
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(4, 0))

        utilisateurs_disponibles = []

        def rafraichir_combo_utilisateurs():
            utilisateurs_disponibles.clear()
            utilisateurs_disponibles.extend(self.base_donnees.lister_utilisateurs())
            combo_utilisateur["values"] = [
                f"{nom} {prenom}".strip() for _id, nom, prenom in utilisateurs_disponibles
            ]
            if utilisateurs_disponibles:
                combo_utilisateur.current(0)

        def associer_badge():
            numero = extraire_matricule(var_badge.get().strip())
            index = combo_utilisateur.current()
            if not var_badge.get().strip():
                messagebox.showwarning("Matricule", "Le matricule ne peut pas être vide.")
                return
            if index < 0:
                messagebox.showwarning("Matricule", "Créez d'abord un utilisateur.")
                return
            utilisateur_id = utilisateurs_disponibles[index][0]
            if self.base_donnees.associer_badge(numero, utilisateur_id):
                var_badge.set("")
                rafraichir_liste()
            else:
                messagebox.showerror(
                    "Matricule",
                    self.base_donnees.derniere_erreur
                    or "Échec (matricule déjà associé ?)."
                )

        ttk.Button(cadre_badge, text="🔗 Associer", style="Accent.TButton",
                   command=associer_badge).grid(row=1, column=2, padx=6)

        # -- Liste des associations existantes --
        cadre_liste = ttk.LabelFrame(fenetre, text="Utilisateurs et badges enregistrés", padding=10)
        cadre_liste.pack(fill="both", expand=True, padx=14, pady=(8, 14))

        arbre_users = ttk.Treeview(
            cadre_liste, columns=("badge", "nom"), show="headings", height=10
        )
        arbre_users.heading("badge", text="Numéro de badge")
        arbre_users.heading("nom", text="Utilisateur")
        arbre_users.column("badge", width=180, anchor="w")
        arbre_users.column("nom", width=240, anchor="w")
        arbre_users.pack(fill="both", expand=True)

        def rafraichir_liste():
            for item in arbre_users.get_children():
                arbre_users.delete(item)
            for numero_badge, nom, prenom in self.base_donnees.lister_badges():
                arbre_users.insert("", "end", values=(numero_badge, f"{nom} {prenom}".strip()))

        rafraichir_combo_utilisateurs()
        rafraichir_liste()

    # ---------------- CLOSE ----------------

    def _fermer(self):
        self.lecteur.deconnecter()
        self.imprimante.fermer()
        self.base_donnees.deconnecter()
        self.destroy()
