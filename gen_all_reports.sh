#!/bin/bash -x
# gen all reports
OUTDIR=./sensitive/generated-reports
DATESTAMP=$(date +%d-%m-%Y)
REPSUFFIX="slack-activity-report-week-ending-${DATESTAMP}"

echo generating all reports on $DATESTAMP
rm   ${OUTDIR}/slack-activity-report-*.txt    ${OUTDIR}/slack-activity-report-*.png

for CITY in london westmidlands northwest
do
    echo generating documents for city: $CITY
    ./sensitive/start_${CITY}_report.sh > ${OUTDIR}/${CITY}-${REPSUFFIX}.txt
    dot -Tpng -O ./sensitive/calls.dot
    mv sensitive/calls.dot.png ${OUTDIR}/${CITY}-${REPSUFFIX}.calls.png
done
