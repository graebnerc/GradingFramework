#!/usr/bin/env bash
# Run the full grading pipeline (parse → render) for every student in grading/
# Safe to double-click on macOS — keeps the Terminal window open on completion.

export LANG=en_US.UTF-8
export PYTHONIOENCODING=utf-8

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GRADING_DIR="$SCRIPT_DIR/grading"
PYTHON="$SCRIPT_DIR/venv/bin/python"

if [ ! -d "$GRADING_DIR" ]; then
  echo "Error: grading directory not found at $GRADING_DIR"
  read -n 1 -s -r -p "Press any key to close..."
  exit 1
fi

students=()
for d in "$GRADING_DIR"/*/; do
  [ -d "$d" ] && students+=("$(basename "$d")")
done

if [ ${#students[@]} -eq 0 ]; then
  echo "No student folders found in $GRADING_DIR"
  read -n 1 -s -r -p "Press any key to close..."
  exit 0
fi

echo "Running pipeline for ${#students[@]} student(s)..."
echo

failed=0
for name in "${students[@]}"; do
  echo "════════════════════════════════════════"
  echo "  $name"
  echo "════════════════════════════════════════"
  if "$PYTHON" "$SCRIPT_DIR/grade.py" pipeline "$name" --lang en; then
    echo "  OK"
  else
    echo "  FAILED (exit code $?)"
    failed=$((failed + 1))
  fi
  echo
done

if [ "$failed" -eq 0 ]; then
  echo "Done. All ${#students[@]} student(s) processed successfully."
else
  echo "Done. $failed of ${#students[@]} student(s) had errors."
fi

read -n 1 -s -r -p "Press any key to close..."
