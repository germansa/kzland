"""Genera el mapa inicial de Kzland: una aldea y sus alrededores.

Escribe data/world/kzland.otbm, su archivo de spawns y el de casas.

Los ids de item NO estan puestos a mano: se eligieron analizando el mapa
original de Tibia (que sigue en el historial de git) para deducir que pieza
va en cada sitio, y cada uno se valida contra items.otb al arrancar. Ver
tools/README.md.

Uso:  python tools/build_village.py
"""

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from itemsdb import ItemsDB
from otbmmap import OTBMMap, TILEFLAG_PROTECTIONZONE

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORLD = os.path.join(ROOT, "data", "world")
OTB_PATH = os.path.join(ROOT, "data", "items", "items.otb")

MAP_W = MAP_H = 256
GROUND_Z = 7           # piso donde se camina
ROOF_Z = 6             # los techos van en el piso de arriba

CENTER_X = CENTER_Y = 128
TEMPLE = (CENTER_X, CENTER_Y + 4, GROUND_Z)

# --- Radios del terreno, medidos desde el centro del mapa ---
GRASS_R = 52
BEACH_R = 56
SHALLOW_R = 60
WATER_R = 66

# --- Ids de item (verificados contra items.otb al generar) ---
GRASS = 4526
SAND = 231
SHALLOW = 4608
WATER = 493
PAVEMENT = 724          # calles y plaza
STONE_TILE = 424        # suelo interior de los edificios
DIRT = 351              # senderos de tierra

WALL_H = 1050           # muro este-oeste
WALL_V = 1049           # muro norte-sur
WALL_NW = 1051          # esquina noroeste
WALL_SE = 1053          # esquina sureste
# Puertas normales, no de casa: las de casa (6255/6257) solo se abren en
# tiles pertenecientes a una casa, y estos edificios no lo son. El script
# data/scripts/actions/others/doors.lua las abre usando las tablas de
# data/global.lua, donde 6250 y 6253 estan en closedDoors.
DOOR_H = 6253           # puerta en muro este-oeste
DOOR_V = 6250           # puerta en muro norte-sur
WINDOW_H = 6444
WINDOW_V = 6445

ROOF_FILL = 920
ROOF_N = 921            # borde norte del techo
ROOF_W = 922            # borde oeste del techo
ROOF_NW = 923

STREET_LAMP = 1479
WALL_LAMP = 2038        # lit wall lamp
WELL = 1368
TABLE = 1627
COUNTER = 1618
BED_HEAD = 1760
BED_FOOT = 1761
CRATE = 1739
BARREL = 1770

TREE = 6180
TREE_ALT = 6181
FIR = 2700
SMALL_FIR = 2768
BUSH = 2767
ROCK = 4456
FLOWERS = 108
GRASS_TUFT = (6216, 6217, 6218, 6219)

# Edificios de la aldea: (x, y, ancho, alto, lado_puerta, tipo)
BUILDINGS = [
    (122, 114, 13, 8, "S", "temple"),
    (108, 121, 9, 7, "E", "house"),
    (140, 121, 9, 7, "W", "house"),
    (108, 137, 9, 7, "N", "house"),
    (140, 137, 9, 7, "N", "house"),
    (117, 139, 10, 7, "N", "shop"),
    (130, 139, 10, 7, "N", "inn"),
]

# Zonas de aparicion de monstruos, lejos de la plaza
SPAWNS = [
    (104, 104, 5, [("Rat", 0, 0), ("Rat", 2, 1), ("Rabbit", -2, 2)]),
    (152, 108, 5, [("Wolf", 0, 0), ("Spider", 2, -1)]),
    (110, 156, 5, [("Troll", 0, 0), ("Rat", 3, 2)]),
    (150, 152, 6, [("Wolf", 0, 0), ("Spider", -2, 2), ("Rabbit", 2, 2)]),
]


def dist(x, y):
    return ((x - CENTER_X) ** 2 + (y - CENTER_Y) ** 2) ** 0.5


class Village:
    def __init__(self, seed=20260824):
        self.rng = random.Random(seed)
        self.db = ItemsDB(OTB_PATH)
        self.map = OTBMMap(
            MAP_W, MAP_H,
            description="Kzland - aldea inicial",
            spawn_file="kzland-spawn.xml",
            house_file="kzland-house.xml",
        )
        self.blocked = set()   # tiles ocupados por construccion o calle
        self._check_ids()

    def _check_ids(self):
        """Falla al generar, no dentro del juego, si un id no es lo esperado."""
        for item_id in (GRASS, SAND, SHALLOW, WATER, PAVEMENT, STONE_TILE, DIRT):
            self.db.require(item_id, ground=True)
        for item_id in (WALL_H, WALL_V, WALL_NW, WALL_SE):
            self.db.require(item_id, ground=False, blocks=True)
        for item_id in (ROOF_N, ROOF_W, ROOF_NW):
            self.db.require(item_id, ground=False)
        self.db.require(ROOF_FILL, ground=True)
        for item_id in (DOOR_H, DOOR_V, WINDOW_H, WINDOW_V):
            self.db.require(item_id, ground=False)

    # ---------- terreno ----------

    def build_terrain(self):
        for y in range(MAP_H):
            for x in range(MAP_W):
                # borde irregular para que la costa no sea un circulo perfecto
                wobble = self.rng.uniform(-1.6, 1.6)
                d = dist(x, y) + wobble
                if d < GRASS_R:
                    self.map.set_ground(x, y, GROUND_Z, GRASS)
                elif d < BEACH_R:
                    self.map.set_ground(x, y, GROUND_Z, SAND)
                elif d < SHALLOW_R:
                    self.map.set_ground(x, y, GROUND_Z, SHALLOW)
                elif d < WATER_R:
                    self.map.set_ground(x, y, GROUND_Z, WATER)

    # ---------- calles ----------

    def build_roads(self):
        plaza = range(CENTER_X - 6, CENTER_X + 7)
        for y in range(CENTER_Y - 6, CENTER_Y + 7):
            for x in plaza:
                self.map.set_ground(x, y, GROUND_Z, PAVEMENT)
                self.map.tile(x, y, GROUND_Z).flags = TILEFLAG_PROTECTIONZONE
                self.blocked.add((x, y))

        # dos calles principales que cruzan la aldea y salen al campo
        for offset in (-1, 0, 1):
            for n in range(CENTER_X - 34, CENTER_X + 35):
                for x, y in ((n, CENTER_Y + offset), (CENTER_X + offset, n)):
                    if dist(x, y) < GRASS_R - 1 and (x, y) not in self.blocked:
                        self.map.set_ground(x, y, GROUND_Z, PAVEMENT)
                        self.blocked.add((x, y))

        # senderos de tierra hacia las zonas de monstruos
        for cx, cy, _, _ in SPAWNS:
            self._path(CENTER_X, CENTER_Y, cx, cy)

    def _path(self, x0, y0, x1, y1):
        x, y = x0, y0
        while (x, y) != (x1, y1):
            if x != x1:
                x += 1 if x1 > x else -1
            elif y != y1:
                y += 1 if y1 > y else -1
            if (x, y) in self.blocked or dist(x, y) >= GRASS_R:
                continue
            self.map.set_ground(x, y, GROUND_Z, DIRT)
            self.blocked.add((x, y))

    # ---------- edificios ----------

    def build_buildings(self):
        for x, y, w, h, door_side, kind in BUILDINGS:
            self._building(x, y, w, h, door_side, kind)

    def _building(self, bx, by, w, h, door_side, kind):
        x1, y1 = bx + w - 1, by + h - 1
        door = self._door_position(bx, by, w, h, door_side)
        window = self._window_position(bx, by, w, h, door_side)

        for y in range(by, y1 + 1):
            for x in range(bx, x1 + 1):
                self.map.set_ground(x, y, GROUND_Z, STONE_TILE)
                self.blocked.add((x, y))
                edge_top, edge_bottom = y == by, y == y1
                edge_left, edge_right = x == bx, x == x1
                if not (edge_top or edge_bottom or edge_left or edge_right):
                    continue

                if (x, y) == door:
                    self.map.add_item(x, y, GROUND_Z,
                                      DOOR_H if door_side in "NS" else DOOR_V)
                    continue
                if (x, y) == window:
                    self.map.add_item(x, y, GROUND_Z,
                                      WINDOW_H if door_side in "NS" else WINDOW_V)
                    continue

                if edge_top and edge_left:
                    piece = WALL_NW
                elif edge_bottom and edge_right:
                    piece = WALL_SE
                elif edge_top or edge_bottom:
                    piece = WALL_H
                else:
                    piece = WALL_V
                self.map.add_item(x, y, GROUND_Z, piece)

        # Anillo despejado alrededor del edificio: la decoracion se genera
        # despues y un arbol delante de la puerta dejaria el interior
        # inaccesible.
        for y in range(by - 1, y1 + 2):
            for x in range(bx - 1, x1 + 2):
                self.blocked.add((x, y))

        self._roof(bx, by, w, h)
        self._furnish(bx, by, w, h, kind)

        if kind == "temple":
            for y in range(by, y1 + 1):
                for x in range(bx, x1 + 1):
                    self.map.tile(x, y, GROUND_Z).flags = TILEFLAG_PROTECTIONZONE

    @staticmethod
    def _door_position(bx, by, w, h, side):
        if side == "N":
            return (bx + w // 2, by)
        if side == "S":
            return (bx + w // 2, by + h - 1)
        if side == "W":
            return (bx, by + h // 2)
        return (bx + w - 1, by + h // 2)

    @staticmethod
    def _window_position(bx, by, w, h, side):
        # la ventana va en el mismo muro que la puerta, corrida un par de tiles
        if side in "NS":
            y = by if side == "N" else by + h - 1
            return (bx + w // 2 + 2, y)
        x = bx if side == "W" else bx + w - 1
        return (x, by + h // 2 + 2)

    def _roof(self, bx, by, w, h):
        for y in range(by, by + h):
            for x in range(bx, bx + w):
                if x == bx and y == by:
                    piece = ROOF_NW
                elif y == by:
                    piece = ROOF_N
                elif x == bx:
                    piece = ROOF_W
                else:
                    piece = ROOF_FILL
                self.map.set_ground(x, y, ROOF_Z, piece)

    def _furnish(self, bx, by, w, h, kind):
        inside = [(x, y)
                  for y in range(by + 1, by + h - 1)
                  for x in range(bx + 1, bx + w - 1)]
        if not inside:
            return

        # lamparas de pared para que el interior no quede a oscuras
        self.map.add_item(bx + 1, by + 1, GROUND_Z, WALL_LAMP)
        self.map.add_item(bx + w - 2, by + 1, GROUND_Z, WALL_LAMP)

        if kind == "house":
            self.map.add_item(bx + 1, by + h - 2, GROUND_Z, BED_HEAD)
            self.map.add_item(bx + 2, by + h - 2, GROUND_Z, BED_FOOT)
            self.map.add_item(bx + w - 2, by + h - 2, GROUND_Z, TABLE)
        elif kind == "shop":
            for x in range(bx + 2, bx + w - 2):
                self.map.add_item(x, by + 2, GROUND_Z, COUNTER)
            self.map.add_item(bx + 1, by + h - 2, GROUND_Z, CRATE)
            self.map.add_item(bx + w - 2, by + h - 2, GROUND_Z, BARREL)
        elif kind == "inn":
            self.map.add_item(bx + 2, by + 2, GROUND_Z, TABLE)
            self.map.add_item(bx + w - 3, by + 2, GROUND_Z, TABLE)
            self.map.add_item(bx + 1, by + h - 2, GROUND_Z, BED_HEAD)
            self.map.add_item(bx + 2, by + h - 2, GROUND_Z, BED_FOOT)
            self.map.add_item(bx + w - 2, by + h - 2, GROUND_Z, BARREL)

    # ---------- plaza y decoracion ----------

    def decorate_plaza(self):
        self.map.add_item(CENTER_X, CENTER_Y - 3, GROUND_Z, WELL)
        for dx, dy in ((-5, -5), (5, -5), (-5, 5), (5, 5)):
            self.map.add_item(CENTER_X + dx, CENTER_Y + dy, GROUND_Z, STREET_LAMP)

        # farolas a lo largo de las dos calles principales
        for n in range(CENTER_X - 30, CENTER_X + 31, 6):
            for x, y in ((n, CENTER_Y - 2), (CENTER_X - 2, n)):
                if dist(x, y) < GRASS_R - 2 and (x, y) not in self.blocked:
                    self.map.add_item(x, y, GROUND_Z, STREET_LAMP)
                    self.blocked.add((x, y))

    def decorate_nature(self):
        for y in range(MAP_H):
            for x in range(MAP_W):
                if (x, y) in self.blocked:
                    continue
                d = dist(x, y)
                if d >= GRASS_R - 1:
                    continue
                roll = self.rng.random()
                # cerca de la aldea solo hierba suelta; el bosque queda fuera
                if d < 22:
                    if roll < 0.05:
                        self.map.add_item(x, y, GROUND_Z,
                                          self.rng.choice(GRASS_TUFT))
                    elif roll < 0.06:
                        self.map.add_item(x, y, GROUND_Z, FLOWERS)
                    continue
                if roll < 0.06:
                    self.map.add_item(x, y, GROUND_Z,
                                      self.rng.choice((TREE, TREE_ALT, FIR)))
                elif roll < 0.09:
                    self.map.add_item(x, y, GROUND_Z,
                                      self.rng.choice((BUSH, SMALL_FIR)))
                elif roll < 0.11:
                    self.map.add_item(x, y, GROUND_Z, ROCK)
                elif roll < 0.16:
                    self.map.add_item(x, y, GROUND_Z,
                                      self.rng.choice(GRASS_TUFT))

    # ---------- salida ----------

    def write(self):
        self.map.add_town(1, "Kzland", *TEMPLE)
        self.map.save(os.path.join(WORLD, "kzland.otbm"))
        self._write_spawns()
        with open(os.path.join(WORLD, "kzland-house.xml"), "w",
                  encoding="utf-8", newline="\n") as fh:
            fh.write('<?xml version="1.0" encoding="UTF-8"?>\n<houses />\n')

    def _write_spawns(self):
        lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<spawns>"]
        for cx, cy, radius, monsters in SPAWNS:
            lines.append('\t<spawn centerx="{}" centery="{}" centerz="{}" radius="{}">'
                         .format(cx, cy, GROUND_Z, radius))
            for name, dx, dy in monsters:
                lines.append('\t\t<monster name="{}" x="{}" y="{}" spawntime="{}" />'
                             .format(name, dx, dy, 60))
            lines.append("\t</spawn>")
        lines.append("</spawns>")
        with open(os.path.join(WORLD, "kzland-spawn.xml"), "w",
                  encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines) + "\n")

    def used_item_ids(self):
        ids = set()
        for tile in self.map.tiles.values():
            if tile.ground is not None:
                ids.add(tile.ground)
            ids.update(tile.items)
        return ids


def main():
    village = Village()
    village.build_terrain()
    village.build_roads()
    village.build_buildings()
    village.decorate_plaza()
    village.decorate_nature()
    village.write()

    print("tiles      : {}".format(len(village.map.tiles)))
    print("templo     : {}".format(TEMPLE))
    print("ids usados : {}".format(len(village.used_item_ids())))
    ids_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "used_item_ids.txt")
    with open(ids_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(str(i) for i in sorted(village.used_item_ids())) + "\n")
    print("ids en     : {}".format(ids_path))


if __name__ == "__main__":
    main()
