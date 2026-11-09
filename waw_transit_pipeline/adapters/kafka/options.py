from waw_transit_pipeline.core.config import KafkaConfig


def stream_options(config: KafkaConfig) -> dict[str, str]:
    return {
        "kafka.bootstrap.servers": config.bootstrap_servers,
        "subscribe": ",".join(config.topics.values()),
        "startingOffsets": config.starting_offsets,
        "failOnDataLoss": "false",
    }
