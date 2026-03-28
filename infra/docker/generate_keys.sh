#!/bin/bash
set -e

KEYS_DIR="infra/docker/keys"
mkdir -p "$KEYS_DIR"

if [ ! -f "$KEYS_DIR/jwt_private.pem" ]; then
    echo "Generating JWT RSA-256 key pair..."
    openssl genrsa -out "$KEYS_DIR/jwt_private.pem" 2048
    openssl rsa -in "$KEYS_DIR/jwt_private.pem" -pubout -out "$KEYS_DIR/jwt_public.pem"
    chmod 600 "$KEYS_DIR/jwt_private.pem"
    chmod 644 "$KEYS_DIR/jwt_public.pem"
    echo "Keys generated in $KEYS_DIR/"
else
    echo "JWT keys already exist, skipping."
fi

# Also generate a random JWT_SECRET for HS256 fallback
if [ ! -f "$KEYS_DIR/.env.secrets" ]; then
    echo "JWT_SECRET=$(openssl rand -hex 32)" > "$KEYS_DIR/.env.secrets"
    echo "POSTGRES_PASSWORD=$(openssl rand -hex 16)" >> "$KEYS_DIR/.env.secrets"
    echo "ARCADEDB_ROOT_PASSWORD=$(openssl rand -hex 16)" >> "$KEYS_DIR/.env.secrets"
    chmod 600 "$KEYS_DIR/.env.secrets"
    echo "Generated secrets in $KEYS_DIR/.env.secrets"
else
    echo "Secrets file already exists, skipping."
fi

echo "Done. Never commit $KEYS_DIR/ to version control."
