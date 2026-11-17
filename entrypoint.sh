#!/bin/sh
# Démarre en root uniquement pour corriger les droits du volume /data,
# puis relance l'application avec un utilisateur non privilégié.
set -e

PUID="${PUID:-1000}"
PGID="${PGID:-1000}"
DATA_DIR="$(dirname "${DB_PATH:-/data/links.db}")"

if [ "$(id -u)" = "0" ]; then
    mkdir -p "$DATA_DIR"
    chown -R "$PUID:$PGID" "$DATA_DIR"
    exec setpriv --reuid="$PUID" --regid="$PGID" --clear-groups "$@"
fi

exec "$@"
