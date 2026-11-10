from langchain_core.messages import HumanMessage, SystemMessage

from app.prompts.planner_prompt import planner_prompt


def test_planner_prompt_formatting():
    messages = planner_prompt.format_messages(
        goal="Coordinate feature launch",
        sop_context="1. Review PR\n2. Notify lead",
    )

    assert len(messages) == 2
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)

    assert "1. Review PR\n2. Notify lead" in messages[0].content
    assert "Coordinate feature launch" in messages[1].content
    assert "Available Tools:" in messages[0].content
    assert "four or more dependent steps" in messages[0].content

