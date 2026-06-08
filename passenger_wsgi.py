import os
import sys

# Cambiamos al directorio mailclient para que Flask encuentre tus archivos y el .env
app_dir = os.path.join(os.path.dirname(__file__), 'mailclient')
os.chdir(app_dir)
sys.path.insert(0, app_dir)

# Importamos la aplicación Flask (app.py) como 'application' para que Passenger la reconozca
from app import app as application
