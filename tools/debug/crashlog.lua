-- crashlog.lua: why a scene hangs. warp.py SCENE --cue C --probe tools/debug/crashlog.lua (runs under the debugger, slow).
-- Logs CPU exceptions other than interrupts, with the faulting PC, and any game assert (8004CA2C: file, line).
local ffi = require("ffi")
local M = ffi.cast("uint8_t*", PCSX.getMemPtr())
local function cstr(a)
  a = a % 0x200000
  local out = {}
  while M[a] ~= 0 and #out < 60 do out[#out + 1] = string.char(M[a]); a = a + 1 end
  return table.concat(out)
end
local exc, asserts = 0, 0
L.on_exec(0x80000080, function()
  local r = PCSX.getRegisters()
  local code = bit.band(bit.rshift(r.CP0.r[13], 2), 31)  -- Cause
  if code ~= 0 and code ~= 8 and exc < 20 then  -- 8: syscall, the BIOS and libraries do it all the time
    exc = exc + 1
    L.log(string.format("EXC code=%d f=%d epc=%08X badv=%08X ra=%08X sp=%08X", code, L.frame, r.CP0.r[14], r.CP0.r[8], r.GPR.n.ra, r.GPR.n.sp))
  end
end)
L.on_exec(0x8004CA2C, function()
  local r = PCSX.getRegisters()
  asserts = asserts + 1
  if asserts <= 5 then L.log(string.format("ASSERT f=%d %s line %d ra=%08X", L.frame, cstr(r.GPR.n.a0), r.GPR.n.a1, r.GPR.n.ra)) end
end)
