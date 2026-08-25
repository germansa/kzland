"""Genera sprites con la API de PixelLab usando los sprites del cliente como
referencia de estilo.

La ventaja sobre la interfaz web no es el prompt, sino los parametros: la API
expone justo los que fallaban al generar a mano.

    view    = high top-down            <- el angulo de camara de Tibia
    outline = single color black outline
    shading = flat shading
    detail  = low detail
    image_size 32x32

Ademas admite una imagen de paleta (color_image) y referencias por direccion,
asi que se le puede pasar un sprite real extraido del cliente.

Necesita un token en el .env del proyecto:

    PIXELLAB_TOKEN=...

Se saca en https://api.pixellab.ai/mcp . La generacion consume creditos de esa
cuenta, asi que cada llamada cuesta dinero: el script imprime el saldo antes y
despues.

Uso:
    python tools/pixellab.py saldo
    python tools/pixellab.py crear "plain villager, brown tunic" --salida pj
    python tools/pixellab.py estilo "plain villager" --ref referencia.png
"""

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://api.pixellab.ai/v2"

# Ajustes que reproducen el aspecto de Tibia. Ver docs/interfaz-cliente.md y
# el analisis de los sprites reales en tools/extract_sprites.py.
TIBIA_LOOK = {
    "view": "high top-down",
    "outline": "single color black outline",
    "shading": "flat shading",
    "detail": "low detail",
    "image_size": {"width": 32, "height": 32},
}


# Nombres admitidos para la clave en el .env
TOKEN_KEYS = ("PIXELLAB_TOKEN", "PIXELART_SECRET", "PIXELLAB_SECRET")


def token():
    env_file = os.path.join(ROOT, ".env")
    if os.path.exists(env_file):
        with open(env_file, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                for key in TOKEN_KEYS:
                    if line.startswith(key + "="):
                        value = line.split("=", 1)[1].strip()
                        if value:
                            return value
    raise SystemExit(
        "falta la clave de PixelLab en el .env del proyecto.\n"
        "Se acepta cualquiera de: {}\n"
        "Se obtiene en https://api.pixellab.ai/mcp".format(", ".join(TOKEN_KEYS)))


def call(path, payload=None, method="POST"):
    url = API + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": "Bearer " + token(),
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", "replace")[:600]
        raise SystemExit("error {} en {}\n{}".format(err.code, path, detail))


def encode_image(path):
    with open(path, "rb") as fh:
        return {"type": "base64",
                "base64": base64.b64encode(fh.read()).decode(),
                "format": "png"}


def save_images(node, prefix, saved=None):
    """Recorre la respuesta y guarda cualquier imagen base64 que encuentre."""
    if saved is None:
        saved = []
    if isinstance(node, dict):
        if node.get("base64"):
            name = "{}_{}.png".format(prefix, len(saved))
            with open(name, "wb") as fh:
                fh.write(base64.b64decode(node["base64"]))
            saved.append(name)
        else:
            for key, value in node.items():
                save_images(value, "{}_{}".format(prefix, key)
                            if isinstance(value, (dict, list)) else prefix, saved)
    elif isinstance(node, list):
        for item in node:
            save_images(item, prefix, saved)
    return saved


def wait_for(character_id, prefix, timeout=600):
    """La creacion de personajes es asincrona; se sondea hasta que termina."""
    started = time.time()
    while time.time() - started < timeout:
        info = call("/characters/" + character_id, method="GET")
        status = info.get("status") or info.get("state")
        print("   estado: {}".format(status))
        if status in ("completed", "succeeded", "done"):
            return save_images(info, prefix)
        if status in ("failed", "error"):
            raise SystemExit("la generacion fallo: " + json.dumps(info)[:400])
        time.sleep(10)
    raise SystemExit("tiempo de espera agotado")


def cmd_saldo(_args):
    print(json.dumps(call("/balance", method="GET"), indent=2))


def cmd_crear(args):
    payload = dict(TIBIA_LOOK)
    payload["description"] = args.descripcion
    if args.paleta:
        payload["color_image"] = encode_image(args.paleta)
        # Forzar los colores copia la paleta tal cual, incluido el pelo o la
        # ropa del sprite de referencia; por defecto se deja como sugerencia.
        payload["force_colors"] = bool(args.forzar_paleta)
    if args.referencia:
        payload["directions"] = {"south": encode_image(args.referencia)}
    if args.seed is not None:
        payload["seed"] = args.seed

    print("saldo antes:", call("/balance", method="GET"))
    res = call("/create-character-with-4-directions", payload)
    character_id = res.get("character_id")
    print("personaje {} en marcha...".format(character_id))
    files = wait_for(character_id, args.salida)
    print("guardado:", ", ".join(files) if files else "(sin imagenes)")
    print("saldo despues:", call("/balance", method="GET"))


def cmd_sprite(args):
    """Un solo sprite con bitforge: admite imagen de estilo y es lo mas barato."""
    payload = {
        "description": args.descripcion,
        "image_size": {"width": args.tam, "height": args.tam},
        "view": TIBIA_LOOK["view"],
        "outline": TIBIA_LOOK["outline"],
        "shading": TIBIA_LOOK["shading"],
        "detail": TIBIA_LOOK["detail"],
        "direction": args.direccion,
        "no_background": True,
    }
    if args.negativo:
        payload["negative_description"] = args.negativo
    if args.estilo:
        payload["style_image"] = encode_image(args.estilo)
        payload["style_strength"] = args.fuerza
    if args.paleta:
        payload["color_image"] = encode_image(args.paleta)
    if args.seed is not None:
        payload["seed"] = args.seed

    res = call("/create-image-bitforge", payload)
    files = save_images(res, args.salida)
    print("guardado:", ", ".join(files) if files else json.dumps(res)[:300])
    if "usage" in res:
        print("consumo:", res["usage"])


def cmd_estilo(args):
    payload = {
        "description": args.descripcion,
        "style_images": [encode_image(p) for p in args.ref],
    }
    if args.estilo_desc:
        payload["style_description"] = args.estilo_desc
    if args.seed is not None:
        payload["seed"] = args.seed
    payload["no_background"] = True

    res = call("/generate-with-style-v2", payload)
    files = save_images(res, args.salida)
    print("guardado:", ", ".join(files) if files else json.dumps(res)[:300])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("saldo", help="consulta el saldo de creditos")

    p = sub.add_parser("crear", help="personaje con 4 direcciones")
    p.add_argument("descripcion")
    p.add_argument("--salida", default="pj")
    p.add_argument("--paleta", help="PNG del que tomar la paleta")
    p.add_argument("--forzar-paleta", dest="forzar_paleta", action="store_true",
                   help="copia los colores tal cual en vez de sugerirlos")
    p.add_argument("--referencia", help="PNG de referencia para la vista sur")
    p.add_argument("--seed", type=int)

    p = sub.add_parser("sprite", help="un solo sprite (bitforge), lo mas barato")
    p.add_argument("descripcion")
    p.add_argument("--negativo", help="que evitar")
    p.add_argument("--estilo", help="PNG de referencia de estilo")
    p.add_argument("--fuerza", type=int, default=60, help="0-100, peso del estilo")
    p.add_argument("--paleta", help="PNG del que tomar la paleta")
    p.add_argument("--direccion", default="south")
    p.add_argument("--tam", type=int, default=32)
    p.add_argument("--salida", default="sprite")
    p.add_argument("--seed", type=int)

    p = sub.add_parser("estilo", help="generar copiando el estilo de imagenes")
    p.add_argument("descripcion")
    p.add_argument("--ref", nargs="+", required=True, help="1 a 4 PNG de estilo")
    p.add_argument("--estilo-desc", dest="estilo_desc")
    p.add_argument("--salida", default="estilo")
    p.add_argument("--seed", type=int)

    args = parser.parse_args()
    {"saldo": cmd_saldo, "crear": cmd_crear,
     "sprite": cmd_sprite, "estilo": cmd_estilo}[args.cmd](args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
