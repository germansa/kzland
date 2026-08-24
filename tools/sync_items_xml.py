"""Anade a data/items/items.xml las definiciones de los items que usa el mapa.

items.otb ya define que es cada item a nivel de servidor, pero items.xml es lo
que le da nombre y atributos de juego. Sin la entrada correspondiente una
puerta, por ejemplo, se comporta como un bloque solido en vez de abrirse.

Las definiciones se copian tal cual del items.xml original de Forgotten Server,
que sigue disponible en el historial de git:

    git show 6f143b7:data/items/items.xml > referencia.xml
    python tools/sync_items_xml.py referencia.xml

Es idempotente: los ids que ya estaban no se duplican.
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(ROOT, "data", "items", "items.xml")
USED_IDS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "used_item_ids.txt")

ITEM_BLOCK = re.compile(
    r'\t?<item\s+[^>]*?(?:/>|>.*?</item>)', re.DOTALL)
ID_ATTR = re.compile(r'\bid="(\d+)"')
RANGE_ATTR = re.compile(r'\bfromid="(\d+)"\s+toid="(\d+)"')


def covered_ids(block):
    match = RANGE_ATTR.search(block)
    if match:
        return set(range(int(match.group(1)), int(match.group(2)) + 1))
    match = ID_ATTR.search(block)
    return {int(match.group(1))} if match else set()


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    reference_path = sys.argv[1]

    with open(USED_IDS, encoding="utf-8") as fh:
        wanted = {int(line) for line in fh if line.strip()}

    with open(TARGET, encoding="utf-8") as fh:
        target = fh.read()
    already = set()
    for block in ITEM_BLOCK.findall(target):
        already |= covered_ids(block)

    missing = wanted - already
    if not missing:
        print("items.xml ya cubre los {} ids usados".format(len(wanted)))
        return 0

    with open(reference_path, encoding="utf-8", errors="replace") as fh:
        reference = fh.read()

    additions = []
    resolved = set()
    for block in ITEM_BLOCK.findall(reference):
        ids = covered_ids(block)
        if ids & missing and not (ids & resolved):
            additions.append(block.strip())
            resolved |= ids

    still_missing = sorted(missing - resolved)
    marker = "</items>"
    body = "\n".join("\t" + line for line in
                     "\n".join(additions).splitlines())
    updated = target.replace(
        marker,
        "\t<!-- items usados por el mapa, copiados del datapack original -->\n"
        + body + "\n" + marker)

    with open(TARGET, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(updated)

    print("anadidos {} bloques para {} ids".format(len(additions),
                                                   len(missing & resolved)))
    if still_missing:
        print("SIN DEFINICION en la referencia: {}".format(still_missing))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
