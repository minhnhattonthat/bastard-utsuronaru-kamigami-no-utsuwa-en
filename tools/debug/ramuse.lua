-- ramuse.lua: which RAM bytes ever go nonzero. OR of all main RAM every 30 frames, written to ramuse.bin in the run's
-- folder every 600 frames. tools/debug/ramuse.py merges runs: a range still zero in every scene is a free-space candidate.
local ffi = require("ffi")
local N = 0x200000
local M = ffi.cast("uint32_t*", PCSX.getMemPtr())
local buf = ffi.new("uint32_t[?]", N / 4)
L.on_frame(function(n)
  if n % 30 == 0 then
    for i = 0, N / 4 - 1 do buf[i] = bit.bor(buf[i], M[i]) end
  end
  if n % 600 == 0 then L.write_file("ramuse.bin", ffi.string(buf, N)) end
end)
