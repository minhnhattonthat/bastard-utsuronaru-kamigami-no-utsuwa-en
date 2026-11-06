-- printlog.lua: the last menu strings before a hang. warp.py SCENE --cue C --probe tools/debug/printlog.lua (under the debugger, slow).
-- Logs each new string given to the menu printer (80049ED4, string pointer at sp+0x14) with its frame.
local ffi = require("ffi")
local M = ffi.cast("uint8_t*", PCSX.getMemPtr())
local function u32(a) a = a % 0x200000; return M[a] + M[a + 1] * 256 + M[a + 2] * 65536 + M[a + 3] * 16777216 end
local function cstr(a)
  a = a % 0x200000
  local out = {}
  while M[a] ~= 0 and #out < 60 do out[#out + 1] = string.format(M[a] < 0x80 and "%c" or "<%02X>", M[a]); a = a + 1 end
  return table.concat(out)
end
local last = ""
L.on_exec(0x80049ED4, function()
  local r = PCSX.getRegisters()
  local s = cstr(u32(r.GPR.n.sp + 0x14))
  if s ~= last then
    last = s
    L.log(string.format("PRINT f=%d ra=%08X %s", L.frame, r.GPR.n.ra, s))
  end
end)
