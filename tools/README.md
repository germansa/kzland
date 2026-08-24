# tools/

Utilidades para generar contenido del mapa sin abrir un editor grafico.

## Por que existen

El mapa se genera por codigo porque Remere's Map Editor es una aplicacion
de escritorio que se maneja a mano. Estas herramientas permiten versionar el
mapa como un script reproducible en vez de como un binario opaco.

El mapa sigue siendo un `.otbm` normal: se puede abrir y editar en RME
cuando haga falta trabajo manual.

## De donde salen los ids de item

Ningun id esta puesto de memoria. El criterio fue:

1. `items.otb` (binario, sin tocar) dice **que es** cada item: si es suelo,
   si bloquea el paso, etc. `itemsdb.py` lo lee.
2. El `items.xml` original de Forgotten Server, que sigue en el historial de
   git, aporta los **nombres**:

       git show 6f143b7:data/items/items.xml > referencia.xml

3. Para lo que el nombre no resuelve --que pieza de muro va horizontal, cual
   es la esquina, como se arma un techo-- se analizo el **mapa original de
   Tibia** (`git show 6f143b7:data/world/forgotten.otbm`) contando como se
   agrupan esos ids en la practica. Ejemplo: el muro 1050 aparece 477 veces
   con otro 1050 al este y solo 3 veces con uno al sur, luego 1050 es el
   muro este-oeste.

`build_village.py` revalida cada id contra `items.otb` al arrancar
(`ItemsDB.require`), asi un id equivocado falla al generar y no en silencio
dentro del juego.

## Archivos

| Archivo | Para que sirve |
| --- | --- |
| `otbfile.py` | Contenedor binario de nodos comun a `.otb` y `.otbm` |
| `itemsdb.py` | Lee `items.otb`: grupo y flags de cada item |
| `otbmmap.py` | Lee y escribe mapas `.otbm` |
| `build_village.py` | Genera la aldea inicial y sus alrededores |
| `sync_items_xml.py` | Declara en `items.xml` los items que usa el mapa |
| `used_item_ids.txt` | Ids que usa el mapa actual (lo genera build_village) |

## Regenerar el mapa

    python tools/build_village.py
    python tools/sync_items_xml.py referencia.xml

El segundo paso es necesario porque `items.otb` define el item a nivel de
servidor pero `items.xml` es lo que le da nombre y comportamiento: sin su
entrada, una puerta queda como un bloque solido en vez de abrirse.

Ojo: `build_village.py` **sobrescribe** `data/world/kzland.otbm`. Si el mapa
se edita a mano en RME, no volver a ejecutarlo sin trasladar antes esos
cambios al script.
