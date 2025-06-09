from __future__ import annotations
import logging
import abc
from ingestion import models
from ingestion.config import QueueConfig
import typing as t
from confluent_kafka import Producer
from ingestion.dto import Transaction
from confluent_kafka import (
    Consumer,
    KafkaError,
    KafkaException,
)


class DBRepository(abc.ABC):
    def get_users(self, skip: int, limit: int) -> list[t.Any]: ...

    def get_currencies(self) -> list[str]: ...

    def create_or_update_transaction(self, transaction: models.Transaction): ...


class PostgresRepository(DBRepository):
    def __init__(self, host: str, port: int, user: str, password: str, db: str) -> None:
        self._uri = f"postgresql://{user}:{password}@{host}:{port}/{db}"

    def get_users(self, skip: int, limit: int) -> list[t.Any]: ...

    def get_currencies(self) -> list[str]: ...

    def create_or_update_transaction(self, transaction: models.Transaction): ...


class KafkaProducerRepository:
    def __init__(
        self,
        logger: logging.Logger,
        client_id: str,
        config: QueueConfig,
        batch_size: int = 10,
    ) -> None:
        self._logger = logger
        self._config = config
        queue_config = {
            "bootstrap.servers": config.bootstrap_servers,
            "client.id": client_id,
        }
        self._producer = Producer(queue_config)
        self._messages_written = 0
        self._batch_size = batch_size

    def write(self, message: Transaction) -> int:
        try:
            message = message.model_dump_json()
            self._producer.produce(topic=self._config.topic, value=message)
            self._logger.info("Message %s sent", message)
        except KeyboardInterrupt:
            self._logger.error("Stopping")
            raise
        except Exception:
            self._logger.exception("failed to send message")
            raise

        self._messages_written += 1

        if self._messages_written % self._batch_size == 0:
            return self._producer.flush(self._config.io_timeout_seconds)
        return 0

    def flush(self) -> int:
        return self._producer.flush(self._config.io_timeout_seconds)


class KafkaConsumerRepository:
    def __init__(
        self,
        logger: logging.Logger,
        client_id: str,
        config: QueueConfig,
    ) -> None:
        self._logger = logger
        self._config = config
        queue_config = {
            "bootstrap.servers": config.bootstrap_servers,
            "client.id": client_id,
        }
        queue_config = {
            "bootstrap.servers": config.bootstrap_servers,
            "client.id": client_id,
            "enable.auto.commit": "false",
            "enable.auto.offset.store": "true",
            "group.id": "tx-stream-ingestor",
            "default.topic.config": {"auto.offset.reset": "earliest"},
        }
        self._consumer = Consumer(queue_config)
        self._consumer.subscribe([self._config.topic])

    def next(self) -> t.Generator[Transaction, None, None]:
        try:
            while True:
                try:
                    message_container = self._consumer.poll(
                        timeout=self._config.io_timeout_seconds
                    )
                    if not message_container:
                        continue

                    if message_container.error():
                        if (
                            message_container.error().code()
                            == KafkaError._PARTITION_EOF
                        ):
                            self._logger.info(
                                "Topic %s/%s reached end at offset %s",
                                message_container.topic(),
                                message_container.partition(),
                                message_container.offset(),
                            )
                        elif message_container.error():
                            raise KafkaException(message_container.error())

                    message_body = message_container.value()
                    if not message_body:
                        self._logger.info("Empty message")

                    yield message_body
                except KeyboardInterrupt:
                    self._logger.info("Stopping")
                    raise
                except Exception:
                    self._logger.exception("Failed to process message")
        finally:
            self._consumer.close()
