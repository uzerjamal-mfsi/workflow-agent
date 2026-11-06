from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from app.schemas.core_schemas.tool_schemas import CheckCalendarArgs, CreateTaskArgs, SearchTemplatesArgs, SendNotificationArgs, UpdateTaskArgs

class Step(BaseModel):
    step_id: str = Field(
        description="Unique identifier for the step, e.g. 'step_1', 'step_2'"
    )
    title: str = Field(
        description="Short description of what this step accomplishes"
    )
    tool: Literal[
        "search_workflow_templates",
        "create_task",
        "update_task",
        "send_notification",
        "check_calendar_availability",
    ] = Field(description="The exact tool to execute for this step")
    args: CreateTaskArgs | SendNotificationArgs | CheckCalendarArgs | UpdateTaskArgs | SearchTemplatesArgs
    dependencies: list[str] = Field(
        default_factory=list,
        description="List of step_ids that must finish before this step can run",
    )
    requires_approval: bool = Field(
        default=False,
        description="Set to True if step involves external notifications, bulk updates, or deletions",
    )
    expected_outcome: str = Field(
        default="",
        description="Expected postcondition or result of this step",
    )

class Plan(BaseModel):
    reasoning: str = Field(description="Brief summary explaining why this plan was formed based on SOPs")
    steps: list[Step] = Field(
        description="Ordered list of steps to achieve the goal"
    )

class WorkflowState(TypedDict, total=False):
    messages: Annotated[list[Any], add_messages]
    user_request: str
    parsed_goal: str
    thread_id: str
    retrieved_sops: list[str]
    plan: Plan
    