from pathlib import Path

import pytest

from route_planner.models import Delivery


@pytest.fixture
def make_delivery():
    def build(delivery_id="1", area="Maadi", priority=1, weight_kg=1.0):
        return Delivery(delivery_id, area, priority, weight_kg)

    return build


@pytest.fixture
def write_file(tmp_path):
    def build(name, content):
        path = tmp_path / name
        path.write_text(content, encoding="utf-8")
        return path

    return build


@pytest.fixture(scope="session")
def data_dir():
    return Path(__file__).resolve().parents[1] / "data"
