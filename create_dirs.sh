#!/usr/bin/env bash
# Move loose markdown files in grading/ into student directories.
# For each .md file, creates a directory with the same name (minus extension)
# and moves the file into it.
# Safe to double-click on macOS — keeps the Terminal window open on completion.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GRADING_DIR="$SCRIPT_DIR/grading"

if [ ! -d "$GRADING_DIR" ]; then
  echo "Error: grading directory not found at $GRADING_DIR"
  read -n 1 -s -r -p "Press any key to close..."
  exit 1
fi

moved=0
for mdfile in "$GRADING_DIR"/*.md; do
  [ -f "$mdfile" ] || continue

  name="$(basename "$mdfile" .md)"
  target_dir="$GRADING_DIR/$name"

  if [ ! -d "$target_dir" ]; then
    mkdir -p "$target_dir"
    mv "$mdfile" "$target_dir/annotations.md"
    echo "Created $name/ and moved $name.md into it as annotations.md."
    moved=$((moved + 1))
  fi
done

if [ "$moved" -eq 0 ]; then
  echo "No loose markdown files to move."
else
  echo "Done. Moved $moved file(s)."
fi

read -n 1 -s -r -p "Press any key to close..."
