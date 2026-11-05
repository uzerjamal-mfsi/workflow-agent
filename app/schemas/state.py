from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class WorkflowState(TypedDict, total=False):
    messages: Annotated[list[Any], add_messages]
    user_request: str
    parsed_goal: str
    thread_id: str
    