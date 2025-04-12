#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para testar a atualização da Selic Apurada forçando um período específico.
Isso é útil para simular situações onde o cache está desatualizado.
"""

import sys
import datetime
from datetime import datetime, timedelta
from atualizar_selic_apurada import obter_dados_selic, formatar_data

def testar_consulta():
    """Testa a consulta à API do BCB para um período específico."""
    # Define um período de 10 dias para o teste
    data_final = datetime.now() - timedelta(days=1)  # Ontem
    data_inicial = data_final - timedelta(days=10)   # 10 dias atrás
    
    print(f"Testando consulta de {formatar_data(data_inicial)} até {formatar_data(data_final)}...")
    
    resultado = obter_dados_selic(data_inicial, data_final)
    
    if not resultado or "registros" not in resultado:
        print("Falha ao obter dados.")
        return False
    
    print(f"Sucesso! Obtidos {len(resultado['registros'])} registros.")
    
    # Exibe os primeiros 3 registros para verificação
    for i, registro in enumerate(resultado['registros'][:3]):
        print(f"Registro {i+1}: Data={registro['dataCotacao']}, Taxa Anual={registro['taxaAnual']}")
    
    return True

if __name__ == "__main__":
    testar_consulta() 