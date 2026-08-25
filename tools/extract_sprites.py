"""Extrae hojas de sprites del cliente a PNG, para usarlas de referencia.

Los assets del cliente vienen en .bmp.lzma con una cabecera propia de CipSoft:

    [0x00, X)        relleno de bytes nulos, longitud variable
    [X, X+5)         la constante 70 0A FA 80 24
    [X+5, ...)       tamano del archivo LZMA como entero de 7 bits
    luego            props LZMA (1) + tamano de diccionario (4) + tamano
                     comprimido (8, se ignora) y el stream LZMA1 en crudo

Formato tomado de SpriteAppearances::loadSpriteSheet en el codigo de OTClient
(src/client/spriteappearances.cpp). Dentro sale un BMP de 384x384 a 32 bpp,
en BGRA y con el magenta 0xFF00FF como color transparente.

Uso:
    python tools/extract_sprites.py <indice_hoja> [destino.png]
    python tools/extract_sprites.py --buscar     # lista hojas con personajes

La ruta del cliente sale de CLIENT_PATH en el .env.
"""

import argparse
import json
import lzma
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAGENTA = (255, 0, 255)


def client_path():
    env_file = os.path.join(ROOT, ".env")
    if os.path.exists(env_file):
        with open(env_file, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if line.startswith("CLIENT_PATH="):
                    value = line.split("=", 1)[1].strip()
                    if value:
                        return value
    return r"C:\kzland-client"


def assets_dir(version="1310"):
    return os.path.join(client_path(), "data", "things", version)


def decompress(path):
    """Devuelve el BMP contenido en un .bmp.lzma del cliente."""
    raw = open(path, "rb").read()

    i = 0
    while raw[i] == 0x00:          # relleno
        i += 1
    i += 5                         # constante 70 0A FA 80 24
    while raw[i] & 0x80:           # tamano en entero de 7 bits
        i += 1
    i += 1

    lclppb = raw[i]
    i += 1
    lc = lclppb % 9
    remainder = lclppb // 9
    lp = remainder % 5
    pb = remainder // 5

    dict_size = int.from_bytes(raw[i:i + 4], "little")
    i += 4
    i += 8                         # tamano comprimido de CIP, no hace falta

    filters = [{"id": lzma.FILTER_LZMA1, "dict_size": dict_size,
                "lc": lc, "lp": lp, "pb": pb}]
    return lzma.LZMADecompressor(format=lzma.FORMAT_RAW,
                                 filters=filters).decompress(raw[i:])


def to_image(bmp):
    """Convierte el BMP crudo en una imagen RGBA con el fondo transparente."""
    from PIL import Image

    width, height = struct.unpack_from("<ii", bmp, 18)
    offset = struct.unpack_from("<I", bmp, 10)[0]
    pixels = bmp[offset:offset + width * abs(height) * 4]

    img = Image.frombytes("RGBA", (width, abs(height)), pixels)
    b, g, r, a = img.split()
    img = Image.merge("RGBA", (r, g, b, a))
    if height > 0:
        img = img.transpose(Image.FLIP_TOP_BOTTOM)   # los BMP van al reves

    # el magenta es el color reservado para transparencia
    data = [(0, 0, 0, 0) if px[:3] == MAGENTA else px for px in img.getdata()]
    img.putdata(data)
    return img


def sheets(version="1310"):
    catalog = os.path.join(assets_dir(version), "catalog-content.json")
    with open(catalog, encoding="utf-8") as fh:
        return [c for c in json.load(fh) if c.get("type") == "sprite"]


def load(index, version="1310"):
    entry = sheets(version)[index]
    path = os.path.join(assets_dir(version), entry["file"])
    return to_image(decompress(path)), entry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", nargs="?", type=int, default=0)
    parser.add_argument("destino", nargs="?", default=None)
    parser.add_argument("--version", default="1310")
    args = parser.parse_args()

    img, entry = load(args.index, args.version)
    destino = args.destino or "hoja_{}.png".format(args.index)
    img.save(destino)
    print("hoja {} (sprites {}-{}) -> {}".format(
        args.index, entry["firstspriteid"], entry["lastspriteid"], destino))
    return 0


if __name__ == "__main__":
    sys.exit(main())
