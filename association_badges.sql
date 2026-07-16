-- ============================================================
-- Association matricule <-> nom/prénom
-- À exécuter dans phpMyAdmin (onglet SQL), base "scan_pointeuse"
-- ============================================================
--
-- IMPORTANT : la colonne "badges.numero_badge" doit contenir le
-- MATRICULE SIMPLE (ex: '11'), PAS la valeur brute du lecteur
-- (ex: '0,11'). C'est ce que l'application compare désormais.
--
-- Remplacez NOM_A / PRENOM_A, NOM_B / PRENOM_B, etc. par les vrais
-- noms, puis exécutez tout le bloc. Ajoutez/retirez des blocs pour
-- chaque matricule que vous voulez enregistrer.

-- Matricule 11
INSERT INTO utilisateurs (nom, prenom) VALUES ('NOM_A', 'PRENOM_A');
INSERT INTO badges (numero_badge, utilisateur_id) VALUES ('11', LAST_INSERT_ID());

-- Matricule 8
INSERT INTO utilisateurs (nom, prenom) VALUES ('NOM_B', 'PRENOM_B');
INSERT INTO badges (numero_badge, utilisateur_id) VALUES ('8', LAST_INSERT_ID());

-- Matricule 7
INSERT INTO utilisateurs (nom, prenom) VALUES ('NOM_C', 'PRENOM_C');
INSERT INTO badges (numero_badge, utilisateur_id) VALUES ('7', LAST_INSERT_ID());

-- ============================================================
-- Pour ajouter un nouveau matricule plus tard, copiez ce modèle :
-- ============================================================
-- INSERT INTO utilisateurs (nom, prenom) VALUES ('NOM', 'PRENOM');
-- INSERT INTO badges (numero_badge, utilisateur_id) VALUES ('MATRICULE', LAST_INSERT_ID());

-- ============================================================
-- Vérification : liste tous les matricules et leur nom associé
-- ============================================================
SELECT b.numero_badge AS matricule, u.nom, u.prenom
FROM badges b
JOIN utilisateurs u ON u.id = b.utilisateur_id
ORDER BY b.numero_badge;
