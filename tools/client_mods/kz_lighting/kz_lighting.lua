--[[
Luz por piso, y sin indicador de dia/noche.

Contexto: el servidor nunca envia la luz del mundo (opcode 0x82) ni la hora
(0xEF), asi que g_map.getLight() se queda a cero y la superficie sale negra.
Lo unico que ilumina son los items con luz, que tienen color, y de ahi los
tintes raros sobre el fondo negro.

Como lo resuelve el cliente (src/client/mapview.cpp, MapView::updateLight):

    Light ambient = camaraZ > seaFloor ? Light() : g_map.getLight();
    ambient.intensity = max(minimumAmbientLight * 255, ambient.intensity);

O sea: bajo tierra ignora la luz del mundo, pero el minimo ambiental se aplica
en los dos casos. Como g_map.setLight no esta expuesto a Lua, la unica palanca
disponible es ese minimo, y hay que moverlo segun el piso:

    superficie (z <= 7) -> minimo alto  -> se ve todo
    subsuelo   (z >  7) -> minimo cero  -> oscuro, solo antorchas

Asi no hace falta tocar el core en C++ ni el protocolo.
]]

-- data/setup.otml -> map.sea-floor
local SEA_FLOOR = 7

-- 0 = negro, 1 = sin sombras. En superficie queremos verlo todo.
local SURFACE_LIGHT = 1.0
local UNDERGROUND_LIGHT = 0.0

local function applyForFloor(z)
    local mapPanel = modules.game_interface and modules.game_interface.getMapPanel()
    if not mapPanel then
        return
    end

    local value = z > SEA_FLOOR and UNDERGROUND_LIGHT or SURFACE_LIGHT
    mapPanel:setMinimumAmbientLight(value)
    -- Las luces siguen dibujandose para que antorchas y lamparas se vean bajo
    -- tierra; en superficie el minimo alto las deja sin efecto visible.
    mapPanel:setDrawLights(true)
end

local function refresh()
    local player = g_game.getLocalPlayer()
    if not player then
        return
    end
    -- Al entrar, la posicion puede no estar lista todavia.
    local pos = player:getPosition()
    if pos then
        applyForFloor(pos.z)
    end
end

-- El indicador de dia/noche es la rosa del minimapa: 'rosePanel' agrupa el
-- degradado horario ('ambients') y el anillo ('rose'). Nunca recibe datos
-- porque el servidor no manda la hora, asi que se oculta entero. Los botones
-- de zoom son hermanos de rosePanel, no hijos, y no se ven afectados.
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
    connect(g_game, {
        onGameStart = function()
            refresh()
            hideDayTimeIndicator()
        end
    })
    connect(LocalPlayer, {
        onPositionChange = function(_, newPos, oldPos)
            -- solo cuando cambia de piso, no en cada paso
            if not oldPos or newPos.z ~= oldPos.z then
                applyForFloor(newPos.z)
            end
        end
    })
    refresh()
end

function terminate()
    disconnect(g_game, { onGameStart = refresh })
    disconnect(LocalPlayer, { onPositionChange = refresh })
end
