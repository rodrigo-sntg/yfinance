#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Ferramenta de diagnóstico para analisar o cache da Selic Apurada.
Identifica possíveis problemas, inconsistências ou lacunas nos dados.
"""

import json
import os
import sys
import datetime
from datetime import datetime, timedelta
from collections import defaultdict
from atualizar_selic_apurada import (
    carregar_cache,
    converter_data_string_para_datetime,
    formatar_data,
    eh_registro_valido,
    encontrar_ultima_data_valida
)

def mostrar_estatisticas(cache):
    """Mostra estatísticas gerais do cache."""
    if not cache or "registros" not in cache or not cache["registros"]:
        print("Arquivo de cache não encontrado ou vazio.")
        return
    
    total_registros = len(cache["registros"])
    
    # Contadores
    dias_uteis = 0
    dias_nao_uteis = 0
    feriados = 0
    finais_semana = 0
    outros_nao_uteis = 0
    registros_validos = 0
    registros_invalidos = 0
    
    # Datas
    primeira_data = None
    ultima_data = None
    ultima_data_valida = encontrar_ultima_data_valida(cache["registros"])
    
    # Contagens por ano
    registros_por_ano = defaultdict(int)
    
    for registro in cache["registros"]:
        data = converter_data_string_para_datetime(registro["dataCotacao"])
        
        if data:
            # Atualiza primeira e última data
            if primeira_data is None or data < primeira_data:
                primeira_data = data
            if ultima_data is None or data > ultima_data:
                ultima_data = data
            
            # Contagem por ano
            registros_por_ano[data.year] += 1
        
        # Verifica se é dia útil ou não
        if registro.get("isBusinessDay") is True:
            dias_uteis += 1
            if eh_registro_valido(registro):
                registros_validos += 1
            else:
                registros_invalidos += 1
        else:
            dias_nao_uteis += 1
            # Verifica se é fim de semana ou feriado
            reason = registro.get("reason", "").lower()
            if "final_de_semana" in reason:
                finais_semana += 1
            elif "feriado" in reason:
                feriados += 1
            else:
                outros_nao_uteis += 1
    
    print("\n=== ESTATÍSTICAS DO CACHE DA SELIC APURADA ===\n")
    print(f"Total de registros: {total_registros}")
    print(f"Período: de {formatar_data(primeira_data)} até {formatar_data(ultima_data)} ({(ultima_data - primeira_data).days + 1} dias)")
    print(f"Última data válida: {formatar_data(ultima_data_valida)}")
    print(f"Dias úteis: {dias_uteis} ({(dias_uteis/total_registros)*100:.1f}%)")
    print(f"Dias não úteis: {dias_nao_uteis} ({(dias_nao_uteis/total_registros)*100:.1f}%)")
    print(f"   - Finais de semana: {finais_semana}")
    print(f"   - Feriados: {feriados}")
    print(f"   - Outros dias não úteis: {outros_nao_uteis}")
    print(f"Registros válidos: {registros_validos} de {dias_uteis} dias úteis ({(registros_validos/dias_uteis)*100:.1f}% se dia útil)")
    print(f"Registros inválidos: {registros_invalidos} dias úteis sem dados válidos")
    
    print("\nRegistros por ano:")
    for ano in sorted(registros_por_ano.keys()):
        print(f"   - {ano}: {registros_por_ano[ano]} registros")

def verificar_lacunas(cache, modo_resumido=True):
    """Verifica lacunas no cache (dias consecutivos sem dados válidos)."""
    if not cache or "registros" not in cache or not cache["registros"]:
        return
    
    # Ordena os registros por data
    registros_ordenados = sorted(
        cache["registros"],
        key=lambda x: converter_data_string_para_datetime(x["dataCotacao"]) or datetime.min
    )
    
    # Mapeia as datas para seus registros
    datas_registros = {
        converter_data_string_para_datetime(r["dataCotacao"]): r
        for r in registros_ordenados
        if converter_data_string_para_datetime(r["dataCotacao"])
    }
    
    primeira_data = converter_data_string_para_datetime(registros_ordenados[0]["dataCotacao"])
    ultima_data = converter_data_string_para_datetime(registros_ordenados[-1]["dataCotacao"])
    
    print("\n=== VERIFICAÇÃO DE LACUNAS ===\n")
    
    # Verifica se há datas faltando no período
    lacunas = []
    lacuna_atual = []
    total_dias_faltantes = 0
    
    data_atual = primeira_data
    while data_atual <= ultima_data:
        if data_atual not in datas_registros:
            if not modo_resumido:
                print(f"ALERTA: Data {formatar_data(data_atual)} não está presente no cache!")
            total_dias_faltantes += 1
            lacuna_atual.append(data_atual)
        else:
            if lacuna_atual:
                lacunas.append(lacuna_atual)
                lacuna_atual = []
        
        data_atual += timedelta(days=1)
    
    if lacuna_atual:
        lacunas.append(lacuna_atual)
    
    if lacunas:
        print(f"Total de {total_dias_faltantes} dias faltantes no cache, distribuídos em {len(lacunas)} lacunas.")
        
        # Ordena as lacunas por tamanho (da maior para a menor)
        lacunas_ordenadas = sorted(lacunas, key=len, reverse=True)
        
        # Mostra as 5 maiores lacunas
        print("\nMaiores lacunas:")
        for i, lacuna in enumerate(lacunas_ordenadas[:5]):
            inicio = lacuna[0]
            fim = lacuna[-1]
            print(f"Lacuna {i+1}: de {formatar_data(inicio)} até {formatar_data(fim)} ({len(lacuna)} dias)")
        
        # Mostra as lacunas mais recentes
        print("\nLacunas mais recentes:")
        lacunas_recentes = sorted(lacunas, key=lambda x: x[-1], reverse=True)
        for i, lacuna in enumerate(lacunas_recentes[:3]):
            inicio = lacuna[0]
            fim = lacuna[-1]
            print(f"Lacuna recente {i+1}: de {formatar_data(inicio)} até {formatar_data(fim)} ({len(lacuna)} dias)")
    else:
        print("Nenhuma lacuna encontrada no cache. Todas as datas estão presentes.")

def verificar_dias_uteis_sem_dados(cache):
    """Verifica dias úteis (segunda a sexta) que não possuem dados da Selic."""
    if not cache or "registros" not in cache or not cache["registros"]:
        return
    
    print("\n=== DIAS ÚTEIS SEM DADOS VÁLIDOS ===\n")
    
    # Conta quantos dias úteis estão sem dados válidos
    dias_sem_dados = []
    for registro in cache["registros"]:
        data = converter_data_string_para_datetime(registro["dataCotacao"])
        
        # Verifica se é dia útil (de segunda a sexta)
        if data and data.weekday() < 5:
            if registro.get("isBusinessDay") is True and not eh_registro_valido(registro):
                dias_sem_dados.append((data, registro.get("reason", "Sem razão especificada")))
    
    # Ordena por data (mais recente primeiro)
    dias_sem_dados.sort(key=lambda x: x[0], reverse=True)
    
    if dias_sem_dados:
        print(f"Encontrados {len(dias_sem_dados)} dias úteis sem dados válidos:")
        for i, (data, reason) in enumerate(dias_sem_dados[:20]):  # Mostra apenas os 20 mais recentes
            print(f"{i+1:02d}. {formatar_data(data)}: {reason}")
        
        if len(dias_sem_dados) > 20:
            print(f"... e mais {len(dias_sem_dados) - 20} dias (use --full para ver todos)")
    else:
        print("Não foram encontrados dias úteis sem dados válidos.")

def verificar_ultimos_dias(cache, dias=30):
    """Verifica a integridade dos dados dos últimos X dias."""
    if not cache or "registros" not in cache or not cache["registros"]:
        return
    
    data_final = datetime.now() - timedelta(days=1)  # Ontem
    data_inicial = data_final - timedelta(days=dias)  # X dias atrás
    
    print(f"\n=== VERIFICAÇÃO DOS ÚLTIMOS {dias} DIAS ===\n")
    print(f"Período: de {formatar_data(data_inicial)} até {formatar_data(data_final)}")
    
    # Filtra registros no período
    registros_periodo = []
    dias_uteis_sem_dados = []
    dias_registrados = set()
    
    for registro in cache["registros"]:
        data = converter_data_string_para_datetime(registro["dataCotacao"])
        if data and data_inicial <= data <= data_final:
            registros_periodo.append(registro)
            dias_registrados.add(data)
            
            # Verifica dias úteis sem dados
            if data.weekday() < 5 and registro.get("isBusinessDay") is True and not eh_registro_valido(registro):
                dias_uteis_sem_dados.append(data)
    
    # Verifica dias faltantes
    dias_faltantes = []
    data_atual = data_inicial
    while data_atual <= data_final:
        if data_atual not in dias_registrados:
            dias_faltantes.append(data_atual)
        data_atual += timedelta(days=1)
    
    # Resultados
    print(f"Total de dias no período: {(data_final - data_inicial).days + 1}")
    print(f"Dias com registros: {len(registros_periodo)}")
    print(f"Dias faltantes: {len(dias_faltantes)}")
    print(f"Dias úteis sem dados válidos: {len(dias_uteis_sem_dados)}")
    
    if dias_uteis_sem_dados:
        print("\nDias úteis sem dados válidos no período:")
        for data in sorted(dias_uteis_sem_dados):
            print(f"- {formatar_data(data)}")
    
    if dias_faltantes:
        print("\nDias faltantes no período:")
        for data in sorted(dias_faltantes)[:10]:  # Mostra apenas os 10 primeiros
            print(f"- {formatar_data(data)}")
        if len(dias_faltantes) > 10:
            print(f"... e mais {len(dias_faltantes) - 10} dias")

def main():
    """Função principal"""
    # Carrega o cache
    cache = carregar_cache()
    
    if not cache or "registros" not in cache or not cache["registros"]:
        print("Arquivo de cache não encontrado ou vazio.")
        return 1
    
    # Modo completo (mostra mais detalhes)
    modo_completo = "--full" in sys.argv
    
    # Mostra estatísticas gerais
    mostrar_estatisticas(cache)
    
    # Verifica os últimos 30 dias
    verificar_ultimos_dias(cache, 30)
    
    # Verifica lacunas
    verificar_lacunas(cache, not modo_completo)
    
    # Verifica dias úteis sem dados
    verificar_dias_uteis_sem_dados(cache)
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 