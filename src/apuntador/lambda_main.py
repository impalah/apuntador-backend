from mangum import Mangum

from apuntador.application import create_app

app = create_app()
# Configure as lambda handler
lambda_handler = Mangum(app)
