#!/bin/sh
# Применяем миграции перед стартом приложения
set -e
alembic upgrade head
exec "$@"
