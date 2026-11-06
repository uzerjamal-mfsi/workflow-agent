from pydantic import BaseModel, Field
from typing import Any, Literal

class CreateTaskArgs(BaseModel):
    title: str = Field(description="Task title")
    assignee: str = Field(description="Active team member ID, e.g. dev01")
    priority: Literal["Lowest", "Low", "Medium", "High", "Highest"] = "Medium"
class SendNotificationArgs(BaseModel):
    recipient: str = Field(description="Recipient user ID, e.g. pm01")
    message: str = Field(description="Message content")
class CheckCalendarArgs(BaseModel):
    user_id: str = Field(description="Team member ID")
    date: str = Field(description="Date in YYYY-MM-DD format")
class UpdateTaskArgs(BaseModel):
    task_id: str = Field(description="ID of task to update, e.g. TASK-101")
    fields: dict[str, Any] = Field(description="Dictionary of fields to update")
class SearchTemplatesArgs(BaseModel):
    query: str = Field(description="Search text")