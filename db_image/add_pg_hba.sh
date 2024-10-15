#!/bin/bash
set -e

# Путь к файлу pg_hba.conf
PG_HBA_FILE="/var/lib/postgresql/data/pg_hba.conf"

# Проверяем, существует ли файл и добавляем строку, если ее нет
if ! grep -q "host all all 0.0.0.0/0 md5" "$PG_HBA_FILE"; then
    echo "host all all 0.0.0.0/0 md5" >> "$PG_HBA_FILE"
    echo "host replication repl_user 0.0.0.0/0 md5" >> "$PG_HBA_FILE"
    echo "Строка добавлена в pg_hba.conf"
else
    echo "Строка уже существует в pg_hba.conf"
fi


pg_ctl -D /var/lib/postgresql/data reload
