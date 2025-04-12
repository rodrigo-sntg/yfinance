#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script para popular o cache de taxas Selic diárias desde 2000.

Este script busca as taxas Selic diárias na API do Banco Central do Brasil
e salva os dados em um arquivo de cache local para uso futuro.

Uso:
    python popular_selic_diaria.py [--ano_inicio YYYY] [--ano_fim YYYY] [--verbose]

Exemplos:
    # Popula todo o período desde 2000 até o ano atual
    python popular_selic_diaria.py
    
    # Popula apenas dados de 2010 a 2015
    python popular_selic_diaria.py --ano_inicio 2010 --ano_fim 2015
    
    # Popula desde 2018 até o ano atual com logs detalhados
    python popular_selic_diaria.py --ano_inicio 2018 --verbose
"""

import os
import sys
import argparse
import logging
from datetime import datetime, date, timedelta
import json
import time

# Adiciona o diretório pai ao sys.path para permitir importar os módulos da aplicação
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.selic_diaria import ensure_selic_diaria_in_cache, load_selic_diaria_cache
from app.logger import logger

def configurar_logging(verbose=False):
    """Configura o logging do script"""
    nivel = logging.DEBUG if verbose else logging.INFO
    
    # Configura o formato do log
    formato = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configura o handler para console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(nivel)
    console_handler.setFormatter(logging.Formatter(formato))
    
    # Configura o logger raiz
    root_logger = logging.getLogger()
    root_logger.setLevel(nivel)
    
    # Remove handlers existentes e adiciona o novo
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    root_logger.addHandler(console_handler)
    
    return root_logger

def parse_args():
    """Processa os argumentos de linha de comando"""
    parser = argparse.ArgumentParser(description="Popula o cache de taxas Selic diárias desde 2000")
    
    # Ano atual como padrão para o fim
    ano_atual = datetime.now().year
    
    parser.add_argument('--ano_inicio', type=int, default=2000,
                        help='Ano de início para buscar dados (padrão: 2000)')
    parser.add_argument('--ano_fim', type=int, default=ano_atual,
                        help=f'Ano final para buscar dados (padrão: {ano_atual})')
    parser.add_argument('--verbose', action='store_true',
                        help='Exibe logs mais detalhados durante a execução')
    
    args = parser.parse_args()
    
    # Valida os anos
    if args.ano_inicio < 2000:
        print(f"AVISO: Ano de início {args.ano_inicio} é anterior a 2000. Ajustando para 2000.")
        args.ano_inicio = 2000
        
    if args.ano_fim > ano_atual:
        print(f"AVISO: Ano de fim {args.ano_fim} é posterior ao ano atual. Ajustando para {ano_atual}.")
        args.ano_fim = ano_atual
        
    if args.ano_inicio > args.ano_fim:
        print(f"ERRO: Ano de início ({args.ano_inicio}) é posterior ao ano de fim ({args.ano_fim}).")
        sys.exit(1)
        
    return args

def verificar_datas_faltantes(data_inicial, data_final, cache):
    """
    Verifica quais datas estão faltando no cache para o período especificado
    
    Args:
        data_inicial (str): Data inicial no formato YYYY-MM-DD
        data_final (str): Data final no formato YYYY-MM-DD
        cache (dict): Cache atual com as taxas Selic
        
    Returns:
        list: Lista de datas faltantes em formato date
    """
    # Converte as datas para objetos date para comparação
    data_inicial_obj = datetime.strptime(data_inicial, "%Y-%m-%d").date()
    data_final_obj = datetime.strptime(data_final, "%Y-%m-%d").date()
    
    # Obtém os registros do cache
    conteudo = cache.get("conteudo", [])
    
    # Cria um dicionário com as datas presentes no cache
    datas_cache = {datetime.strptime(item["data"], "%d/%m/%Y").date() for item in conteudo}
    
    # Verifica quais datas estão faltando no cache
    datas_faltantes = []
    data_atual = data_inicial_obj
    while data_atual <= data_final_obj:
        if data_atual not in datas_cache:
            datas_faltantes.append(data_atual)
        data_atual += timedelta(days=1)
    
    return datas_faltantes

def main():
    """Função principal do script"""
    # Processa os argumentos
    args = parse_args()
    
    # Configura o logging
    script_logger = configurar_logging(args.verbose)
    
    script_logger.info(f"Iniciando população do cache de taxas Selic diárias")
    script_logger.info(f"Período: {args.ano_inicio} a {args.ano_fim}")
    
    # Inicializa contadores para estatísticas
    total_registros_antes = 0
    total_registros_novos = 0
    anos_processados = 0
    total_datas_faltantes = 0
    
    # Carrega o cache inicial
    cache_inicial = load_selic_diaria_cache()
    total_registros_antes = len(cache_inicial.get("conteudo", []))
    script_logger.info(f"Cache inicial contém {total_registros_antes} registros")
    
    # Processa ano a ano para evitar requisições muito grandes
    for ano in range(args.ano_inicio, args.ano_fim + 1):
        script_logger.info(f"Processando ano {ano}...")
        
        # Define o período do ano
        if ano == datetime.now().year:
            # Se for o ano atual, vai até a data atual
            data_inicial = f"{ano}-01-01"
            data_final = datetime.now().strftime("%Y-%m-%d")
        else:
            # Se for um ano passado, processa o ano todo
            data_inicial = f"{ano}-01-01"
            data_final = f"{ano}-12-31"
        
        # Verifica quais datas estão faltando para esse período
        cache_atual = load_selic_diaria_cache()
        datas_faltantes = verificar_datas_faltantes(data_inicial, data_final, cache_atual)
        
        if not datas_faltantes:
            script_logger.info(f"Todas as taxas para o ano {ano} já estão no cache. Pulando...")
            anos_processados += 1
            continue
        
        script_logger.info(f"Buscando {len(datas_faltantes)} taxas faltantes para o período de {data_inicial} a {data_final}")
        total_datas_faltantes += len(datas_faltantes)
        
        try:
            # Garante que as taxas para o período estão no cache
            cache_atualizado = ensure_selic_diaria_in_cache(data_inicial, data_final)
            
            # Conta quantos registros foram adicionados verificando o cache atual
            cache_apos = load_selic_diaria_cache()
            registros_apos = len(cache_apos.get("conteudo", []))
            novos_registros = registros_apos - total_registros_antes - total_registros_novos
            
            script_logger.info(f"Processamento do ano {ano} concluído: {novos_registros} novos registros")
            
            # Atualiza contadores
            total_registros_novos += novos_registros
            anos_processados += 1
            
            # Espera um pouco entre os anos para não sobrecarregar a API
            if ano < args.ano_fim:
                script_logger.debug("Aguardando 3 segundos antes de processar o próximo ano...")
                time.sleep(3)
                
        except Exception as e:
            script_logger.error(f"Erro ao processar o ano {ano}: {str(e)}")
    
    # Carrega o cache final para verificar o total de registros
    cache_final = load_selic_diaria_cache()
    total_registros_final = len(cache_final.get("conteudo", []))
    
    # Exibe estatísticas finais
    script_logger.info("\n" + "="*60)
    script_logger.info("ESTATÍSTICAS DE PROCESSAMENTO")
    script_logger.info("="*60)
    script_logger.info(f"Anos processados: {anos_processados}")
    script_logger.info(f"Total de registros no início: {total_registros_antes}")
    script_logger.info(f"Total de datas faltantes verificadas: {total_datas_faltantes}")
    script_logger.info(f"Novos registros adicionados: {total_registros_novos}")
    script_logger.info(f"Total de registros no cache: {total_registros_final}")
    script_logger.info("="*60)
    
    script_logger.info("Processo concluído com sucesso!")

if __name__ == "__main__":
    main()