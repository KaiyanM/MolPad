"""Structured outputs of the LLM calls (agent/frame.py): the frame of a question, its sub-frames,
the plan, and the messages."""

from typing import Literal, Optional

from pydantic import BaseModel, Field

from .module import controls, explainable, manifests, named
from ..modules.ribbon.detect import TIGHTNESS, TOOLS
from ..modules.stackbar.examples import EXAMPLE_FINDERS as _FINDERS

# The words a plan can use come from the modules: the criteria from their manifests, the rest
# from the code that runs them.
_CRITERIA = {kind: tuple(c) for m in manifests() for kind, c in m.criteria.items()}
PATTERN_CRITERIA = _CRITERIA["pattern"]
RIBBON_CRITERIA = _CRITERIA["ribbon"]
NETWORK_CRITERIA = _CRITERIA["network"]
RIBBON_MEASURES = TIGHTNESS + ("all",)     # one definition of ribbon width, or every one
COMPARE_TOOLS = TOOLS
EXAMPLE_FINDERS = tuple(_FINDERS)
SELECTOR_KINDS = named("selectors")     # how clusters are picked
MEASURES = named("measures")            # what is reported about them
CONTROLS = tuple(controls())            # controls of the page a question can be about


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
    start: Optional[str] = Field(None, description="first timepoint column of the stretch")
    end: Optional[str] = Field(None, description="last timepoint column of the stretch")


class SelectorStep(BaseModel):
    kind: Literal[SELECTOR_KINDS]
    criterion: Optional[Literal[PATTERN_CRITERIA + RIBBON_CRITERIA + NETWORK_CRITERIA]] = Field(
        None, description="required for pattern, ribbon and network")
    measure: Optional[Literal[RIBBON_MEASURES]] = Field(
        None, description="ribbon tightest / widest: the width measure the question names; "
                          "empty or 'all' when it is vague")
    subject: Optional[str] = Field(None, description="pattern / ribbon: sample group the shape is read in")
    timepoint: Optional[str] = Field(None, description="peak_at: exact timepoint column")
    position: Optional[Literal["early", "mid", "late"]] = Field(
        None, description="peak_at: when no exact timepoint is named")
    tool: Optional[Literal[COMPARE_TOOLS]] = Field(
        None, description="compare: the relation looked for between the two curves")
    between: Optional[Literal["subjects", "windows", "clusters"]] = Field(
        None, description="compare: what the two curves are")
    a: Optional[CurveSlice] = Field(None, description="compare: first curve")
    b: Optional[CurveSlice] = Field(None, description="compare: second curve")
    match: Optional[Literal["all", "any"]] = Field(
        None, description="compare tool=similar between=clusters, over several sample groups: 'all' when "
                          "the question says the curves agree in every sample group, 'any' when in at "
                          "least one; leave empty when the question does not say")
    top_n: Optional[int] = Field(None, description="how many clusters to keep, when the question says")
    threshold: Optional[str] = Field(
        None, description="network: 'current', 'max', 'min' or a number for the importance score")
    clusters: list[str] = Field(default_factory=list, description="given: clusters named by the user")
    example_by: Optional[Literal[EXAMPLE_FINDERS]] = Field(
        None, description="example: the evidence an example cluster is picked by")


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
    reason: str = Field(description="one short sentence for the user: what will be put in focus and why "
                                    "that answers the question")


class SlotText(BaseModel):
    slot: int = Field(description="the number of the message slot this text is for")
    text: str


class Messages(BaseModel):
    texts: list[SlotText] = Field(description="one text per requested message slot, each with its slot number")


# ---- the frame of a question -----------------------------------------------
# One parse call fills the roles of a question; code then looks every mention up
# in the data. The roles map onto the tree: K=N0, R=N1, H=N2, C+D=N3, A+E=N4,
# B=N5, F=N6.


class Mention(BaseModel):
    """A term of the question that may name something in the data."""
    text: str = Field(description="copied from the question as written")
    role: Literal["condition", "compare", "measure", "target"] = Field(
        description="condition: limits the data (C); compare: one side of a comparison (D); "
                    "measure: is what gets read or counted (B); target: names the clusters (A)")


PARTS = tuple(explainable())       # parts that can explain how they are made


class FrameCore(BaseModel):
    """The roles of one data question."""
    mentions: list[Mention] = Field(default_factory=list)
    target: list[Literal[SELECTOR_KINDS]] = Field(
        default_factory=list, description="A then E: the rule(s) that pick clusters, in order; empty = all")
    measure: list[Literal[MEASURES]] = Field(
        default_factory=list, description="B: what is read from the picked clusters")
    compare: Literal["none", "level1", "level2", "with_and_without_level2", "curves"] = Field(
        "none", description="D: what is set against what")
    outside_concept: Optional[str] = Field(
        None, description="a function or family named in words instead of ids")
    outside_ids: list[str] = Field(default_factory=list, description="ids you know for outside_concept")


class Frame(FrameCore):
    """parse: K, R and H of the question plus its roles."""
    kind: Literal["out_of_scope", "design", "method", "data"]
    part: Optional[Literal[PARTS]] = Field(
        None, description="method only: the part of the dashboard whose making or meaning is asked about")
    control: Optional[Literal[CONTROLS]] = Field(
        None, description="design only: the dashboard control the question is about")
    value: Optional[str] = Field(None, description="design only: the setting to showcase, e.g. 'circle'")
    status: Literal["ask", "assume_default", "use_current_selection", "ok"] = "ok"
    note: str = Field("", description="what to ask, or the assumption made; empty for ok")
    shape: Literal["direct", "multi_step", "evidence_chain"] = "direct"
    reason: str = Field(description="one short sentence")


class SubFrame(FrameCore):
    question: str = Field(description="the sub-question, answerable from the data alone")
    reason: str = Field("", description="one sentence for the user: why this step comes here and, for a "
                                        "hypothesis, what result would support or weaken it")
    uses: Optional[int] = Field(
        None, description="the number (1 for the first) of an earlier sub-question whose clusters this one "
                          "starts from; empty when it picks its clusters by itself")


class SubFrames(BaseModel):
    """breakdown: a question split into direct sub-questions with their roles filled."""
    sub_frames: list[SubFrame] = Field(description="2 to 4, in the order they are answered")


class PlanUnit(BaseModel):
    steps: list[SelectorStep] = Field(description="N4: one step, or two when the second works on the first")
    descriptor: Descriptor = Field(description="N5")


class Plans(BaseModel):
    """plan: N4 + N5 for each (sub-)question, and N6 for the whole answer."""
    plans: list[PlanUnit] = Field(description="one per (sub-)question, in order")
    display: Display
