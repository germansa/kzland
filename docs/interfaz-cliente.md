# Editar los paneles del cliente

Guía para modificar la interfaz de OTClient en este proyecto: qué capas
existen, cómo quitar cosas sin romper el cliente y cómo diagnosticar cuando
algo falla.

Escrita después de romper el panel derecho y tardar bastante en entender por
qué. Las secciones marcadas con **⚠** son los errores concretos que ya se
cometieron; léelas antes de tocar nada.

---

## 1. Dónde vive el cliente

El cliente **no está en el repositorio**. Se instala aparte y su ruta está en
`CLIENT_PATH` del `.env` (por defecto `C:\kzland-client`).

Por eso los cambios se describen como datos en
[`tools/client_tweaks.py`](../tools/client_tweaks.py) y se aplican sobre una
instalación concreta. Así sobreviven a una reinstalación del cliente y se
pueden repetir en otra máquina.

```
python tools/client_tweaks.py            # aplica
python tools/client_tweaks.py --restore  # deshace
```

`--restore` barre todas las copias `.orig` bajo `modules/` y `mods/`, no las
listas del script. Es a propósito: si un módulo sale de una lista, su cambio
seguiría aplicado y no habría forma de revertirlo.

**Nunca edites los `.otmod` a mano.** Añade el módulo a la lista del script y
vuelve a aplicar; si no, el cambio queda sin versionar.

---

## 2. Las tres capas

La interfaz se quita a tres niveles distintos. Elige el más suave que resuelva
el problema.

| Capa | Dónde | Efecto | Cuándo usarla |
|---|---|---|---|
| **Botones** | ajuste `control_buttons` | Oculta un botón | El sistema existe y funciona, solo estorba |
| **Mini-ventanas** | `CharMiniWindows` en `config.otml` | Cierra una ventana por personaje | Ajuste puntual del jugador |
| **Módulos** | `interface.otmod` / `mods.otmod` | Elimina la funcionalidad entera | El servidor no implementa ese sistema |

### Capa 1 — botones

`game_mainpanel` mantiene `buttonConfigs` y `buttonOrder`, persistidos en el
ajuste `control_buttons`, y **trae interfaz gráfica propia** para mostrar,
ocultar y reordenar botones (`option_control_buttons.otui`). Es la vía menos
invasiva y no requiere tocar código.

Los botones se registran con
`modules.game_mainpanel.addToggleButton(id, descripcion, imagen, callback)`.

### Capa 2 — mini-ventanas

Cada panel del lateral es una `UIMiniWindow`. Su posición y estado se guardan
por personaje en el nodo `CharMiniWindows` de `config.otml`:

```
CharMiniWindows:
  Tester:
    buttons:
      parentId: gameRightPanel
      index: 2
```

### Capa 3 — módulos y mods

Dos cargadores distintos:

- **Módulos**: `modules/game_interface/interface.otmod`, lista `load-later`.
- **Mods**: `mods/client_mods/mods.otmod`, lista `load-later`.
  El bot/cavebot es un **mod** (`mods/game_bot`), no un módulo. Si buscas algo
  en `modules/` y no aparece, mira en `mods/`.

Algunos módulos además se cargan solos con `autoload: true` en su propio
`.otmod`, sin depender de que `game_interface` los liste. Para esos no basta
con quitarlos de `load-later`: hay que poner `autoload: false`. El script ya
lo hace con los que lo necesitan (`SELF_LOADING`).

---

## 3. ⚠ Antes de desactivar un módulo: buscar usos sin proteger

**Este es el error que rompió el panel derecho.**

Hay código del núcleo que usa otros módulos **sin comprobar si existen**. Al
desactivar uno de esos, salta un error de Lua que corta la inicialización de
la interfaz y el panel derecho se queda vacío, sin ningún mensaje visible en
pantalla.

Estas dependencias **no están declaradas en ningún `.otmod`**, así que revisar
dependencias declaradas no sirve de nada. Hay que buscarlas en el código:

```bash
cd "$CLIENT_PATH/modules"
grep -rn "modules\.game_XXXX\b" --include=*.lua . | grep -v "^\./game_XXXX/"
```

Y mirar cada resultado: si es `if modules.game_XXXX then` está protegido; si
es `modules.game_XXXX.algo()` directo, **no lo desactives** (o el código que lo
llama debe estar muerto, y hay que demostrarlo).

### Módulos que NO se pueden desactivar

| Módulo | Quién lo usa sin proteger |
|---|---|
| `game_healthcircle` | `game_interface/widgets/statsbar.lua` en `OnGameStart()`, y `client_options/data_options.lua` |
| `game_attachedeffects` | `game_outfit/outfit.lua` |
| `game_shop` | `game_mainpanel.toggleStore()`, cuando el servidor no envía `GameIngameStore` — nuestro caso |

Son contenido de Tibia que preferiríamos quitar, pero el cliente no lo tolera.

---

## 4. ⚠ No borres el estado de la interfaz

Regla de `corelib/ui/uiminiwindow.lua`, función `setupOnStart()`:

> Si una mini-ventana **no tiene ajustes guardados**, el cliente **no la abre**.
> La única excepción es `battleWindow`.

No existe "abierta por defecto". Consecuencias:

- Borrar el nodo `CharMiniWindows` deja todas las ventanas cerradas.
- La barra de botones **también es una mini-ventana** (`buttons`), así que al
  borrarla desaparece el propio medio para reabrir las demás.
- Borrar `config.otml` o el perfil entero (`%APPDATA%\otcr`) tiene el mismo
  efecto, y **no se arregla solo** al reiniciar.

Si hay que tocar `config.otml`, haz copia antes. Si el panel ya está vacío,
restaura una copia que conserve `CharMiniWindows`.

Cuando un personaje nuevo no tiene ajustes, el cliente **copia los de otro
personaje** (líneas 134-142) para no dejar las ventanas descolocadas. Si el
estado copiado está roto, el personaje nuevo hereda el problema.

---

## 5. Anatomía del panel

Definido en `modules/game_interface/gameinterface.otui`. De derecha a
izquierda:

```
[ gameRightPanel 176 ]  <- mini-ventanas (inventario, minimapa, VIP...)
[ gameRightExtraPanel 176 ]  <- 2a columna, oculta por defecto
[ gameRightActionPanel 36 ]
[ gameMapPanel ]  <- el mundo
```

`gameMainRightPanel` va anclado arriba a la derecha (alto 200) y contiene la
barra de botones. `gameRightPanel` cuelga justo debajo.

Los paneles con estado `$!on` colapsan a ancho 0; `gameRightPanel` no lo
declara, así que siempre mide 176.

### Modos de vista

`setupViewMode(mode)` tiene tres modos y **Ctrl+.** los cicla. El modo 2 hace
que el mapa ocupe todo y vuelve los paneles transparentes.

Ojo con esto: `setupViewMode` sale inmediatamente si el modo pedido es el
actual. Como `currentViewMode` empieza en 0 y `show()` llama a
`setupViewMode(0)`, **esa configuración nunca llega a ejecutarse** al entrar.
Los paneles se quedan con lo que dice el `.otui`.

El modo 2 se fuerza si `g_gameConfig.isExtendedViewUI()` es cierto, que sale
de `extended-view-ui` en `data/setup.otml` (aquí está en `false`).

---

## 6. Diagnóstico

**El log del cliente es lo primero que hay que mirar:**
`C:\kzland-client\otclient.log`

Los errores de Lua salen ahí y **no se ven en pantalla**. Un
`attempt to index field 'game_XXXX' (a nil value)` significa que se desactivó
un módulo del que algo depende sin proteger.

```bash
grep -E "LUA ERROR|attempt to index|Lua exception" "$CLIENT_PATH/otclient.log"
```

**Terminal del cliente: Ctrl+T.** Permite ejecutar Lua en vivo, que es la
forma rápida de inspeccionar widgets:

```lua
print(modules.game_interface.getRightPanel():getChildCount())
```

**Sonda por script:** `init.lua` ejecuta `otclientrc.lua` del directorio del
cliente si existe, y sirve para volcar estado al log. Aviso por experiencia:
ni `connect(g_game, {onGameStart=...})` ni `scheduleEvent` llegaron a
dispararse desde ese archivo, así que la terminal es más fiable.

**Cierra el cliente por su ventana, no matando el proceso.** Guarda su
configuración al salir; matarlo repetidamente deja estado a medias.

---

## 7. Otros puntos de configuración

| Qué | Dónde |
|---|---|
| Lista de servidores | `init.lua` → `Servers_init`. **Aquí** va nuestro servidor, no parcheando `config.otml`: si no, las entradas de ejemplo (`ip.net`, `login.php`) reaparecen en cada perfil nuevo |
| Discord, YouTube, "players online" | `init.lua` → `Services` |
| Viewport, extended view | `data/setup.otml` |
| Descarga de assets | `modules/client_assets/client_assets.lua` → `DEFAULT_CONFIG` |
| Hechizos que lista el cliente | `modules/gamelib/spells.lua` (192 hechizos de Tibia cableados) |

---

## 8. Estado actual

Desactivados: prey, imbuing, imbuement tracker, forge, wheel, cyclopedia,
taskboard, reward wall, proficiency, stash, store, blessings, highscore,
quick loot, tutorial, paperdolls, analyser, loot splitter, lista de hechizos,
skills, quest log + quest tracker, y el mod del bot/cavebot.

La lista viva está en `DISABLED_MODULES` y `DISABLED_MODS` de
[`tools/client_tweaks.py`](../tools/client_tweaks.py).

Pendiente conocido: faltan los sonidos (`/data/sounds/1310/`). Es un aviso
inofensivo; son 154 MB en el mismo repo de assets.
