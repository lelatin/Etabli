"""
Extrait une version légère de AllPrintings.json (MTGJSON).

Usage :
    pip install ijson
    python extraire_cartes.py AllPrintings.json cartes.json

Résultat : cartes.json contenant
  - "editions" : la liste des extensions (code, nom, nom français, date, type)
  - "cartes"   : une seule entrée par carte (impression la plus récente),
                 avec ses traductions françaises et la liste de ses extensions.
"""
import json
import sys
from decimal import Decimal

import ijson


def convertir_nombre(o):
    """ijson renvoie des Decimal : on les convertit en int ou float pour json."""
    if isinstance(o, Decimal):
        return int(o) if o == o.to_integral_value() else float(o)
    raise TypeError(f"Type non sérialisable : {type(o).__name__}")


def main(chemin_entree, chemin_sortie):
    editions = []

    # On lit édition par édition, sans charger les 661 Mo d'un coup
    with open(chemin_entree, "rb") as f:
        for code, ed in ijson.kvitems(f, "data"):
            editions.append(
                {
                    "code": code,
                    "nom": ed.get("name", code),
                    "nom_fr": (ed.get("translations") or {}).get("French"),
                    "type": ed.get("type", ""),
                    "date": ed.get("releaseDate", "0000-00-00"),
                    "cartes": ed.get("cards", []),
                }
            )
            print(f"Lu : {code}", end="\r")

    # Du plus ancien au plus récent : les impressions récentes écrasent les anciennes
    editions.sort(key=lambda e: e["date"])

    cartes = {}
    francais = {}         # nom anglais -> traduction française la plus récente
    presences = {}        # nom anglais -> codes des extensions où la carte existe
    infos_editions = []

    for ed in editions:
        vus = set()
        for c in ed["cartes"]:
            # Pour les cartes à deux faces, on ne garde que la face avant
            if c.get("side") not in (None, "a"):
                continue

            nom = c["name"]
            if nom not in vus:
                vus.add(nom)
                presences.setdefault(nom, []).append(ed["code"])

            # Traduction française : on la retient même si l'impression la plus
            # récente de la carte n'existe pas en français
            for fd in c.get("foreignData", []):
                if fd.get("language") == "French" and fd.get("name"):
                    francais[nom] = {
                        "nom_fr": fd.get("name", ""),
                        "type_fr": fd.get("type", ""),
                        "texte_fr": fd.get("text", ""),
                    }

            ident = c.get("identifiers", {})
            cartes[nom] = {
                "nom": nom,
                "cout": c.get("manaCost", ""),
                "cmc": c.get("manaValue", 0),
                "type": c.get("type", ""),
                "types": c.get("types", []),
                "texte": c.get("text", ""),
                "couleurs": c.get("colors", []),
                "identite": c.get("colorIdentity", []),
                "force": c.get("power"),
                "endurance": c.get("toughness"),
                "mots_cles": c.get("keywords", []),
                "rarete": c.get("rarity"),
                "edition": ed["code"],
                "numero": c.get("number"),
                "legalites": c.get("legalities", {}),
                "scryfall_id": ident.get("scryfallId"),
            }

        infos_editions.append(
            {
                "code": ed["code"],
                "nom": ed["nom"],
                "nom_fr": ed["nom_fr"],
                "type": ed["type"],
                "date": ed["date"],
                "nb": len(vus),
            }
        )

    for nom, carte in cartes.items():
        carte.update(francais.get(nom, {}))
        carte["editions"] = presences.get(nom, [])

    liste = sorted(cartes.values(), key=lambda c: c["nom"])
    traduites = sum(1 for c in liste if c.get("nom_fr"))

    with open(chemin_sortie, "w", encoding="utf-8") as f:
        json.dump(
            {"editions": infos_editions, "cartes": liste},
            f,
            ensure_ascii=False,
            separators=(",", ":"),
            default=convertir_nombre,
        )

    print(f"\n{len(liste)} cartes uniques écrites dans {chemin_sortie}")
    print(f"dont {traduites} avec une traduction française")
    print(f"{len(infos_editions)} extensions")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage : python extraire_cartes.py AllPrintings.json cartes.json")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
