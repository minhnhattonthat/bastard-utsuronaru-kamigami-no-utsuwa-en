-- pin.lua: hold RAM values every frame from PIN_FROM on. --var "PINS='80106C2C:4:1,80157750:2:1'" (hex addr:width:value)
local ffi = require("ffi")
local M = ffi.cast("uint8_t*", PCSX.getMemPtr())
local pins = {}
for addr, width, value in PINS:gmatch("(%x+):(%d):(%d+)") do
  pins[#pins + 1] = { tonumber(addr, 16) % 0x200000, tonumber(width), tonumber(value) }
end
-- ENEMY_HP=n: enemy records are on the heap, which moves between builds. Finds 3 u32 = n at the record stride, sets them to 1, once.
-- The record's max HP comes first and also matches, 0x12C before the current HP (0x801374B0 on the original disc).
local U32 = ffi.cast("uint32_t*", M)
local enemies_done = not ENEMY_HP
local function find_enemies()
  for w = 0x100000 / 4, 0x1F0000 / 4 do
    if U32[w] == ENEMY_HP and U32[w + 0x70] == ENEMY_HP and U32[w + 0xE0] == ENEMY_HP
      and U32[w + 0x4B] == ENEMY_HP and U32[w + 0x4B + 0x70] == ENEMY_HP and U32[w + 0x4B + 0xE0] == ENEMY_HP then
      w = w + 0x4B
      U32[w], U32[w + 0x70], U32[w + 0xE0] = 1, 1, 1
      L.log(string.format("PIN enemies at %08X", 0x80000000 + w * 4))
      return true
    end
  end
end
L.on_frame(function(n)
  if not enemies_done and n >= (PIN_FROM or 0) and n % 30 == 0 then enemies_done = find_enemies() end
  -- PIN_ONCE=1 writes at PIN_FROM only: a battle waits for its HP bar to reach the value, so holding HP hangs it.
  if n < (PIN_FROM or 0) or (PIN_ONCE and n > PIN_FROM) then return end
  for _, p in ipairs(pins) do
    if p[2] == 4 then ffi.cast("uint32_t*", M + p[1])[0] = p[3]
    elseif p[2] == 2 then ffi.cast("uint16_t*", M + p[1])[0] = p[3]
    else M[p[1]] = p[3] end
  end
end)
