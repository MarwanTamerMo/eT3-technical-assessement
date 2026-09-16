import subprocess
import sys

import pytest

from route_planner.cli import main


def test_plans_the_sample_csv(capsys, data_dir):
    exit_code = main([str(data_dir / "deliveries.sample.csv")])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Delivery plan — 3 trips, 10 kg vehicle" in output
    assert "Trip 1  Maadi  —  5.5/10 kg" in output
    assert "Utilisation" in output


def test_csv_and_json_samples_report_identically(capsys, data_dir):
    main([str(data_dir / "deliveries.sample.csv")])
    from_csv = capsys.readouterr().out
    main([str(data_dir / "deliveries.sample.json")])
    from_json = capsys.readouterr().out

    assert from_csv == from_json


def test_edge_case_sample_reports_every_rejection(capsys, data_dir):
    exit_code = main([str(data_dir / "deliveries.edge-cases.csv")])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Not planned (6)" in output
    for reason in ("duplicate id", "missing field", "invalid weight", "invalid priority"):
        assert reason in output
    assert "exceeds vehicle capacity" in output


def test_capacity_flag_changes_the_plan(capsys, data_dir):
    main([str(data_dir / "deliveries.sample.csv"), "--capacity", "20"])
    output = capsys.readouterr().out

    assert "Delivery plan — 3 trips, 20 kg vehicle" in output


def test_missing_file_exits_with_an_error(capsys, tmp_path):
    exit_code = main([str(tmp_path / "absent.csv")])

    assert exit_code == 1
    assert "error:" in capsys.readouterr().err


def test_unsupported_format_exits_with_an_error(capsys, write_file):
    exit_code = main([str(write_file("in.txt", "id,area,priority,weight_kg\n"))])

    assert exit_code == 1
    assert "unsupported input format" in capsys.readouterr().err


@pytest.mark.parametrize("capacity", ["0", "-5", "heavy"])
def test_invalid_capacity_is_refused(data_dir, capacity):
    with pytest.raises(SystemExit) as exit_info:
        main([str(data_dir / "deliveries.sample.csv"), "--capacity", capacity])

    assert exit_info.value.code == 2


def test_runs_as_a_module(data_dir):
    result = subprocess.run(
        [sys.executable, "-m", "route_planner", str(data_dir / "deliveries.sample.csv")],
        capture_output=True,
        text=True,
        check=True,
    )

    assert "Delivery plan" in result.stdout
