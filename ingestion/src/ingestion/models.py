from datetime import datetime
from pydantic import BaseModel
from pydantic.types import UUID4


class Transaction(BaseModel):
    transaction_id: UUID4
    sender_id: UUID4
    receiver_id: UUID4
    amount: float
    currency: str
    timestamp: datetime
    status: str
    is_suspicious: bool
    suspicious_reasons: list[str] = []
