--liquibase formatted sql

--comment: drop reporting tables
DROP TABLE report_monthly_user_stats;
DROP TABLE report_daily_user_stats;