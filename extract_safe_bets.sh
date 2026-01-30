#!/bin/bash

# Usage: ./extract_safe_bets.sh input.txt [output.txt]

INPUT_FILE="$1"
OUTPUT_FILE="${2:-filtered_output.txt}"

if [[ -z "$INPUT_FILE" ]]; then
  echo "Usage: $0 input.txt [output.txt]"
  exit 1
fi

# Find the line number of the last "Sorted by"
START_LINE=$(grep -n "Sorted by" "$INPUT_FILE" | tail -1 | cut -d: -f1)

# Extract from that line onward, then search for PARIU SIGUR matches
# tail -n +"$START_LINE" "$INPUT_FILE" | grep -B3 "Evaluare:.*PARIU SIGUR" | grep "Echipe:" > "$OUTPUT_FILE"
tail -n +"$START_LINE" "$INPUT_FILE" \
  | grep "Echipe:" \
  | awk -F'Echipe:[[:space:]]*| vs ' '{print $2 "|" $0}' \
  | sort -f \
  | cut -d'|' -f2- > "$OUTPUT_FILE"

TODAY=$(date +%Y%m%d)
mkdir -p manualanalysis
cp "$OUTPUT_FILE" "manualanalysis/football${TODAY}_gpt.txt"
cp "$OUTPUT_FILE" "manualanalysis/football${TODAY}_grok.txt"
cp "$OUTPUT_FILE" "manualanalysis/football${TODAY}_med.txt"
cp "$OUTPUT_FILE" "manualanalysis/football${TODAY}_odd.txt"
cp "$OUTPUT_FILE" "manualanalysis/football${TODAY}_res.txt"

echo "Done. Matches saved to $OUTPUT_FILE"