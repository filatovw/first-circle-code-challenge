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
from ingestion.anomaly_detection import AnomalyDetector
import dotenv

APP_NAME = "tx_stream2db_ingestor"


@dataclass
class Config:
    transactions_consumer_config: QueueConfig
    failed_transactions_producer_config: QueueConfig
    db_config: DBConfig


def get_config():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--bootstrap-servers", required=True, help="bootstrap server (e.g., kafka:9092)"
    )
    parser.add_argument("--topic-transactions", required=True, help="source topic")
    parser.add_argument(
        "--topic-failed-transactions", required=True, help="failed transactions topic"
    )
    parser.add_argument("--pg-user", type=str, help="database user")
    parser.add_argument("--pg-port", type=str, help="database port")
    parser.add_argument("--pg-host", type=str, help="database host")
    parser.add_argument("--pg-db", type=str, help="database name")

    parsed = parser.parse_args()
    pg_password = os.environ["PG_PASSWORD"]
    if not parsed.pg_user:
        parsed.pg_user = os.environ["PG_USER"]
    if not parsed.pg_port:
        parsed.pg_port = os.environ["PG_PORT"]
    if not parsed.pg_host:
        parsed.pg_host = os.environ["PG_HOST"]
    if not parsed.pg_db:
        parsed.pg_db = os.environ["PG_DATABASE"]
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
        anomaly_detector = AnomalyDetector(logger, db)
        for message_body in consumer.next():
            try:
                # validation against the schema
                transaction = dto.Transaction.model_validate_json(message_body)
                logger.info("transaction: %s", transaction)

                # anomaly detection
                is_suspicious = False
                reasons = []
                if (
                    reason := anomaly_detector.check_amount_outlier(transaction, 10000)
                ) and reason:
                    reasons.append(str(reason))
                    is_suspicious = True
                if (
                    reason := anomaly_detector.check_unknown_currency(transaction)
                ) and reason:
                    reasons.append(str(reason))
                    is_suspicious = True
                if (
                    reason := anomaly_detector.check_unknown_receiver(transaction)
                ) and reason:
                    reasons.append(str(reason))
                    is_suspicious = True
                if (
                    reason := anomaly_detector.check_unknown_sender(transaction)
                ) and reason:
                    reasons.append(str(reason))
                    is_suspicious = True

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
            except ValueError as err:
                logger.exception("failed to parse transaction message")
                failed_transaction_message = dto.FailedTransaction(
                    error=str(err), message_body=message_body.decode()
                )
                producer.write(failed_transaction_message)
                logger.info("Message %s sent", failed_transaction_message)
            except Exception:
                logger.exception("Failed on a transaction processing")


if __name__ == "__main__":
    dotenv.load_dotenv(verbose=True)
    main()
