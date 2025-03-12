import os
import logging
from app.config import LOG_DIR, LOG_FILE

# Criando diretório de logs se não existir
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Obtém o logger para uso em outros módulos
logger = logging.getLogger(__name__) 