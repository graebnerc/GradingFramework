# Thesis Grading Framework

An annotation-driven grading tool for academic theses. Annotate a PDF directly in PDF Expert using a simple tag syntax, export the annotations as Markdown, and the framework computes scores and generates a professional `.docx` grading report — in English or German.

Feedback, rubric suggestions, and ideas for improvement are very welcome in the [GitHub Discussions](../../discussions).

---

## How it works

1. **Annotate** the thesis in PDF Expert using dimension tags (`ARG+`, `MET-`, etc.)
2. **Export** the annotations as Markdown and paste them into `annotations.md`
3. **Run** `grade.py pipeline` — the framework parses the annotations, pre-populates scores from sentiment, and renders a `.docx` report
4. **Review** `ratings.yml` to adjust scores and add written feedback, then re-render

Scores are pre-populated automatically from your annotation sentiments, but every score can be manually overridden. The output is a fully formatted report on your institution's letterhead.

---

## Installation

### Requirements

- Python 3.9 or newer
- [PDF Expert](https://pdfexpert.com) for annotating theses and exporting to Markdown
- A `.docx` letterhead template with a `<Start editing here>` placeholder (see [Template setup](#template-setup))

### Setup

```bash
# Clone the repository
git clone https://github.com/your-username/GradingFramework.git
cd GradingFramework

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Edit `config.yml` to set your name, institution, and preferences:

```yaml
author: "Prof. Dr. Jane Smith"
institution: "Your University"
default_language: "en"       # "en" or "de"
reference_doc: "templates/reference.docx"
show_sub_tables: false        # true = always show sub-criteria tables in the report
default_score: 1.5            # score when a dimension has no annotations (midpoint)
```

### Template setup

Place your university's Word letterhead as `templates/reference.docx`. The document must contain the text `<Start editing here>` at the exact position where the report content should begin. Everything after that placeholder will be replaced by the generated content.

---

## Workflow

### 1. Initialize a student folder

```bash
python grade.py init "Doe_Thesis"
```

This creates `grading/Doe_Thesis/` with a blank `annotations.md` and a starter `ratings.yml`.

For an interactive prompt (double-clickable on macOS), use:

```bash
./init_student.sh
```

You can enter multiple folder names — one per line, or separated by semicolons.

### 2. Annotate the thesis

Open the thesis PDF in PDF Expert and add **Notes** using the tag syntax described below. When finished, export the annotations (File → Export → Annotations → Markdown) and paste the entire export into `grading/Doe_Thesis/annotations.md`.

### 3. Parse and render

```bash
# Parse + render in one step
python grade.py pipeline "Doe_Thesis" --lang de

# Or run the steps separately:
python grade.py parse  "Doe_Thesis"
python grade.py render "Doe_Thesis" --lang de
```

### 4. Review and adjust

Open `grading/Doe_Thesis/ratings.yml`. The `_auto_score` field shows what the system computed from your annotations. Set a manual `score` for any dimension where the auto-score does not match your judgment, and fill in `comment` text for each dimension. Then re-run `render`.

### 5. Archive

```bash
python grade.py cleanup "Doe_Thesis"
```

Moves the folder from `grading/` to `complete/`.

### Batch processing

```bash
./run_all_de.sh     # run pipeline for all student folders (German)
./run_all_en.sh     # run pipeline for all student folders (English)
./cleanup_all.sh    # archive all folders
```

All shell scripts are double-clickable on macOS and keep the Terminal window open for review.

---

## Annotation tag syntax

All tags go into **Notes** in PDF Expert. The general format is:

```
DIM[.sub_criterion] VALENCE   your comment text
```

### Dimensions

| Tag | Name | Weight |
|-----|------|--------|
| `ARG` | Argumentation & Logic | 20% |
| `MET` | Research Design & Methods | 15% |
| `LIT` | Literature & Theory | 15% |
| `RES` | Results & Analysis | 20% |
| `REF` | Critical Reflection | 10% |
| `CRF` | Academic Craft | 20% |
| `IND` | Independence & Difficulty | — (adjustment only, not weighted) |

Tags are case-insensitive.

### Valence markers

| Symbol | Meaning | Score weight |
|--------|---------|--------------|
| `++` | strong strength | +2 |
| `+` | strength | +1 |
| `~` | neutral observation | 0 |
| `-` | weakness | −1 |
| `--` | strong weakness | −2 |

### Examples

```
ARG+    The research question is stated clearly from the outset.
MET-    Methodological limitations are not discussed.
LIT++   Impressive command of the theoretical literature.
RES~    Findings are presented but not interpreted in depth.
CRF.citation-   Page numbers missing in several citations.
IND+    Unusually ambitious topic for a Bachelor's thesis.
```

### Sub-criterion targeting

Append `.sub_criterion_key` to direct an annotation at a specific sub-criterion:

```
ARG.thesis_question+    Strong, precise research question.
MET.limitations-        Methodological boundaries not reflected.
CRF.structure+          Clear red thread throughout the thesis.
```

Sub-criterion keys per dimension:

| Dimension | Sub-criteria |
|-----------|-------------|
| `ARG` | `thesis_question`, `logical_coherence`, `evidence_support`, `conclusion` |
| `MET` | `appropriateness`, `explanation`, `limitations`, `transparency` |
| `LIT` | `relevance`, `framework`, `engagement`, `state_of_research` |
| `RES` | `presentation`, `depth`, `addresses_question`, `data_use` |
| `REF` | `self_critical`, `alternatives`, `implications`, `honesty` |
| `CRF` | `structure`, `language`, `citation`, `formatting` |
| `IND` | `ambition`, `originality`, `independence` |

### Metadata tags

These special tags carry information into the report but are not scored. They can appear on any page.

| Tag | Effect |
|-----|--------|
| `NAME Jane Doe` | Student's full name — pre-fills `ratings.yml` |
| `TIT Title of the Thesis` | Thesis title — pre-fills `ratings.yml` |
| `SUM Short summary sentence.` | Appended to the intro paragraph on the cover page |
| `GRADE 2.0` | Replaces the `NOTE` placeholder in the grade line |

Example annotations using metadata tags:

```
*Note [page 1]:* NAME Jane Doe
*Note [page 1]:* TIT Material Witnesses and Scientific Practice
*Note [page 1]:* SUM The thesis develops a coherent argument and engages well with the literature.
*Note [page 1]:* GRADE 2.0
```

---

## Scoring logic

### Pre-population from annotations

When you run `parse`, each dimension receives an auto-score derived from the valence weights of its annotations:

```
sentiment = sum(valence_weights) / (2 × count of scored annotations)   ∈ [−1, 1]
score     = default_score + sentiment × default_score                   ∈ [0, 3]
```

With `default_score: 1.5`, a dimension with no annotations gets 1.5 — the midpoint, representing an average thesis. Positive annotations pull the score up; negative annotations pull it down.

### Manual overrides

Set `score` explicitly in `ratings.yml` to override the auto-score for a dimension. Sub-criteria scores can also be set individually. Manual values are preserved when you re-run `parse`.

### Overall score

```
overall_score = Σ (dimension_score × weight)   for ARG, MET, LIT, RES, REF, CRF
overall_pct   = (overall_score / 3.0) × 100
```

### Adjustment dimension (IND)

`IND` is not included in the weighted calculation. It appears as a separate entry in the report — a qualitative signal for exceptional independence or unusual topic difficulty. It is only shown if you have added IND annotations or set a manual score.

---

## ratings.yml reference

After running `parse`, `ratings.yml` has this structure:

```yaml
student:
  name: Jane Doe          # from NAME tag, or set manually
  title: Thesis Title     # from TIT tag, or set manually
  course: ""
  semester: ""
  date: ""

dimensions:
  ARG:
    score: null           # null = auto-computed; set a number to override
    comment: ""           # your written feedback for this dimension
    sub_criteria:
      thesis_question: null   # null = inherit dimension score
      logical_coherence: null
      evidence_support: null
      conclusion: null
    _auto_score: 2.15     # informational — computed from annotations
    _annotation_count: 5  # informational — number of ARG annotations

  # MET, LIT, RES, REF, CRF, IND follow the same structure

overall_comment: ""       # optional paragraph shown at the top of the detailed assessment
```

---

## Report structure

The generated `.docx` report contains:

**Cover page**
- Student name, thesis title, date
- Optional short summary (from `SUM` tag)
- Summary table: dimension, weight, score
- Overall score and percentage
- Grade (from `GRADE` tag, or `NOTE` placeholder)
- Closing and grader signature

**Detailed assessment**
- Optional overall comment (from `ratings.yml`)
- One section per dimension: score, qualitative rating, written feedback, and a verbatim list of your annotations with page numbers
- Sub-criteria table shown when annotations target specific sub-criteria (or always, if `show_sub_tables: true` in `config.yml`)
- Adjustment dimension (IND) shown separately if used

**Appendix**
- All untagged highlights and notes, for context

Reports can be rendered in English (`--lang en`) or German (`--lang de`). The locale strings are in `locales/en.yml` and `locales/de.yml`.

---

## File layout

```
GradingFramework/
├── grade.py                  # CLI: init, parse, render, pipeline, cleanup
├── config.yml                # Author, institution, language, score defaults
├── rubric.yml                # Dimensions, weights, sub-criteria
├── requirements.txt          # Python dependencies
├── init_student.sh           # Interactive student folder initialization (macOS)
├── run_all_en.sh             # Batch pipeline — English (macOS)
├── run_all_de.sh             # Batch pipeline — German (macOS)
├── cleanup_all.sh            # Batch archive (macOS)
├── scripts/
│   ├── parser.py             # Markdown annotations → structured data
│   ├── scoring.py            # Score computation and pre-population
│   └── docx_report.py        # .docx report builder
├── locales/
│   ├── en.yml                # English UI strings
│   └── de.yml                # German UI strings
├── templates/
│   └── reference.docx        # University letterhead (add your own)
├── grading/                  # Active student folders
│   └── Doe_Thesis/
│       ├── annotations.md    # PDF Expert annotation export (you paste this)
│       ├── ratings.yml       # Scores and comments (auto-generated, you edit)
│       └── Doe_Thesis_Report.docx   ← generated
└── complete/                 # Archived folders after cleanup
```

---

## CLI reference

```
python grade.py init        NAME              Create a new student folder
python grade.py parse       NAME              Parse annotations, update ratings.yml
python grade.py render      NAME [--lang de]  Render the .docx report
python grade.py pipeline    NAME [--lang de]  parse + render in one step
python grade.py cleanup     NAME              Move folder to complete/
python grade.py cleanup-all                   Move all folders to complete/
```

---

## Extending the framework

**Adding a language:** Create `locales/xx.yml` following the structure of `en.yml`, then pass `--lang xx` when rendering.

**Modifying the rubric:** Edit `rubric.yml`. Adjust weights (must sum to 1.0 across non-adjustment dimensions), rename sub-criteria, or add new ones. Changes take effect on the next `parse` run.

**Adding an adjustment dimension:** Set `weight: 0` and `adjustment: true` on any rubric dimension. It will be excluded from the weighted score and shown separately in the report.

---

## Contributing

Suggestions for improving the rubric, the scoring logic, or the workflow are very welcome. Please open a thread in [GitHub Discussions](../../discussions) — especially regarding:

- Rubric dimensions or sub-criteria that should be added, removed, or reweighted
- Alternative scoring or pre-population approaches
- Support for annotation exports from tools other than PDF Expert
- Additional report layouts or output formats

Bug reports and pull requests are welcome via [GitHub Issues](../../issues).

---
