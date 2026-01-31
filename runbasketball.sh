#!/bin/bash

# Clean up previous runs
rm -rf ponturi/basketball
rm output.txt

python3 main.py --basketball --days 2

./extract_safe_bets.sh output.txt filtered_basketball_output.txt basketball