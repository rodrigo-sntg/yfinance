import os

# Configuração de diretórios
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "app.log")

# Diretório para backups do cache
CACHE_BACKUP_DIR = "backups"

# Arquivos de cache
CACHE_FILE = "selic_apurada_cache.json"
HOLIDAYS_CACHE_FILE = "feriados_cache.json"

# URLs de APIs externas
BCB_API_URL = "https://www3.bcb.gov.br/novoselic/rest/taxaSelicApurada/pub/search?parametrosOrdenacao=%5B%5D&page=1&pageSize=20"
BRASIL_API_HOLIDAYS_URL = "https://brasilapi.com.br/api/feriados/v1/{year}" 