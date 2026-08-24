"""Lectura y escritura de mapas .otbm.

El formato lo define src/iomap.h (enums de nodos/atributos) y lo interpreta
src/iomap.cpp. Aqui solo se cubre lo que ese parser entiende: areas de tiles,
tiles normales y de casa, items, towns y waypoints.
"""

import struct
from collections import OrderedDict

from otbfile import Node, Reader, parse, write

# src/iomap.h -> OTBM_NodeTypes_t
OTBM_ROOTV1 = 1
OTBM_MAP_DATA = 2
OTBM_TILE_AREA = 4
OTBM_TILE = 5
OTBM_ITEM = 6
OTBM_TOWNS = 12
OTBM_TOWN = 13
OTBM_HOUSETILE = 14
OTBM_WAYPOINTS = 15

# src/iomap.h -> OTBM_AttrTypes_t
OTBM_ATTR_DESCRIPTION = 1
OTBM_ATTR_TILE_FLAGS = 3
OTBM_ATTR_ACTION_ID = 4
OTBM_ATTR_UNIQUE_ID = 5
OTBM_ATTR_TELE_DEST = 8
OTBM_ATTR_ITEM = 9
OTBM_ATTR_DEPOT_ID = 10
OTBM_ATTR_EXT_SPAWN_FILE = 11
OTBM_ATTR_EXT_HOUSE_FILE = 13
OTBM_ATTR_HOUSEDOORID = 14
OTBM_ATTR_COUNT = 15

# src/iomap.h -> OTBM_TileFlag_t
TILEFLAG_PROTECTIONZONE = 1 << 0
TILEFLAG_NOPVPZONE = 1 << 2
TILEFLAG_NOLOGOUT = 1 << 3
TILEFLAG_PVPZONE = 1 << 4

# Las areas agrupan tiles en bloques de 256x256 con coordenadas relativas de
# 1 byte (OTBM_Tile_coords en src/iomap.h).
AREA_SIZE = 256


class Tile:
    __slots__ = ("x", "y", "z", "ground", "items", "flags", "house_id")

    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z
        self.ground = None      # id del item de suelo
        self.items = []         # ids apilados encima
        self.flags = 0
        self.house_id = None


class OTBMMap:
    def __init__(self, width=1024, height=1024, description="",
                 spawn_file="", house_file=""):
        self.width = width
        self.height = height
        self.description = description
        self.spawn_file = spawn_file
        self.house_file = house_file
        self.major_items = 3
        self.minor_items = 65
        self.tiles = OrderedDict()   # (x, y, z) -> Tile
        self.towns = []              # (id, nombre, x, y, z)

    # ---------- construccion ----------

    def tile(self, x, y, z):
        key = (x, y, z)
        found = self.tiles.get(key)
        if found is None:
            found = Tile(x, y, z)
            self.tiles[key] = found
        return found

    def set_ground(self, x, y, z, item_id):
        self.tile(x, y, z).ground = item_id

    def add_item(self, x, y, z, item_id):
        self.tile(x, y, z).items.append(item_id)

    def add_town(self, town_id, name, x, y, z):
        self.towns.append((town_id, name, x, y, z))

    # ---------- lectura ----------

    @classmethod
    def load(cls, path):
        _, root = parse(path)
        reader = Reader(root.props)
        version = reader.u32()
        width = reader.u16()
        height = reader.u16()
        major = reader.u32()
        minor = reader.u32()

        result = cls(width, height)
        result.major_items = major
        result.minor_items = minor
        result.otbm_version = version

        map_node = root.children[0]
        for node in map_node.children:
            if node.type == OTBM_TILE_AREA:
                result._read_area(node)
            elif node.type == OTBM_TOWNS:
                for town in node.children:
                    tr = Reader(town.props)
                    town_id = tr.u32()
                    name_len = tr.u16()
                    name = tr.raw(name_len).decode("utf-8", "replace")
                    result.towns.append((town_id, name, tr.u16(), tr.u16(), tr.u8()))
        return result

    def _read_area(self, area_node):
        reader = Reader(area_node.props)
        base_x = reader.u16()
        base_y = reader.u16()
        base_z = reader.u8()

        for tile_node in area_node.children:
            tr = Reader(tile_node.props)
            x = base_x + tr.u8()
            y = base_y + tr.u8()
            tile = self.tile(x, y, base_z)

            if tile_node.type == OTBM_HOUSETILE:
                tile.house_id = tr.u32()

            while tr.left() > 0:
                attr = tr.u8()
                if attr == OTBM_ATTR_TILE_FLAGS:
                    tile.flags = tr.u32()
                elif attr == OTBM_ATTR_ITEM:
                    item_id = tr.u16()
                    if tile.ground is None:
                        tile.ground = item_id
                    else:
                        tile.items.append(item_id)
                else:
                    # Atributos que no interesan para el analisis; el resto del
                    # bloque no se puede saltar de forma fiable, se corta aqui.
                    break

            for item_node in tile_node.children:
                ir = Reader(item_node.props)
                item_id = ir.u16()
                if tile.ground is None:
                    tile.ground = item_id
                else:
                    tile.items.append(item_id)

    # ---------- escritura ----------

    def save(self, path):
        header = struct.pack("<IHHII", 2, self.width, self.height,
                             self.major_items, self.minor_items)
        root = Node(0, header)

        props = bytearray()
        if self.description:
            data = self.description.encode("utf-8")
            props += struct.pack("<BH", OTBM_ATTR_DESCRIPTION, len(data)) + data
        if self.spawn_file:
            data = self.spawn_file.encode("utf-8")
            props += struct.pack("<BH", OTBM_ATTR_EXT_SPAWN_FILE, len(data)) + data
        if self.house_file:
            data = self.house_file.encode("utf-8")
            props += struct.pack("<BH", OTBM_ATTR_EXT_HOUSE_FILE, len(data)) + data

        map_node = Node(OTBM_MAP_DATA, bytes(props))
        root.children.append(map_node)

        for area_node in self._build_areas():
            map_node.children.append(area_node)

        if self.towns:
            towns_node = Node(OTBM_TOWNS, b"")
            for town_id, name, x, y, z in self.towns:
                data = name.encode("utf-8")
                payload = (struct.pack("<I", town_id)
                           + struct.pack("<H", len(data)) + data
                           + struct.pack("<HHB", x, y, z))
                towns_node.children.append(Node(OTBM_TOWN, payload))
            map_node.children.append(towns_node)

        write(path, b"\0\0\0\0", root)

    def _build_areas(self):
        grouped = OrderedDict()
        for (x, y, z), tile in self.tiles.items():
            key = (x // AREA_SIZE * AREA_SIZE, y // AREA_SIZE * AREA_SIZE, z)
            grouped.setdefault(key, []).append(tile)

        areas = []
        for (base_x, base_y, base_z), tiles in grouped.items():
            area = Node(OTBM_TILE_AREA,
                        struct.pack("<HHB", base_x, base_y, base_z))
            for tile in tiles:
                area.children.append(
                    self._build_tile(tile, base_x, base_y))
            areas.append(area)
        return areas

    def _build_tile(self, tile, base_x, base_y):
        node_type = OTBM_HOUSETILE if tile.house_id else OTBM_TILE
        props = bytearray(struct.pack("<BB", tile.x - base_x, tile.y - base_y))
        if tile.house_id:
            props += struct.pack("<I", tile.house_id)
        if tile.flags:
            props += struct.pack("<BI", OTBM_ATTR_TILE_FLAGS, tile.flags)
        if tile.ground is not None:
            props += struct.pack("<BH", OTBM_ATTR_ITEM, tile.ground)

        node = Node(node_type, bytes(props))
        # Los items sobre el suelo van como nodos hijo; el parser del servidor
        # acepta ambas formas, pero asi se pueden anadir atributos por item.
        for item_id in tile.items:
            node.children.append(Node(OTBM_ITEM, struct.pack("<H", item_id)))
        return node
