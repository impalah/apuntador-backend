#################################################################
# Common services
#################################################################

# Obtener las AZs disponibles en la región
data "aws_availability_zones" "available" {
  state = "available"
}

