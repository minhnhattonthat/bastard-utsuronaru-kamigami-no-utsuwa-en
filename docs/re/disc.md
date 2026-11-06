# Disc

Single MODE2/2352 data track, 240,642 sectors, no audio tracks. PVD: system PLAYSTATION, volume BASTARD, publisher SETA CORPORATION, preparer HIROKI AZUMADA, dated 1996-12-06. Verified by parsing the PVD and root directory (`tools/disc.py` holds the listing).

| File | LBA | Bytes (directory) | Content |
|---|---|---|---|
| SYSTEM.CNF | 23 | 68 | `BOOT = cdrom:\SLPS_005.42;1`, TCB 4, EVENT 16, STACK 801fff00 |
| SLPS_005.42 | 24 | 1,091,584 | EXE, load 0x80010000 (file offset 0x800), entry 0x8008ACB4, t_size 0x10A000 |
| RSRCALL.RBB | 557 | 78,738,528 | Resource archive, form 1. See `rbb.md`. Ends at LBA 39003 |
| MOVIE.MMB | 39004 | 185,016,320 | 157 short effect STRs (no text) |
| ANIME.MMB | 129344 | 190,767,104 | 6 long STRs (opening, prologue, endings) |
| DUMMY | 222492 | 36,864,000 | 18,000 form 1 sectors, **all zero** (verified: every sector compared) |

MMB directory sizes count 2048 per sector. Their sectors are video (subheader submode 0x42, form 1 layout with an STR header `60 01 01 80`) interleaved with XA audio (0x64, form 2). A raw copy of the sectors decodes with ffmpeg's `psxstr` demuxer (verified, `tools/movies.py`).

## Free space
- **DUMMY: 36 MB zeroed at the end of the disc.** Candidate only: not yet proven unread (padding files normally are; check with a read log before relying on it). The directory entry could be retargeted, or the sectors used through RBB offsets if the RBB loader takes offsets past its own size (**guess**, read `rsrcctl.cpp`/`rsrchan.cpp` code in the EXE in phase 5).
- **RSRCALL.RBB:** 1,555,457 bytes of padding between 0x800-aligned entries, spread over 1,541 entries, plus GAP0 (0x724 bytes of 0x1A). No slack after the file: MOVIE.MMB follows at the next sector.
- **Raw `ssg` entries:** stored uncompressed while sibling entries use LZSS; if the loader accepts `00zL` on any entry (**guess**, dsg/fcg entries do), packing them recovers far more than English adds.
- **EXE/overlays:** no measured free space yet; strings sit in .rdata. Treat runs of zeros as candidates only.

## Rebuild
Not done yet (phase 3). Plan: patch file sectors in place and recompute EDC/ECC for changed sectors only, so LBAs never move; `dumpsxiso`/`mkpsxiso` are unnecessary while nothing moves. Identity test: unpack + repack == original SHA-1.
