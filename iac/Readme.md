# AWS infrastructure

IaC to build the infrastructure for apuntador backend.

## Prerequisites

### S3 bucket for infrastrcuture state

Create an S3 bucket for storing infrastructure state:

```bash
aws s3api create-bucket --bucket press-any-key-devops --region eu-west-1 --create-bucket-configuration LocationConstraint=eu-west-1
```


## IaC execution

```powershell
$env:AWS_PROFILE="my_profile"; terraform init -backend-config="application.conf"
$env:AWS_PROFILE="my_profile"; terraform apply -var-file="configuration.tfvars"
```


