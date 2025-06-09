import json
import socket
import os
import argparse
from dataclasses import dataclass
from confluent_kafka import (
    Producer,
    Message,
    Consumer,
    KafkaError,
    KafkaException,
)
from ingestion import dto
import logging


@dataclass
class Config:
    bootstrap_server: str
    topic_transactions: str
    topic_failed_transactions: str

    pg_user: str
    pg_password: str
    pg_port: int
    pg_db: str
    pg_host: str


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
        bootstrap_server=parsed.bootstrap_servers,
        topic_transactions=parsed.topic_transactions,
        topic_failed_transactions=parsed.topic_failed_transactions,
        pg_user=parsed.pg_user,
        pg_port=parsed.pg_port,
        pg_host=parsed.pg_host,
        pg_db=parsed.pg_db,
        pg_password=pg_password,
    )


def acked(err: KafkaError, msg: Message):
    if err is not None:
        print("Failed to deliver message: %s: %s" % (str(msg), str(err)))
    else:
        print("Message produced: %s" % (str(msg)))


def get_producer(config: Config) -> Producer:
    queue_config = {
        "bootstrap.servers": config.bootstrap_server,
        "client.id": "tx-stream-ingestor",
    }
    return Producer(queue_config)


def get_consumer(config: Config) -> Consumer:
    queue_config = {
        "bootstrap.servers": config.bootstrap_server,
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
    producer = get_producer(config)
    consumer = get_consumer(config)

    consumer.subscribe([config.topic_transactions])
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
                    try:
                        failed_transaction_message = json.dumps(
                            {"error": str(exc), "message": message_body.decode()}
                        )
                        producer.produce(
                            topic=config.topic_failed_transactions,
                            value=failed_transaction_message,
                        )
                        logger.info("Message %s sent", failed_transaction_message)
                    except KeyboardInterrupt:
                        logger.error("Stopping")
                        raise
                    except Exception:
                        logger.exception("failed to send message")
                        # fail fast. Writing to the failed transaction topic must work
                        raise
                    finally:
                        producer.flush(1)
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
