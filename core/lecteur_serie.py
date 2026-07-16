"""
Logique de communication avec la pointeuse (via le convertisseur Wie232).

Cette classe ne connaît rien de Tkinter : elle se contente d'ouvrir le
port série, d'écouter en continu dans un thread séparé, et de prévenir
l'appelant (via une fonction "callback") à chaque badge détecté.

Cette séparation permet de réutiliser cette classe telle quelle dans
n'importe quelle autre interface (ligne de commande, autre GUI, backend...).

Amélioration : tentative de reconnexion automatique si le port se
déconnecte en cours de lecture (câble débranché, etc.).
"""

import threading
import time

import serial
import serial.tools.list_ports

import config


class LecteurSerie:
    def __init__(self, callback_badge=None, callback_erreur=None, callback_statut=None):
        """
        callback_badge  : fonction appelée avec le numéro de badge (str)
                           à chaque badge détecté.
        callback_erreur : fonction appelée avec un message d'erreur (str)
                           en cas de problème de connexion.
        callback_statut : fonction appelée avec un statut (str) parmi
                           "connecte", "deconnecte", "reconnexion"
                           pour informer l'UI des changements d'état.
        """
        self.connexion = None
        self.port_actuel = None
        self.lecture_active = False
        self.reconnexion_auto = True
        self.thread_lecture = None

        self.callback_badge = callback_badge
        self.callback_erreur = callback_erreur
        self.callback_statut = callback_statut

    @staticmethod
    def lister_ports():
        """Retourne la liste des noms de ports série disponibles (ex: ['COM3', 'COM4'])."""
        return [p.device for p in serial.tools.list_ports.comports()]

    def est_connecte(self):
        return self.lecture_active and self.connexion is not None and self.connexion.is_open

    def connecter(self, port: str) -> bool:
        """Ouvre la connexion série et démarre l'écoute dans un thread séparé."""
        try:
            self.connexion = serial.Serial(
                port=port,
                baudrate=config.BAUDRATE,
                bytesize=config.BYTESIZE,
                parity=config.PARITY,
                stopbits=config.STOPBITS,
                timeout=config.TIMEOUT,
            )
        except serial.SerialException as erreur:
            if self.callback_erreur:
                self.callback_erreur(str(erreur))
            return False

        self.port_actuel = port
        self.lecture_active = True
        self.thread_lecture = threading.Thread(target=self._boucle_lecture, daemon=True)
        self.thread_lecture.start()

        if self.callback_statut:
            self.callback_statut("connecte")
        return True

    def deconnecter(self):
        """Arrête l'écoute et ferme le port série proprement (arrêt volontaire)."""
        self.reconnexion_auto = False
        self.lecture_active = False
        if self.connexion:
            try:
                self.connexion.close()
            except serial.SerialException:
                pass
            self.connexion = None

        if self.callback_statut:
            self.callback_statut("deconnecte")

    def _boucle_lecture(self):
        """Tourne dans un thread séparé : lit le port en continu et notifie via callback."""
        while self.lecture_active and self.connexion:
            try:
                ligne = self.connexion.readline()
            except serial.SerialException as erreur:
                self.lecture_active = False
                if self.callback_erreur:
                    self.callback_erreur(str(erreur))
                self._tenter_reconnexion()
                return

            if ligne:
                numero_badge = ligne.decode(errors="ignore").strip()
                if numero_badge and self.callback_badge:
                    self.callback_badge(numero_badge)

    def _tenter_reconnexion(self):
        """Boucle de reconnexion automatique tant que le port a disparu."""
        if not self.reconnexion_auto or not self.port_actuel:
            return

        if self.callback_statut:
            self.callback_statut("reconnexion")

        while self.reconnexion_auto:
            time.sleep(config.RECONNECT_DELAY)

            ports_dispo = self.lister_ports()
            if self.port_actuel not in ports_dispo:
                continue

            try:
                self.connexion = serial.Serial(
                    port=self.port_actuel,
                    baudrate=config.BAUDRATE,
                    bytesize=config.BYTESIZE,
                    parity=config.PARITY,
                    stopbits=config.STOPBITS,
                    timeout=config.TIMEOUT,
                )
                self.lecture_active = True
                self.thread_lecture = threading.Thread(target=self._boucle_lecture, daemon=True)
                self.thread_lecture.start()

                if self.callback_statut:
                    self.callback_statut("connecte")
                return
            except serial.SerialException:
                continue
