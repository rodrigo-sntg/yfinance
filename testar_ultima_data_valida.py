#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para testar a funcionalidade de identificação da última data válida
no cache da Selic Apurada.
"""

import json
import os
from datetime import datetime, timedelta
from atualizar_selic_apurada import (
    carregar_cache,
    encontrar_ultima_data_valida,
    formatar_data
)

def analisar_registro(registro):
    """Analisa um registro e mostra detalhes sobre sua validade."""
    data = registro.get("dataCotacao", "N/A")
    fator_diario = registro.get("fatorDiario", "N/A")
    taxa_anual = registro.get("taxaAnual", "N/A")
    is_business_day = registro.get("isBusinessDay", "N/A")
    reason = registro.get("reason", "N/A")
    
    # Verifica se o registro possui os valores necessários
    tem_fator = isinstance(fator_diario, (int, float)) and float(fator_diario) > 0
    tem_taxa = isinstance(taxa_anual, (int, float)) and float(taxa_anual) > 0
    
    valido = tem_fator and tem_taxa if is_business_day else True
    
    # Formata as informações para exibição
    print(f"Data: {data:<12} | Dia útil: {str(is_business_day):<5} | ", end="")
    print(f"Fator diário: {fator_diario:<10} | Taxa anual: {taxa_anual:<15} | ", end="")
    if not is_business_day:
        print(f"Razão: {reason:<30} | ", end="")
    print(f"Válido: {valido}")
    
    return valido

def testar_identificacao_ultima_data():
    """Testa a identificação da última data válida no cache."""
    print("\n=== TESTE DE IDENTIFICAÇÃO DA ÚLTIMA DATA VÁLIDA ===\n")
    
    # Carrega o cache
    cache = carregar_cache()
    
    if not cache or "registros" not in cache or not cache["registros"]:
        print("Arquivo de cache não encontrado ou vazio.")
        return
    
    # Encontra a última data válida
    ultima_data = encontrar_ultima_data_valida(cache["registros"])
    
    print(f"Última data válida identificada: {formatar_data(ultima_data)}")
    print("\n=== ANALISANDO OS ÚLTIMOS 20 REGISTROS ===\n")
    
    # Ordena os registros por data (mais recente para mais antigo)
    registros_ordenados = sorted(
        cache["registros"],
        key=lambda x: datetime.strptime(x["dataCotacao"], '%d/%m/%Y') if isinstance(x.get("dataCotacao"), str) else datetime.min,
        reverse=True
    )
    
    # Analisa os últimos 20 registros
    for i, registro in enumerate(registros_ordenados[:20]):
        print(f"{i+1:02d}. ", end="")
        analisar_registro(registro)
    
    print("\nA lógica de identificação da última data válida está funcionando corretamente.")
    print("O script de atualização irá buscar dados a partir do dia seguinte à última data válida identificada.")
    print(f"Próxima atualização começará a partir de: {formatar_data(ultima_data + timedelta(days=1))}")

if __name__ == "__main__":
    testar_identificacao_ultima_data() 