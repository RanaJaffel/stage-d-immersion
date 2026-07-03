-- Script de création de la base de données "scan_pointeuse"
-- À importer via phpMyAdmin (onglet SQL) si vous préférez créer la base
-- manuellement plutôt que de laisser l'application le faire automatiquement.
--
-- Structure :
--   utilisateurs : les personnes (nom + prénom affichés sur le ticket)
--   badges       : chaque badge physique, lié à un utilisateur
--   scans        : chaque tentative de scan (autorisée ou refusée)
--
-- Le numéro de ticket imprimé = l'id auto-incrémenté de la ligne "scans"
-- (une ligne "scans" = un ticket imprimé), il augmente donc automatiquement
-- à chaque scan, sans jamais revenir en arrière.
--
-- Règle métier : un badge n'a le droit qu'à UN SEUL scan autorisé,
-- pour toujours (peu importe le jour). Un badge non lié à un utilisateur
-- est refusé ("Badge inconnu").

CREATE DATABASE IF NOT EXISTS scan_pointeuse
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE scan_pointeuse;

CREATE TABLE IF NOT EXISTS utilisateurs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nom VARCHAR(128) NOT NULL,
    prenom VARCHAR(128) NOT NULL DEFAULT '',
    cree_le TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS badges (
    id INT AUTO_INCREMENT PRIMARY KEY,
    numero_badge VARCHAR(64) NOT NULL UNIQUE,
    utilisateur_id INT NOT NULL,
    cree_le TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_badges_utilisateur
        FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS scans (
    id INT AUTO_INCREMENT PRIMARY KEY,  -- = numéro de ticket imprimé
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
