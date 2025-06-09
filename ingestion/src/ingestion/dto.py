from __future__ import annotations
from typing import Literal
from datetime import datetime, timezone
from pydantic import BaseModel, model_validator

from pydantic.types import AwareDatetime, UUID4

TX_STATUSES = ["pending", "completed", "failed"]


class Transaction(BaseModel):
    transaction_id: UUID4
    sender_id: UUID4
    receiver_id: UUID4
    amount: float  # NOTE: potential issue with rounding
    currency: str
    timestamp: AwareDatetime
    status: Literal["pending", "completed", "failed"]

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            UUID4: str,
        }

    @model_validator(mode="after")
    def amount_validation(self) -> Transaction:
        if self.amount <= 0:
            raise ValueError("Amount must be positive")
        return self

    @model_validator(mode="after")
    def sender_receiver_pair_validation(self) -> Transaction:
        if self.sender_id == self.receiver_id:
            raise ValueError("Sender and receiver must differ")
        return self

    @model_validator(mode="after")
    def message_from_future_validation(self) -> Transaction:
        if self.timestamp > datetime.now(timezone.utc):
            raise ValueError("Timestamp cannot be in the future")

        return self


class FailedTransaction(BaseModel):
    error: str
    message_body: str
