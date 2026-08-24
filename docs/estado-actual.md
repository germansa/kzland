# Estado actual del proyecto

Instantánea de dónde está Kzland, para poder decidir el plan de desarrollo.
Fecha: 24 de agosto de 2026 · 12 commits.

**Resumen en una línea:** la infraestructura está montada y probada; el
contenido de juego está prácticamente vacío a propósito.

---

## 1. Lo que funciona hoy

Todo esto está verificado, no supuesto:

| Pieza | Estado |
|---|---|
| Servidor | Forgotten Server **1.7**, compilado y arrancando sin un solo aviso |
| Base de datos | MariaDB 11.8 LTS, 32 tablas, esquema cargado |
| Protocolo | **13.10** (fijo en `src/definitions.h`, no configurable) |
| Cliente | OTClient Redemption 4.1 con assets 13.10 instalados |
| Login | Verificado de extremo a extremo por HTTP y entrando al juego |
| Mapa | Aldea de 118 KB cargando en 0,004 s |
| Compilación | `build.ps1` un solo comando, probado también ante errores |
| Repositorio | `github.com/germansa/kzland`, SSH configurado |

**Cuenta de prueba:** `admin@kzland.local` / `kzland123` (es email, no nombre
de cuenta). Personajes `Tester` (jugador) y `God` (grupo 6, comandos de GM).
Datos en el `.env`, que está gitignored.

---

## 2. Contenido de juego

Aquí está el verdadero estado del proyecto:

| Sistema | Cantidad | Nota |
|---|---|---|
| Vocaciones | **1** | Solo `None`, el mínimo que exige el motor |
| Ítems | **97** | Solo los que el core referencia por ID fijo, más los del mapa |
| Criaturas | **5** | rat, rabbit, wolf, spider, troll — prestados de Tibia, sin loot |
| Hechizos | **0** | |
| Acciones | **0** | |
| NPCs | **0** | El framework `npcsystem` sí está |
| Outfits | **2** | Aldeano masculino y femenino |
| Monturas | **0** | |
| Quests | **0** | |

### El mapa

Isla de césped de ~96 tiles en un mapa de 256x256, un solo piso (z=7).

- **Aldea**: plaza empedrada con pozo y farolas en zona protegida, templo,
  4 casas, una tienda y una posada. Cada edificio con paredes de piedra,
  puerta funcional, ventana, techo en el piso superior y lámparas dentro.
- **Alrededores**: bosque, arbustos, rocas, playa de arena y agua.
- **Respawn**: `128,132,7`, en la plaza.
- **4 puntos de spawn** de monstruos, fuera del pueblo.

El mapa **se genera por código** (`tools/build_village.py`), no a mano, así que
es reproducible. Sigue siendo un `.otbm` normal y se puede abrir en RME.

---

## 3. Lo que hay de motor (no tocar sin motivo)

Estos sistemas están vacíos de contenido pero **operativos**, listos para
colgarles lo nuestro:

- `data/scripts/` — actions, creaturescripts (login, logout, muerte),
  movements (ahogarse, decay), globalevents, spells, weapons, talkactions.
- `data/events/` — hooks del motor: `onLook`, `onMoveItem`, `onTargetCombat`…
- `data/lib/` — API base en Lua.
- **42 talkactions**: comandos de GM (`/create_item`, `/teleport`,
  `/broadcast`). Muy útiles mientras se desarrolla.
- `data/npc/lib/npcsystem` — framework de diálogos de NPC.

---

## 4. Herramientas propias

En `tools/`, todas versionadas y documentadas:

| Herramienta | Para qué |
|---|---|
| `build_village.py` | Genera el mapa y sus spawns |
| `otbfile.py` / `otbmmap.py` | Leen y escriben `.otb` y `.otbm` |
| `itemsdb.py` | Consulta `items.otb`: grupo y flags de cada ítem |
| `sync_items_xml.py` | Declara en `items.xml` los ítems que usa el mapa |
| `client_tweaks.py` | Ajusta la interfaz del cliente y le instala mods |
| `client_mods/kz_lighting` | Oculta el indicador horario del minimapa |

Método para no inventar IDs: `items.otb` dice **qué es** cada ítem, el
`items.xml` original (en el historial de git) da los **nombres**, y lo que el
nombre no resuelve —qué pieza de muro va horizontal, cómo se arma un techo— se
dedujo **midiendo el mapa original de Tibia**. Cada ID se revalida al generar.

---

## 5. Decisiones ya tomadas

- **Sin ciclo de día y noche.** Se eliminó; la luz es de día fija. El cliente
  oscurece el subsuelo por su cuenta, así que las cuevas quedarán oscuras sin
  configurar nada.
- **Interfaz del cliente recortada**: fuera lista de hechizos, skills, quest
  log, cavebot y 19 paneles de sistemas que el servidor no implementa.
- **Sin sistema de casas** por ahora: los edificios de la aldea son escenografía
  con puertas normales, no casas comprables.
- **Rates**: las de por defecto de Forgotten Server, sin revisar.

---

## 6. Lo que bloquea de verdad

**Los sprites.** Cualquier ítem o criatura que se defina usará arte de Tibia,
porque los assets instalados son los del cliente oficial 13.10. Se puede
avanzar en toda la lógica sin resolverlo, pero el juego **seguirá pareciendo
Tibia** hasta que entre un artista o se compre un set.

Esto condiciona el orden del plan: conviene atacar primero lo que no depende
del arte (vocaciones, fórmulas, economía, mecánicas) y dejar para después lo
que sí (criaturas nuevas, equipo, decorados).

---

## 7. Pendientes conocidos

- **Sonidos del cliente sin instalar**: avisa al arrancar, es inofensivo. Son
  154 MB en el repo de assets.
- **`items.otb` sigue con los 15.101 ítems** a nivel binario. `items.xml` solo
  declara 97, así que el resto son inertes, pero para depurarlo del todo hace
  falta una herramienta gráfica (Item Editor / RME).
- **`key.pem` es la clave RSA de ejemplo** del repo de Forgotten Server.
  Regenerarla antes de exponer el servidor.
- **Las tablas de IDs de puertas en `data/global.lua`** siguen llenas de IDs de
  Tibia. Son datos de una mecánica que funciona; recortarlas es cosmético.
- **Sin cuevas todavía**: el mapa es un solo piso, así que la oscuridad del
  subsuelo no se ha podido probar en la práctica.

---

## 8. Qué falta definir antes de programar

No es borrar, es diseñar. Por orden de dependencia:

1. **Vocaciones** — qué clases hay, cómo suben, qué las diferencia. Todo lo
   demás cuelga de esto.
2. **Fórmulas de combate** — daño, defensa, velocidad de ataque.
3. **Ítems base** — armas, armaduras, consumibles; qué slots usa cada uno.
4. **Economía** — moneda, precios, cómo entra y sale oro del mundo.
5. **Criaturas** — estadísticas, comportamiento, loot.
6. **Progresión** — experiencia, niveles, qué se desbloquea.
7. **Contenido del mundo** — NPCs, quests, mazmorras.

Documentación relacionada: [interfaz-cliente.md](interfaz-cliente.md) para el
cliente, [../tools/README.md](../tools/README.md) para las herramientas del
mapa, y [../CLAUDE.md](../CLAUDE.md) para las reglas del proyecto.
