#!/usr/bin/env bash
# Gesamte Bewertungspipeline (parse → render) für alle Studierenden in grading/
# Kann auf macOS per Doppelklick gestartet werden — Terminal bleibt offen.

export LANG=de_DE.UTF-8
export PYTHONIOENCODING=utf-8

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GRADING_DIR="$SCRIPT_DIR/grading"
PYTHON="$SCRIPT_DIR/venv/bin/python"

if [ ! -d "$GRADING_DIR" ]; then
  echo "Fehler: Verzeichnis grading nicht gefunden unter $GRADING_DIR"
  read -n 1 -s -r -p "Beliebige Taste drücken zum Schließen..."
  exit 1
fi

students=()
for d in "$GRADING_DIR"/*/; do
  [ -d "$d" ] && students+=("$(basename "$d")")
done

if [ ${#students[@]} -eq 0 ]; then
  echo "Keine Studierenden-Ordner in $GRADING_DIR gefunden"
  read -n 1 -s -r -p "Beliebige Taste drücken zum Schließen..."
  exit 0
fi

echo "Pipeline wird für ${#students[@]} Studierende(n) ausgeführt..."
echo

failed=0
for name in "${students[@]}"; do
  echo "════════════════════════════════════════"
  echo "  $name"
  echo "════════════════════════════════════════"
  if "$PYTHON" "$SCRIPT_DIR/grade.py" pipeline "$name" --lang de; then
    echo "  OK"
  else
    echo "  FEHLGESCHLAGEN (Exit-Code $?)"
    failed=$((failed + 1))
  fi
  echo
done

if [ "$failed" -eq 0 ]; then
  echo "Fertig. Alle ${#students[@]} Studierende(n) erfolgreich verarbeitet."
else
  echo "Fertig. $failed von ${#students[@]} Studierende(n) mit Fehlern."
fi

read -n 1 -s -r -p "Beliebige Taste drücken zum Schließen..."
