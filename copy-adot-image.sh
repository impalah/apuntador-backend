#!/bin/bash
set -e

AWS_ACCOUNT_ID="670089840758"
AWS_REGION="eu-west-1"
REPO_NAME="aws-otel-collector"

echo "📦 Copiando imagen ADOT collector a ECR privado..."

# 1. Crear repositorio ECR si no existe
echo "1️⃣ Creando repositorio ECR..."
aws ecr describe-repositories --repository-names $REPO_NAME --region $AWS_REGION 2>/dev/null || \
aws ecr create-repository \
  --repository-name $REPO_NAME \
  --region $AWS_REGION \
  --image-scanning-configuration scanOnPush=true

# 2. Login a ECR público (región us-east-1 siempre)
echo "2️⃣ Login a ECR público..."
aws ecr-public get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin public.ecr.aws

# 3. Login a ECR privado
echo "3️⃣ Login a ECR privado..."
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# 4. Eliminar imagen local si existe (para evitar caché)
echo "4️⃣ Eliminando imagen local en caché..."
docker rmi public.ecr.aws/aws-observability/aws-otel-collector:latest 2>/dev/null || true
docker rmi ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${REPO_NAME}:latest 2>/dev/null || true

# 5. Pull imagen pública (forzando linux/amd64)
echo "5️⃣ Descargando imagen pública (linux/amd64 para Fargate X86_64)..."
docker pull --platform linux/amd64 public.ecr.aws/aws-observability/aws-otel-collector:latest

# 6. Verificar arquitectura
echo "6️⃣ Verificando arquitectura..."
ARCH=$(docker inspect public.ecr.aws/aws-observability/aws-otel-collector:latest | grep -m1 Architecture | cut -d'"' -f4)
echo "   Arquitectura detectada: $ARCH"
if [ "$ARCH" != "amd64" ]; then
  echo "❌ ERROR: La imagen no es amd64 (es $ARCH). Algo salió mal."
  exit 1
fi

# 7. Tag con repositorio privado
echo "7️⃣ Etiquetando imagen..."
docker tag public.ecr.aws/aws-observability/aws-otel-collector:latest \
  ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${REPO_NAME}:latest

# 8. Push a ECR privado
echo "8️⃣ Subiendo a ECR privado..."
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${REPO_NAME}:latest

echo "✅ Imagen copiada exitosamente!"
echo "📌 URI: ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${REPO_NAME}:latest"
