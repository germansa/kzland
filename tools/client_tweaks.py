"""Ajusta la interfaz del cliente OTClient para este proyecto.

El cliente se instala fuera del repositorio, asi que sus modificaciones no
quedarian versionadas. Este script las describe como datos y las aplica sobre
una instalacion concreta, de modo que se puedan repetir si el cliente se
reinstala o se monta en otra maquina.

Que hace: dejar de cargar los paneles de sistemas que este servidor no
implementa (prey, imbuing, forge, cyclopedia, ...) mas la lista de hechizos y
el panel de skills, que son contenido de Tibia.

No borra nada: guarda una copia .orig la primera vez y desactiva la carga del
modulo, asi que se puede volver atras.

Uso:
    python tools/client_tweaks.py              # aplica
    python tools/client_tweaks.py --restore    # deshace
    python tools/client_tweaks.py --client D:\\otra\\ruta

La ruta por defecto sale de CLIENT_PATH en el .env del proyecto.
"""

import argparse
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CLIENT = r"C:\kzland-client"

# Paneles que se dejan de cargar. Los tres primeros grupos son sistemas de
# Tibia 12/13 que el servidor no implementa; los dos ultimos son contenido de
# Tibia que el proyecto va a definir por su cuenta.
DISABLED_MODULES = [
    # sistemas no implementados por el servidor
    "game_prey",
    "game_imbuing",
    "game_imbuementtracker",
    "game_forge",
    "game_wheel",
    "game_cyclopedia",
    "game_taskboard",
    "game_rewardwall",
    "game_proficiency",
    "game_stash",
    "game_store",
    "game_shop",
    "game_blessing",
    "game_highscore",
    "game_quickloot",
    "game_tutorial",
    # extras cosmeticos del cliente
    "game_paperdolls",
    "game_attachedeffects",
    "game_healthcircle",
    "game_analyser",
    "game_lootsplitter",
    # contenido de Tibia que definiremos nosotros
    "game_spelllist",
    "game_skills",
]

# Modulos que se cargan solos por su propio autoload y no dependen de que
# game_interface los liste.
SELF_LOADING = [
    ("game_analyser", "analyser.otmod"),
    ("game_cyclopedia", "game_cyclopedia.otmod"),
    ("game_healthcircle", "game_healthcircle.otmod"),
    ("game_lootsplitter", "lootsplitter.otmod"),
    ("game_proficiency", "proficiency.otmod"),
    ("game_taskboard", "tasks.otmod"),
]

INTERFACE_OTMOD = os.path.join("modules", "game_interface", "interface.otmod")


def client_path_from_env():
    env_file = os.path.join(ROOT, ".env")
    if os.path.exists(env_file):
        with open(env_file, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if line.startswith("CLIENT_PATH="):
                    value = line.split("=", 1)[1].strip()
                    if value:
                        return value
    return DEFAULT_CLIENT


def backup(path):
    """Guarda el original una sola vez; las siguientes pasadas no lo pisan."""
    original = path + ".orig"
    if not os.path.exists(original):
        shutil.copy2(path, original)


def restore(path):
    original = path + ".orig"
    if os.path.exists(original):
        shutil.copy2(original, path)
        os.remove(original)
        return True
    return False


def apply_interface(client, undo):
    path = os.path.join(client, INTERFACE_OTMOD)
    if not os.path.exists(path):
        raise SystemExit("no se encontro {}".format(path))

    if undo:
        return "restaurado" if restore(path) else "sin cambios que deshacer"

    backup(path)
    with open(path, encoding="utf-8") as fh:
        lines = fh.readlines()

    keep, removed = [], 0
    for line in lines:
        entry = line.strip()
        if entry.startswith("- ") and entry[2:] in DISABLED_MODULES:
            removed += 1
            continue
        keep.append(line)

    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.writelines(keep)
    return "{} paneles fuera de la carga".format(removed)


def apply_self_loading(client, undo):
    changed = 0
    for folder, filename in SELF_LOADING:
        path = os.path.join(client, "modules", folder, filename)
        if not os.path.exists(path):
            continue
        if undo:
            if restore(path):
                changed += 1
            continue
        backup(path)
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        updated = re.sub(r"(?m)^(\s*)autoload:\s*true\s*$",
                         r"\1autoload: false", text)
        if updated != text:
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(updated)
            changed += 1
    return "{} modulos con autoload {}".format(
        changed, "restaurado" if undo else "desactivado")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", default=None,
                        help="ruta de la instalacion del cliente")
    parser.add_argument("--restore", action="store_true",
                        help="deshace los cambios usando las copias .orig")
    args = parser.parse_args()

    client = args.client or client_path_from_env()
    if not os.path.isdir(client):
        raise SystemExit("la ruta del cliente no existe: {}".format(client))

    print("cliente: {}".format(client))
    print(apply_interface(client, args.restore))
    print(apply_self_loading(client, args.restore))
    print("hecho. reinicia el cliente para ver el cambio.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
