"""
parser.py — Parse PDF Expert annotation exports (Markdown) into structured data.

Annotation format expected:
    # Annotation Summary of Doe_Hausarbeit.pdf
    *Highlight [page 3]:* Some highlighted text
    *Note [page 4]:* ARG+ Überzeugende übergeordnete Story
    *Note [page 5]:* MET.limitations- Grenzen nicht diskutiert

Tag syntax:
    DIM[.sub_criterion] VALENCE comment_text
    where DIM    ∈ {ARG, MET, LIT, RES, REF, CRF, IND}
          VALENCE ∈ {++, +, ~, -, --}
          sub_criterion is optional (e.g., ARG.logic+)

Metadata tags (no valence, consumed but not scored):
    NAME Jane Doe          → parsed into metadata["student_name"]
    TIT  Material Witnesses → parsed into metadata["thesis_title"]
"""

import re
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict
from pathlib import Path

DIMENSIONS = ["ARG", "MET", "LIT", "RES", "REF", "CRF", "IND"]

# Metadata tags — not grading dimensions; extracted to pre-fill student info.
# Usage:  *Note [page 1]:* NAME Jane Doe
#         *Note [page 1]:* TIT Material Witnesses and Scientific Practice
META_TAGS = {"NAME": "student_name", "TIT": "thesis_title"}

# Pre-compile patterns
_HEADER_RE = re.compile(
    r"^#\s*Annotation\s+Summary\s+of\s+(.+?)\.?\s*$", re.MULTILINE
)

# Matches:  *Note [page 4]:* content...
# Captures: (type, page_number, content_until_next_annotation_or_end)
_ANNOTATION_RE = re.compile(
    r"\*(\w[\w\s]*?)\s*\[page\s*(\d+)\]:\*\s*(.*?)(?=\n\s*\*\w[\w\s]*?\s*\[page|\n#{1,3}\s|\Z)",
    re.DOTALL,
)

# Matches:  ARG+ ..., MET.limitations-- ..., CRF~ ...
_TAG_RE = re.compile(
    r"^(" + "|".join(DIMENSIONS) + r")"  # dimension
    r"(?:\.([\w]+))?"                     # optional .sub_criterion
    r"\s*(\+\+?|--?|~|[?0])"             # valence (? and 0 treated as neutral)
    r"\s*(.*)",                           # comment text
    re.DOTALL,
)

# Matches metadata tags:  NAME Jane Doe   or   TIT Some Title
_META_RE = re.compile(
    r"^(" + "|".join(META_TAGS.keys()) + r")\s+(.*)",
    re.DOTALL,
)


@dataclass
class Annotation:
    """A single parsed annotation."""
    type: str                          # Note, Highlight, Underline, etc.
    page: int
    dimension: Optional[str] = None    # ARG, MET, ...
    sub_criterion: Optional[str] = None
    valence: Optional[str] = None      # ++, +, ~, -, --
    valence_weight: float = 0.0        # numeric: +2, +1, 0, -1, -2
    text: str = ""
    raw: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ParseResult:
    """Structured output from parsing an annotations file."""
    source_pdf: str
    annotations: List[Annotation]

    # Convenience aggregations
    by_dimension: Dict[str, List[Annotation]] = field(default_factory=dict)
    untagged: List[Annotation] = field(default_factory=list)

    # Metadata extracted from NAME / TIT tags
    metadata: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "source_pdf": self.source_pdf,
            "metadata": self.metadata,
            "annotations": [a.to_dict() for a in self.annotations],
            "summary": {
                dim: {
                    "count": len(anns),
                    "positive": sum(1 for a in anns if a.valence_weight > 0),
                    "negative": sum(1 for a in anns if a.valence_weight < 0),
                    "neutral": sum(1 for a in anns if a.valence_weight == 0),
                }
                for dim, anns in self.by_dimension.items()
            },
            "untagged_count": len(self.untagged),
        }


def _valence_to_weight(valence: Optional[str]) -> float:
    """Convert valence symbol to numeric weight."""
    return {
        "++": 2.0,
        "+": 1.0,
        "~": 0.0,
        "?": 0.0,
        "0": 0.0,
        "-": -1.0,
        "--": -2.0,
    }.get(valence, 0.0)


def parse_annotations(md_path: Path) -> ParseResult:
    """
    Parse a PDF Expert Markdown annotation export.

    Parameters
    ----------
    md_path : Path
        Path to the .md annotation file.

    Returns
    -------
    ParseResult with all annotations, grouped by dimension.
    """
    text = md_path.read_text(encoding="utf-8")

    # --- Extract source PDF name from header ---
    header_match = _HEADER_RE.search(text)
    source_pdf = header_match.group(1).strip() if header_match else md_path.stem

    # --- Parse individual annotations ---
    annotations: List[Annotation] = []
    metadata: Dict[str, str] = {}

    for match in _ANNOTATION_RE.finditer(text):
        ann_type = match.group(1).strip()
        page = int(match.group(2))
        content = match.group(3).strip()

        # 1. Check for metadata tags (NAME, TIT) — consume, don't add as annotation
        meta_match = _META_RE.match(content)
        if meta_match:
            meta_key = meta_match.group(1)          # NAME or TIT
            meta_value = meta_match.group(2).strip()
            metadata[META_TAGS[meta_key]] = meta_value
            continue

        # 2. Try to extract a dimension tag
        tag_match = _TAG_RE.match(content)

        if tag_match:
            dimension = tag_match.group(1)
            sub_criterion = tag_match.group(2)  # may be None
            valence = tag_match.group(3)
            comment_text = tag_match.group(4).strip()
        else:
            dimension = None
            sub_criterion = None
            valence = None
            comment_text = content

        annotations.append(
            Annotation(
                type=ann_type,
                page=page,
                dimension=dimension,
                sub_criterion=sub_criterion,
                valence=valence,
                valence_weight=_valence_to_weight(valence),
                text=comment_text,
                raw=content,
            )
        )

    # --- Group by dimension ---
    by_dimension: Dict[str, List[Annotation]] = {dim: [] for dim in DIMENSIONS}
    untagged: List[Annotation] = []

    for ann in annotations:
        if ann.dimension and ann.dimension in by_dimension:
            by_dimension[ann.dimension].append(ann)
        elif ann.dimension is None:
            untagged.append(ann)

    return ParseResult(
        source_pdf=source_pdf,
        annotations=annotations,
        by_dimension=by_dimension,
        untagged=untagged,
        metadata=metadata,
    )
