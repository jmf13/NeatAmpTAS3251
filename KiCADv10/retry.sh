#!/bin/bash
cd "$(dirname "$0")"
IDS="C138687 C144397 C151282 C165948 C170101 C207841 C221880 C269426 C269699 C269705
C269716 C307331 C434162 C434218 C434236 C492429 C513314 C544648 C718262 C780769
C2827654 C2827938 C2829089 C2862740 C2902971 C2906876 C2907011 C2907025 C2907042
C2907069 C2907406 C2930060 C2980300 C3911721 C5137480 C5139491 C5156676 C5159418
C5159427 C5199872 C16194026 C19171392 C19271903 C29781155 C42431808"
: > still_failed.txt
for id in $IDS; do
  wait=300
  while true; do
    out=$(easyeda2kicad --full --lcsc_id=$id --output libs/easyeda2kicad --overwrite 2>&1)
    if echo "$out" | grep -q "403"; then
      echo "$id: 403, pausing ${wait}s"; sleep $wait
      wait=$(( wait*2 > 1800 ? 1800 : wait*2 ))
    elif echo "$out" | grep -q "Failed to fetch"; then
      echo "$id: not available"; echo $id >> still_failed.txt; break
    else
      echo "$id: OK"; break
    fi
  done
  sleep 15
done
echo "Done. Not available: $(wc -l < still_failed.txt)"
