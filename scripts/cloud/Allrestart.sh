#!/bin/bash
# Resume an interrupted decomposed I4 run from its latest checkpoint (processor*/<time>).
# No mesh, field or setting is changed. Usage: Allrestart.sh <case dir>
d=$(realpath "$1") || exit 1
cd "$d" || exit 1
source /usr/lib/openfoam/openfoam2512/etc/bashrc >/dev/null 2>&1
np=$(awk '$1=="np"{print $2; exit}' run_info.txt)
echo "restart $(date -Is) np $np host $(hostname)" >> run_info.txt
/usr/bin/time -v mpirun -np "$np" hisa -parallel >> log.solver 2>> log.time
rc=$?
reconstructPar > log.reconstructPar 2>&1 || rc=90
tail -n 300 log.solver > log.solver.tail
echo "end $(date -Is) rc $rc" >> run_info.txt
exit $rc
