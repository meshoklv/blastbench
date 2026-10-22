#!/bin/sh
# Starts a private PostgreSQL (localhost only, data on tmpfs) and the exec server (PID 1's child).
set -e
PGDATA="${PGDATA:-/var/lib/postgresql/data}"

su-exec postgres initdb -D "$PGDATA" -U postgres -E UTF8 --no-locale \
    --auth-local=peer --auth-host=scram-sha-256 >/dev/null
# root has no DAC_OVERRIDE here, so write the config as the postgres user
su-exec postgres sh -c "cat >> '$PGDATA/postgresql.conf'" <<CONF
listen_addresses = '127.0.0.1'
port = 5432
unix_socket_directories = '/run/postgresql'
shared_buffers = 32MB
max_connections = 20
fsync = off
CONF
su-exec postgres pg_ctl -D "$PGDATA" -l /tmp/postgres.log -w start >/dev/null

exec python3 /opt/sandbox/exec_server.py
