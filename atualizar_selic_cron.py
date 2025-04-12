#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para atualização automática do cache da Selic Apurada.
Ideal para ser executado via crontab ou outro agendador.

Exemplo de configuração no crontab:
0 22 * * * /caminho/para/python /caminho/para/atualizar_selic_cron.py >> /caminho/para/selic_atualizacao.log 2>&1
"""

import os
import sys
import logging
import traceback
from datetime import datetime
from atualizar_selic_apurada import atualizar_selic_apurada

# Configuração de logging
LOG_FILE = 'selic_atualizacao.log'

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  # Exibe logs no console
        logging.FileHandler(LOG_FILE)  # Salva logs em arquivo
    ]
)

logger = logging.getLogger('selic_update')

def main():
    """Função principal para executar a atualização e registrar logs."""
    logger.info("=== Iniciando atualização automática da Selic Apurada ===")
    
    try:
        # Registra o diretório de trabalho atual para fins de depuração
        logger.info(f"Diretório de trabalho: {os.getcwd()}")
        
        # Executa a atualização com verificação de registros inválidos
        inicio = datetime.now()
        # Força a atualização e verifica os últimos 30 dias para problemas 
        atualizar_selic_apurada(forcar_atualizacao=True, dias_para_verificar=30)
        fim = datetime.now()
        
        duracao = (fim - inicio).total_seconds()
        logger.info(f"Atualização concluída em {duracao:.2f} segundos.")
        
    except Exception as e:
        logger.error(f"Erro durante a atualização: {str(e)}")
        logger.error(traceback.format_exc())
        return 1
    
    logger.info("=== Atualização automática finalizada ===")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 