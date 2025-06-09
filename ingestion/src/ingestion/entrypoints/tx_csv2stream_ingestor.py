import argparse
import polars as pl
from dataclasses import dataclass
from ingestion import dto
from ingestion.config import QueueConfig
from ingestion.logger import get_logger
from ingestion.repositories import KafkaProducerRepository

APP_NAME = "tx_csv2stream_ingestor"

logger = get_logger(APP_NAME)


@dataclass
class Config:
    producer_config: QueueConfig
    source_path: str


def get_config():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--bootstrap-servers", required=True, help="bootstrap server (e.g., kafka:9092)"
    )
    parser.add_argument(
        "--transactions-topic", required=True, help="transactions topic"
    )
    parser.add_argument(
        "--source-path", "-s", required=True, help="path to the file with transactions"
    )
    parsed = parser.parse_args()
    return Config(
        producer_config=QueueConfig(
            bootstrap_servers=parsed.bootstrap_servers,
            topic=parsed.transactions_topic,
        ),
        source_path=parsed.source_path,
    )


def main():
    config = get_config()

    producer = KafkaProducerRepository(logger, APP_NAME, config.producer_config)

    tx_df = pl.read_csv(config.source_path)
    counter = 0
    for row in tx_df.to_dicts():
        counter += 1
        try:
            tx = dto.Transaction(**row)
        except Exception:
            logger.exception("Validation error")

        try:
            counter += producer.write(tx)
        except Exception:
            logger.exception("Failed to write transaction to the topic")

    producer.flush()
    logger.info("Rows ingested: %d", counter)


if __name__ == "__main__":
    main()
