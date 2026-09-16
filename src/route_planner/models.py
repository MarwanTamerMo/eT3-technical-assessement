from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Delivery:
    id: str
    area: str
    priority: int
    weight_kg: float


@dataclass(frozen=True, slots=True)
class Rejection:
    reason: str
    source: str
    detail: str

    def __str__(self) -> str:
        return f"{self.source}: {self.detail} ({self.reason})"


@dataclass(slots=True)
class Trip:
    number: int
    area: str
    capacity_kg: float
    deliveries: list[Delivery] = field(default_factory=list)

    @property
    def load_kg(self) -> float:
        return round(sum(d.weight_kg for d in self.deliveries), 3)

    @property
    def utilisation(self) -> float:
        return self.load_kg / self.capacity_kg if self.capacity_kg else 0.0


@dataclass(slots=True)
class Plan:
    capacity_kg: float
    trips: list[Trip] = field(default_factory=list)
    rejections: list[Rejection] = field(default_factory=list)

    @property
    def delivered_count(self) -> int:
        return sum(len(trip.deliveries) for trip in self.trips)

    @property
    def total_load_kg(self) -> float:
        return round(sum(trip.load_kg for trip in self.trips), 3)

    @property
    def total_capacity_kg(self) -> float:
        return round(len(self.trips) * self.capacity_kg, 3)

    @property
    def utilisation(self) -> float:
        total = self.total_capacity_kg
        return self.total_load_kg / total if total else 0.0
