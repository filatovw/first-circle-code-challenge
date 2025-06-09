from datetime import datetime
from dataclasses import dataclass


@dataclass
class Transaction:
    transaction_id: str
    sender_id: str
    receiver_id: str
    amount: str
    currency: str
    timestamp: str
    status: str

