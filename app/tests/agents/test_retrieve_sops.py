from unittest.mock import MagicMock, patch

from app.agents.nodes.retrieve_sops import retrieve_sops
from app.schemas.state import WorkflowState


def test_retrieve_sops_empty_goal():
    state: WorkflowState = {
        "parsed_goal": "",
        "messages": [],
    }
    with patch("app.agents.nodes.retrieve_sops.search_sops") as mock_search:
        result = retrieve_sops(state)
        assert result == {"retrieved_sops": []}
        mock_search.assert_not_called()


def test_retrieve_sops_missing_goal():
    state: WorkflowState = {
        "messages": [],
    }
    with patch("app.agents.nodes.retrieve_sops.search_sops") as mock_search:
        result = retrieve_sops(state)
        assert result == {"retrieved_sops": []}
        mock_search.assert_not_called()


def test_retrieve_sops_with_valid_goal():
    state: WorkflowState = {
        "parsed_goal": "Schedule a team meeting",
        "messages": [],
    }
    expected_sops = ["## Calendar SOP\nAlways check availability."]

    mock_repo = MagicMock()
    mock_provider = MagicMock()
    mock_settings = MagicMock()
    mock_settings.QDRANT_COLLECTION = "test_sops"

    with (
        patch(
            "app.agents.nodes.retrieve_sops.get_qdrant_repository",
            return_value=mock_repo,
        ),
        patch(
            "app.agents.nodes.retrieve_sops.get_embedding_provider",
            return_value=mock_provider,
        ),
        patch(
            "app.agents.nodes.retrieve_sops.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "app.agents.nodes.retrieve_sops.search_sops",
            return_value=expected_sops,
        ) as mock_search,
    ):
        result = retrieve_sops(state)

        assert result == {"retrieved_sops": expected_sops}
        mock_search.assert_called_once_with(
            repository=mock_repo,
            embedding_provider=mock_provider,
            collection_name="test_sops",
            query="Schedule a team meeting",
        )

