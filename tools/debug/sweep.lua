-- sweep.lua: show every script string of a map through the game's own printer, whichever branch of whichever event holds it.
-- warp.lua starts EVENT by pressing start in the field; this replaces that event's code with a generated list of print calls.
-- Used with warp.py scenes of group `sweep` (gen_scenes.py writes SWEEP_DIR/<ssg>.txt). The disc is untouched, as with warp.lua.
-- Proves: the line prints, whole, in the box its call site uses. Does not prove: the story path that reaches it.
-- File: first line "<event code offset>", then "<ori file offset> <kind n|d|c> <speaker or -1>".
local ffi = require("ffi")
local M = ffi.cast("uint8_t*", PCSX.getMemPtr())
local function r32(a) return ffi.cast("uint32_t*", M + (a % 0x200000))[0] end
local function w32(a, v) ffi.cast("uint32_t*", M + (a % 0x200000))[0] = v end

local CODE, DONE = 0x801F2000, 0x801F7FF0  -- map 2_11 uses RAM up to 801F11A4 (ramuse.py); DONE's low half must not sign-extend
local SEQ_PTR = 0x8009D3A8
local BAL = { n = 0x240, d = 0x280, c = 0x2B0 }  -- bal targets: narration, dialogue, choice; 0x2A0 speaker; 0x10 event end
local items, evOff = {}, nil
for line in io.lines(string.format("%s/%04d.txt", SWEEP_DIR, SWEEP)) do
  if not evOff then evOff = tonumber(line)
  else
    local ref, kind, spk = line:match("(%d+) (%a) (-?%d+)")
    items[#items + 1] = { tonumber(ref), kind, tonumber(spk) }
  end
end

local function jal(a) return 0x0C000000 + (a % 0x10000000) / 4 end
local function ori(rt, imm) return 0x34000000 + rt * 0x10000 + imm end
local function addu_gp(rd) return rd * 0x200000 + 28 * 0x10000 + rd * 0x800 + 0x21 end  -- addu rd, rd, $gp

local function build(base)
  local stub = function(t) return jal(base + t) end  -- base = file offset 8, what bal targets and event records count from
  local out = { 0x27BDFFE8, 0xAFBF0010 }                 -- addiu $sp,-0x18; sw $ra,0x10($sp)
  local function emit(...) for _, w in ipairs({ ... }) do out[#out + 1] = w end end
  local who = -1
  for _, it in ipairs(items) do
    local word = r32(base + it[1] - 8)
    if bit.rshift(word, 26) ~= 0x0D then error(string.format("SWEEP: no ori at +%x: %08x", it[1], word)) end
    local imm = word % 0x10000
    if it[2] == "d" and it[3] >= 0 and it[3] ~= who then
      emit(stub(0x2A0), ori(4, it[3]))
      who = it[3]
    end
    emit(ori(4, imm), addu_gp(4))
    if it[2] == "c" then
      -- The string as prompt and as both options: a1 = 2, a2 = a3 = a0.
      emit(ori(5, 2), 0x00803021, stub(BAL.c), 0x00803821)
    else
      emit(stub(BAL[it[2]]), 0)
    end
  end
  emit(0x3C010000 + bit.rshift(DONE, 16), 0x34020001, 0xAC220000 + (DONE % 0x10000))  -- lui $at; ori $v0,1; sw $v0,lo($at)
  emit(stub(0x10), 0)
  emit(0x8FBF0010, 0x27BD0018, 0x03E00008, 0)                                          -- lw $ra; addiu $sp; jr $ra; nop
  if CODE + #out * 4 > DONE then error("SWEEP: code too long") end
  for i, w in ipairs(out) do
    if r32(CODE + (i - 1) * 4) ~= 0 then error("SWEEP: code area in use on this map") end
    w32(CODE + (i - 1) * 4, w)
  end
  w32(base + evOff, 0x08000000 + (CODE % 0x10000000) / 4)  -- j CODE
  w32(base + evOff + 4, 0)
  L.log(string.format("SWEEP %d strings, %d words, base %08x", #items, #out, base))
end

local built = false
L.on_frame(function(n)
  if not built and n >= 2100 then  -- the map is up (gen_scenes FIELD = 2200, then start)
    local seq = r32(SEQ_PTR)
    local base = seq >= 0x80000000 and r32(seq + 0x1AC + 0x24) or 0
    if base >= 0x80000000 then
      build(base)
      built = true
    end
  end
  if built and r32(DONE) == 1 then
    L.log("SWEEP done at frame " .. n)
    L.finish(0)
  end
end)
