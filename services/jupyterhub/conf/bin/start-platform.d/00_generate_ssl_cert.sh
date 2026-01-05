#!/bin/bash
# ----------------------------------------------------------------------------------------
# Generates SSL keys used by jupyterlab & traefik
# ----------------------------------------------------------------------------------------

# generate ssl keys if don't exist yet (happens first time the script is run)
# skip this step if no certificate dir
CERTS_DIR="/mnt/certs"
DOMAIN_NAME="${CERTIFICATE_DOMAIN_NAME:-localhost}"
if [[ -z $(find $CERTS_DIR -name '*.crt') ]]; then
	/mkcert.sh "$CERTS_DIR" "$DOMAIN_NAME" "server" # params: certs_dir, common_name, file_prefix
fi


# EOF

