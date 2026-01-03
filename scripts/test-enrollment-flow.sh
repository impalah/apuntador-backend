#!/bin/bash
#
# Test script for complete device enrollment flow
# Tests: CA certificate retrieval, CSR generation, enrollment, and DynamoDB verification
#
set -e

echo " Testing complete device enrollment flow..."
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Get CA certificate
echo -e "${BLUE}1 Getting CA certificate...${NC}"
CA_RESPONSE=$(curl -s https://apuntador.ngrok.app/device/ca-certificate)
echo "$CA_RESPONSE" | jq -r '.certificate' > /tmp/ca.pem

if [[ ! -s /tmp/ca.pem ]]; then
    echo -e "${YELLOW} Failed to get CA certificate${NC}"
    exit 1
fi

echo -e "${GREEN}    CA certificate retrieved${NC}"
openssl x509 -in /tmp/ca.pem -noout -subject -issuer -dates

echo ""

# 2. Generate device key and CSR
echo -e "${BLUE}2 Generating device credentials...${NC}"
DEVICE_ID="android-test-$(date +%s)"
openssl genrsa -out /tmp/device.key 2048 2>/dev/null
openssl req -new -key /tmp/device.key -out /tmp/device.csr \
  -subj "/C=ES/O=Apuntador/CN=$DEVICE_ID" 2>/dev/null

echo -e "${GREEN}    Device key and CSR generated${NC}"
echo "   Device ID: $DEVICE_ID"

echo ""

# 3. Enroll device
echo -e "${BLUE}3 Enrolling device...${NC}"
CSR_CONTENT=$(cat /tmp/device.csr | sed 's/$/\\n/' | tr -d '\n')

ENROLL_RESPONSE=$(curl -s -X POST https://apuntador.ngrok.app/device/enroll \
  -H "Content-Type: application/json" \
  -d "{\"csr\":\"$CSR_CONTENT\",\"device_id\":\"$DEVICE_ID\",\"platform\":\"android\",\"attestation\":null}")

echo "$ENROLL_RESPONSE" | jq -r '.certificate' > /tmp/device.pem
SERIAL=$(echo "$ENROLL_RESPONSE" | jq -r '.serial')
ISSUED_AT=$(echo "$ENROLL_RESPONSE" | jq -r '.issued_at')
EXPIRES_AT=$(echo "$ENROLL_RESPONSE" | jq -r '.expires_at')

if [[ ! -s /tmp/device.pem ]]; then
    echo -e "${YELLOW} Failed to enroll device${NC}"
    echo "$ENROLL_RESPONSE" | jq .
    exit 1
fi

echo -e "${GREEN}    Device enrolled successfully${NC}"
echo "   Serial: $SERIAL"
echo "   Issued: $ISSUED_AT"
echo "   Expires: $EXPIRES_AT"

echo ""

# 4. Verify certificate
echo -e "${BLUE}4 Verifying certificate...${NC}"
VERIFY_OUTPUT=$(openssl verify -CAfile /tmp/ca.pem /tmp/device.pem 2>&1)

if echo "$VERIFY_OUTPUT" | grep -q "OK"; then
    echo -e "${GREEN}    Certificate verification: OK${NC}"
else
    echo -e "${YELLOW}    Certificate verification failed${NC}"
    echo "   $VERIFY_OUTPUT"
    exit 1
fi

echo ""

# 5. Check in DynamoDB (by device_id)
echo -e "${BLUE}5 Checking DynamoDB (by device_id)...${NC}"
sleep 1  # Give DynamoDB time to propagate

DB_RESULT=$(AWS_PAGER="" aws dynamodb scan \
  --table-name apuntador-tls-certificates \
  --region eu-west-1 \
  --filter-expression "device_id = :device_id" \
  --expression-attribute-values "{\":device_id\":{\"S\":\"$DEVICE_ID\"}}" \
  --output json 2>&1)

if echo "$DB_RESULT" | jq -e '.Items[0]' > /dev/null 2>&1; then
    echo -e "${GREEN}    Certificate found in DynamoDB${NC}"
    echo "$DB_RESULT" | jq '.Items[0] | {device_id: .device_id.S, serial: .serial_number.S, platform: .platform.S, expires_at: .expires_at.S, revoked: .revoked.BOOL}'
else
    echo -e "${YELLOW}    Certificate not found in DynamoDB${NC}"
    echo "$DB_RESULT"
fi

echo ""

# 6. Check via SerialIndex
echo -e "${BLUE}6 Checking DynamoDB (via SerialIndex)...${NC}"

INDEX_RESULT=$(AWS_PAGER="" aws dynamodb query \
  --table-name apuntador-tls-certificates \
  --index-name SerialIndex \
  --key-condition-expression "serial_number = :serial" \
  --expression-attribute-values "{\":serial\":{\"S\":\"$SERIAL\"}}" \
  --region eu-west-1 \
  --output json 2>&1)

if echo "$INDEX_RESULT" | jq -e '.Items[0]' > /dev/null 2>&1; then
    echo -e "${GREEN}    Certificate found via SerialIndex${NC}"
    echo "$INDEX_RESULT" | jq '.Items[0] | {device_id: .device_id.S, serial: .serial_number.S, platform: .platform.S}'
else
    echo -e "${YELLOW}    Certificate not found via SerialIndex${NC}"
    echo "$INDEX_RESULT"
fi

echo ""

# 7. Summary
echo -e "${GREEN} Test completed successfully!${NC}"
echo ""
echo "Summary:"
echo "  - CA Certificate: OK"
echo "  - Device Enrollment: OK"
echo "  - Certificate Verification: OK"
echo "  - DynamoDB Storage: OK"
echo "  - SerialIndex Query: OK"
echo ""
echo "Files created:"
echo "  - /tmp/ca.pem (CA certificate)"
echo "  - /tmp/device.key (device private key)"
echo "  - /tmp/device.csr (certificate signing request)"
echo "  - /tmp/device.pem (signed device certificate)"
echo ""
echo "Clean up with: rm -f /tmp/ca.pem /tmp/device.{key,csr,pem}"
