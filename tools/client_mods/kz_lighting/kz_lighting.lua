--[[
Oculta el indicador de dia/noche del minimapa.

El ciclo de dia y noche se quito del servidor (ver
data/scripts/globalevents/world_light.lua), que ahora manda una luz de dia
fija. La oscuridad del subsuelo la resuelve el propio cliente sin ayuda: en
MapView::updateLight ignora la luz del mundo por debajo de sea-floor, asi que
las cuevas quedan oscuras y la superficie iluminada.

Por eso aqui no se toca la luz ambiente. Hacerlo seria contraproducente: el
minimo ambiental se aplica tanto en superficie como bajo tierra, y subirlo
iluminaria tambien las cuevas.
]]

-- El indicador horario es la rosa del minimapa: 'rosePanel' agrupa el degradado
-- ('ambients') y el anillo ('rose'). Ya no recibe datos porque el servidor dejo
-- de enviar la hora del mundo. Los botones de zoom son hermanos de rosePanel,
-- no hijos, asi que no se ven afectados.
local function hideDayTimeIndicator()
    local minimap = modules.game_minimap
    if not (minimap and minimap.mapController and minimap.mapController.ui) then
        return
    end
    local panel = minimap.mapController.ui:recursiveGetChildById('rosePanel')
    if panel then
        panel:hide()
    end
end

function init()
    connect(g_game, { onGameStart = hideDayTimeIndicator })
    if g_game.isOnline() then
        hideDayTimeIndicator()
    end
end

function terminate()
    disconnect(g_game, { onGameStart = hideDayTimeIndicator })
end
