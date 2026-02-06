#!/bin/bash
# =============================================================================
# Generate self-signed certificate with custom CN and SAN entries
# =============================================================================
#
# Usage: ./generate-certs.sh --cn <name> --dns-altnames <domains> [--output-prefix <prefix>]
#
# Options:
#   --cn <name>                Certificate Common Name (CN)
#   --dns-altnames <domains>   Comma-separated DNS SANs
#   --output-prefix <prefix>   Prefix for output folder and tls.yml
#                              (default: CN lowercase, spaces to hyphens)
#   -h, --help                 Show this help message
#
# Creates:
#   <prefix>/cert.pem   - Certificate
#   <prefix>/key.pem    - Private key
#   <prefix>.tls.yml    - Traefik TLS configuration
#
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

show_help() {
    cat << 'EOF'
Generate self-signed certificate with custom CN and SAN entries

Usage: generate-certs.sh --cn <name> --dns-altnames <domains> [--output-prefix <prefix>]

Options:
  --cn <name>                Certificate Common Name (CN)
  --dns-altnames <domains>   Comma-separated DNS SANs
  --output-prefix <prefix>   Prefix for output folder and tls.yml
                             (default: CN lowercase, spaces to hyphens)
  -h, --help                 Show this help message

Creates:
  <script-dir>/<prefix>/cert.pem   - Certificate
  <script-dir>/<prefix>/key.pem    - Private key
  <script-dir>/<prefix>.tls.yml    - Traefik TLS configuration

Examples:
  ./generate-certs.sh --cn "DEV Certificate" --dns-altnames "*.example.com,example.com,*.localhost,localhost"
  ./generate-certs.sh --cn "My Cert" --dns-altnames "*.lab.local,lab.local" --output-prefix my-certs
EOF
    exit 0
}

CN=""
DNS_ALTNAMES=""
OUTPUT_PREFIX=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            ;;
        --cn)
            CN="$2"
            shift 2
            ;;
        --dns-altnames)
            DNS_ALTNAMES="$2"
            shift 2
            ;;
        --output-prefix)
            OUTPUT_PREFIX="$2"
            shift 2
            ;;
        *)
            echo "Error: Unknown option: $1"
            echo "Use --help for usage information."
            exit 1
            ;;
    esac
done

if [ -z "$CN" ]; then
    echo "Error: --cn is required"
    echo "Use --help for usage information."
    exit 1
fi

if [ -z "$DNS_ALTNAMES" ]; then
    echo "Error: --dns-altnames is required"
    echo "Use --help for usage information."
    exit 1
fi

# Default prefix: based on CN (lowercase, spaces to hyphens)
if [ -z "$OUTPUT_PREFIX" ]; then
    OUTPUT_PREFIX=$(echo "$CN" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')
fi

CERT_DIR="$SCRIPT_DIR/certs/${OUTPUT_PREFIX}"
TLS_CONFIG="$SCRIPT_DIR/certs/${OUTPUT_PREFIX}.tls.yml"

# Build SAN string with DNS: prefixes
SAN_STRING=""
IFS=',' read -ra DOMAINS <<< "$DNS_ALTNAMES"
for domain in "${DOMAINS[@]}"; do
    domain=$(echo "$domain" | xargs)  # trim whitespace
    if [ -n "$SAN_STRING" ]; then
        SAN_STRING="${SAN_STRING},"
    fi
    SAN_STRING="${SAN_STRING}DNS:${domain}"
done

mkdir -p "$CERT_DIR"

echo "Generating certificate:"
echo "  CN:     $CN"
echo "  SANs:   $DNS_ALTNAMES"
echo "  Certs:  $CERT_DIR"
echo "  TLS:    $TLS_CONFIG"
echo ""

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$CERT_DIR/key.pem" \
    -out "$CERT_DIR/cert.pem" \
    -subj "/CN=$CN" \
    -addext "subjectAltName=$SAN_STRING"

# Generate Traefik TLS configuration
cat > "$TLS_CONFIG" << EOF
# TLS Configuration for: $CN
# Import cert.pem to browser for trusted HTTPS

tls:
  certificates:
    - certFile: /certs/${OUTPUT_PREFIX}/cert.pem
      keyFile: /certs/${OUTPUT_PREFIX}/key.pem

  stores:
    default:
      defaultCertificate:
        certFile: /certs/${OUTPUT_PREFIX}/cert.pem
        keyFile: /certs/${OUTPUT_PREFIX}/key.pem
EOF

echo "Certificate generated:"
openssl x509 -in "$CERT_DIR/cert.pem" -noout -subject -dates -ext subjectAltName

echo ""
echo "Key verified:"
openssl rsa -in "$CERT_DIR/key.pem" -check -noout
