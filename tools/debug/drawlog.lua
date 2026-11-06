-- drawlog.lua: what a marker or --qa build really shows, at full speed (no debugger). Read by tour_report.py.
--   warp.py SCENE --cue build/bastard_marker.cue --script-only tools/debug/drawlog.lua
-- The QA hook (tools/engine.py) puts every glyph of fonts 1 and 8 in a ring: (box width << 16 | code). Logs:
--   ID <marker id> <w>     a marker id on screen and the width of the box it went into
--   JP <hex codes>         Shift-JIS still being drawn: a string the build did not replace
local ffi = require("ffi")
local M = ffi.cast("uint8_t*", PCSX.getMemPtr())
local RING, SIZE = 0x1FD000, 0x2000  -- engine.RING, engine.RING_SIZE
local function u32(o) return ffi.cast("uint32_t*", M + o)[0] end

local seen, seenJp = {}, {}
local rd = 0
local cur, jp = nil, {}
local badRing = false
local function flush_jp()
  if #jp > 0 then
    local s = table.concat(jp, " ")
    if not seenJp[s] then seenJp[s] = true; L.log("JP " .. s) end
    jp = {}
  end
end

L.on_frame(function()
  local wr = u32(RING - 4)
  if wr >= SIZE or wr % 4 ~= 0 then  -- not our index: a movie or scene is using this RAM, and `rd` would never reach it
    if not badRing then badRing = true; L.log("RING index overwritten: " .. wr) end
    return
  end
  while rd ~= wr do
    local e = u32(RING + rd)
    rd = (rd + 4) % SIZE
    local code, w = e % 0x10000, math.floor(e / 0x10000)
    if code >= 0x80 then
      if #jp < 64 then jp[#jp + 1] = string.format("%04X", code) end
    else
      flush_jp()
      local ch = code >= 0x20 and code < 0x7F and string.char(code) or nil
      if ch == "[" then
        cur = ""
      elseif cur then
        if ch == "]" then
          local k = cur .. " " .. w
          if not seen[k] then seen[k] = true; L.log("ID " .. k) end
          cur = nil
        elseif ch and #cur < 16 then
          cur = cur .. ch
        else
          cur = nil
        end
      end
    end
  end
  flush_jp()
end)
