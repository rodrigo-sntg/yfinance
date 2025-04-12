#!/usr/bin/env python3
"""
Script para atualizar a lista de taxas SELIC apuradas com todos os dias desde 2023.
Inclui feriados e dias não úteis como finais de semana com taxa 0.
"""

import sys
import os
from datetime import datetime, date, timedelta
import json
import argparse

# Importa as funções necessárias do módulo app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.selic import ensure_rates_in_cache
from app.cache import load_cache, save_cache, get_cached_rates
from app.logger import logger

def parse_arguments():
    """Parse os argumentos da linha de comando."""
    parser = argparse.ArgumentParser(description='Atualiza a lista SELIC apurada com todos os dias desde 2023.')
    parser.add_argument('--data-inicial', type=str, default='01/01/2023',
                      help='Data inicial no formato DD/MM/YYYY (padrão: 01/01/2023)')
    parser.add_argument('--data-final', type=str, default=None,
                      help='Data final no formato DD/MM/YYYY (padrão: data atual)')
    parser.add_argument('--mostrar-resumo', action='store_true',
                      help='Mostra um resumo da lista após a atualização')
    parser.add_argument('--dias-uteis', action='store_true',
                      help='Mostrar apenas dias úteis no resumo')
    parser.add_argument('--dias-n-uteis', action='store_true',
                      help='Mostrar apenas dias não úteis no resumo')
    parser.add_argument('--verbose', action='store_true',
                      help='Mostra informações detalhadas durante a execução')
    
    return parser.parse_args()

def converter_data(data_str):
    """Converte uma string de data para um objeto date."""
    return datetime.strptime(data_str, '%d/%m/%Y').date()

def calcular_estatisticas(taxas_diarias):
    """Calcula estatísticas sobre as taxas diárias."""
    dias_uteis = sum(1 for taxa in taxas_diarias.values() if taxa > 0)
    dias_nao_uteis = sum(1 for taxa in taxas_diarias.values() if taxa == 0)
    total_dias = len(taxas_diarias)
    
    # Encontra a menor e a maior data
    datas = [d for d in taxas_diarias.keys()]
    data_inicio = min(datas) if datas else None
    data_fim = max(datas) if datas else None
    
    return {
        "dias_uteis": dias_uteis,
        "dias_nao_uteis": dias_nao_uteis,
        "total_dias": total_dias,
        "data_inicio": data_inicio,
        "data_fim": data_fim
    }

def mostrar_resumo(taxas_diarias, apenas_dias_uteis=False, apenas_dias_nao_uteis=False, max_itens=10):
    """Mostra um resumo da lista de taxas diárias."""
    print("\n=== RESUMO DA LISTA SELIC APURADA ===")
    
    # Calcula estatísticas
    stats = calcular_estatisticas(taxas_diarias)
    
    print(f"Período: {stats['data_inicio'].strftime('%d/%m/%Y')} a {stats['data_fim'].strftime('%d/%m/%Y')}")
    print(f"Total de dias: {stats['total_dias']}")
    print(f"Dias úteis: {stats['dias_uteis']} ({stats['dias_uteis']/stats['total_dias']*100:.1f}%)")
    print(f"Dias não úteis: {stats['dias_nao_uteis']} ({stats['dias_nao_uteis']/stats['total_dias']*100:.1f}%)")
    
    # Prepara dados para mostrar
    itens = list(taxas_diarias.items())
    itens.sort(key=lambda x: x[0])  # Ordena por data
    
    # Filtra se necessário
    if apenas_dias_uteis:
        itens = [(data, taxa) for data, taxa in itens if taxa > 0]
        titulo = "PRIMEIROS DIAS ÚTEIS"
    elif apenas_dias_nao_uteis:
        itens = [(data, taxa) for data, taxa in itens if taxa == 0]
        titulo = "PRIMEIROS DIAS NÃO ÚTEIS"
    else:
        titulo = "PRIMEIROS DIAS"
    
    # Mostra os primeiros itens
    if itens:
        print(f"\n=== {titulo} ===")
        for i, (data, taxa) in enumerate(itens[:max_itens]):
            print(f"{data.strftime('%d/%m/%Y')}: {taxa:.8f}")
    
    # Mostra os últimos itens
    if len(itens) > max_itens * 2:
        if apenas_dias_uteis:
            titulo = "ÚLTIMOS DIAS ÚTEIS"
        elif apenas_dias_nao_uteis:
            titulo = "ÚLTIMOS DIAS NÃO ÚTEIS"
        else:
            titulo = "ÚLTIMOS DIAS"
            
        print(f"\n=== {titulo} ===")
        for data, taxa in itens[-max_itens:]:
            print(f"{data.strftime('%d/%m/%Y')}: {taxa:.8f}")

def main():
    """Função principal do script."""
    args = parse_arguments()
    
    # Configura o logger para maior verbosidade se solicitado
    if args.verbose:
        logger.setLevel('DEBUG')
    
    # Define o período para atualização
    data_inicial = converter_data(args.data_inicial)
    
    if args.data_final:
        data_final = converter_data(args.data_final)
    else:
        data_final = date.today()
    
    print(f"Atualizando lista SELIC apurada para o período de {data_inicial.strftime('%d/%m/%Y')} a {data_final.strftime('%d/%m/%Y')}")
    
    # Garante que as taxas estejam no cache para todo o período
    try:
        taxas_diarias = ensure_rates_in_cache(data_inicial, data_final)
        print(f"Cache atualizado com sucesso! Total de {len(taxas_diarias)} dias no período.")
    except Exception as e:
        print(f"Erro ao atualizar o cache: {e}")
        sys.exit(1)
    
    # Mostra resumo se solicitado
    if args.mostrar_resumo:
        mostrar_resumo(taxas_diarias, args.dias_uteis, args.dias_n_uteis)

if __name__ == "__main__":
    main() 