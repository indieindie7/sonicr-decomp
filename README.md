# Sonic R (Sega Saturn, 1997) reverse-engineering notes and symbols

Hand-named function map, review records, format notes and tools for the Sega Saturn game
**Sonic R** (Traveller's Tales / Sonic Team, 1997). The main program `0.BIN` loads at 0x06004000;
all 391 of its functions carry hand names, with no `FUN_` and no provisional names left after three
review rounds. Same method as
[scorcher-decomp](https://github.com/indieindie7/scorcher-decomp),
[amok-decomp](https://github.com/indieindie7/amok-decomp),
[cybersled-decomp](https://github.com/indieindie7/cybersled-decomp) and
[cyberspeedway-decomp](https://github.com/indieindie7/cyberspeedway-decomp). Non-commercial, done for study and preservation.

**No game data is included**: no disc image, no program files, no unpacked data, no decompiled C,
no Ghidra database. You need your own copy of the game to use any of this.

## What is here

| Path | Content |
|---|---|
| `NOTES.md` | the working log: disc layout, the naming pipeline, file formats (TRACK containers, `<course>HI.BIN` collision, PATH demo recordings), every review round |
| `study_handling.md` | racer physics: speeds, gravity, jumps, ground and wall response |
| `study_ai_camera.md` | AI path following, the branch table and action grids, rubber-banding, cameras |
| `ghidra/hand_0.txt` | hand-named functions (`0x<addr> func <name> hand <comment>`) |
| `ghidra/funcinfo_0.tsv` | per-function export: `F` address name source size, `C` callees, `S` string references |
| `ghidra/naming/` | naming batches (`h1-h5`), review prompt and verdicts (`<prog> 0x<addr> <old> CONFIRM/RENAME/UNSURE <new> <reason>`) |
| `ghidra/scripts/` | `FindSh2FunctionsMem.java` (SH-2 function discovery), `DumpLong.java` |
| `ghidra/srrun.sh` | headless Ghidra wrapper |
| `tools/rnc.py` | Rob Northen ProPack method 2 unpacker (checks the CRC; splits chained images) |
| `tools/scr2png.py` | renders the 157696-byte VDP2 screen files to PNG |
| `tools/` (rest) | gap and pointer scans, provisional review context and apply scripts |

Paths inside the scripts point at the author's machine; edit them for yours. `ApplyNames.java` and
`ExportFuncInfo.java` come from the Scorcher / AMOK repos.

## Licence

Notes, names and tools: MIT (see `LICENSE`). Sonic R belongs to Sega; nothing from the game is
distributed here. Takedown requests will be honoured.
