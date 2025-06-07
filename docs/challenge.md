# First Circle: Data Engineer Test

Create a simple application (system) in a language of your choice (preferably kotlin/java but not a must) that covers the topics bellow.

Readme file should contain short explanation how to start the app, preferably with short summary of it.

### Database Design:

Design a relational database schema to store **payment transactions**. Keep it minimal but realistic.

- Users can send payments to each other
- Payments include: ID, sender, receiver, amount, currency, timestamp, status (`pending`, `completed`, `failed`)
- Support querying:
    - All payments by a user
    - Daily total sent/received per user

Would prefer using **PostgreSQL** as un underlaying db, but can opt for a different choice. 

SQL DDL for 2–3 tables: `users`, `transactions`, optionally `currency` along with constraints. Make this a part of the project as database migrations or whatever you find suitable.

### Ingest from a Queue

Simulate a stream of transaction events coming from a message queue (e.g., Kafka, RabbitMQ or any way that mimics this approach).

Things to cover:

- Listening to a queue for data ingestion:
- Parsing of JSON messages
- Validating data and inserting to a database
- Skip and log invalid/malformed messages

Sample JSON:

```json
{
"transaction_id": "tx123",
"sender_id": "user1",
"receiver_id": "user2",
"amount": 250.00,
"currency": "USD",
"timestamp": "2025-05-01T12:00:00Z",
"status": "completed"
}
```

### CSV import

Things to cover:

- Load transactions from a CSV file
- validate and insert into the same `transactions` table
- flag suspicious transactions based on rules (no need to go all out here, a simple rule would be amount >10000, but feel free to add your own)
- detect and handle duplicates

Generate your own sample files for this to use as an example.

### Reporting

Provide a way of reporting data per user for a set period of time.
Nice to have would be a time based job that generates monthly report every day.

NOTE: If something is not specified or unclear, make reasonable assumptions and note them where **relevant**.