import polars as pl
import os
import argparse
from dataclasses import dataclass
from ingestion import dto
from ingestion import models
from ingestion.logger import get_logger
from ingestion.repositories import (
    KafkaProducerRepository,
    PostgresRepository,
)
from ingestion.config import QueueConfig, DBConfig
import json
from ingestion.anomaly_detection import AnomalyDetector
import dotenv

APP_NAME = "tx_csv2db_ingestor"


@dataclass
class Config:
    failed_transactions_producer_config: QueueConfig
    source_path: str
    db_config: DBConfig


def get_config():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--bootstrap-servers", required=True, help="bootstrap server (e.g., kafka:9092)"
    )
    parser.add_argument(
        "--topic-failed-transactions", required=True, help="failed transactions topic"
    )
    parser.add_argument(
        "--source-path", "-s", required=True, help="path to the file with transactions"
    )
    parser.add_argument("--pg-user", "-u", type=str, help="database user")
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
        failed_transactions_producer_config=QueueConfig(
            bootstrap_servers=parsed.bootstrap_servers,
            topic=parsed.topic_failed_transactions,
        ),
        source_path=parsed.source_path,
        db_config=DBConfig(
            user=parsed.pg_user,
            port=parsed.pg_port,
            host=parsed.pg_host,
            database=parsed.pg_db,
            password=pg_password,
        ),
    )


def main():
    dotenv.load_dotenv(verbose=True)
    config = get_config()
    logger = get_logger(APP_NAME)
    producer = KafkaProducerRepository(
        logger, APP_NAME, config.failed_transactions_producer_config, batch_size=1
    )

    db = PostgresRepository(logger, APP_NAME, config.db_config)

    with db:
        anomaly_detector = AnomalyDetector(logger, db)
        tx_df = pl.read_csv(config.source_path)
        counter = 0
        for row in tx_df.to_dicts():
            counter += 1
            try:
                transaction = dto.Transaction(**row)

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
                logger.error("Failed on a transaction validation")
                failed_transaction_message = dto.FailedTransaction(
                    error=str(err), message_body=json.dumps(row)
                )
                producer.write(failed_transaction_message)
                logger.info("Message %s sent", failed_transaction_message)
            except Exception:
                logger.exception("Failed on a transaction processing")

        producer.flush()
        logger.info("Rows ingested: %d", counter)


if __name__ == "__main__":
    main()
