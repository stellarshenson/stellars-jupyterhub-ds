#!/bin/bash

# Show help
show_help() {
    cat << 'EOF'
Certificate Installer - Install certificates to system trust store

Usage: install_cert.sh [OPTIONS] [DIRECTORY]

Arguments:
  DIRECTORY     Folder to search for certificates (default: current directory)

Options:
  -h, --help    Show this help message and exit

Supported file types:
  .cer, .crt, .pem, .der   - X.509 certificates (will be installed)
  .key                      - Private keys (skipped)
  .p12, .pfx                - PKCS#12 bundles (skipped - use different tool)

Examples:
  install_cert.sh                    # Scan current directory
  install_cert.sh /path/to/certs     # Scan specific directory
  install_cert.sh ./my-certs         # Scan relative path

Note: Requires sudo privileges for system-wide certificate installation.
EOF
    exit 0
}

# Parse arguments
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    show_help
fi

# Optional argument: folder to search for certificates (default: current directory)
CERT_DIR="${1:-.}"

# Resolve to absolute path and check if exists
if [ ! -d "$CERT_DIR" ]; then
    echo "Error: Directory '$CERT_DIR' not found."
    echo "Use --help for usage information."
    exit 1
fi

echo "============================================"
echo "  Certificate Installer - Root Trust Store"
echo "============================================"
echo ""
echo " Scanning directory: $CERT_DIR"
echo ""
echo " WARNING: This script installs certificates"
echo " into your system's trusted root store."
echo ""
echo " This is intended for custom self-signed"
echo " certificates from TRUSTED sources only."
echo ""
echo " *** INSTALLING UNKNOWN CERTIFICATES IS ***"
echo " ***       EXTREMELY DANGEROUS!         ***"
echo ""
echo " A malicious root certificate can allow"
echo " attackers to intercept ALL your encrypted"
echo " traffic, including passwords, banking,"
echo " and personal data."
echo ""
echo " Only proceed if you know and trust the"
echo " source of these certificates!"
echo "============================================"
echo ""
read -p "Do you want to continue? (Y/N): " proceed

if [[ ! "$proceed" =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo "Scanning for certificate and key files..."
echo ""

found=0
certcount=0
keycount=0

# Detect OS for correct certificate installation path
install_cert() {
    local certfile="$1"

    if [ -f /etc/debian_version ]; then
        # Debian/Ubuntu
        sudo cp "$certfile" /usr/local/share/ca-certificates/
        sudo update-ca-certificates
    elif [ -f /etc/redhat-release ]; then
        # RHEL/CentOS/Fedora
        sudo cp "$certfile" /etc/pki/ca-trust/source/anchors/
        sudo update-ca-trust
    elif [ -f /etc/arch-release ]; then
        # Arch Linux
        sudo cp "$certfile" /etc/ca-certificates/trust-source/anchors/
        sudo trust extract-compat
    elif [ -f /etc/alpine-release ]; then
        # Alpine Linux
        sudo cp "$certfile" /usr/local/share/ca-certificates/
        sudo update-ca-certificates
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain "$certfile"
    else
        echo "[ERROR] Unknown OS. Please install manually."
        return 1
    fi
    return 0
}

for file in "$CERT_DIR"/*.cer "$CERT_DIR"/*.crt "$CERT_DIR"/*.pem "$CERT_DIR"/*.der "$CERT_DIR"/*.key "$CERT_DIR"/*.p12 "$CERT_DIR"/*.pfx; do
    # Skip if no files match the pattern
    [ -e "$file" ] || continue

    found=1
    echo "--------------------------------------------"
    echo "File: $file"
    echo "--------------------------------------------"

    ext="${file##*.}"
    ext=$(echo "$ext" | tr '[:upper:]' '[:lower:]')

    # Check for private key
    is_key=false

    if [ "$ext" = "key" ]; then
        is_key=true
    elif [ -f "$file" ] && grep -q -E "-----BEGIN (RSA |EC |ENCRYPTED |)PRIVATE KEY-----|-----BEGIN OPENSSH PRIVATE KEY-----" "$file" 2>/dev/null; then
        is_key=true
    fi

    if [ "$is_key" = true ]; then
        echo -e "\033[33m[PRIVATE KEY]\033[0m - Skipping (not a certificate)"
        echo "Type: Private Key file"
        echo ""
        echo "[Skipped - Private key]"
        ((keycount++))
        echo ""
        continue
    fi

    # Check for PKCS#12/PFX files
    if [ "$ext" = "p12" ] || [ "$ext" = "pfx" ]; then
        echo -e "\033[33m[PKCS#12/PFX]\033[0m - Contains certificate + private key bundle"
        echo "Note: Use 'openssl pkcs12' to extract certificate, or import directly with browser"
        echo ""
        echo "[Skipped - Use different tool for PFX import]"
        echo ""
        continue
    fi

    # Try to parse as certificate using openssl
    cert_info=$(openssl x509 -in "$file" -noout -subject -issuer -dates -fingerprint -ext subjectAltName 2>/dev/null)

    if [ $? -eq 0 ]; then
        echo -e "\033[32m[CERTIFICATE]\033[0m"

        # Extract and display certificate details
        subject=$(openssl x509 -in "$file" -noout -subject 2>/dev/null | sed 's/subject=/Subject (CN): /')
        issuer=$(openssl x509 -in "$file" -noout -issuer 2>/dev/null | sed 's/issuer=/Issuer: /')
        startdate=$(openssl x509 -in "$file" -noout -startdate 2>/dev/null | sed 's/notBefore=/Valid From: /')
        enddate=$(openssl x509 -in "$file" -noout -enddate 2>/dev/null | sed 's/notAfter=/Valid To: /')
        fingerprint=$(openssl x509 -in "$file" -noout -fingerprint -sha256 2>/dev/null | sed 's/sha256 Fingerprint=/Thumbprint (SHA256): /' | sed 's/SHA256 Fingerprint=/Thumbprint (SHA256): /')
        san=$(openssl x509 -in "$file" -noout -ext subjectAltName 2>/dev/null | grep -v "X509v3 Subject Alternative Name:")

        echo "$subject"
        echo "$issuer"
        echo "$startdate"
        echo "$enddate"
        echo "$fingerprint"

        if [ -n "$san" ]; then
            echo "SANs:$san"
        else
            echo "SANs: (none)"
        fi

        echo ""
        read -p "Install this certificate to Trusted Root store? (Y/N): " confirm

        if [[ "$confirm" =~ ^[Yy]$ ]]; then
            echo "Installing $file..."

            # Convert to PEM if needed (for DER format)
            if [ "$ext" = "der" ]; then
                tmpfile=$(mktemp)
                openssl x509 -in "$file" -inform DER -out "$tmpfile" -outform PEM
                install_cert "$tmpfile"
                result=$?
                rm -f "$tmpfile"
            else
                install_cert "$file"
                result=$?
            fi

            if [ $result -eq 0 ]; then
                echo "[SUCCESS] Certificate installed."
                ((certcount++))
            else
                echo "[ERROR] Failed to install certificate. Make sure you have sudo privileges."
            fi
        else
            echo "Skipped $file"
        fi
    else
        echo -e "\033[31m[UNKNOWN/INVALID]\033[0m - Could not parse as certificate"
        echo "Error: File is not a valid X.509 certificate or format not recognized"
        echo ""
        echo "[Skipped - Invalid or unrecognized file]"
    fi
    echo ""
done

if [ "$found" -eq 0 ]; then
    echo "No certificate or key files found in '$CERT_DIR'."
    echo "Supported extensions: .cer, .crt, .pem, .der, .key, .p12, .pfx"
fi

echo "============================================"
echo "Summary:"
echo "  Certificates installed: $certcount"
echo "  Private keys found (skipped): $keycount"
echo "============================================"
echo ""
echo "Done."
