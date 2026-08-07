#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$SCRIPT_DIR/pyvenv/bin/activate"

python3 "$SCRIPT_DIR/bot.py"
