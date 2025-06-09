from typing import Literal
from datetime import datetime
from pydantic import BaseModel
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
