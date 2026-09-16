import random

import pytest

from route_planner.models import Delivery
from route_planner.planner import plan_trips

BRIEF_SAMPLE = [
    Delivery("1", "Nasr City", 2, 4.5),
    Delivery("2", "Maadi", 1, 2.0),
    Delivery("3", "Nasr City", 3, 1.2),
    Delivery("4", "Zamalek", 1, 7.0),
    Delivery("5", "Maadi", 2, 3.5),
]


def test_no_deliveries_produces_an_empty_plan():
    plan = plan_trips([])

    assert plan.trips == []
    assert plan.rejections == []


def test_rejects_non_positive_capacity():
    with pytest.raises(ValueError, match="greater than 0"):
        plan_trips([], capacity_kg=0)


def test_plans_the_brief_sample():
    plan = plan_trips(BRIEF_SAMPLE)

    assert [(t.area, [d.id for d in t.deliveries], t.load_kg) for t in plan.trips] == [
        ("Maadi", ["2", "5"], 5.5),
        ("Zamalek", ["4"], 7.0),
        ("Nasr City", ["1", "3"], 5.7),
    ]


def test_package_heavier_than_the_vehicle_is_unassignable(make_delivery):
    plan = plan_trips([make_delivery(weight_kg=15.0)])

    assert plan.trips == []
    assert [r.reason for r in plan.rejections] == ["exceeds vehicle capacity"]


def test_package_matching_the_capacity_exactly_is_assignable(make_delivery):
    plan = plan_trips([make_delivery(weight_kg=10.0)])

    assert len(plan.trips) == 1
    assert plan.rejections == []


def test_load_that_fills_the_vehicle_stays_in_one_trip(make_delivery):
    # These three sum to 10.000000000000002 in floating point, not 10.0.
    weights = [2.8, 6.57, 0.63]
    deliveries = [make_delivery(delivery_id=str(i), weight_kg=w) for i, w in enumerate(weights)]

    plan = plan_trips(deliveries)

    assert len(plan.trips) == 1


def test_trips_never_mix_areas():
    plan = plan_trips(BRIEF_SAMPLE)

    for trip in plan.trips:
        assert len({d.area for d in trip.deliveries}) == 1


def test_areas_are_matched_ignoring_case_and_padding(make_delivery):
    deliveries = [
        make_delivery(delivery_id="1", area="Maadi", weight_kg=1.0),
        make_delivery(delivery_id="2", area=" maadi ", weight_kg=1.0),
    ]

    plan = plan_trips(deliveries)

    assert len(plan.trips) == 1
    assert plan.trips[0].area == "Maadi"


def test_equal_priorities_are_ordered_by_numeric_id(make_delivery):
    deliveries = [
        make_delivery(delivery_id="10", priority=1, weight_kg=1.0),
        make_delivery(delivery_id="2", priority=1, weight_kg=1.0),
        make_delivery(delivery_id="1", priority=1, weight_kg=1.0),
    ]

    plan = plan_trips(deliveries)

    assert [d.id for d in plan.trips[0].deliveries] == ["1", "2", "10"]


def test_a_later_delivery_backfills_an_earlier_trip(make_delivery):
    deliveries = [
        make_delivery(delivery_id="1", priority=1, weight_kg=6.0),
        make_delivery(delivery_id="2", priority=2, weight_kg=5.0),
        make_delivery(delivery_id="3", priority=3, weight_kg=3.0),
    ]

    plan = plan_trips(deliveries)

    assert [[d.id for d in t.deliveries] for t in plan.trips] == [["1", "3"], ["2"]]


def test_areas_with_urgent_work_are_dispatched_first(make_delivery):
    deliveries = [
        make_delivery(delivery_id="1", area="Nasr City", priority=3, weight_kg=1.0),
        make_delivery(delivery_id="2", area="Zamalek", priority=1, weight_kg=1.0),
        make_delivery(delivery_id="3", area="Maadi", priority=2, weight_kg=1.0),
    ]

    plan = plan_trips(deliveries)

    assert [t.area for t in plan.trips] == ["Zamalek", "Maadi", "Nasr City"]


def test_trips_are_numbered_consecutively_from_one(make_delivery):
    deliveries = [make_delivery(delivery_id=str(i), weight_kg=6.0) for i in range(5)]

    plan = plan_trips(deliveries)

    assert [t.number for t in plan.trips] == [1, 2, 3, 4, 5]


def test_every_delivery_is_placed_exactly_once_within_capacity():
    rng = random.Random(20260917)
    areas = ["Maadi", "Nasr City", "Zamalek", "Dokki"]
    deliveries = [
        Delivery(str(i), rng.choice(areas), rng.randint(1, 5), round(rng.uniform(0.1, 12.0), 2))
        for i in range(500)
    ]

    plan = plan_trips(deliveries)

    placed = [d for trip in plan.trips for d in trip.deliveries]
    rejected = [d for d in deliveries if d.weight_kg > 10.0]

    assert len(placed) == len(set(placed))
    assert set(placed) | set(rejected) == set(deliveries)
    assert len(plan.rejections) == len(rejected)
    assert all(trip.load_kg <= trip.capacity_kg for trip in plan.trips)


def test_capacity_is_configurable(make_delivery):
    deliveries = [make_delivery(delivery_id=str(i), weight_kg=4.0) for i in range(3)]

    plan = plan_trips(deliveries, capacity_kg=20.0)

    assert len(plan.trips) == 1
    assert plan.trips[0].capacity_kg == 20.0
