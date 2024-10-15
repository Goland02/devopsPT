#!/bin/bash

# Ждем, пока PostgreSQL запустится и создаст каталог логов
sleep 10

# Устанавливаем права на каталоги логов
chmod -R 777 /var/lib/postgresql/data/log/
