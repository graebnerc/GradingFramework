#!/usr/bin/env bash
# Initialize one or more student grading folders interactively.
# Enter names one per line, or separate multiple names with semicolons.
# Leave the input empty and press Enter to finish.
# Safe to double-click on macOS — keeps the Terminal window open on completion.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$SCRIPT_DIR/venv/bin/python"

echo "════════════════════════════════════════"
echo "  New Student Initialization"
echo "════════════════════════════════════════"
echo "Enter folder names one per line, or separate with semicolons."
echo "Leave empty and press Enter when done."
echo

NAMES=()
while true; do
  read -r -p "Folder name: " INPUT
  [ -z "$INPUT" ] && break
  # Split on semicolons
  IFS=';' read -ra PARTS <<< "$INPUT"
  for part in "${PARTS[@]}"; do
    part="$(echo "$part" | xargs)"  # trim whitespace
    [ -n "$part" ] && NAMES+=("$part")
  done
done

if [ ${#NAMES[@]} -eq 0 ]; then
  echo "No names entered. Nothing to do."
  read -n 1 -s -r -p "Press any key to close..."
  exit 0
fi

echo

failed=0
for NAME in "${NAMES[@]}"; do
  if "$PYTHON" "$SCRIPT_DIR/grade.py" init "$NAME"; then
    : # success message printed by grade.py
  else
    echo "  ✗ Failed to initialize: $NAME"
    failed=$((failed + 1))
  fi
done

echo
if [ "$failed" -eq 0 ]; then
  echo "Done. Initialized ${#NAMES[@]} folder(s)."
else
  echo "Done. $failed of ${#NAMES[@]} failed."
fi

read -n 1 -s -r -p "Press any key to close..."
