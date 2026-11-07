from waw_transit_pipeline.core.config import KafkaConfig

_VEHICLE_TYPES = {"bus": 1, "tram": 2}


def topic_to_vehicle_type(config: KafkaConfig) -> dict[str, int]:
    return {
        config.topics[name]: vehicle_type
        for name, vehicle_type in _VEHICLE_TYPES.items()
    }
