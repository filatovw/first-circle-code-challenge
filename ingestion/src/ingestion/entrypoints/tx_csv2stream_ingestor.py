import argparse
import polars as pl
from dataclasses import dataclass
from confluent_kafka import Producer, Message, KafkaError
from ingestion import models
import logging


@dataclass
class Config:
    bootstrap_server: str
    topic: str
    source_path: str


def get_config():
    parser = argparse.ArgumentParser(description="Kafka producer using confluent-kafka")
    parser.add_argument(
        "--bootstrap-servers", required=True, help="bootstrap server (e.g., kafka:9092)"
    )
    parser.add_argument("--topic", required=True, help="topic name")
    parser.add_argument(
        "--source-path", "-s", required=True, help="path to the file with transactions"
    )
    parsed = parser.parse_args()
    return Config(
        bootstrap_server=parsed.bootstrap_servers,
        topic=parsed.topic,
        source_path=parsed.source_path,
    )


def acked(err: KafkaError, msg: Message):
    if err is not None:
        print("Failed to deliver message: %s: %s" % (str(msg), str(err)))
    else:
        print("Message produced: %s" % (str(msg)))


def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("TX-CSV2Stream-Ingestor")

    config = get_config()
    tx_df = pl.read_csv(config.source_path)

    queue_config = {
        "bootstrap.servers": config.bootstrap_server,
        "client.id": "tx-producer",
    }

    producer = Producer(queue_config)
    counter = 0

    for row in tx_df.to_dicts():
        counter += 1
        try:
            tx = models.Transaction(**row)
            message = tx.model_dump_json()
            producer.produce(topic=config.topic, value=message)
            logger.info("Message %s sent", message)
        except KeyboardInterrupt:
            logger.error("Stopping")
            raise
        except Exception as err:
            logger.exception("failed to send message: %s", err)
        if counter % 100 == 0:
            producer.flush(5)
    producer.flush(5)
    logger.info("Rows ingested: %d", counter)


if __name__ == "__main__":
    main()
