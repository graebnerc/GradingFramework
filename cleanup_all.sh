#!/usr/bin/env bash
# Move all student folders from grading/ to complete/

export LANG=en_US.UTF-8
export PYTHONIOENCODING=utf-8

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
"$SCRIPT_DIR/venv/bin/python" "$SCRIPT_DIR/grade.py" cleanup-all

read -n 1 -s -r -p "Press any key to close..."
