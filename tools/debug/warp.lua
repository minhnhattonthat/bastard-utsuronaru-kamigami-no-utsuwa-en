-- warp.lua: cold boot straight into any scene, no title, no save, no playthrough. Normal entry: tools/debug/warp.py.
--   emu.py <cue> --out D --script tools/debug/warp.lua --var MAP=12 --var "POINT='p001'" --frames 3000 --sheet
-- MAP = index into the EXE map table, POINT = letter + number of one of its dsg points (tools/debug/maps.tsv).
-- How (docs/re/code.md): the sequence object at *0x8009D3A8 holds the debug bit (+0x50C & 4), the current map record
-- (+4) and the entry point (+0xC). The patches below edit the new-game branch in RAM to fill those in; nothing is
-- written to the disc, and the debug bit is off the disc too, so a release build never contains any of this.
-- Optional globals:
--   EVENT=n     run script event n when the route presses start in the field (no entry event 1000 before it)
--   ENTRY_EVENT=n  run script event n in place of map entry's event 1000; the route needs no start press
--   SETFLAGS    'id:value,...' story flags held until the event starts (gen_scenes.py reads them from its opening tests)
--   STATE=n     sequence state: 0 field (default), 1-2 movie then field, 3-4 ending
--   FLAGBITS=n  extra bits for seq+0x50C (2 = alternate ending)
--   MASTER=1    clear the debug bit on arrival: Start/Select menus, encounters and no "P1" HUD
--   DEBUG_AT=n  set the debug bit again at frame n, for routes that use menus first and debug keys after
--   BATTLE=n    fill the debug "replay battle" arguments; the route then presses select+square. BATTLE2, BATTLE3 too
--   CHECK       'map', 'event', 'battle', 'won', 'lost', 'ending' or 'none': the RAM test behind the log line "WARP ok"
local ffi = require("ffi")
local M = ffi.cast("uint8_t*", PCSX.getMemPtr())
local function r32(a) return ffi.cast("uint32_t*", M + (a % 0x200000))[0] end
local function w32(a, v) ffi.cast("uint32_t*", M + (a % 0x200000))[0] = v end

local SEQ_PTR, MAP_TABLE, FIELD_PTR = 0x8009D3A8, 0x8009BFA4, 0x800D1730
local mapRec = MAP_TABLE + 64 * (MAP or 0)
local point = POINT or "p001"
-- seq+0xC layout: bits 4-11 letter, bits 12-21 number; the other bits start at zero on a new game.
local entry = point:sub(1, 1):byte() * 16 + tonumber(point:sub(2)) * 4096
local function lo16(v) return v % 0x10000 end

-- { address, expected original word, replacement }: refuse to patch anything but the code this was read from.
local PATCH = {
  { 0x8003D0D0, 0x0C00F874, 0x34020000 },                                -- jal title -> v0 = 0 (New Game)
  { 0x8003D19C, 0x34020001, 0x34020000 + (STATE or 0) },                 -- v0 = sequence state
  { 0x8003D1A8, 0xAC600000, 0xAC620000 },                                -- debug branch stores v0, not zero
  { 0x8003D1C4, 0x2463BFA4, 0x24630000 + lo16(mapRec) },                 -- +4 = our map record
  { 0x8003D1CC, 0x2403F00F, 0x3C020000 + math.floor(entry / 0x10000) },  -- lui v0, entry hi
  { 0x8003D1D0, 0x00431024, 0x34420000 + lo16(entry) },                  -- ori v0, entry lo
  { 0x8003D1D4, 0x34420700, 0 },
  { 0x8003D1D8, 0x00441024, 0 },
  { 0x8003D1E0, 0x34421000, 0 },
  { 0x8003D1F0, 0xACA00004, 0 },                                         -- debug branch keeps +4
}

-- Events run from inside the field loop, as they do in play: the map-entry hook fires before the screen is up, and
-- 307 of 737 events stayed black from there. EVENT turns the Start-press branch (80038160) into a direct call of the
-- event runner, so the route must press start in the field (gen_scenes.py does), and Start then has no camp menu until
-- the event has started. The entry event 1000 is skipped because it would hold the field; a scene for event 1000 itself
-- lets it run. All of this goes in before the code first runs: words rewritten later can execute stale (the entry
-- hook's immediate did), which is also why the Start branch holds the event number itself.
local swapEvent = EVENT and EVENT ~= 1000
if swapEvent then
  local more = {
    { 0x80038D50, 0x340503E8, 0x34050000 + 999 },    -- entry event: none, no script has a 999
    { 0x80038164, 0x2484DFF4, 0x8C84D3A8 },          -- a0 = sequence object
    { 0x80038168, 0x0C012317, 0x34050000 + EVENT },  -- a1 = event (in the load delay slot)
    { 0x8003816C, 0x34050808, 0x8C840040 },          -- a0 = script object, seq+0x34+0xC
    { 0x80038170, 0x0C00F817, 0x0C00FE2F },          -- jal 8003F8BC instead of the camp menu
    { 0x80038174, 0x00000000, 0x34060001 },          -- a2 = 1
    -- Chest animation of the object that triggered the event. Here there is none: the index (0x27) is past the object table, so
    -- 800C16F0 calls through heap garbage and hangs if the heap layout is unlucky (ev_1_09_0006 on the marker build).
    { 0x80044A10, 0x0C0305BC, 0 },
    { 0x80044A9C, 0x0C0305BC, 0 },
    { 0x80044B00, 0x0C0305BC, 0 },
    { 0x80044B6C, 0x0C0305BC, 0 },
  }
  for _, p in ipairs(more) do PATCH[#PATCH + 1] = p end
end
-- The map-entry hook instead: only that path fades the field back in after an event that ends on black (1_01 event 3).
if ENTRY_EVENT then PATCH[#PATCH + 1] = { 0x80038D50, 0x340503E8, 0x34050000 + ENTRY_EVENT } end
local RESTORE_ON_ARRIVAL = 10  -- the new-game branch; the event words must stay until the event has run

local patched, arrived, setBit, ok = false, false, false, false
local scrWas, evStarted, sawBattle = 0, nil, false
local function pass(why)
  if not ok then ok = true; L.log("WARP ok " .. why .. " at frame " .. L.frame) end
end
-- Same layout as the flag read at 80039900: id bits 11+ byte, 8-10 bit position, 0-2 width - 1; storage at *(seq+0x18C).
local function set_flag(seq, id, val)
  local a = (r32(seq + 0x18C) + bit.rshift(id, 11)) % 0x200000
  local pos = bit.band(bit.rshift(id, 8), 7)
  local mask = bit.lshift(bit.lshift(1, bit.band(id, 7) + 1) - 1, pos)
  local v = bit.bor(bit.band(M[a] + M[a + 1] * 256, bit.bnot(mask)), bit.band(bit.lshift(val, pos), mask))
  M[a], M[a + 1] = bit.band(v, 255), bit.rshift(v, 8)
end
local function code_matches()
  for _, p in ipairs(PATCH) do if r32(p[1]) ~= p[2] then return false end end
  return true
end

L.on_frame(function(n)
  if not patched then
    if code_matches() then
      for _, p in ipairs(PATCH) do w32(p[1], p[3]) end
      patched = true
      L.log(string.format("WARP patched at frame %d map=%d point=%s", n, MAP or 0, point))
    elseif n > 2000 then
      error("WARP: EXE code differs from the patch table (wrong disc, or hooks moved this code)")
    end
    return
  end
  local seq = r32(SEQ_PTR)
  if seq < 0x80000000 then return end
  if not setBit then w32(seq + 0x50C, bit.bor(r32(seq + 0x50C), 4 + (FLAGBITS or 0))); setBit = true end
  -- Every frame until the event starts: new-game setup clears the flags, and event 1000 starts before "arrived".
  if SETFLAGS and not evStarted and r32(seq + 0x18C) >= 0x80000000 then
    for id, val in SETFLAGS:gmatch("(0x%x+):(%d+)") do set_flag(seq, tonumber(id), tonumber(val)) end
  end
  if not arrived and r32(seq + 4) == mapRec and r32(FIELD_PTR) >= 0x80000000 then
    arrived = n
    L.log("WARP arrived at frame " .. n)
    -- Back to the original code (all but the event swap), so a later return to the title behaves like the real game.
    for i = 1, RESTORE_ON_ARRIVAL do w32(PATCH[i][1], PATCH[i][2]) end
    if MASTER then w32(seq + 0x50C, bit.band(r32(seq + 0x50C), bit.bnot(4))) end
    -- Debug "replay last battle" key: select+square in the field, with the battle's arguments at seq+0x2F8.
    if BATTLE then
      w32(seq + 0x2F8, BATTLE); w32(seq + 0x2FC, BATTLE2 or 0); w32(seq + 0x300, BATTLE3 or 0)
      w32(seq + 0x304, 0); w32(seq + 0x308, 0)
    end
  end
  if DEBUG_AT and n == DEBUG_AT then w32(seq + 0x50C, bit.bor(r32(seq + 0x50C), 4)) end
  local overlay = r32(seq + 0x28)
  if CHECK == "map" and arrived and n > arrived + 300 and r32(seq + 4) == mapRec and overlay == 0 then pass("map") end
  if CHECK == "battle" and arrived and overlay == 1 then pass("battle overlay") end
  if overlay == 1 then sawBattle = true end
  if CHECK == "lost" and sawBattle and overlay == 3 then pass("title overlay after a battle") end
  if CHECK == "won" and sawBattle and overlay == 0 then pass("field overlay after a battle") end  -- a loss goes to title
  if CHECK == "ending" and overlay == 4 then pass("ending overlay") end
  if CHECK == "event" and arrived then
    -- Script object +0x30: written only after the named event was found and is about to run (8003F84C), and it stays
    -- set, so this proves the start of the event, not its end. A missing event never sets it (scene ev_missing).
    local s = r32(seq + 0x1AC + 0x30)
    if s ~= scrWas then
      L.log(string.format("WARP script %d -> %d at frame %d", scrWas, s, n))
      if s ~= 0 and not evStarted then
        evStarted = n
        pass("event " .. tostring(EVENT or ENTRY_EVENT))
        -- Start is the camp menu again, and later entry events are the game's own
        for i = RESTORE_ON_ARRIVAL + 1, #PATCH do w32(PATCH[i][1], PATCH[i][2]) end
      end
      scrWas = s
    end
    if evStarted and n == evStarted + 900 then L.shot("proof.png") end
  end
end)
