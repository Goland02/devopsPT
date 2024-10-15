CREATE DATABASE tg_base;


CREATE USER repl_user WITH REPLICATION ENCRYPTED PASSWORD '123';


\c tg_base;

CREATE TABLE number (
    id SERIAL PRIMARY KEY,
    number VARCHAR(20) NOT NULL
);

CREATE TABLE email (
    id SERIAL PRIMARY KEY,
    email VARCHAR(100) NOT NULL
);

ALTER SYSTEM SET archive_mode = 'on';
ALTER SYSTEM SET max_wal_senders = '10';
ALTER SYSTEM SET wal_log_hints = 'on';
ALTER SYSTEM SET listen_addresses = '*';
ALTER SYSTEM SET log_replication_commands = 'on';
ALTER SYSTEM SET logging_collector = 'on';
SELECT pg_reload_conf();
