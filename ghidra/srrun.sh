#!/bin/bash
# headless Ghidra on the SonicR project. usage: csprun.sh <abs log> <args...> (e.g. -process X -noanalysis -postScript Y)
log="$1"; shift
cd /c/Users/john/Documents/SonicR/ghidra || exit 1
cmd //c "C:\Users\john\Documents\Tools\ghidra-headless.bat C:\Users\john\Documents\SonicR\ghidra SonicR $* -scriptPath ${SP:-C:\Users\john\Documents\SonicR\ghidra\scripts}" < /dev/null > "$log" 2>&1
tail -2 "$log"
