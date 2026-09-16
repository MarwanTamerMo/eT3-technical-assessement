from route_planner.models import Delivery, Plan, Rejection, Trip
from route_planner.reporting import format_plan


def _plan(*loads, capacity_kg=10.0, rejections=()):
    trips = [
        Trip(
            number,
            f"Area {number}",
            capacity_kg,
            [Delivery(f"{number}-{i}", f"Area {number}", 1, w) for i, w in enumerate(load)],
        )
        for number, load in enumerate(loads, start=1)
    ]
    return Plan(capacity_kg=capacity_kg, trips=trips, rejections=list(rejections))


def test_empty_plan_says_there_is_nothing_to_do():
    assert format_plan(Plan(capacity_kg=10.0)) == "No deliveries to plan."


def test_plan_with_only_rejections_reports_them():
    rejection = Rejection("exceeds vehicle capacity", "delivery 9", "15 kg cannot fit")
    output = format_plan(Plan(capacity_kg=10.0, rejections=[rejection]))

    assert "No deliveries could be planned." in output
    assert "Not planned (1)" in output
    assert "delivery 9" in output


def test_trip_lines_show_load_and_members():
    output = format_plan(_plan([4.5, 1.2]))

    assert "Trip 1  Area 1  —  5.7/10 kg  (57%, 2 deliveries)" in output
    assert "1-0   priority 1   4.5 kg" in output


def test_utilisation_totals_across_trips():
    output = format_plan(_plan([6.0], [4.0]))

    assert "Trips planned        2" in output
    assert "Deliveries assigned  2" in output
    assert "Capacity used        10 of 20 kg (50%)" in output
    assert "Spare capacity       10 kg" in output


def test_trip_exactly_at_the_threshold_is_not_flagged():
    assert "Under 60% utilised   none" in format_plan(_plan([6.0, 4.0], [6.0]))


def test_trip_below_the_threshold_is_flagged():
    output = format_plan(_plan([6.0, 4.0], [5.9]))

    assert "Under 60% utilised   1 (trip 2 Area 2 59%)" in output
