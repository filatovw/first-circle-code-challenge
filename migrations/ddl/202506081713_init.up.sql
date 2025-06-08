--liquibase formatted sql

--comment: table users

CREATE TABLE currencies (
    currency_id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    name text NOT NULL,
    symbol text UNIQUE NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz
);

CREATE TABLE users (
    user_id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    email text NOT NULL,
    full_name text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz
);

CREATE TABLE transactions (
    transaction_id uuid PRIMARY KEY,
    sender_id uuid REFERENCES users (user_id),
    receiver_id uuid REFERENCES users (user_id),
    amount text NOT NULL,
    currency_id uuid REFERENCES currencies (currency_id),
    created_at timestamptz NOT NULL,
    status text,
    is_suspicious boolean DEFAULT FALSE,
    suspicious_reasons text []
);
