"""Unit tests for the assignment strategy (app.services.assignment)."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from app.services.assignment import AssignmentError, SingleAttorneyStrategy
from tests.conftest import make_lead, make_user


def _strategy_with_attorney(attorney):
    strategy = SingleAttorneyStrategy(MagicMock(name="Session"))
    strategy._users = MagicMock()
    strategy._users.first_attorney.return_value = attorney
    return strategy


def test_assign_routes_to_the_seeded_attorney():
    attorney = make_user(id=uuid.uuid4())
    strategy = _strategy_with_attorney(attorney)

    assert strategy.assign(make_lead()) == attorney.id


def test_assign_raises_when_no_attorney_available():
    strategy = _strategy_with_attorney(None)

    with pytest.raises(AssignmentError):
        strategy.assign(make_lead())
