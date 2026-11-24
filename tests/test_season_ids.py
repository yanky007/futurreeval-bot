import pytest
from forecasting_tools import MetaculusClient


def test_ids_are_this_season():
    # Fails on purpose when the library's season IDs change, so you notice and re-check.
    assert MetaculusClient.CURRENT_AI_COMPETITION_ID == 33121
    assert MetaculusClient.CURRENT_MINIBENCH_ID == "minibench"


@pytest.mark.network
def test_tournament_slug_resolves():
    # An expired slug silently returns no questions; this at least proves the ID is valid.
    MetaculusClient().get_all_open_questions_from_tournament(MetaculusClient.CURRENT_AI_COMPETITION_ID)
