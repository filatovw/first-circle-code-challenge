import argparse
import polars as pl
from dataclasses import dataclass
from confluent_kafka import Producer
from ingestion import models


@dataclass
class Config:
    bootstrap_server: str
    topic: str
    source_path: str


def get_config():
    parser = argparse.ArgumentParser(description="Kafka producer using confluent-kafka")
    parser.add_argument(
        "--server", required=True, help="bootstrap server (e.g., kafka:9092)"
    )
    parser.add_argument("--topic", required=True, help="topic name")
    parser.add_argument(
        "--source-path", "-s", required=True, help="path to the file with transactions"
    )
    parsed = parser.parse_args()
    return Config(
        bootstrap_server=parsed.server,
        topic=parsed.topic,
        source_path=parsed.source_path,
    )


def main():
    config = get_config()
    tx_df = pl.read_csv(config.source_path)

    queue_config = {
        "bootstrap.servers": config.bootstrap_server,
        "client.id": "tx-producer",
    }
    producer = Producer(queue_config)

    for row in tx_df.to_dicts():
        tx = models.Transaction(**row)
        producer.produce(topic=config.topic, value=tx.model_dump_json())
        producer.flush(5)

    pass


if __name__ == "__main__":
    main()
