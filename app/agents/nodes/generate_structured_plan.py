from typing import Any, cast

from langchain_core.runnables import Runnable

from app.llms.llm_client import get_llm
from app.prompts.planner_prompt import planner_prompt
from app.schemas.state import Plan, WorkflowState


def generate_structured_plan(state: WorkflowState) -> dict[str, Any]:
    """LangGraph node to generate a structured execution plan using an LLM."""
    goal = state.get("parsed_goal", "")
    if not goal:
        return {"plan": Plan(reasoning="No goal provided", steps=[])}

    # If this is a replan format the new goal
    if feedback := state.get("feedback"):
        goal = f"{goal}\n\n[USER REPLAN FEEDBACK]: {feedback}"
    elif (last_result := state.get("last_step_result")) and not last_result.success:
        goal = f"{goal}\n\n[PREVIOUS FAILURE TO REVISE]: Step '{last_result.step_id}' failed with error: {last_result.error}"

    # Format the retrieved SOP chunks into a single readable context block
    sops = state.get("retrieved_sops", [])
    sop_context = "\n\n".join(sops) if sops else "No specific SOPs retrieved."

    llm = get_llm()
    structured_llm = cast(Runnable[Any, Plan], llm.with_structured_output(Plan))

    prompt_messages = planner_prompt.format_messages(
        goal=goal,
        sop_context=sop_context,
    )
    plan = structured_llm.invoke(prompt_messages)

    print(plan)
    return {"plan": plan}
