#!/bin/bash
set -e

# Останавливаем PostgreSQL
echo "Stopping PostgreSQL..."
pg_ctl -D /var/lib/postgresql/data stop

# Удаляем файлы из каталога main
echo "Removing files from main directory..."
rm -rf /var/lib/postgresql/data/*

# Выполняем pg_basebackup
echo "Starting pg_basebackup..."
pg_basebackup -R -h db_container -U repl_user -D /var/lib/postgresql/data/ -P

# Перезапускаем PostgreSQL
echo "Starting PostgreSQL..."
pg_ctl -D /var/lib/postgresql/data start
