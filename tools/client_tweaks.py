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
    "game_blessing",
    "game_highscore",
    "game_quickloot",
    "game_tutorial",
    # game_shop NO se desactiva: mainpanel.toggleStore() lo llama sin
    # comprobar cuando el servidor no envia GameIngameStore, que es
    # nuestro caso, y el boton Store del panel reventaria al pulsarlo.
    # extras cosmeticos del cliente
    "game_paperdolls",
    "game_analyser",
    "game_lootsplitter",
    # contenido de Tibia que definiremos nosotros
    "game_spelllist",
    "game_skills",
    # el registro de misiones y su rastreador; no hay quests todavia
    "game_questlog",
]

# Los mods viven en mods/ y los carga client_mods, no game_interface.
DISABLED_MODS = [
    # cavebot / bot de automatizacion completo
    "game_bot",
]

MODS_OTMOD = os.path.join("mods", "client_mods", "mods.otmod")

# Mods propios que se copian al cliente y se anaden al cargador. Viven en el
# repositorio para que si el cliente se reinstala no se pierdan.
OWN_MODS_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "client_mods")
OWN_MODS = ["kz_lighting"]

# Modulos que NO se deben desactivar aunque sean contenido de Tibia: hay
# codigo del nucleo que los usa sin comprobar si existen, asi que al faltar
# lanzan un error de Lua que corta la inicializacion de la interfaz y deja el
# panel derecho vacio.
#   game_healthcircle    -> game_interface/widgets/statsbar.lua (OnGameStart)
#                           y client_options/data_options.lua
#   game_attachedeffects -> game_outfit/outfit.lua
#   game_shop            -> game_mainpanel/mainpanel.lua (toggleStore)
# Ninguna de esas dependencias esta declarada en los .otmod, solo en el codigo,
# por lo que revisar dependencias declaradas no basta: hay que buscar
# "modules.<nombre>" en los modulos que se quedan.

# Modulos que se cargan solos por su propio autoload y no dependen de que
# game_interface los liste.
SELF_LOADING = [
    ("game_analyser", "analyser.otmod"),
    ("game_cyclopedia", "game_cyclopedia.otmod"),
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


def _strip_entries(path, names, undo, label):
    """Quita entradas de una lista load-later de un .otmod."""
    if not os.path.exists(path):
        raise SystemExit("no se encontro {}".format(path))

    if undo:
        return "{}: restaurado".format(label) if restore(path) \
            else "{}: sin cambios que deshacer".format(label)

    backup(path)
    with open(path, encoding="utf-8") as fh:
        lines = fh.readlines()

    keep, removed = [], 0
    for line in lines:
        entry = line.strip()
        if entry.startswith("- ") and entry[2:] in names:
            removed += 1
            continue
        keep.append(line)

    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.writelines(keep)
    return "{}: {} fuera de la carga".format(label, removed)


def apply_interface(client, undo):
    return _strip_entries(os.path.join(client, INTERFACE_OTMOD),
                          DISABLED_MODULES, undo, "paneles")


def apply_mods(client, undo):
    return _strip_entries(os.path.join(client, MODS_OTMOD),
                          DISABLED_MODS, undo, "mods")


def install_own_mods(client, undo):
    """Copia los mods del repositorio y los registra en el cargador."""
    loader = os.path.join(client, MODS_OTMOD)
    installed = 0

    for name in OWN_MODS:
        target = os.path.join(client, "mods", name)
        if undo:
            if os.path.isdir(target):
                shutil.rmtree(target)
                installed += 1
            continue
        source = os.path.join(OWN_MODS_SRC, name)
        if not os.path.isdir(source):
            raise SystemExit("falta el mod {} en {}".format(name, OWN_MODS_SRC))
        if os.path.isdir(target):
            shutil.rmtree(target)
        shutil.copytree(source, target)
        installed += 1

    if undo:
        return "mods propios: {} eliminados".format(installed)

    # registrar en la lista load-later, sin duplicar
    with open(loader, encoding="utf-8") as fh:
        text = fh.read()
    added = 0
    for name in OWN_MODS:
        if "- {}".format(name) not in text:
            text = text.rstrip("\n") + "\n    - {}\n".format(name)
            added += 1
    if added:
        with open(loader, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)

    return "mods propios: {} instalados".format(installed)


def restore_all(client):
    """Deshace cualquier cambio con copia .orig, este o no en las listas.

    Barrer el disco en vez de recorrer las listas evita dejar cambios
    huerfanos cuando un modulo deja de estar en ellas.
    """
    restored = 0
    for base in ("modules", "mods"):
        root = os.path.join(client, base)
        for current, _dirs, files in os.walk(root):
            for name in files:
                if name.endswith(".orig"):
                    target = os.path.join(current, name[:-len(".orig")])
                    if restore(target):
                        restored += 1
    return "{} archivos restaurados".format(restored)


def apply_self_loading(client, undo):
    if undo:
        return "autoload: incluido en la restauracion"

    changed = 0
    for folder, filename in SELF_LOADING:
        path = os.path.join(client, "modules", folder, filename)
        if not os.path.exists(path):
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
    return "autoload: {} modulos desactivados".format(changed)


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
    if args.restore:
        print(install_own_mods(client, True))
        print(restore_all(client))
        print("hecho. reinicia el cliente para ver el cambio.")
        return 0

    print(apply_interface(client, args.restore))
    print(apply_mods(client, args.restore))
    print(install_own_mods(client, args.restore))
    print(apply_self_loading(client, args.restore))
    print("hecho. reinicia el cliente para ver el cambio.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
