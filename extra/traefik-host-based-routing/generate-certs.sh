#!/bin/bash
# =============================================================================
# Generate self-signed wildcard certificate for Traefik
# =============================================================================
#
# Usage: ./generate-certs.sh <domain>
# Example: ./generate-certs.sh lab.example.com
#
# Creates:
#   certs/_.domain/cert.pem  - Certificate (import to browser)
#   certs/_.domain/key.pem   - Private key
#   certs/tls.yml            - Traefik TLS configuration
#
# Note: Uses generic CN to avoid browser CN validation issues across multiple
# domains. All domains are specified in SAN (Subject Alternative Name) field.
#
# =============================================================================

set -e

DOMAIN="${1:-}"

if [ -z "$DOMAIN" ]; then
    echo "Usage: $0 <domain>"
    echo "Example: $0 lab.example.com"
    exit 1
fi

CERT_DIR="certs/_.${DOMAIN}"
TLS_CONFIG="certs/tls.yml"

echo "Generating self-signed certificate for *.${DOMAIN}"

# Create certificate directory
mkdir -p "$CERT_DIR"

# Generate self-signed certificate
# Uses generic CN to avoid browser CN validation issues; domains are in SAN
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "${CERT_DIR}/key.pem" \
    -out "${CERT_DIR}/cert.pem" \
    -subj "/CN=DEV Certificate" \
    -addext "subjectAltName=DNS:*.${DOMAIN},DNS:${DOMAIN},DNS:*.app.localhost,DNS:app.localhost,DNS:*.localhost,DNS:localhost"

# Generate Traefik TLS configuration
cat > "$TLS_CONFIG" << EOF
# TLS Configuration for self-signed certificates
# Wildcard cert: *.${DOMAIN}, *.localhost
# Import cert.pem to browser for trusted HTTPS

tls:
  certificates:
    - certFile: /certs/_.${DOMAIN}/cert.pem
      keyFile: /certs/_.${DOMAIN}/key.pem

  stores:
    default:
      defaultCertificate:
        certFile: /certs/_.${DOMAIN}/cert.pem
        keyFile: /certs/_.${DOMAIN}/key.pem
EOF

echo ""
echo "Certificate generated:"
openssl x509 -in "${CERT_DIR}/cert.pem" -noout -subject -dates -ext subjectAltName

echo ""
echo "Key verified:"
openssl rsa -in "${CERT_DIR}/key.pem" -check -noout

echo ""
echo "Next steps:"
echo "  1. Edit compose_override.yml - replace YOURDOMAIN with ${DOMAIN}"
echo "  2. Import ${CERT_DIR}/cert.pem to your browser"
echo "  3. Run: ./start.sh"
