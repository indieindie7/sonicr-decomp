#!/bin/bash
# headless Ghidra on the SonicR project. usage: srrun.sh <abs log> <args...> (e.g. -process X -noanalysis -postScript Y)
# set GHIDRA_HEADLESS (path to analyzeHeadless / a wrapper .bat), PROJ_DIR (Windows path of this ghidra folder) and SP (script path)
log="$1"; shift
cd "$(dirname "$0")" || exit 1
cmd //c "$GHIDRA_HEADLESS $PROJ_DIR SonicR $* -scriptPath ${SP:-$PROJ_DIR\scripts}" < /dev/null > "$log" 2>&1
tail -2 "$log"
