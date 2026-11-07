from dataclasses import dataclass


@dataclass(frozen=True)
class Payload[Frame]:
    frame: Frame
    sha256: str
