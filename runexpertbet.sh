#!/bin/bash

# Clean up previous runs
rm -rf ponturi
rm output.txt

python3 main.py --football

./extract_safe_bets.sh output.txt