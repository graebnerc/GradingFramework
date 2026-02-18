#!/usr/bin/env python3
"""
grade.py — CLI entry point for the Thesis Grading Framework.

Usage:
    python grade.py init     "Doe_Hausarbeit" --student "Jane Doe" --title "Title"
    python grade.py parse    "Doe_Hausarbeit"
    python grade.py render   "Doe_Hausarbeit" --lang de
    python grade.py pipeline "Doe_Hausarbeit" --lang de   # parse + render in one step
"""

import sys
from pathlib import Path

import click
import yaml

# Ensure the framework root is on the path
FRAMEWORK_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(FRAMEWORK_DIR))

from scripts.parser import parse_annotations
from scripts.scoring import compute_scores, generate_ratings_template
from scripts.docx_report import build_docx_report


def _load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _save_yaml(data: dict, path: Path):
    """Save YAML with clean formatting."""
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(
            data, f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=120,
        )


def _get_config() -> dict:
    return _load_yaml(FRAMEWORK_DIR / "config.yml")


def _get_rubric() -> dict:
    return _load_yaml(FRAMEWORK_DIR / "rubric.yml")


def _get_locale(lang: str) -> dict:
    locale_path = FRAMEWORK_DIR / "locales" / f"{lang}.yml"
    if not locale_path.exists():
        click.echo(f"  ⚠ Locale '{lang}' not found, falling back to 'en'.")
        locale_path = FRAMEWORK_DIR / "locales" / "en.yml"
    return _load_yaml(locale_path)


def _student_dir(name: str, config: dict) -> Path:
    grading_dir = FRAMEWORK_DIR / config.get("grading_directory", "grading")
    return grading_dir / name


def _empty_parse_result(name: str):
    from scripts.parser import ParseResult, DIMENSIONS
    return ParseResult(
        source_pdf=name,
        annotations=[],
        by_dimension={dim: [] for dim in DIMENSIONS},
        untagged=[],
    )


# ─── CLI ─────────────────────────────────────────────────────

@click.group()
def cli():
    """Thesis Grading Framework — automate annotation-based grading."""
    pass


@cli.command()
@click.argument("name")
@click.option("--student", "-s", default="", help="Student's full name.")
@click.option("--title", "-t", default="", help="Thesis title.")
@click.option("--course", "-c", default="", help="Course name.")
@click.option("--semester", default="", help="Semester (e.g., WS 2025/26).")
def init(name, student, title, course, semester):
    """Initialize a new grading folder for a student."""
    config = _get_config()
    student_dir = _student_dir(name, config)
    student_dir.mkdir(parents=True, exist_ok=True)

    # Create a blank annotations.md placeholder
    ann_path = student_dir / "annotations.md"
    if not ann_path.exists():
        ann_path.write_text(
            f"# Annotation Summary of {name}.pdf\n\n"
            "<!-- Paste your PDF Expert annotation export here -->\n",
            encoding="utf-8",
        )

    # Create a starter ratings.yml
    ratings_path = student_dir / "ratings.yml"
    if not ratings_path.exists():
        rubric = _get_rubric()
        empty_result = _empty_parse_result(name)
        template = generate_ratings_template(empty_result, rubric, config)
        template["student"]["name"] = student
        template["student"]["title"] = title
        template["student"]["course"] = course
        template["student"]["semester"] = semester
        _save_yaml(template, ratings_path)

    click.echo(f"  ✓ Initialized: {student_dir}")
    click.echo(f"    1. Paste annotation export into: annotations.md")
    click.echo(f"    2. Run: python grade.py parse \"{name}\"")


@cli.command()
@click.argument("name")
def parse(name):
    """Parse annotations and pre-populate ratings from sentiments."""
    config = _get_config()
    rubric = _get_rubric()
    student_dir = _student_dir(name, config)

    ann_path = student_dir / "annotations.md"
    if not ann_path.exists():
        click.echo(f"  ✗ No annotations.md found in {student_dir}")
        click.echo(f"    Export your PDF Expert annotations and save them there.")
        raise SystemExit(1)

    # Parse
    result = parse_annotations(ann_path)
    click.echo(f"  ✓ Parsed {len(result.annotations)} annotations from: {result.source_pdf}")
    for dim, anns in result.by_dimension.items():
        if anns:
            pos = sum(1 for a in anns if a.valence_weight > 0)
            neg = sum(1 for a in anns if a.valence_weight < 0)
            click.echo(f"    {dim}: {len(anns)} annotations ({pos}+ / {neg}-)")

    if result.untagged:
        click.echo(f"    Untagged: {len(result.untagged)} highlights/notes")

    # Save parsed data as JSON (for debugging / downstream use)
    import json
    parsed_json = student_dir / "parsed_annotations.json"
    with open(parsed_json, "w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)

    # Generate / update ratings template
    ratings_path = student_dir / "ratings.yml"
    existing = _load_yaml(ratings_path) if ratings_path.exists() else None
    template = generate_ratings_template(result, rubric, config, existing)
    _save_yaml(template, ratings_path)

    click.echo(f"  ✓ Ratings template updated: {ratings_path}")
    click.echo(f"    Review scores and add comments, then run:")
    click.echo(f"    python grade.py render \"{name}\"")


@cli.command()
@click.argument("name")
@click.option("--lang", "-l", default=None, help="Report language: en or de.")
def render(name, lang):
    """Render the final .docx grading report."""
    config = _get_config()
    rubric = _get_rubric()
    student_dir = _student_dir(name, config)

    lang = lang or config.get("default_language", "en")
    locale = _get_locale(lang)

    # Load ratings
    ratings_path = student_dir / "ratings.yml"
    if not ratings_path.exists():
        click.echo(f"  ✗ No ratings.yml found. Run 'parse' first.")
        raise SystemExit(1)
    ratings = _load_yaml(ratings_path)

    # Load parsed annotations
    ann_path = student_dir / "annotations.md"
    if ann_path.exists():
        result = parse_annotations(ann_path)
    else:
        result = _empty_parse_result(name)

    # Compute scores
    grading_result = compute_scores(result, rubric, ratings, config, lang)

    click.echo(f"  ─ Overall score: {grading_result.overall_score:.2f} / 3.00 "
               f"({grading_result.overall_percentage:.1f}%)")
    for d in grading_result.dimensions:
        click.echo(f"    {d.code}: {d.score:.1f} / 3.0 (weight {d.weight*100:.0f}%)")

    # Build .docx report
    output_path = build_docx_report(
        result=grading_result,
        rubric=rubric,
        config=config,
        locale=locale,
        lang=lang,
        output_dir=student_dir,
        framework_dir=FRAMEWORK_DIR,
    )

    click.echo(f"\n  ✓ Report generated: {output_path}")


@cli.command()
@click.argument("name")
@click.option("--lang", "-l", default=None, help="Report language: en or de.")
def pipeline(name, lang):
    """Run the full pipeline: parse → render (for when annotations are ready)."""
    ctx = click.get_current_context()
    ctx.invoke(parse, name=name)
    click.echo()
    ctx.invoke(render, name=name, lang=lang)


@cli.command()
@click.argument("name")
def cleanup(name):
    """Move a completed student folder from grading/ to complete/."""
    config = _get_config()
    student_dir = _student_dir(name, config)

    if not student_dir.exists():
        click.echo(f"  ✗ Student folder not found: {student_dir}")
        raise SystemExit(1)

    complete_dir = FRAMEWORK_DIR / "complete"
    complete_dir.mkdir(exist_ok=True)

    target = complete_dir / name
    if target.exists():
        click.echo(f"  ✗ Target already exists: {target}")
        click.echo(f"    Remove or rename it first.")
        raise SystemExit(1)

    import shutil
    shutil.move(str(student_dir), str(target))
    click.echo(f"  ✓ Moved {name} → complete/{name}")


@cli.command(name="cleanup-all")
def cleanup_all():
    """Move ALL student folders from grading/ to complete/."""
    config = _get_config()
    grading_dir = FRAMEWORK_DIR / config.get("grading_directory", "grading")

    if not grading_dir.exists():
        click.echo("  ✗ No grading directory found.")
        raise SystemExit(1)

    subdirs = [d for d in grading_dir.iterdir() if d.is_dir()]
    if not subdirs:
        click.echo("  No student folders to clean up.")
        return

    complete_dir = FRAMEWORK_DIR / "complete"
    complete_dir.mkdir(exist_ok=True)

    import shutil
    for student_dir in subdirs:
        name = student_dir.name
        target = complete_dir / name
        if target.exists():
            click.echo(f"  ⚠ Skipping {name} (already in complete/)")
            continue
        shutil.move(str(student_dir), str(target))
        click.echo(f"  ✓ Moved {name} → complete/{name}")


if __name__ == "__main__":
    cli()
