#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import argparse
from datetime import datetime
import time
import sys
from app.cache import get_cached_rates, save_cache
from app.logger import logger

def parse_args():
    """
    Processa os argumentos da linha de comando.
    
    Returns:
        argparse.Namespace: Argumentos processados
    """
    parser = argparse.ArgumentParser(
        description="Ordena e remove duplicatas do cache da Selic.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Apenas simula as operações sem modificar o cache"
    )
    
    parser.add_argument(
        "--estrategia", 
        choices=["recente", "maior", "menor"],
        default="recente",
        help="Estratégia para lidar com duplicatas: recente (último registro), maior (maior taxa) ou menor (menor taxa)"
    )
    
    parser.add_argument(
        "--backup", 
        action="store_true", 
        help="Cria um backup do cache antes de modificá-lo"
    )
    
    parser.add_argument(
        "--mostrar-duplicatas", 
        action="store_true", 
        help="Mostra detalhes das duplicatas encontradas"
    )
    
    return parser.parse_args()

def data_str_to_date(data_str):
    """
    Converte uma string de data para um objeto datetime.
    
    Args:
        data_str (str): Data no formato DD/MM/YYYY
        
    Returns:
        datetime: Objeto datetime convertido
    """
    return datetime.strptime(data_str, "%d/%m/%Y").date()

def selecionar_melhor_registro(registros, estrategia="recente"):
    """
    Seleciona o melhor registro entre duplicatas de acordo com a estratégia escolhida.
    
    Args:
        registros (list): Lista de registros duplicados
        estrategia (str): Estratégia de seleção: recente, maior ou menor
        
    Returns:
        dict: Registro selecionado
    """
    if estrategia == "recente":
        # Assume que o último registro é o mais recente
        return registros[-1]
    elif estrategia == "maior":
        # Seleciona o registro com maior fator diário
        return max(registros, key=lambda r: float(r.get("fatorDiario", 0)))
    elif estrategia == "menor":
        # Seleciona o registro com menor fator diário
        return min(registros, key=lambda r: float(r.get("fatorDiario", 0)))
    else:
        # Padrão: usa o último
        return registros[-1]

def verificar_ordenacao_e_duplicatas(registros):
    """
    Verifica se os registros estão ordenados por data e identifica duplicatas.
    
    Args:
        registros (list): Lista de registros
        
    Returns:
        tuple: (esta_ordenado, duplicatas)
            - esta_ordenado (bool): True se estiver ordenado
            - duplicatas (dict): Dicionário com datas duplicadas e seus registros
    """
    datas = []
    data_to_registros = {}
    invalidos = []
    
    # Mapeia datas para registros
    for i, registro in enumerate(registros):
        try:
            data_str = registro.get("dataCotacao")
            if not data_str:
                invalidos.append(i)
                continue
                
            # Converte para data
            data = data_str_to_date(data_str)
            datas.append(data)
            
            # Adiciona ao mapeamento
            if data_str not in data_to_registros:
                data_to_registros[data_str] = []
            data_to_registros[data_str].append(registro)
                
        except Exception as e:
            logger.error(f"Erro ao processar registro {i}: {e}")
            invalidos.append(i)
    
    # Verifica ordenação
    esta_ordenado = all(datas[i] <= datas[i+1] for i in range(len(datas)-1))
    
    # Identifica duplicatas
    duplicatas = {data_str: registros for data_str, registros in data_to_registros.items() if len(registros) > 1}
    
    return esta_ordenado, duplicatas, invalidos

def processar_registros(registros, estrategia="recente", mostrar_duplicatas=False):
    """
    Processa registros para remover duplicatas e ordenar por data.
    
    Args:
        registros (list): Lista de registros
        estrategia (str): Estratégia para lidar com duplicatas
        mostrar_duplicatas (bool): Se deve mostrar detalhes das duplicatas
        
    Returns:
        tuple: (registros_processados, esta_ordenado, duplicatas, invalidos)
    """
    # Verifica estado atual
    esta_ordenado, duplicatas, invalidos = verificar_ordenacao_e_duplicatas(registros)
    
    # Mostra duplicatas se solicitado
    if mostrar_duplicatas and duplicatas:
        print("\n== DUPLICATAS ENCONTRADAS ==")
        for data, regs in duplicatas.items():
            print(f"\nData: {data} ({len(regs)} registros)")
            for i, r in enumerate(regs):
                print(f"  {i+1}. Fator: {r.get('fatorDiario')}, IsBusinessDay: {r.get('isBusinessDay')}, Razão: {r.get('reason', 'N/A')}")
    
    # Contadores para relatório
    total_original = len(registros)
    total_duplicatas = sum(len(regs) - 1 for regs in duplicatas.values())
    
    # Seleciona apenas um registro para cada data
    registros_unicos = []
    datas_adicionadas = set()
    
    # Primeiro, adiciona registros sem duplicatas
    for registro in registros:
        try:
            data_str = registro.get("dataCotacao")
            if not data_str:
                continue
                
            if data_str not in duplicatas and data_str not in datas_adicionadas:
                registros_unicos.append(registro)
                datas_adicionadas.add(data_str)
        except Exception:
            continue
    
    # Adiciona o melhor registro para cada data duplicada
    for data_str, regs in duplicatas.items():
        melhor_registro = selecionar_melhor_registro(regs, estrategia)
        registros_unicos.append(melhor_registro)
    
    # Ordena registros por data
    try:
        registros_unicos.sort(key=lambda r: data_str_to_date(r.get("dataCotacao", "01/01/2000")))
        ordenacao_realizada = True
    except Exception as e:
        logger.error(f"Erro ao ordenar registros: {e}")
        ordenacao_realizada = False
    
    return registros_unicos, esta_ordenado, duplicatas, invalidos, ordenacao_realizada

def main():
    """
    Função principal do script.
    """
    # Processa argumentos
    args = parse_args()
    
    # Carrega dados do cache
    try:
        taxas_diarias, registros_originais = get_cached_rates()
        print(f"Cache carregado com {len(registros_originais)} registros.")
    except Exception as e:
        logger.error(f"Erro ao carregar cache: {e}")
        print(f"Erro ao carregar o cache: {e}")
        return 1
    
    # Processa registros
    registros_processados, esta_ordenado, duplicatas, invalidos, ordenacao_realizada = processar_registros(
        registros_originais, 
        estrategia=args.estrategia,
        mostrar_duplicatas=args.mostrar_duplicatas
    )
    
    # Gera relatório
    print("\n== RELATÓRIO ==")
    print(f"Total de registros originais: {len(registros_originais)}")
    print(f"Registros já ordenados por data: {'Sim' if esta_ordenado else 'Não'}")
    print(f"Duplicatas encontradas: {len(duplicatas)} datas ({sum(len(regs) - 1 for regs in duplicatas.values())} registros extras)")
    print(f"Registros inválidos (sem data): {len(invalidos)}")
    print(f"Total de registros após processamento: {len(registros_processados)}")
    
    # Amostra antes e depois
    if duplicatas and args.mostrar_duplicatas:
        print("\n== EXEMPLO DE PROCESSAMENTO ==")
        for data, regs in list(duplicatas.items())[:2]:  # Mostra apenas os 2 primeiros exemplos
            print(f"\nData: {data}")
            print("Registros originais:")
            for i, r in enumerate(regs):
                print(f"  {i+1}. Fator: {r.get('fatorDiario')}, IsBusinessDay: {r.get('isBusinessDay')}, Razão: {r.get('reason', 'N/A')}")
            
            print("Registro selecionado (estratégia: {args.estrategia}):")
            selecionado = selecionar_melhor_registro(regs, args.estrategia)
            print(f"  Fator: {selecionado.get('fatorDiario')}, IsBusinessDay: {selecionado.get('isBusinessDay')}, Razão: {selecionado.get('reason', 'N/A')}")
    
    # Se for apenas simulação, para aqui
    if args.dry_run:
        print("\nOperação realizada em modo simulação (--dry-run). Nenhuma alteração foi salva.")
        return 0
    
    # Cria backup se solicitado
    if args.backup:
        try:
            backup_file = f"selic_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(backup_file, "w") as f:
                json.dump({"registros": registros_originais}, f, ensure_ascii=False, indent=4)
            print(f"\nBackup criado: {backup_file}")
        except Exception as e:
            logger.error(f"Erro ao criar backup: {e}")
            print(f"Erro ao criar backup: {e}")
            return 1
    
    # Salva as alterações
    try:
        save_cache({"registros": registros_processados})
        print("\nCache atualizado com sucesso!")
        
        # Verifica se as alterações foram aplicadas
        _, registros_verificacao = get_cached_rates()
        
        if len(registros_verificacao) == len(registros_processados):
            print(f"Verificação: {len(registros_verificacao)} registros salvos corretamente.")
            
            # Verifica se ainda há duplicatas - CORREÇÃO AQUI
            _, duplicatas_apos, _ = verificar_ordenacao_e_duplicatas(registros_verificacao)
            if duplicatas_apos:
                print(f"AVISO: Ainda existem {len(duplicatas_apos)} datas com duplicatas após o processamento.")
            else:
                print("Verificação: Nenhuma duplicata encontrada após o processamento.")
        else:
            print(f"AVISO: Número de registros após salvamento ({len(registros_verificacao)}) difere do número processado ({len(registros_processados)}).")
    except Exception as e:
        logger.error(f"Erro ao salvar cache: {e}")
        print(f"Erro ao salvar as alterações no cache: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 