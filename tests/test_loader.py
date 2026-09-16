import pytest

from route_planner.loader import load_deliveries
from route_planner.models import Delivery

VALID_CSV = """id,area,priority,weight_kg
1,Nasr City,2,4.5
2,Maadi,1,2.0
"""

VALID_JSON = """[
  {"id": "1", "area": "Nasr City", "priority": 2, "weight_kg": 4.5},
  {"id": "2", "area": "Maadi", "priority": 1, "weight_kg": 2.0}
]
"""


def test_reads_csv(write_file):
    deliveries, rejections = load_deliveries(write_file("in.csv", VALID_CSV))

    assert rejections == []
    assert deliveries == [
        Delivery("1", "Nasr City", 2, 4.5),
        Delivery("2", "Maadi", 1, 2.0),
    ]


def test_csv_and_json_produce_the_same_deliveries(write_file):
    from_csv, _ = load_deliveries(write_file("in.csv", VALID_CSV))
    from_json, _ = load_deliveries(write_file("in.json", VALID_JSON))

    assert from_csv == from_json


def test_strips_surrounding_whitespace(write_file):
    csv_text = "id,area,priority,weight_kg\n  7  , Maadi ,1,2.0\n"
    deliveries, _ = load_deliveries(write_file("in.csv", csv_text))

    assert deliveries == [Delivery("7", "Maadi", 1, 2.0)]


def test_reads_bom_prefixed_csv(write_file):
    path = write_file("in.csv", VALID_CSV)
    path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())

    deliveries, rejections = load_deliveries(path)

    assert len(deliveries) == 2
    assert rejections == []


@pytest.mark.parametrize(
    ("row", "reason"),
    [
        ("3,Maadi,1,", "missing field"),
        ("3,,1,2.0", "missing field"),
        (",Maadi,1,2.0", "missing field"),
        ("3,Maadi,,2.0", "missing field"),
        ("3,Maadi,1,heavy", "invalid weight"),
        ("3,Maadi,1,0", "invalid weight"),
        ("3,Maadi,1,-2.0", "invalid weight"),
        ("3,Maadi,1,nan", "invalid weight"),
        ("3,Maadi,0,2.0", "invalid priority"),
        ("3,Maadi,1.5,2.0", "invalid priority"),
        ("3,Maadi,urgent,2.0", "invalid priority"),
    ],
)
def test_rejects_unusable_rows(write_file, row, reason):
    deliveries, rejections = load_deliveries(write_file("in.csv", f"{VALID_CSV}{row}\n"))

    assert len(deliveries) == 2
    assert [r.reason for r in rejections] == [reason]
    assert rejections[0].source == "row 4"


def test_rejects_duplicate_ids(write_file):
    deliveries, rejections = load_deliveries(write_file("in.csv", f"{VALID_CSV}1,Dokki,1,3.0\n"))

    assert [d.id for d in deliveries] == ["1", "2"]
    assert [r.reason for r in rejections] == ["duplicate id"]


def test_rejects_non_object_json_items(write_file):
    deliveries, rejections = load_deliveries(write_file("in.json", '["not an object"]'))

    assert deliveries == []
    assert [r.reason for r in rejections] == ["malformed record"]


def test_empty_file_yields_nothing(write_file):
    assert load_deliveries(write_file("in.csv", "")) == ([], [])


def test_header_only_csv_yields_nothing(write_file):
    assert load_deliveries(write_file("in.csv", "id,area,priority,weight_kg\n")) == ([], [])


def test_rejects_unsupported_extension(write_file):
    with pytest.raises(ValueError, match="unsupported input format"):
        load_deliveries(write_file("in.txt", VALID_CSV))


def test_rejects_json_that_is_not_an_array(write_file):
    with pytest.raises(ValueError, match="expected a JSON array"):
        load_deliveries(write_file("in.json", '{"id": "1"}'))


def test_missing_file_raises_oserror(tmp_path):
    with pytest.raises(OSError):
        load_deliveries(tmp_path / "absent.csv")
