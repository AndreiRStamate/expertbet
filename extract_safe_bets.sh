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
tail -n +"$START_LINE" "$INPUT_FILE" | grep "Echipe:" > "$OUTPUT_FILE"

echo "Done. Matches saved to $OUTPUT_FILE"