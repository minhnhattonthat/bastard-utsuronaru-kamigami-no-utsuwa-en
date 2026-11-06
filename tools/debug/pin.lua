-- pin.lua: hold RAM values every frame from PIN_FROM on. --var "PINS='80106C2C:4:1,80157750:2:1'" (hex addr:width:value)
local ffi = require("ffi")
local M = ffi.cast("uint8_t*", PCSX.getMemPtr())
local pins = {}
for addr, width, value in PINS:gmatch("(%x+):(%d):(%d+)") do
  pins[#pins + 1] = { tonumber(addr, 16) % 0x200000, tonumber(width), tonumber(value) }
end
L.on_frame(function(n)
  -- PIN_ONCE=1 writes at PIN_FROM only: a battle waits for its HP bar to reach the value, so holding HP hangs it.
  if n < (PIN_FROM or 0) or (PIN_ONCE and n > PIN_FROM) then return end
  for _, p in ipairs(pins) do
    if p[2] == 4 then ffi.cast("uint32_t*", M + p[1])[0] = p[3]
    elseif p[2] == 2 then ffi.cast("uint16_t*", M + p[1])[0] = p[3]
    else M[p[1]] = p[3] end
  end
end)
