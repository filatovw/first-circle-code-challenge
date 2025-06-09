import socket
import os
import argparse
from dataclasses import dataclass
from confluent_kafka import (
    Consumer,
    KafkaError,
    KafkaException,
)
from ingestion import dto
import logging

from ingestion.repositories import KafkaProducerRepository
from ingestion.config import QueueConfig, DBConfig

APP_NAME = "tx_stream2db_ingestor"


@dataclass
class Config:
    transactions_consumer_config: QueueConfig
    failed_transactions_producer_config: QueueConfig
    db_config: DBConfig


def get_config():
    parser = argparse.ArgumentParser(description="Kafka producer using confluent-kafka")
    parser.add_argument(
        "--bootstrap-servers", required=True, help="bootstrap server (e.g., kafka:9092)"
    )
    parser.add_argument("--topic-transactions", required=True, help="source topic")
    parser.add_argument(
        "--topic-failed-transactions", required=True, help="failed transactions topic"
    )
    parser.add_argument(
        "--pg-user", "-u", type=str, required=True, help="database user"
    )
    parser.add_argument("--pg-port", type=str, required=True, help="database port")
    parser.add_argument("--pg-host", type=str, required=True, help="database host")
    parser.add_argument("--pg-db", type=str, required=True, help="database name")

    parsed = parser.parse_args()
    pg_password = os.environ.get("POSTGRES_PASSWORD")
    if not pg_password:
        raise ValueError("POSTGRES_PASSWORD Env Var is not set")
    return Config(
        transactions_consumer_config=QueueConfig(
            bootstrap_servers=parsed.bootstrap_servers,
            topic=parsed.topic_transactions,
        ),
        failed_transactions_producer_config=QueueConfig(
            bootstrap_servers=parsed.bootstrap_servers,
            topic=parsed.topic_failed_transactions,
        ),
        db_config=DBConfig(
            user=parsed.pg_user,
            port=parsed.pg_port,
            host=parsed.pg_host,
            database=parsed.pg_db,
            password=pg_password,
        ),
    )


def get_consumer(config: Config) -> Consumer:
    queue_config = {
        "bootstrap.servers": config.transactions_consumer_config.bootstrap_servers,
        "client.id": f"tx-stream-ingestor:{socket.gethostname()}",
        "enable.auto.commit": "false",
        "enable.auto.offset.store": "true",
        "group.id": "tx-stream-ingestor",
        "default.topic.config": {"auto.offset.reset": "earliest"},
    }
    return Consumer(queue_config)


def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("TX-Stream-Ingestor")

    config = get_config()
    producer = KafkaProducerRepository(
        logger, APP_NAME, config.failed_transactions_producer_config, batch_size=1
    )

    consumer = get_consumer(config)

    consumer.subscribe([config.transactions_consumer_config.topic])
    count = 0
    try:
        while True:
            try:
                message_container = consumer.poll(timeout=3.0)
                if not message_container:
                    continue

                try:
                    if message_container.error():
                        if (
                            message_container.error().code()
                            == KafkaError._PARTITION_EOF
                        ):
                            logger.info(
                                "Topic %s/%s reached end at offset %s",
                                message_container.topic(),
                                message_container.partition(),
                                message_container.offset(),
                            )
                        elif message_container.error():
                            raise KafkaException(message_container.error())

                    message_body = message_container.value()
                    if not message_body:
                        logger.info("Empty message")

                    # validation against the schema
                    transaction = dto.Transaction.model_validate_json(message_body)
                    logger.info("transaction: %s", transaction)
                    # business logic validation
                    if transaction.sender_id == transaction.receiver_id:
                        raise ValueError(
                            "Sender and Receiver cannot be the same person"
                        )
                    if transaction.amount <= 0:
                        raise ValueError("Non-positive amount")

                    is_suspicious = False
                    reasons = []
                    if transaction.amount > 10000:
                        is_suspicious = True
                        reasons.append("UPPER_BOUNDARY_EXCEEDED")

                    # store to DB
                    ...

                except Exception as exc:
                    logger.exception("failed to parse transaction message")
                    failed_transaction_message = dto.FailedTransaction(
                        error=str(exc), message_body=message_body.decode()
                    )
                    producer.write(failed_transaction_message)
                    logger.info("Message %s sent", failed_transaction_message)
                count += 1
                consumer.commit()

            except KeyboardInterrupt:
                logger.info("Stopping")
                raise
            except Exception:
                logger.exception("Failed to process message")
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
