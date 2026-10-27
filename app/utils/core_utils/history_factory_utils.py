from app.utils.core_utils.in_memory_utils import in_memory_history


def get_message_history_factory():
    """Return the in-memory history factory for agent chat memory."""
    return in_memory_history.get_history


message_history_factory = get_message_history_factory()
