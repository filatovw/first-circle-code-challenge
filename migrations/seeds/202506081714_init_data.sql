--liquibase formatted sql

--changeset filatov.vadim:2
--comment: fill core tables with default values

INSERT INTO currencies (name, symbol) VALUES
('american dollar', 'USD'),
('euro', 'EUR'),
('serbian dinar', 'RSD');

INSERT INTO users (email, full_name) VALUES
('alice.brooks@example.com', 'Alice Brooks'),
('john.dawson@example.com', 'John Dawson'),
('emily.jenkins@example.com', 'Emily Jenkins'),
('michael.reed@example.com', 'Michael Reed'),
('sophia.wilson@example.com', 'Sophia Wilson'),
('david.turner@example.com', 'David Turner'),
('olivia.morris@example.com', 'Olivia Morris'),
('chris.bennett@example.com', 'Chris Bennett'),
('natalie.hughes@example.com', 'Natalie Hughes'),
('ryan.mitchell@example.com', 'Ryan Mitchell');
