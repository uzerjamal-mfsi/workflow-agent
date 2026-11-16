from langchain_core.prompts import ChatPromptTemplate

CLASSIFIER_SYSTEM_PROMPT = """You are an intent classifier for an automated workflow agent.
Determine if the user's request is a supported workflow task that can be executed using platform tools, or an unsupported message.

Supported capabilities:
1. Jira Task Management (creating tasks, updating tasks, searching templates)
2. Calendar Availability (checking team member calendar availability)
3. Notifications (sending alerts/emails to team members)
4. Workflow SOP execution (onboarding, offboarding, incident response, operational workflows, deployments, bug fixes, reports)

Rules:
- Set is_supported = True if the request is an actionable operational workflow goal related to the capabilities above.
- Set is_supported = False if the request is casual chat, greetings (e.g. "hi", "hello"), open-ended conversation, general knowledge questions, or unsupported tasks (e.g. baking, weather, personal advice, general coding).
- If is_supported is False, set rejection_reason to a concise explanation stating that this type of message is not supported and noting that only operational workflow tasks are handled. Do not engage in casual chat.
"""

classifier_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", CLASSIFIER_SYSTEM_PROMPT),
        ("human", "User request: {goal}"),
    ]
)

DEFAULT_UNSUPPORTED_MESSAGE = (
    "This type of message is not supported. I can only execute workflow tasks such as "
    "Jira task management, calendar availability checks, and notifications."
)
