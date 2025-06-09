import logging
from ingestion import dto
from ingestion.repositories import PostgresRepository
import enum


class Anomalies(str, enum.Enum):
    UNKNOWN_CURRENCY = "unknown_currency"
    AMOUNT_OUTLIER = "amount_outlier"
    UNKNOWN_SENDER = "unknown_sender"
    UNKNOWN_RECEIVER = "unknown_receiver"

    def __str__(self) -> str:
        return self.value


class AnomalyDetector:
    def __init__(self, logger: logging.Logger, db: PostgresRepository):
        self._logger = logger
        self._db = db

    def check_unknown_currency(self, transaction: dto.Transaction) -> Anomalies | None:
        if not self._db.currency_exists(transaction.currency):
            return Anomalies.UNKNOWN_CURRENCY

    def check_amount_outlier(
        self, transaction: dto.Transaction, value: float
    ) -> Anomalies | None:
        if transaction.amount > value:
            return Anomalies.AMOUNT_OUTLIER

    def check_unknown_sender(self, transaction: dto.Transaction) -> Anomalies | None:
        if not self._db.user_exists(transaction.sender_id):
            return Anomalies.UNKNOWN_SENDER

    def check_unknown_receiver(self, transaction: dto.Transaction) -> Anomalies | None:
        if not self._db.user_exists(transaction.receiver_id):
            return Anomalies.UNKNOWN_RECEIVER
