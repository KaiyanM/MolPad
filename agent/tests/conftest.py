"""The tests run on the cheese test data (the agent has no data of its own).

It is loaded when the test session starts, for fixtures of any scope, and set again before
every test, because some tests switch to another dataset.
"""

import pytest

from agent.core.dataset import use_dataset
from agent.tests.cheese import cheese

use_dataset(cheese())


@pytest.fixture(autouse=True)
def cheese_data():
    return use_dataset(cheese())
