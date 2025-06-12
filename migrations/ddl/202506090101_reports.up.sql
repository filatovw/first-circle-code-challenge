--liquibase formatted sql

--comment: table report tables

CREATE TABLE report_daily_user_stats (
    user_id TEXT NOT NULL,
    day DATE NOT NULL,
    sent_count INTEGER NOT NULL,
    received_count INTEGER NOT NULL,
    total_sent NUMERIC(12, 2) NOT NULL,
    total_received NUMERIC(12, 2) NOT NULL,
    PRIMARY KEY (user_id, day)
);

CREATE TABLE report_monthly_user_stats (
    user_id TEXT NOT NULL,
    month DATE NOT NULL,
    sent_count INTEGER NOT NULL,
    received_count INTEGER NOT NULL,
    total_sent NUMERIC(12, 2) NOT NULL,
    total_received NUMERIC(12, 2) NOT NULL,
    PRIMARY KEY (user_id, month)
);