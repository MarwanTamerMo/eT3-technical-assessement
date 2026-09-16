from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from route_planner.loader import load_deliveries
from route_planner.planner import DEFAULT_CAPACITY_KG, plan_trips
from route_planner.reporting import format_plan


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point: plan the deliveries in the given file and print the report."""
    args = _parse_args(argv)

    try:
        deliveries, rejections = load_deliveries(args.input)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    plan = plan_trips(deliveries, args.capacity)
    plan.rejections = [*rejections, *plan.rejections]
    print(format_plan(plan))
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="route-planner",
        description="Group delivery requests into capacity-limited, priority-ordered trips.",
    )
    parser.add_argument("input", help="path to a .csv or .json file of delivery requests")
    parser.add_argument(
        "--capacity",
        type=_positive_float,
        default=DEFAULT_CAPACITY_KG,
        metavar="KG",
        help=f"vehicle capacity in kilograms (default: {DEFAULT_CAPACITY_KG:g})",
    )
    return parser.parse_args(argv)


def _positive_float(value: str) -> float:
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' is not a number") from None
    if number <= 0:
        raise argparse.ArgumentTypeError("capacity must be greater than 0")
    return number
