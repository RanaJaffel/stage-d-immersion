"""
Utilitaires partagés (extraction du matricule depuis la valeur brute
envoyée par le lecteur de badges).

Centralisé ici pour être utilisé à la fois par l'interface (dès la
réception du badge) et par l'imprimante (au moment d'imprimer).
"""


def extraire_matricule(numero_badge: str) -> str:
    """
    Isole le matricule réel à partir de la valeur brute envoyée par le
    lecteur de badges.

    Le lecteur transmet une valeur au format "code_site.matricule" ou
    "code_site,matricule" (ex: "0.2" ou "0,11") selon le paramétrage /
    la locale du convertisseur. Le matricule à utiliser partout dans
    l'application (base de données, affichage, ticket imprimé) est la
    partie numérique non nulle (ex: "2", "11"), jamais "0".

    Si la valeur reçue est déjà un matricule simple (ex: "2"), elle est
    retournée telle quelle.
    """
    brut = (numero_badge or "").strip()
    if not brut:
        return "0"

    parties = brut.replace(",", ".").split(".")
    parties_valides = [p for p in parties if p.isdigit() and int(p) != 0]
    if parties_valides:
        # La dernière partie non nulle est le matricule (et non le code site).
        return str(int(parties_valides[-1]))

    # Repli : on garde uniquement les chiffres, en retirant les zéros de tête.
    chiffres = "".join(c for c in brut if c.isdigit()).lstrip("0")
    return chiffres or brut
