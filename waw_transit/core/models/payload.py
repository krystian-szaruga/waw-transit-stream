from dataclasses import dataclass


@dataclass(frozen=True)
class Payload[Frame]:
    frame: Frame
    sha256: str


@dataclass(frozen=True)
class GtfsPayload[Frame]:
    timetable: Frame
    trip_shapes: Frame
    shape_points: Frame
    sha256: str
