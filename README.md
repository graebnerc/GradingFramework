# Thesis Grading Framework

Annotation-driven grading for academic theses. Annotate student work on your tablet with tagged comments, export the annotations, and the framework produces a professional `.docx` grading report on your university letterhead.

## Workflow

```bash
# 1. Initialize a student folder
python grade.py init "Doe_Hausarbeit"

# 2. Export PDF Expert annotations → paste into grading/Doe_Hausarbeit/annotations.md

# 3. Parse annotations and pre-populate scores
python grade.py parse "Doe_Hausarbeit"

# 4. Review and adjust scores in grading/Doe_Hausarbeit/ratings.yml

# 5. Render the report
python grade.py render "Doe_Hausarbeit" --lang de

# Or run parse + render in one step:
python grade.py pipeline "Doe_Hausarbeit" --lang de

# After grading is done, archive the student folder:
python grade.py cleanup "Doe_Hausarbeit"
python grade.py cleanup-all   # moves everything at once
```

## Annotation Tags

In PDF Expert, start each note with a dimension tag and valence:

```
ARG+   Überzeugende übergeordnete Story
MET~   Methode wird erwähnt, aber nicht systematisch hergeleitet
CRF.citation-  Quellenangaben im Literaturverzeichnis unvollständig
```

**Dimensions:** 

- `ARG` (argumentation)
- `MET` (methodology)
- `LIT` (literature)
- `RES` (results)
- `REF` (reflection)
- `CRF` (craft)
- `IND` (independence)

**Valence:** 

- `++` strong positive
- `+` positive
- `~` neutral
- `-` negative 
- `--` strong negative

**Metadata tags** (extracted, not scored):

```
NAME Jane Doe
TIT  Material Witnesses and Scientific Practice
```

If NAME/TIT are missing, the report uses "XXX" as placeholder.

Highlights and untagged notes are kept as context in the report appendix.

## File Layout

```
GradingFramework/
├── grade.py              # CLI (init, parse, render, pipeline, cleanup)
├── config.yml            # Author, institution, default language, score defaults
├── rubric.yml            # Dimensions, weights, sub-criteria
├── requirements.txt      # pyyaml, click, jinja2, python-docx
├── scripts/
│   ├── parser.py         # Markdown annotations → structured data
│   ├── scoring.py        # Score computation + pre-population from sentiment
│   └── docx_report.py    # python-docx report builder
├── templates/
│   └── Muster.docx       # University letterhead template
├── locales/
│   ├── en.yml            # English strings
│   └── de.yml            # German strings
├── example/
│   └── annotations.md    # Sample annotation export
├── grading/              # Active student folders (one per thesis)
│   └── Doe_Hausarbeit/
│       ├── annotations.md
│       ├── ratings.yml
│       └── report.docx          ← generated
└── complete/             # Archived after cleanup
```

**Where to put files:**

- Your university `.docx` template goes in `templates/Muster.docx` — include a `<Start editing here>` placeholder where report content should begin
- Student annotation exports go in `grading/<name>/annotations.md`
- Generated reports appear in the same student folder as `report.docx`
- After grading, `cleanup` moves the folder to `complete/`

## Scoring

Scores range from 0 (insufficient) to 3 (excellent). When no annotations exist for a dimension, the default score is 1.5 — a thesis with nothing remarkable gets an average grade. Annotation sentiment pre-populates the scores, which you can then adjust manually in `ratings.yml`. The overall score is a weighted sum of all dimensions.

## Setup

```bash
pip install -r requirements.txt
```

Requires Python 3.9+. Edit `config.yml` to set your name, institution, and preferred language.
