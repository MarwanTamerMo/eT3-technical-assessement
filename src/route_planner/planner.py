from __future__ import annotations

from collections.abc import Iterable, Sequence

from route_planner.models import Delivery, Plan, Rejection, Trip

DEFAULT_CAPACITY_KG = 10.0

# Float addition overshoots: 2.8 + 6.57 + 0.63 evaluates to 10.000000000000002. Without this
# tolerance a load that exactly fills a vehicle would spill onto a needless extra trip.
_TOLERANCE_KG = 1e-9


def plan_trips(deliveries: Iterable[Delivery], capacity_kg: float = DEFAULT_CAPACITY_KG) -> Plan:
    """Group deliveries into single-area trips that respect the vehicle capacity."""
    if capacity_kg <= 0:
        raise ValueError("capacity must be greater than 0 kg")

    carriable, rejections = _split_unassignable(deliveries, capacity_kg)
    plan = Plan(capacity_kg=capacity_kg, rejections=rejections)

    for area, area_deliveries in _areas_by_urgency(carriable):
        for load in _pack(area_deliveries, capacity_kg):
            plan.trips.append(Trip(len(plan.trips) + 1, area, capacity_kg, load))

    return plan


def _split_unassignable(
    deliveries: Iterable[Delivery], capacity_kg: float
) -> tuple[list[Delivery], list[Rejection]]:
    carriable: list[Delivery] = []
    rejections: list[Rejection] = []
    for delivery in deliveries:
        if delivery.weight_kg > capacity_kg + _TOLERANCE_KG:
            rejections.append(
                Rejection(
                    "exceeds vehicle capacity",
                    f"delivery {delivery.id}",
                    f"{delivery.weight_kg:g} kg cannot fit a {capacity_kg:g} kg vehicle",
                )
            )
        else:
            carriable.append(delivery)
    return carriable, rejections


def _areas_by_urgency(deliveries: Sequence[Delivery]) -> list[tuple[str, list[Delivery]]]:
    groups: dict[str, list[Delivery]] = {}
    labels: dict[str, str] = {}
    for delivery in deliveries:
        key = delivery.area.strip().casefold()
        groups.setdefault(key, []).append(delivery)
        labels.setdefault(key, delivery.area.strip())

    ordered_keys = sorted(groups, key=lambda key: (min(d.priority for d in groups[key]), key))
    return [(labels[key], sorted(groups[key], key=_delivery_order)) for key in ordered_keys]


def _delivery_order(delivery: Delivery) -> tuple[int, int, str]:
    # Numeric ids sort numerically so trip 10 follows trip 9 rather than trip 1.
    if delivery.id.isdigit():
        return (delivery.priority, int(delivery.id), "")
    return (delivery.priority, 0, delivery.id)


def _pack(deliveries: Sequence[Delivery], capacity_kg: float) -> list[list[Delivery]]:
    loads: list[list[Delivery]] = []
    for delivery in deliveries:
        for load in loads:
            if _weight_of(load) + delivery.weight_kg <= capacity_kg + _TOLERANCE_KG:
                load.append(delivery)
                break
        else:
            loads.append([delivery])
    return loads


def _weight_of(load: Sequence[Delivery]) -> float:
    return sum(delivery.weight_kg for delivery in load)
