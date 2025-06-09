import os
import argparse
from dataclasses import dataclass
from ingestion import dto
from ingestion import models
import logging

from ingestion.repositories import (
    KafkaProducerRepository,
    KafkaConsumerRepository,
    PostgresRepository,
)
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


def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("TX-Stream-Ingestor")

    config = get_config()
    producer = KafkaProducerRepository(
        logger, APP_NAME, config.failed_transactions_producer_config, batch_size=1
    )

    consumer = KafkaConsumerRepository(
        logger, APP_NAME, config.transactions_consumer_config
    )

    db = PostgresRepository(logger, APP_NAME, config.db_config)

    with db:
        for message_body in consumer.next():
            try:
                # validation against the schema
                transaction = dto.Transaction.model_validate_json(message_body)
                logger.info("transaction: %s", transaction)
                # business logic validation
                if transaction.sender_id == transaction.receiver_id:
                    raise ValueError("Sender and Receiver cannot be the same person")
                if transaction.amount <= 0:
                    raise ValueError("Non-positive amount")

                is_suspicious = False
                reasons = []
                if transaction.amount > 1000:
                    is_suspicious = True
                    reasons.append("UPPER_BOUNDARY_EXCEEDED")

                # store to DB
                rows_affected = db.create_or_update_transaction(
                    models.Transaction(
                        transaction_id=transaction.transaction_id,
                        sender_id=transaction.sender_id,
                        receiver_id=transaction.receiver_id,
                        amount=transaction.amount,
                        currency=transaction.currency,
                        timestamp=transaction.timestamp,
                        status=str(transaction.status),
                        is_suspicious=is_suspicious,
                        suspicious_reasons=reasons,
                    )
                )
                if not rows_affected:
                    logger.info(
                        "Transaction duplicate record: %s", transaction.transaction_id
                    )
                else:
                    logger.info("Transaction added: %s", transaction.transaction_id)

            except Exception as exc:
                logger.exception("failed to parse transaction message")
                failed_transaction_message = dto.FailedTransaction(
                    error=str(exc), message_body=message_body.decode()
                )
                producer.write(failed_transaction_message)
                logger.info("Message %s sent", failed_transaction_message)


if __name__ == "__main__":
    main()
