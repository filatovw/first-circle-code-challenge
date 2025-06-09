from dataclasses import dataclass

@dataclass
class DBConfig:
    user: str
    password: str
    host: str
    port: str
    database: str


@dataclass
class QueueConfig:
    bootstrap_servers: str
    topic: str
    timeout: int

