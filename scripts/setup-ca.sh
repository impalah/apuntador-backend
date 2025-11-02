#!/bin/bash

################################################################################
# Certificate Authority (CA) Setup Script
# 
# Generates a self-managed Certificate Authority for mTLS device authentication.
# Supports both local development and production deployment.
#
# Usage:
#   ./scripts/setup-ca.sh [OPTIONS]
#
# Options:
#   --local          Generate CA for local development (default)
#   --production     Generate CA for production (longer validity)
#   --output DIR     Output directory (default: ./.local_infrastructure/secrets)
#   --help           Show this help message
#
# Requirements:
#   - OpenSSL 1.1.1+ (check: openssl version)
#
# Security Notes:
#   - CA private key is generated with 4096-bit RSA
#   - Private key never leaves the server
#   - Production: Store CA key in AWS Secrets Manager
#   - Local: Files have restrictive permissions (0600)
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
MODE="local"
OUTPUT_DIR="./.credentials"
CA_KEY_SIZE=4096
ORGANIZATION="Apuntador"
COUNTRY="ES"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --local)
            MODE="local"
            shift
            ;;
        --production)
            MODE="production"
            shift
            ;;
        --output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --help)
            head -n 30 "$0" | tail -n +3
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Print header
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        Apuntador Certificate Authority Setup                 ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check OpenSSL version
echo -e "${YELLOW}→ Checking OpenSSL version...${NC}"
OPENSSL_VERSION=$(openssl version)
echo -e "  ${GREEN}✓${NC} $OPENSSL_VERSION"
echo ""

# Set validity based on mode
if [ "$MODE" = "production" ]; then
    CA_DAYS=3650  # 10 years
    echo -e "${YELLOW}→ Mode: Production${NC}"
    echo -e "  CA validity: ${GREEN}$CA_DAYS days (10 years)${NC}"
else
    CA_DAYS=1825  # 5 years (sufficient for local dev)
    echo -e "${YELLOW}→ Mode: Local Development${NC}"
    echo -e "  CA validity: ${GREEN}$CA_DAYS days (5 years)${NC}"
fi
echo ""

# Create output directory
echo -e "${YELLOW}→ Creating output directory...${NC}"
mkdir -p "$OUTPUT_DIR"
chmod 700 "$OUTPUT_DIR"
echo -e "  ${GREEN}✓${NC} $OUTPUT_DIR"
echo ""

# File paths
CA_KEY="$OUTPUT_DIR/ca_private_key.pem"
CA_CERT="$OUTPUT_DIR/ca_certificate.pem"
CA_CONFIG="$OUTPUT_DIR/ca_openssl.cnf"

# Check if CA already exists
if [ -f "$CA_KEY" ] || [ -f "$CA_CERT" ]; then
    echo -e "${RED}⚠ Warning: CA files already exist!${NC}"
    echo -e "  Key:  $CA_KEY"
    echo -e "  Cert: $CA_CERT"
    echo ""
    read -p "Overwrite existing CA? (yes/no): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        echo -e "${YELLOW}Aborted. Existing CA preserved.${NC}"
        exit 0
    fi
    echo ""
fi

# Generate OpenSSL configuration for CA
echo -e "${YELLOW}→ Creating OpenSSL configuration...${NC}"
cat > "$CA_CONFIG" <<EOF
[ req ]
default_bits           = $CA_KEY_SIZE
default_md             = sha256
distinguished_name     = req_distinguished_name
x509_extensions        = v3_ca
prompt                 = no

[ req_distinguished_name ]
C  = $COUNTRY
O  = $ORGANIZATION
CN = Apuntador Certificate Authority

[ v3_ca ]
subjectKeyIdentifier   = hash
authorityKeyIdentifier = keyid:always,issuer
basicConstraints       = critical, CA:true
keyUsage               = critical, digitalSignature, keyCertSign, cRLSign

[ v3_device ]
basicConstraints       = CA:FALSE
keyUsage               = critical, digitalSignature, keyEncipherment
extendedKeyUsage       = clientAuth
subjectKeyIdentifier   = hash
authorityKeyIdentifier = keyid,issuer
EOF

echo -e "  ${GREEN}✓${NC} Configuration file created"
echo ""

# Generate CA private key
echo -e "${YELLOW}→ Generating CA private key (RSA $CA_KEY_SIZE)...${NC}"
openssl genrsa -out "$CA_KEY" $CA_KEY_SIZE 2>/dev/null
chmod 600 "$CA_KEY"
echo -e "  ${GREEN}✓${NC} CA private key generated"
echo -e "  ${GREEN}✓${NC} Permissions set to 0600"
echo ""

# Generate CA certificate
echo -e "${YELLOW}→ Generating CA certificate...${NC}"
openssl req \
    -new \
    -x509 \
    -days $CA_DAYS \
    -key "$CA_KEY" \
    -out "$CA_CERT" \
    -config "$CA_CONFIG" \
    2>/dev/null

chmod 644 "$CA_CERT"
echo -e "  ${GREEN}✓${NC} CA certificate generated"
echo ""

# Display CA certificate information
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}CA Certificate Information:${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
openssl x509 -in "$CA_CERT" -noout -text | grep -E "(Subject:|Issuer:|Not Before|Not After|Public-Key:|Signature Algorithm)"
echo ""

# Generate fingerprint
FINGERPRINT=$(openssl x509 -in "$CA_CERT" -noout -fingerprint -sha256)
echo -e "${YELLOW}SHA256 Fingerprint:${NC}"
echo -e "  $FINGERPRINT"
echo ""

# Summary
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ CA Setup Complete!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Generated files:${NC}"
echo -e "  ${GREEN}✓${NC} CA Private Key: $CA_KEY"
echo -e "  ${GREEN}✓${NC} CA Certificate: $CA_CERT"
echo -e "  ${GREEN}✓${NC} OpenSSL Config: $CA_CONFIG"
echo ""

if [ "$MODE" = "production" ]; then
    echo -e "${RED}⚠ PRODUCTION MODE SECURITY CHECKLIST:${NC}"
    echo -e "  ${YELLOW}1.${NC} Move CA private key to AWS Secrets Manager:"
    echo -e "     ${BLUE}aws secretsmanager create-secret \\${NC}"
    echo -e "     ${BLUE}  --name apuntador/ca-private-key \\${NC}"
    echo -e "     ${BLUE}  --secret-string file://$CA_KEY${NC}"
    echo ""
    echo -e "  ${YELLOW}2.${NC} Upload CA certificate to S3 (public truststore):"
    echo -e "     ${BLUE}aws s3 cp $CA_CERT s3://apuntador-storage/truststore/ca.pem${NC}"
    echo ""
    echo -e "  ${YELLOW}3.${NC} Delete local CA private key:"
    echo -e "     ${BLUE}shred -u $CA_KEY${NC}"
    echo ""
    echo -e "  ${YELLOW}4.${NC} Update backend configuration:"
    echo -e "     ${BLUE}INFRASTRUCTURE_PROVIDER=aws${NC}"
    echo -e "     ${BLUE}AWS_REGION=us-east-1${NC}"
    echo ""
else
    echo -e "${YELLOW}Next steps for local development:${NC}"
    echo -e "  ${GREEN}1.${NC} Files are ready to use (stored in $OUTPUT_DIR)"
    echo -e "  ${GREEN}2.${NC} Start backend with: ${BLUE}uv run uvicorn apuntador.main:app --reload${NC}"
    echo -e "  ${GREEN}3.${NC} Backend will automatically use local infrastructure"
    echo ""
    echo -e "${YELLOW}To test CA:${NC}"
    echo -e "  ${BLUE}openssl x509 -in $CA_CERT -text -noout${NC}"
    echo ""
fi

echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Setup complete! Your CA is ready for device enrollment.${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
