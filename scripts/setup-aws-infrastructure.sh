#!/bin/bash
# setup-aws-infrastructure.sh
# Setup AWS infrastructure for Apuntador Backend mTLS system

set -e  # Exit on error

# Disable AWS CLI pager (no more pressing 'q')
export AWS_PAGER=""

# Variables - Ajusta según tu configuración
AWS_REGION="eu-west-1"
TABLE_NAME="apuntador-tls-certificates"
BUCKET_NAME="apuntador.io-tls-cert-storage"
SECRETS_PREFIX="apuntador"

echo "🚀 Setting up AWS infrastructure for Apuntador Backend"
echo "================================================"
echo "Region: $AWS_REGION"
echo "DynamoDB Table: $TABLE_NAME"
echo "S3 Bucket: $BUCKET_NAME"
echo "Secrets Prefix: $SECRETS_PREFIX"
echo ""

# ============================================================================
# 1. DynamoDB Table
# ============================================================================
echo "📊 Checking DynamoDB table: $TABLE_NAME"

# Check if table exists
if aws dynamodb describe-table --table-name "$TABLE_NAME" --region "$AWS_REGION" &>/dev/null; then
  echo "✅ Table already exists: $TABLE_NAME"
else
  echo "➕ Creating DynamoDB table: $TABLE_NAME"
  aws dynamodb create-table \
    --table-name "$TABLE_NAME" \
    --attribute-definitions \
      AttributeName=device_id,AttributeType=S \
      AttributeName=serial_number,AttributeType=S \
      AttributeName=expires_at,AttributeType=S \
    --key-schema \
      AttributeName=device_id,KeyType=HASH \
      AttributeName=serial_number,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --global-secondary-indexes \
      '[
        {
          "IndexName": "SerialIndex",
          "KeySchema": [
            {"AttributeName": "serial_number", "KeyType": "HASH"}
          ],
          "Projection": {"ProjectionType": "ALL"}
        },
        {
          "IndexName": "ExpirationIndex",
          "KeySchema": [
            {"AttributeName": "device_id", "KeyType": "HASH"},
            {"AttributeName": "expires_at", "KeyType": "RANGE"}
          ],
          "Projection": {"ProjectionType": "ALL"}
        }
      ]' \
    --region "$AWS_REGION" > /dev/null
  
  echo "⏳ Waiting for table to become active..."
  aws dynamodb wait table-exists --table-name "$TABLE_NAME" --region "$AWS_REGION"
  echo "✅ Table created successfully: $TABLE_NAME"
fi

echo ""

# ============================================================================
# 2. S3 Bucket
# ============================================================================
echo "🪣 Checking S3 bucket: $BUCKET_NAME"

# Check if bucket exists
if aws s3api head-bucket --bucket "$BUCKET_NAME" 2>/dev/null; then
  echo "✅ Bucket already exists: $BUCKET_NAME"
else
  echo "➕ Creating S3 bucket: $BUCKET_NAME"
  
  # Create bucket with proper location constraint for non-us-east-1 regions
  if [ "$AWS_REGION" = "us-east-1" ]; then
    aws s3api create-bucket \
      --bucket "$BUCKET_NAME" \
      --region "$AWS_REGION" > /dev/null
  else
    aws s3api create-bucket \
      --bucket "$BUCKET_NAME" \
      --region "$AWS_REGION" \
      --create-bucket-configuration LocationConstraint="$AWS_REGION" > /dev/null
  fi
  
  echo "✅ Bucket created successfully: $BUCKET_NAME"
fi

# Configure bucket encryption (always update)
echo "🔐 Configuring bucket encryption..."
aws s3api put-bucket-encryption \
  --bucket "$BUCKET_NAME" \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      },
      "BucketKeyEnabled": false
    }]
  }' > /dev/null

# Configure bucket versioning (always update)
echo "📦 Enabling bucket versioning..."
aws s3api put-bucket-versioning \
  --bucket "$BUCKET_NAME" \
  --versioning-configuration Status=Enabled > /dev/null

# Configure public access block (always update)
echo "🔒 Blocking public access..."
aws s3api put-public-access-block \
  --bucket "$BUCKET_NAME" \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true" > /dev/null

echo "✅ Bucket configured successfully"
echo ""

# ============================================================================
# 3. Secrets Manager
# ============================================================================
echo "🔐 Checking secrets in Secrets Manager"

# Helper function to check if secret exists
secret_exists() {
  aws secretsmanager describe-secret --secret-id "$1" --region "$AWS_REGION" &>/dev/null
}

# CA Private Key
SECRET_NAME="${SECRETS_PREFIX}/ca-private-key"
echo "🔑 Checking secret: $SECRET_NAME"

if secret_exists "$SECRET_NAME"; then
  echo "✅ Secret already exists: $SECRET_NAME"
else
  if [ -f "../.local_infrastructure/secrets/ca-private-key.pem" ]; then
    echo "➕ Creating secret: $SECRET_NAME"
    aws secretsmanager create-secret \
      --name "$SECRET_NAME" \
      --description "Apuntador CA private key for mTLS device authentication" \
      --secret-string file://../.local_infrastructure/secrets/ca-private-key.pem \
      --region "$AWS_REGION" > /dev/null
    echo "✅ Secret created successfully: $SECRET_NAME"
  else
    echo "⚠️  CA private key not found at: ../.local_infrastructure/secrets/ca-private-key.pem"
    echo "    Run: cd .. && uv run python scripts/setup-ca.py --mode local"
  fi
fi

# CA Certificate
SECRET_NAME="${SECRETS_PREFIX}/ca-certificate"
echo "📜 Checking secret: $SECRET_NAME"

if secret_exists "$SECRET_NAME"; then
  echo "✅ Secret already exists: $SECRET_NAME"
else
  if [ -f "../.local_infrastructure/secrets/ca-certificate.pem" ]; then
    echo "➕ Creating secret: $SECRET_NAME"
    aws secretsmanager create-secret \
      --name "$SECRET_NAME" \
      --description "Apuntador CA certificate for mTLS device authentication" \
      --secret-string file://../.local_infrastructure/secrets/ca-certificate.pem \
      --region "$AWS_REGION" > /dev/null
    echo "✅ Secret created successfully: $SECRET_NAME"
  else
    echo "⚠️  CA certificate not found at: ../.local_infrastructure/secrets/ca-certificate.pem"
    echo "    Run: cd .. && uv run python scripts/setup-ca.py --mode local"
  fi
fi

echo ""
echo "================================================"
echo "✅ AWS infrastructure setup complete!"
echo "================================================"
echo ""
echo "📝 Configuration summary:"
echo "   Region: $AWS_REGION"
echo "   DynamoDB Table: $TABLE_NAME"
echo "   S3 Bucket: $BUCKET_NAME"
echo "   Secrets Prefix: $SECRETS_PREFIX"
echo ""
echo "🔧 Update your .env file with:"
echo ""
echo "INFRASTRUCTURE_PROVIDER=aws"
echo "AWS_REGION=$AWS_REGION"
echo "AWS_DYNAMODB_TABLE=$TABLE_NAME"
echo "AWS_S3_BUCKET=$BUCKET_NAME"
echo "AWS_SECRETS_PREFIX=$SECRETS_PREFIX"
echo "AUTO_CREATE_RESOURCES=false"
echo ""
echo "🚀 To verify resources:"
echo "   aws dynamodb describe-table --table-name $TABLE_NAME --region $AWS_REGION"
echo "   aws s3api head-bucket --bucket $BUCKET_NAME"
echo "   aws secretsmanager list-secrets --region $AWS_REGION"
echo ""
