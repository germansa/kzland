# CLAUDE.md — Reglas del proyecto

## 1. Contexto del proyecto

Este proyecto es un MMORPG inspirado en la jugabilidad clásica de Tibia y está construido sobre Forgotten Server / Forgotten OT como base.

El objetivo es desarrollar y extender el juego manteniendo una arquitectura estable, modular y fácil de mantener.

El código existente del servidor es la fuente principal de verdad sobre el funcionamiento interno del proyecto.

No asumas que Forgotten Server funciona de la misma manera que otras versiones, forks o proyectos basados en Tibia.

---

## 2. Antes de realizar cambios

Antes de implementar cualquier funcionalidad:

1. Inspecciona el código y los archivos relacionados.
2. Identifica cómo funciona actualmente el sistema afectado.
3. Busca APIs, eventos, callbacks, hooks o sistemas existentes que puedan reutilizarse.
4. Determina si el cambio puede realizarse mediante scripts o configuración antes de modificar el core.
5. Evita introducir dependencias o complejidad innecesaria.

No inventes funciones, APIs, callbacks, eventos, estructuras o comportamientos que no existan en el proyecto.

Si no puedes confirmar cómo funciona una parte del código, indícalo claramente antes de realizar cambios.

---

## 3. Prioridad para implementar funcionalidades

Al agregar una nueva funcionalidad, utiliza preferentemente este orden:

1. Configuración existente.
2. Sistemas de datapack.
3. Scripts Lua.
4. Sistemas existentes del servidor.
5. Modificación del core en C++.

No modifiques el core del servidor si la funcionalidad puede implementarse correctamente mediante Lua, XML, configuración u otro sistema ya existente.

Si una modificación del core es necesaria, explica:

* por qué Lua o los sistemas existentes no son suficientes;
* qué componentes serán afectados;
* posibles riesgos de compatibilidad;
* impacto en rendimiento;
* impacto en futuras actualizaciones.

---

## 4. Modificaciones al core

Los cambios en C++ deben mantenerse aislados y ser mínimos.

No mezcles cambios no relacionados dentro de una misma modificación.

Antes de modificar una clase o sistema existente:

* revisa sus dependencias;
* identifica dónde es utilizada;
* evita romper compatibilidad con scripts existentes;
* evita modificar comportamientos globales sin analizar sus consecuencias.

No realices refactors grandes únicamente por preferencia estética.

Un refactor debe tener una razón técnica clara.

---

## 5. Lua y sistemas de gameplay

Los scripts Lua deben ser:

* modulares;
* reutilizables;
* fáciles de entender;
* consistentes con la estructura existente del proyecto.

Evita:

* archivos gigantes con múltiples sistemas no relacionados;
* lógica duplicada;
* números mágicos sin contexto;
* variables globales innecesarias;
* dependencias ocultas entre scripts.

Cuando un sistema crezca, divídelo en módulos con responsabilidades claras.

---

## 6. Sistemas nuevos

Antes de implementar un sistema grande, analiza primero:

* objetivo del sistema;
* interacción con sistemas existentes;
* datos que necesita almacenar;
* eventos que lo activan;
* persistencia necesaria;
* impacto en rendimiento;
* posibles exploits;
* escalabilidad futura.

Para sistemas complejos, primero propone una arquitectura antes de modificar múltiples archivos.

No implementes automáticamente una solución grande sin analizar cómo encaja en la arquitectura existente.

---

## 7. Base de datos

Antes de crear nuevas tablas o modificar tablas existentes:

* revisa el esquema actual;
* reutiliza estructuras existentes cuando tenga sentido;
* evita almacenar información duplicada;
* considera índices para consultas frecuentes;
* considera el crecimiento futuro de los datos.

Las modificaciones de base de datos deben incluir migraciones claras.

No realices cambios destructivos sin advertirlo explícitamente.

---

## 8. Rendimiento

El servidor puede manejar múltiples jugadores simultáneamente.

Evita introducir:

* loops costosos ejecutados frecuentemente;
* consultas innecesarias a la base de datos;
* polling cuando puede utilizarse un evento;
* cálculos repetitivos que puedan almacenarse o cachearse;
* iteraciones globales frecuentes sobre jugadores, criaturas o ítems.

Presta especial atención a código ejecutado en:

* movement events;
* creature events;
* combat;
* callbacks frecuentes;
* think events;
* tareas programadas.

Antes de agregar una tarea periódica, evalúa su impacto cuando existan muchos jugadores conectados.

---

## 9. Seguridad y exploits

Todo sistema de gameplay debe considerar posibles abusos.

Analiza especialmente:

* duplicación de ítems;
* duplicación de oro;
* manipulación de inventario;
* condiciones de carrera;
* spam de eventos;
* abuso de cooldowns;
* abuso de reconexiones;
* manipulación de datos enviados por el cliente;
* exploits relacionados con trading;
* exploits relacionados con containers;
* exploits relacionados con muerte y respawn.

Nunca confíes en información enviada por el cliente cuando pueda ser validada por el servidor.

El servidor debe ser la autoridad final sobre el estado del juego.

---

## 10. Compatibilidad

Antes de realizar cambios, respeta:

* la versión actual de Forgotten Server;
* la versión del protocolo;
* el cliente utilizado por el proyecto;
* la estructura actual del datapack;
* las APIs existentes.

No actualices automáticamente Forgotten Server, librerías o dependencias principales.

Cualquier actualización importante debe analizarse por separado debido al riesgo de incompatibilidades.

---

## 11. Cliente y protocolo

No asumas que el cliente soporta automáticamente una nueva funcionalidad.

Cuando una feature requiera comunicación entre cliente y servidor:

1. identifica si el protocolo actual la soporta;
2. identifica si requiere cambios en el cliente;
3. identifica si requiere cambios en el servidor;
4. documenta el flujo completo de comunicación.

No implementes cambios de protocolo parcialmente.

---

## 12. Cambios grandes

Si una solicitud requiere modificar múltiples sistemas, primero:

1. analiza el código afectado;
2. identifica archivos y componentes involucrados;
3. propone un plan;
4. explica dependencias y riesgos;
5. implementa por etapas.

Evita modificar grandes cantidades de archivos simultáneamente sin una estrategia clara.

---

## 13. Calidad del código

Mantén consistencia con el estilo existente del proyecto.

Prioridades:

1. Correctitud.
2. Compatibilidad.
3. Seguridad.
4. Rendimiento.
5. Mantenibilidad.
6. Elegancia del código.

No sacrifiques estabilidad por introducir patrones, frameworks o abstracciones innecesarias.

---

## 14. Dependencias

Antes de agregar una nueva dependencia:

* verifica si el proyecto ya puede resolver el problema;
* evalúa mantenimiento y compatibilidad;
* evita dependencias pequeñas para problemas simples;
* no agregues frameworks completos para resolver una funcionalidad menor.

Explica brevemente por qué una nueva dependencia es necesaria.

---

## 15. Debugging

Cuando investigues un bug:

1. identifica el comportamiento esperado;
2. identifica el comportamiento actual;
3. localiza el flujo de ejecución;
4. busca la causa raíz;
5. evita aplicar soluciones temporales que oculten el problema.

No soluciones bugs mediante parches arbitrarios sin entender su causa.

---

## 16. No asumir

Nunca:

* inventes APIs;
* inventes funciones;
* inventes callbacks;
* inventes configuraciones;
* inventes nombres de archivos;
* inventes estructuras de Forgotten Server.

Primero verifica el código existente.

Si falta información, pregunta o indica exactamente qué necesitas revisar.

---

## 17. Forma de trabajar

Para cambios pequeños:

* analiza;
* implementa;
* verifica posibles efectos secundarios.

Para cambios medianos o grandes:

* analiza;
* explica la arquitectura propuesta;
* identifica archivos afectados;
* implementa de forma modular;
* revisa compatibilidad;
* identifica riesgos o trabajo pendiente.

El objetivo no es escribir código rápidamente.

El objetivo es construir un servidor estable, mantenible, escalable y consistente a largo plazo.
