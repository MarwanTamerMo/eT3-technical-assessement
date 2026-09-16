from __future__ import annotations

from route_planner.models import Plan, Trip

UNDERUSED_THRESHOLD = 0.60


def format_plan(plan: Plan) -> str:
    """Render a plan as the human-readable report printed by the CLI."""
    if not plan.trips and not plan.rejections:
        return "No deliveries to plan."

    sections: list[list[str]] = []

    if plan.trips:
        trips = _plural(len(plan.trips), "trip")
        sections.append([f"Delivery plan — {trips}, {_kg(plan.capacity_kg)} kg vehicle"])
        sections.extend(_trip_lines(trip) for trip in plan.trips)
        sections.append(_utilisation_lines(plan))
    else:
        sections.append(["No deliveries could be planned."])

    if plan.rejections:
        sections.append(_rejection_lines(plan))

    return "\n\n".join("\n".join(section) for section in sections)


def _trip_lines(trip: Trip) -> list[str]:
    carried = _plural(len(trip.deliveries), "delivery", "deliveries")
    head = (
        f"Trip {trip.number}  {trip.area}  —  {_kg(trip.load_kg)}/{_kg(trip.capacity_kg)} kg"
        f"  ({_percent(trip.utilisation)}, {carried})"
    )
    body = [
        f"  {delivery.id:<5} priority {delivery.priority:<3} {_kg(delivery.weight_kg)} kg"
        for delivery in trip.deliveries
    ]
    return [head, *body]


def _utilisation_lines(plan: Plan) -> list[str]:
    underused = [trip for trip in plan.trips if trip.utilisation < UNDERUSED_THRESHOLD]
    if underused:
        detail = ", ".join(
            f"trip {trip.number} {trip.area} {_percent(trip.utilisation)}" for trip in underused
        )
        underused_summary = f"{len(underused)} ({detail})"
    else:
        underused_summary = "none"

    rows = [
        ("Trips planned", str(len(plan.trips))),
        ("Deliveries assigned", str(plan.delivered_count)),
        (
            "Capacity used",
            f"{_kg(plan.total_load_kg)} of {_kg(plan.total_capacity_kg)} kg"
            f" ({_percent(plan.utilisation)})",
        ),
        ("Spare capacity", f"{_kg(round(plan.total_capacity_kg - plan.total_load_kg, 3))} kg"),
        (f"Under {_percent(UNDERUSED_THRESHOLD)} utilised", underused_summary),
    ]

    width = max(len(label) for label, _ in rows)
    return ["Utilisation", *(f"  {label:<{width}}  {value}" for label, value in rows)]


def _rejection_lines(plan: Plan) -> list[str]:
    return [
        f"Not planned ({len(plan.rejections)})",
        *(f"  {rejection}" for rejection in plan.rejections),
    ]


def _kg(value: float) -> str:
    return f"{value:g}"


def _percent(fraction: float) -> str:
    return f"{round(fraction * 100)}%"


def _plural(count: int, singular: str, plural: str | None = None) -> str:
    word = singular if count == 1 else (plural or f"{singular}s")
    return f"{count} {word}"
