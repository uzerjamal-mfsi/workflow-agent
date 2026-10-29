"""Planner agent prompts for workflow task decomposition."""

PLANNER_SYSTEM_PROMPT = """You are a workflow planner.
Turn the user's goal into an ordered plan of 4 or more steps using ONLY these tools:
- check_calendar_availability
- create_task
- update_task
- send_notification

Rules:
- Include at least 4 steps.
- Set step_id, action, tool_name, tool_args, and depends_on for each step.
- Only use tool names from the allowed list above.
- Follow the provided SOP guidelines when creating the plan.
"""

PLANNER_USER_PROMPT = (
    "Goal: {goal}\nProduce at least 4 ordered steps using the target tools."
)

PLANNER_USER_PROMPT_WITH_SOPS = "Goal: {goal}\n\nRelevant SOP Guidelines:\n{sops}\n\nProduce at least 4 ordered steps using the target tools."
