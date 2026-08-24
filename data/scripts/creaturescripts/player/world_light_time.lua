-- Envia la luz del mundo al entrar.
--
-- Ya no se manda la hora del mundo (paquete 0xEF): alimentaba el indicador
-- horario del minimapa, que se quito junto con el ciclo de dia y noche.
-- Ver data/scripts/globalevents/world_light.lua.

local event = CreatureEvent("WorldLight")

function event.onLogin(player)
	local worldLightColor, worldLightLevel = Game.getWorldLight()
	player:sendWorldLight(worldLightColor, worldLightLevel)
	return true
end

event:register()
