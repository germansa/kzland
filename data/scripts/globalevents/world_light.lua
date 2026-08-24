-- Luz del mundo fija.
--
-- Este proyecto no tiene ciclo de dia y noche: antes habia uno que recalculaba
-- la luz cada 10 segundos (dia 250 / noche 40) con una hora de mundo que
-- avanzaba cada 2.5 segundos, de modo que un dia completo duraba una hora
-- real. Eso hacia que la pantalla entera cambiara de tono cada pocos minutos.
--
-- Ahora se fija una vez la luz de dia y no vuelve a cambiar. El cliente sigue
-- oscureciendo el subsuelo por su cuenta: en MapView::updateLight ignora la luz
-- del mundo por debajo de sea-floor (7), asi que las cuevas quedan oscuras y
-- solo se ven con antorchas, mientras la superficie se ve iluminada.
--
-- Los jugadores la reciben al entrar, en el creaturescript WorldLight.

WORLD_LIGHT_COLOR = 215
WORLD_LIGHT_LEVEL = 250

Game.setWorldLight(WORLD_LIGHT_COLOR, WORLD_LIGHT_LEVEL)
