#!/usr/bin/env python3
"""
Script para testar a funcionalidade de backup diário e limpeza de backups antigos
"""
import os
import glob
import json
import shutil
from datetime import datetime, timedelta
from app.config import CACHE_BACKUP_DIR, CACHE_FILE, HOLIDAYS_CACHE_FILE
from app.cache import save_cache, save_holidays_cache, clean_old_backups

def criar_dados_teste():
    """Cria dados de teste para o cache"""
    dados_selic = {
        "registros": [
            {
                "dataCotacao": "01/06/2023",
                "fatorDiario": "1.000123",
                "testBackup": True
            }
        ]
    }
    
    dados_feriados = {
        "2023": [
            {
                "date": "2023-01-01",
                "name": "Confraternização Universal",
                "type": "national",
                "testBackup": True
            }
        ]
    }
    
    return dados_selic, dados_feriados

def criar_backups_antigos(dias=40):
    """Cria backups antigos para testar a limpeza"""
    os.makedirs(CACHE_BACKUP_DIR, exist_ok=True)
    
    dados_selic, dados_feriados = criar_dados_teste()
    
    hoje = datetime.now()
    
    for i in range(1, dias + 1):
        data = hoje - timedelta(days=i)
        data_str = data.strftime('%Y%m%d')
        
        # Cria backup de selic
        backup_selic = os.path.join(CACHE_BACKUP_DIR, f"selic_backup_{data_str}.json")
        with open(backup_selic, 'w') as f:
            json.dump(dados_selic, f)
        
        # Cria backup de feriados
        backup_feriados = os.path.join(CACHE_BACKUP_DIR, f"feriados_backup_{data_str}.json")
        with open(backup_feriados, 'w') as f:
            json.dump(dados_feriados, f)
        
        print(f"Criados backups para {data_str}")

def contar_backups():
    """Conta quantos backups existem no diretório"""
    if not os.path.exists(CACHE_BACKUP_DIR):
        return 0
    
    padroes = [
        os.path.join(CACHE_BACKUP_DIR, "selic_backup_*.json"),
        os.path.join(CACHE_BACKUP_DIR, "feriados_backup_*.json")
    ]
    
    total = 0
    for padrao in padroes:
        arquivos = glob.glob(padrao)
        total += len(arquivos)
    
    return total

def limpar_diretorio_backups():
    """Remove todos os arquivos de backup para começar o teste limpo"""
    if os.path.exists(CACHE_BACKUP_DIR):
        shutil.rmtree(CACHE_BACKUP_DIR)
        os.makedirs(CACHE_BACKUP_DIR)
        print(f"Diretório de backups limpo: {CACHE_BACKUP_DIR}")

def executar_teste():
    """Executa o teste completo"""
    # Limpa o diretório de backups
    limpar_diretorio_backups()
    
    # Cria dados de teste
    dados_selic, dados_feriados = criar_dados_teste()
    
    # Salva os caches (deve criar backups)
    print("\n1. Salvando caches pela primeira vez (deve criar backups)...")
    save_cache(dados_selic)
    save_holidays_cache(dados_feriados)
    
    # Verifica se os backups foram criados
    qtd_backups = contar_backups()
    print(f"Backups criados: {qtd_backups}")
    
    # Tenta salvar novamente (não deve criar novos backups para o mesmo dia)
    print("\n2. Salvando caches novamente (não deve criar backups duplicados)...")
    save_cache(dados_selic)
    save_holidays_cache(dados_feriados)
    
    # Verifica se o número de backups permanece o mesmo
    qtd_backups_apos = contar_backups()
    print(f"Backups após segunda execução: {qtd_backups_apos}")
    
    # Cria backups antigos
    print("\n3. Criando backups antigos para testar limpeza...")
    criar_backups_antigos(dias=40)
    
    # Conta backups antes da limpeza
    qtd_antes_limpeza = contar_backups()
    print(f"Backups antes da limpeza: {qtd_antes_limpeza}")
    
    # Executa limpeza manual
    print("\n4. Executando limpeza de backups antigos...")
    removidos = clean_old_backups(max_days=30)
    print(f"Backups antigos removidos: {removidos}")
    
    # Conta backups após limpeza
    qtd_apos_limpeza = contar_backups()
    print(f"Backups após limpeza: {qtd_apos_limpeza}")
    
    print("\nTeste concluído!")

if __name__ == "__main__":
    executar_teste() 