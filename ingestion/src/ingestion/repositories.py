import abc
from ingestion import models
import typing as t



class DBRepository(abc.ABC):
    def get_users(self, skip: int, limit: int) -> list[t.Any]:
        ...

    def get_currencies(self) -> list[str]:
        ...

    def create_or_update_transaction(self, transaction: models.Transaction):
        ...



class PostgresRepository(DBRepository):

    def __init__(self, host: str, port: int, user: str, password: str, db: str) -> None:
        self._uri = f"postgresql://{user}:{password}@{host}:{port}/{db}"

    def get_users(self, skip: int, limit: int) -> list[t.Any]:
        ...

    def get_currencies(self) -> list[str]:
        ...

    def create_or_update_transaction(self, transaction: models.Transaction):
        ...


"""
class QueueConsumerRepository(abc.ABC):
    def fetch_transaction(self) -> dto.Transaction:
        ...

class QueueProducerRepository(abc.ABC):
    def write_one(self, transaction: dto.transactino, timeout: int = 1):
        ...

class KafkaConsumerRepository(QueueConsumerRepository):

    def __init__(self, config)

    def fetch_one(self):
        ...

class KafkaProducerRepository(QueueProducerRepository):
    ...
"""