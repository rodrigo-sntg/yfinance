#!/usr/bin/env python3
"""
Script para verificar a estrutura de backups criada
"""
import os
import glob
from app.config import CACHE_BACKUP_DIR, CACHE_FILE, HOLIDAYS_CACHE_FILE

def verificar_backups():
    """Verifica a estrutura de backups"""
    print(f"Verificando backups em: {CACHE_BACKUP_DIR}")
    
    if not os.path.exists(CACHE_BACKUP_DIR):
        print(f"Diretório de backups não existe: {CACHE_BACKUP_DIR}")
        return
    
    print(f"Diretório de backups existe: {CACHE_BACKUP_DIR}")
    
    # Listar arquivos no diretório de backups
    arquivos = os.listdir(CACHE_BACKUP_DIR)
    print(f"Total de arquivos: {len(arquivos)}")
    
    for arquivo in arquivos:
        caminho = os.path.join(CACHE_BACKUP_DIR, arquivo)
        tamanho = os.path.getsize(caminho)
        print(f"- {arquivo} ({tamanho} bytes)")
    
    # Verificar arquivos de cache principais
    if os.path.exists(CACHE_FILE):
        print(f"\nArquivo de cache Selic existe: {CACHE_FILE}")
        print(f"Tamanho: {os.path.getsize(CACHE_FILE)} bytes")
    else:
        print(f"\nArquivo de cache Selic não existe: {CACHE_FILE}")
    
    if os.path.exists(HOLIDAYS_CACHE_FILE):
        print(f"Arquivo de cache de feriados existe: {HOLIDAYS_CACHE_FILE}")
        print(f"Tamanho: {os.path.getsize(HOLIDAYS_CACHE_FILE)} bytes")
    else:
        print(f"Arquivo de cache de feriados não existe: {HOLIDAYS_CACHE_FILE}")

if __name__ == "__main__":
    verificar_backups() 