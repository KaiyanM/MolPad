"""Structured outputs of the decision-tree nodes (one model per LLM judgement)."""

from typing import Literal, Optional

from pydantic import BaseModel, Field

PATTERN_CRITERIA = ("increase", "decrease", "increase_and_decrease", "peak_at", "compare",
                    "color_divergence")
RIBBON_CRITERIA = ("tightest_ribbon", "widest_ribbon", "expanding_ribbon", "contracting_ribbon")
RIBBON_MEASURES = ("mean_width", "max_width", "area", "all")
COMPARE_TOOLS = ("opposite", "similar", "shifted", "diverging", "converging")
NETWORK_CRITERIA = ("most_edges", "strongest_edge", "isolated", "connected_pairs", "neighbours",
                    "connectivity", "components")


class Keywords(BaseModel):
    """Specific terms of the question that name something in the data."""
    keywords: list[str] = Field(description="terms copied from the question, one per item")


class Kind(BaseModel):
    """N0. What kind of question is this?"""
    kind: Literal["out_of_scope", "design", "data"]
    control: Optional[Literal["layout", "importance", "level1", "level2", "table"]] = Field(
        None, description="design only: the dashboard control the question is about")
    value: Optional[str] = Field(None, description="design only: the setting to showcase, e.g. 'circle'")
    reason: str = Field(description="one short sentence")


class Completeness(BaseModel):
    """N1. Is anything missing?"""
    status: Literal["ask", "assume_default", "use_current_selection", "ok"]
    note: str = Field("", description="what to ask, or the assumption that is made; empty for ok")


class Shape(BaseModel):
    """N2. Can it be answered in one pass?"""
    shape: Literal["direct", "evidence_chain"]


class SubClaims(BaseModel):
    """N2, evidence chain: the hypothesis split into direct questions."""
    sub_claims: list[str] = Field(description="2 to 4 direct questions, each answerable from the data alone")


class Filters(BaseModel):
    """N3. Which filters does the question set? Leave a slot empty when it does not apply."""
    cols: Optional[str] = Field(None, description="sample group to keep, e.g. 'A'")
    level1: list[str] = Field(default_factory=list, description="level-1 values used as a condition")
    level2: list[str] = Field(default_factory=list, description="level-2 values used as a condition")
    level3_column: Optional[str] = Field(None, description="level-3 table column that is filtered")
    level3_values: list[str] = Field(default_factory=list, description="ids to keep in that column")
    level3_has_annotation: bool = Field(False, description="keep rows that have any value in that column")
    external_concept: Optional[str] = Field(
        None, description="named gene family or function that level3_values were derived from")
    contrast: Literal["none", "level1", "level2", "with_and_without_level2"] = Field(
        "none", description="run the filter once per value of this slot, or with then without level 2")


class CurveSlice(BaseModel):
    """One side of a comparison: which stretch of the data a curve is read from."""
    subject: Optional[str] = Field(None, description="sample group, e.g. 'A'")
    start: Optional[str] = Field(None, description="first timepoint column of the stretch, e.g. 'A_1'")
    end: Optional[str] = Field(None, description="last timepoint column of the stretch, e.g. 'A_3'")


class SelectorStep(BaseModel):
    kind: Literal["pattern", "ribbon", "feature_number", "network", "feature_lookup", "given", "all"]
    criterion: Optional[Literal[PATTERN_CRITERIA + RIBBON_CRITERIA + NETWORK_CRITERIA]] = Field(
        None, description="required for pattern, ribbon and network")
    measure: Optional[Literal[RIBBON_MEASURES]] = Field(
        None, description="ribbon tightest / widest: the width measure the question names; "
                          "empty or 'all' when it is vague")
    subject: Optional[str] = Field(None, description="pattern / ribbon: sample group the shape is read in")
    timepoint: Optional[str] = Field(None, description="peak_at: exact timepoint column, e.g. 'C_5'")
    position: Optional[Literal["early", "mid", "late"]] = Field(
        None, description="peak_at: when no exact timepoint is named")
    tool: Optional[Literal[COMPARE_TOOLS]] = Field(
        None, description="compare: the relation looked for between the two curves")
    between: Optional[Literal["subjects", "windows", "clusters"]] = Field(
        None, description="compare: what the two curves are")
    a: Optional[CurveSlice] = Field(None, description="compare: first curve")
    b: Optional[CurveSlice] = Field(None, description="compare: second curve")
    top_n: Optional[int] = Field(None, description="how many clusters to keep, when the question says")
    threshold: Optional[str] = Field(
        None, description="network: 'current', 'max', 'min' or a number for the importance score")
    clusters: list[str] = Field(default_factory=list, description="given: clusters named by the user")


class Selector(BaseModel):
    """N4. How are the target clusters chosen? One step, or two when one selector follows another."""
    steps: list[SelectorStep]


class Descriptor(BaseModel):
    """N5. What is measured on the target clusters?"""
    pattern: bool = False
    level2: bool = False
    level3_column: Optional[str] = None
    level3_mode: Optional[Literal["frequency", "coverage", "list"]] = None
    weight: Optional[Literal["neighbours", "degree", "components"]] = None
    feature_number: bool = False


class Display(BaseModel):
    """N6. How should the dashboard show it?"""
    needs_focus: bool = Field(description="6a: the user must look at specific clusters to see the answer")
    network_area: bool = Field(description="6b: the slider must move, or the targets are defined by edges")
    grouping: Literal["together", "one_by_one"] = Field(description="6c, when there are several clusters")
    reason: str = Field(description="one short sentence")


class Messages(BaseModel):
    texts: list[str] = Field(description="one text per requested message, in the same order")
