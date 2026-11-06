-- fontlog.lua: which font function draws which codes. warp.py SCENE --probe tools/debug/fontlog.lua
-- Hooks the draw entry of each font in the table at 0x8009E08C (a2 = x, a3 = code), so both the console path (8004DCA4)
-- and the string path (8004DCF8) count. Logs each new (font, code) once.
local seen = {}
local FONTS = { [0] = 0x8004DE7C, 0x8004E1A8, 0x8004E38C, 0x8004E3B4, 0x8004E5D4, 0x8004EA34, 0x8004E7C8, 0x8004EC20, 0x8004EE04 }
for font = 0, 8 do
  L.on_exec(FONTS[font], function()
    local r = PCSX.getRegisters().GPR.n
    local code = bit.band(r.a3, 0xFFFF)
    local k = font * 65536 + code
    if not seen[k] then
      seen[k] = true
      L.log(string.format("GLYPH font=%d code=%04X x=%d w=%d", font, code, bit.band(r.a2, 0xFFFF), bit.band(r.a1, 0xFFFF)))
    end
  end)
end
