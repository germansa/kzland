"""Consulta de data/items/items.otb para elegir ids de item verificados.

items.otb es la fuente de verdad del servidor sobre que es cada item: a que
grupo pertenece (suelo, contenedor, ...) y que flags tiene (bloquea, es
apilable, ...). Esta clase lo lee para poder construir mapas sin adivinar ids.

Estructura segun Items::loadFromOtb en src/items.cpp y los enums de
src/itemloader.h.
"""

import os
import re

from otbfile import Reader, parse

# src/itemloader.h -> itemgroup_t
GROUP_NONE = 0
GROUP_GROUND = 1
GROUP_CONTAINER = 2
GROUP_SPLASH = 11
GROUP_FLUID = 12
GROUP_DEPRECATED = 14
GROUP_PODIUM = 15

# src/itemloader.h -> itemflags_t
FLAG_BLOCK_SOLID = 1 << 0
FLAG_BLOCK_PROJECTILE = 1 << 1
FLAG_BLOCK_PATHFIND = 1 << 2
FLAG_HAS_HEIGHT = 1 << 3
FLAG_PICKUPABLE = 1 << 5
FLAG_MOVEABLE = 1 << 6
FLAG_STACKABLE = 1 << 7
FLAG_ALWAYSONTOP = 1 << 13
FLAG_HANGABLE = 1 << 16
FLAG_VERTICAL = 1 << 17
FLAG_HORIZONTAL = 1 << 18
FLAG_LOOKTHROUGH = 1 << 23

ITEM_ATTR_SERVERID = 0x10
ITEM_ATTR_CLIENTID = 0x11
ITEM_ATTR_SPEED = 0x14


class ItemType:
    __slots__ = ("server_id", "client_id", "group", "flags", "speed", "name")

    def __init__(self, server_id, client_id, group, flags, speed):
        self.server_id = server_id
        self.client_id = client_id
        self.group = group
        self.flags = flags
        self.speed = speed
        self.name = ""

    @property
    def is_ground(self):
        return self.group == GROUP_GROUND

    @property
    def blocks(self):
        return bool(self.flags & FLAG_BLOCK_SOLID)

    def __repr__(self):
        return "ItemType(id={}, group={}, name={!r})".format(
            self.server_id, self.group, self.name
        )


class ItemsDB:
    def __init__(self, otb_path, names_xml=None):
        self.by_id = {}
        self._load_otb(otb_path)
        if names_xml and os.path.exists(names_xml):
            self._load_names(names_xml)

    def _load_otb(self, path):
        _, root = parse(path)
        for node in root.children:
            reader = Reader(node.props)
            flags = reader.u32()
            server_id = client_id = speed = 0
            while reader.left() >= 3:
                attr = reader.u8()
                length = reader.u16()
                payload = reader.raw(length)
                if attr == ITEM_ATTR_SERVERID and length == 2:
                    server_id = int.from_bytes(payload, "little")
                elif attr == ITEM_ATTR_CLIENTID and length == 2:
                    client_id = int.from_bytes(payload, "little")
                elif attr == ITEM_ATTR_SPEED and length == 2:
                    speed = int.from_bytes(payload, "little")
            if server_id:
                self.by_id[server_id] = ItemType(
                    server_id, client_id, node.type, flags, speed
                )

    def _load_names(self, path):
        """Anota nombres desde un items.xml (se usa el original del repo).

        Se parsea con regex y no con un parser XML porque solo interesan los
        atributos id/fromid/toid/name de cada <item>, y el archivo es grande.
        """
        pattern = re.compile(
            r'<item\s+(?:id="(\d+)"|fromid="(\d+)"\s+toid="(\d+)")[^>]*?name="([^"]*)"'
        )
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for match in pattern.finditer(fh.read()):
                single, from_id, to_id, name = match.groups()
                if single:
                    ids = [int(single)]
                else:
                    ids = range(int(from_id), int(to_id) + 1)
                for item_id in ids:
                    entry = self.by_id.get(item_id)
                    if entry is not None:
                        entry.name = name

    def get(self, item_id):
        return self.by_id.get(item_id)

    def find(self, name_pattern, group=None, blocks=None, limit=40):
        """Busca items por nombre, opcionalmente filtrando por grupo/bloqueo."""
        regex = re.compile(name_pattern, re.IGNORECASE)
        out = []
        for entry in self.by_id.values():
            if not entry.name or not regex.search(entry.name):
                continue
            if group is not None and entry.group != group:
                continue
            if blocks is not None and entry.blocks != blocks:
                continue
            out.append(entry)
            if len(out) >= limit:
                break
        return sorted(out, key=lambda e: e.server_id)

    def require(self, item_id, *, ground=None, blocks=None):
        """Devuelve el item validando que cumple lo esperado.

        Se usa al construir el mapa para que un id equivocado falle al generar
        y no en silencio dentro del juego.
        """
        entry = self.by_id.get(item_id)
        if entry is None:
            raise KeyError("el item {} no existe en items.otb".format(item_id))
        if ground is not None and entry.is_ground != ground:
            raise ValueError(
                "el item {} ({}) ground={} pero se esperaba {}".format(
                    item_id, entry.name or "sin nombre", entry.is_ground, ground
                )
            )
        if blocks is not None and entry.blocks != blocks:
            raise ValueError(
                "el item {} ({}) blocks={} pero se esperaba {}".format(
                    item_id, entry.name or "sin nombre", entry.blocks, blocks
                )
            )
        return entry
