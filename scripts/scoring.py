"""
scoring.py — Compute dimension scores from annotations and manual ratings.

Scoring logic:
  - Each sub-criterion is scored 0–3 (insufficient → excellent).
  - Dimension score = mean of sub-criteria scores × dimension weight.
  - Overall score = sum of weighted dimension scores.

Pre-population:
  - If annotations exist for a dimension, compute a sentiment score
    from valence weights and map it to the 0–3 scale.
  - If NO annotations exist, default to config.default_score (1.5).
  - Manual ratings in ratings.yml ALWAYS override pre-populated values.

The "nothing remarkable = average grade" principle:
  default_score 1.5 on a 0–3 scale ≈ 50% ≈ midpoint.
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, field

from scripts.parser import Annotation, ParseResult, DIMENSIONS


DEFAULT_SCORE = 1.5  # overridden by config if loaded


@dataclass
class SubCriterionScore:
    key: str
    name: str
    score: float          # 0–3
    source: str           # "auto" | "manual"


@dataclass
class DimensionScore:
    code: str
    name: str
    weight: float
    score: float                              # 0–3 (mean of sub-criteria)
    weighted_score: float                     # score × weight
    source: str                               # "auto" | "manual" | "mixed"
    comment: str
    sub_criteria: List[SubCriterionScore]
    annotation_count: int
    positive_count: int
    negative_count: int


@dataclass
class GradingResult:
    student_name: str
    thesis_title: str
    course: str
    semester: str
    date: str
    overall_score: float              # 0–3
    overall_percentage: float         # 0–100
    overall_comment: str
    dimensions: List[DimensionScore]
    annotations: List[dict]           # all annotations as dicts
    untagged_annotations: List[dict]


def _prepopulate_score(annotations: List[Annotation], default: float) -> float:
    """
    Compute a pre-populated score from annotation sentiments.

    Formula:
        scored = annotations with non-zero valence weight
        sentiment = sum(weights) / (2 × count(scored))   → normalized to [-1, 1]
        score = default + sentiment × default             → maps to [0, 3]

    If no scored annotations exist, returns `default`.
    """
    if not annotations:
        return default

    scored = [a for a in annotations if a.valence_weight != 0]
    if not scored:
        return default

    weight_sum = sum(a.valence_weight for a in scored)
    # Normalize: max possible per annotation is ±2, so divide by 2*count
    sentiment = weight_sum / (2.0 * len(scored))  # ∈ [-1, 1]
    score = default + sentiment * default
    return max(0.0, min(3.0, round(score, 2)))


def compute_scores(
    parse_result: ParseResult,
    rubric: dict,
    ratings: dict,
    config: dict,
    lang: str = "en",
) -> GradingResult:
    """
    Compute final grading scores by merging annotations with manual ratings.

    Parameters
    ----------
    parse_result : ParseResult
        Output from parser.parse_annotations().
    rubric : dict
        Loaded rubric.yml content.
    ratings : dict
        Loaded ratings.yml content (student's manual ratings).
    config : dict
        Loaded config.yml content.
    lang : str
        Language code for dimension/sub-criterion names.

    Returns
    -------
    GradingResult with all computed scores.
    """
    default = config.get("default_score", DEFAULT_SCORE)
    name_key = f"name_{lang}"
    dim_defs = rubric["dimensions"]
    manual_dims = ratings.get("dimensions", {})
    student_info = ratings.get("student", {})

    dimension_scores: List[DimensionScore] = []

    for code in DIMENSIONS:
        dim_def = dim_defs[code]
        dim_weight = dim_def["weight"]
        dim_name = dim_def.get(name_key, dim_def.get("name_en", code))
        dim_annotations = parse_result.by_dimension.get(code, [])
        manual = manual_dims.get(code, {})

        # --- Sub-criteria scoring ---
        sub_scores: List[SubCriterionScore] = []
        sub_defs = dim_def.get("sub_criteria", {})

        # Pre-populate dimension-level score from annotations
        auto_score = _prepopulate_score(dim_annotations, default)

        for sub_key, sub_def in sub_defs.items():
            sub_name = sub_def.get(name_key, sub_def.get("name_en", sub_key))
            manual_sub = manual.get("sub_criteria", {}) or {}

            if sub_key in manual_sub and manual_sub[sub_key] is not None:
                # Manual override for this sub-criterion
                sub_score_val = float(manual_sub[sub_key])
                source = "manual"
            else:
                # Check if any annotations target this sub-criterion
                sub_annotations = [
                    a for a in dim_annotations if a.sub_criterion == sub_key
                ]
                if sub_annotations:
                    sub_score_val = _prepopulate_score(sub_annotations, default)
                    source = "auto"
                else:
                    # Fall back to dimension-level auto score
                    sub_score_val = auto_score
                    source = "auto"

            sub_scores.append(
                SubCriterionScore(
                    key=sub_key,
                    name=sub_name,
                    score=round(sub_score_val, 2),
                    source=source,
                )
            )

        # --- Dimension score: manual override or mean of sub-criteria ---
        if "score" in manual and manual["score"] is not None:
            dim_score_val = float(manual["score"])
            dim_source = "manual"
        elif sub_scores:
            dim_score_val = sum(s.score for s in sub_scores) / len(sub_scores)
            sources = set(s.source for s in sub_scores)
            dim_source = "mixed" if len(sources) > 1 else sources.pop()
        else:
            dim_score_val = auto_score
            dim_source = "auto"

        dim_score_val = round(dim_score_val, 2)
        comment = manual.get("comment", "") or ""

        n_pos = sum(1 for a in dim_annotations if a.valence_weight > 0)
        n_neg = sum(1 for a in dim_annotations if a.valence_weight < 0)

        dimension_scores.append(
            DimensionScore(
                code=code,
                name=dim_name,
                weight=dim_weight,
                score=dim_score_val,
                weighted_score=round(dim_score_val * dim_weight, 4),
                source=dim_source,
                comment=comment,
                sub_criteria=sub_scores,
                annotation_count=len(dim_annotations),
                positive_count=n_pos,
                negative_count=n_neg,
            )
        )

    # --- Overall score ---
    overall = sum(d.weighted_score for d in dimension_scores)
    # Normalize: max possible weighted score = 3.0 × sum(weights) = 3.0 × 1.0 = 3.0
    overall_pct = round((overall / 3.0) * 100, 1)

    return GradingResult(
        student_name=student_info.get("name", ""),
        thesis_title=student_info.get("title", ""),
        course=student_info.get("course", ""),
        semester=student_info.get("semester", ""),
        date=student_info.get("date", ""),
        overall_score=round(overall, 2),
        overall_percentage=overall_pct,
        overall_comment=ratings.get("overall_comment", "") or "",
        dimensions=dimension_scores,
        annotations=[a.to_dict() for a in parse_result.annotations],
        untagged_annotations=[a.to_dict() for a in parse_result.untagged],
    )


def generate_ratings_template(
    parse_result: ParseResult,
    rubric: dict,
    config: dict,
    existing_ratings: Optional[dict] = None,
) -> dict:
    """
    Generate a ratings.yml template, pre-populated from annotations.

    If existing_ratings is provided, manual values are preserved
    (only auto-generated values are updated).
    """
    default = config.get("default_score", DEFAULT_SCORE)
    dim_defs = rubric["dimensions"]
    existing_dims = (existing_ratings or {}).get("dimensions", {})

    # Preserve student info if it exists; enrich from metadata tags
    meta = getattr(parse_result, "metadata", {}) or {}

    student = {}
    if existing_ratings and "student" in existing_ratings:
        student = dict(existing_ratings["student"])
    else:
        student = {
            "name": "",
            "title": "",
            "course": "",
            "semester": "",
            "date": "",
        }

    # Fill name / title from NAME and TIT annotation tags.
    # Only overwrite if the field is empty or still the placeholder "XXX".
    parsed_name = meta.get("student_name", "")
    parsed_title = meta.get("thesis_title", "")

    if parsed_name and student.get("name", "") in ("", "XXX"):
        student["name"] = parsed_name
    if parsed_title and student.get("title", "") in ("", "XXX", parse_result.source_pdf):
        student["title"] = parsed_title

    # Fall back to "XXX" so it's obvious something needs filling in
    if not student.get("name"):
        student["name"] = "XXX"
    if not student.get("title"):
        student["title"] = "XXX"

    dimensions = {}
    for code in DIMENSIONS:
        dim_def = dim_defs[code]
        dim_annotations = parse_result.by_dimension.get(code, [])
        existing = existing_dims.get(code, {})

        auto_score = _prepopulate_score(dim_annotations, default)

        # Sub-criteria
        sub_criteria = {}
        for sub_key in dim_def.get("sub_criteria", {}):
            existing_sub = (existing.get("sub_criteria") or {}).get(sub_key)
            if existing_sub is not None:
                sub_criteria[sub_key] = existing_sub  # preserve manual value
            else:
                sub_criteria[sub_key] = None  # null → inherits dimension score

        # Dimension score: preserve ONLY if user manually changed it
        # (i.e., it differs from both the default and any previous auto score)
        prev_auto = existing.get("_auto_score", default)
        existing_score = existing.get("score")
        if (
            existing_score is not None
            and existing_score != default
            and existing_score != prev_auto
        ):
            # User has manually edited the score — keep it
            score = existing_score
        else:
            score = auto_score

        dimensions[code] = {
            "score": score,
            "comment": existing.get("comment", ""),
            "sub_criteria": sub_criteria,
            "_auto_score": auto_score,  # informational; shows what the system computed
            "_annotation_count": len(dim_annotations),
        }

    return {
        "student": student,
        "dimensions": dimensions,
        "overall_comment": (existing_ratings or {}).get("overall_comment", ""),
    }
