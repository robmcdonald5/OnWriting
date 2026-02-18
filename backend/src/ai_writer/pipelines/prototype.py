"""Prototype pipeline — minimal 4-agent story generation with write-edit loop.

Pipeline flow:
    START → plot_architect → beat_outliner → scene_writer → style_editor
        → (revise → scene_writer | advance → scene_writer | complete → END)
"""

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from ai_writer.agents.beat_outliner import run_beat_outliner
from ai_writer.agents.plot_architect import run_plot_architect
from ai_writer.agents.scene_writer import run_scene_writer
from ai_writer.agents.style_editor import run_style_editor
from ai_writer.schemas.characters import CharacterRoster
from ai_writer.schemas.editing import EditFeedback
from ai_writer.schemas.story import StoryBrief
from ai_writer.schemas.structure import StoryOutline
from ai_writer.schemas.world import WorldContext
from ai_writer.schemas.writing import SceneDraft


class GraphState(TypedDict, total=False):
    """LangGraph state — uses TypedDict for graph compatibility.

    Only user_prompt is required. All other fields are populated by agents.
    """

    user_prompt: str
    story_brief: StoryBrief
    character_roster: CharacterRoster
    world_context: WorldContext
    story_outline: StoryOutline
    scene_drafts: list[SceneDraft]
    edit_feedback: list[EditFeedback]
    current_scene_index: int
    revision_count: int
    max_revisions: int
    current_stage: str
    errors: list[str]


def _get_total_scenes(state: GraphState) -> int:
    """Count total scenes across all acts."""
    outline = state.get("story_outline")
    if not outline:
        return 0
    return sum(len(act.scenes) for act in outline.acts)


def should_revise_or_advance(state: GraphState) -> str:
    """Conditional edge: decide whether to revise, advance to next scene, or complete."""
    feedback_list = state.get("edit_feedback", [])
    if not feedback_list:
        return "complete"

    latest_feedback = feedback_list[-1]
    revision_count = state.get("revision_count", 0)
    max_revisions = state.get("max_revisions", 2)
    current_idx = state.get("current_scene_index", 0)
    total_scenes = _get_total_scenes(state)

    # Log dimension scores for visibility
    rubric = latest_feedback.rubric
    decision = "REVISE" if not latest_feedback.approved else "PASS"
    print(
        f"  [Pipeline] Scene {latest_feedback.scene_id}: "
        f"{rubric.dimension_summary()} "
        f"→ {latest_feedback.quality_score:.2f} [{decision}]",
        flush=True,
    )

    # If not approved and we have revision budget, revise
    if not latest_feedback.approved and revision_count < max_revisions:
        return "revise"

    # Move to next scene or complete
    if current_idx + 1 < total_scenes:
        return "next_scene"
    else:
        return "complete"


def prepare_revision(state: GraphState) -> dict:
    """Increment revision count before sending back to scene_writer."""
    return {"revision_count": state.get("revision_count", 0) + 1}


def advance_scene(state: GraphState) -> dict:
    """Move to the next scene and reset revision count."""
    return {
        "current_scene_index": state.get("current_scene_index", 0) + 1,
        "revision_count": 0,
    }


def mark_complete(state: GraphState) -> dict:
    """Mark the pipeline as complete."""
    return {"current_stage": "complete"}


def build_prototype_pipeline() -> CompiledStateGraph:
    """Build and compile the prototype story generation pipeline."""
    builder: StateGraph[Any] = StateGraph(GraphState)

    # Add nodes — agent functions take dict, which is compatible with GraphState
    builder.add_node("plot_architect", run_plot_architect)  # type: ignore[type-var]
    builder.add_node("beat_outliner", run_beat_outliner)  # type: ignore[type-var]
    builder.add_node("scene_writer", run_scene_writer)  # type: ignore[type-var]
    builder.add_node("style_editor", run_style_editor)  # type: ignore[type-var]
    builder.add_node("prepare_revision", prepare_revision)
    builder.add_node("advance_scene", advance_scene)
    builder.add_node("mark_complete", mark_complete)

    # Linear planning edges
    builder.add_edge(START, "plot_architect")
    builder.add_edge("plot_architect", "beat_outliner")
    builder.add_edge("beat_outliner", "scene_writer")

    # Write-edit loop
    builder.add_edge("scene_writer", "style_editor")
    builder.add_conditional_edges(
        "style_editor",
        should_revise_or_advance,
        {
            "revise": "prepare_revision",
            "next_scene": "advance_scene",
            "complete": "mark_complete",
        },
    )
    builder.add_edge("prepare_revision", "scene_writer")
    builder.add_edge("advance_scene", "scene_writer")
    builder.add_edge("mark_complete", END)

    return builder.compile()  # type: ignore[return-value]
