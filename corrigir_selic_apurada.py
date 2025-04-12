#!/usr/bin/env python3
"""
Script para corrigir o cache da Selic apurada:
1. Garantir apenas uma cotação por data (eliminar duplicatas)
2. Ordenar os registros em ordem crescente de data
"""
import os
import json
import argparse
from datetime import datetime
from app.config import CACHE_FILE, CACHE_BACKUP_DIR
from app.cache import save_cache

def carregar_cache_atual():
    """Carrega o cache atual a partir do arquivo"""
    if not os.path.exists(CACHE_FILE):
        print(f"Arquivo de cache não encontrado: {CACHE_FILE}")
        return {"registros": []}
    
    try:
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)
            return cache
    except Exception as e:
        print(f"Erro ao carregar o cache: {e}")
        return {"registros": []}

def converter_data(data_str):
    """Converte string de data no formato DD/MM/YYYY para objeto datetime"""
    try:
        return datetime.strptime(data_str, '%d/%m/%Y')
    except Exception:
        # Retorna uma data arbitrariamente antiga para registros com formato inválido
        return datetime(1900, 1, 1)

def verificar_duplicatas(registros):
    """Verifica e retorna informações sobre duplicatas no cache"""
    datas_contagem = {}
    duplicatas_detalhes = {}
    
    # Contar ocorrências de cada data
    for registro in registros:
        data_cotacao = registro.get("dataCotacao")
        if data_cotacao:
            datas_contagem[data_cotacao] = datas_contagem.get(data_cotacao, 0) + 1
            
            # Armazena detalhes para análise
            if datas_contagem[data_cotacao] > 1:
                if data_cotacao not in duplicatas_detalhes:
                    duplicatas_detalhes[data_cotacao] = []
                duplicatas_detalhes[data_cotacao].append(registro)
    
    # Filtrar apenas as datas duplicadas
    duplicatas = {data: count for data, count in datas_contagem.items() if count > 1}
    
    return duplicatas, duplicatas_detalhes

def escolher_registro_mais_confiavel(registros_mesma_data, estrategia='recente'):
    """
    Escolhe o registro mais confiável quando há múltiplos para a mesma data
    
    Args:
        registros_mesma_data (list): Lista de registros para a mesma data
        estrategia (str): Estratégia de escolha ('recente', 'maior_fator', 'menor_fator')
        
    Returns:
        dict: O registro escolhido como mais confiável
    """
    if not registros_mesma_data:
        return None
    
    if len(registros_mesma_data) == 1:
        return registros_mesma_data[0]
    
    # Cria uma cópia para não afetar a lista original
    registros = registros_mesma_data.copy()
    
    # Tenta converter fatores para números para comparação
    for registro in registros:
        try:
            # Adiciona um campo auxiliar com o fator como número
            fator_str = registro.get("fatorDiario", "0")
            registro["_fator_numerico"] = float(fator_str) if fator_str else 0.0
        except (ValueError, TypeError):
            registro["_fator_numerico"] = 0.0
        
        # Adiciona campo com a data de modificação do registro, se disponível
        try:
            dt_mod = registro.get("dataModificacao")
            if dt_mod:
                registro["_data_mod"] = datetime.strptime(dt_mod, '%Y-%m-%d %H:%M:%S')
            else:
                registro["_data_mod"] = datetime(1900, 1, 1)
        except:
            registro["_data_mod"] = datetime(1900, 1, 1)
    
    # Escolhe conforme a estratégia
    if estrategia == 'recente':
        # Prioriza registro com data de modificação mais recente
        registros.sort(key=lambda r: r.get("_data_mod", datetime(1900, 1, 1)), reverse=True)
    elif estrategia == 'maior_fator':
        # Prioriza registro com maior fator diário
        registros.sort(key=lambda r: r.get("_fator_numerico", 0.0), reverse=True)
    elif estrategia == 'menor_fator':
        # Prioriza registro com menor fator diário (diferente de zero)
        def chave_menor_fator(r):
            fator = r.get("_fator_numerico", 0.0)
            return fator if fator > 0 else float('inf')
        registros.sort(key=chave_menor_fator)
    else:
        # Estratégia padrão: prioriza registros não-zero
        # Se todos iguais a zero, retorna o primeiro
        registros_nao_zero = [r for r in registros if r.get("_fator_numerico", 0.0) > 0]
        if registros_nao_zero:
            return registros_nao_zero[0]
    
    # Remove campos auxiliares para não interferir no resultado
    escolhido = registros[0]
    if "_fator_numerico" in escolhido:
        del escolhido["_fator_numerico"]
    if "_data_mod" in escolhido:
        del escolhido["_data_mod"]
    
    return escolhido

def mostrar_cotacoes(registros, quantidade=5):
    """Mostra as primeiras e últimas cotações do cache"""
    if not registros:
        print("Não há cotações para mostrar.")
        return
    
    total = len(registros)
    print(f"\nMostrando {min(quantidade, total)} primeiras e últimas cotações do total de {total}:")
    
    print("\nPrimeiras cotações:")
    for i, registro in enumerate(registros[:quantidade]):
        data = registro.get("dataCotacao", "Sem data")
        fator = registro.get("fatorDiario", "Sem fator")
        print(f"  {i+1}. Data: {data}, Fator Diário: {fator}")
    
    if total > quantidade * 2:
        print(f"\n  ... {total - (quantidade * 2)} cotações no meio ...")
    
    print("\nÚltimas cotações:")
    for i, registro in enumerate(registros[-quantidade:]):
        data = registro.get("dataCotacao", "Sem data")
        fator = registro.get("fatorDiario", "Sem fator")
        print(f"  {total-quantidade+i+1}. Data: {data}, Fator Diário: {fator}")

def corrigir_cache(estrategia='recente', dry_run=False):
    """Corrige o cache da Selic apurada"""
    print("Iniciando correção do cache da Selic apurada...")
    print(f"Estratégia para resolver duplicatas: {estrategia}")
    if dry_run:
        print("Modo simulação: nenhuma alteração será salva")
    
    # Carregar cache atual
    cache = carregar_cache_atual()
    registros = cache.get("registros", [])
    
    # Contagem inicial
    total_inicial = len(registros)
    print(f"Cache carregado com {total_inicial} registros")
    
    # Verificar se há registros para processar
    if total_inicial == 0:
        print("Nenhum registro para processar. Encerrando.")
        return
    
    # Verificar duplicatas antes da correção
    duplicatas, duplicatas_detalhes = verificar_duplicatas(registros)
    if duplicatas:
        print(f"\nEncontradas {len(duplicatas)} datas com múltiplas cotações:")
        for data, contagem in sorted(duplicatas.items())[:10]:  # Mostrar apenas as 10 primeiras
            print(f"- {data}: {contagem} ocorrências")
        
        # Mostrar detalhes das primeiras 3 duplicatas para análise
        print("\nDetalhes das primeiras duplicatas:")
        for i, (data, registros_duplicados) in enumerate(sorted(duplicatas_detalhes.items())[:3]):
            print(f"\nDuplicata {i+1}: {data} ({len(registros_duplicados)} registros)")
            for j, reg in enumerate(registros_duplicados):
                fator = reg.get("fatorDiario", "Não informado")
                outras_info = []
                for chave in ["isBusinessDay", "dataModificacao", "reason"]:
                    if chave in reg:
                        outras_info.append(f"{chave}:{reg[chave]}")
                outras = ", ".join(outras_info) if outras_info else "sem informações adicionais"
                print(f"  - Registro {j+1}: Fator={fator}, {outras}")
            
            # Mostrar qual seria escolhido
            escolhido = escolher_registro_mais_confiavel(registros_duplicados, estrategia)
            if escolhido:
                print(f"  → Registro escolhido com estratégia '{estrategia}': Fator={escolhido.get('fatorDiario', 'Não informado')}")
        
        if len(duplicatas) > 10:
            print(f"... e mais {len(duplicatas) - 10} datas com duplicatas")
    else:
        print("\nNão foram encontradas duplicatas no cache original.")
    
    # Mostrar algumas cotações antes da correção
    print("\nAmostra do cache ANTES da correção:")
    mostrar_cotacoes(registros)
    
    # Dicionário para agrupar registros por data de cotação
    registros_por_data = {}
    registros_invalidos = 0
    
    # Agrupar registros por data
    for registro in registros:
        data_cotacao = registro.get("dataCotacao")
        if not data_cotacao:
            registros_invalidos += 1
            continue
        
        if data_cotacao not in registros_por_data:
            registros_por_data[data_cotacao] = []
        
        registros_por_data[data_cotacao].append(registro)
    
    # Escolher o registro mais confiável para cada data
    registros_unicos = {}
    for data, lista_registros in registros_por_data.items():
        if len(lista_registros) == 1:
            # Apenas um registro para esta data
            registros_unicos[data] = lista_registros[0]
        else:
            # Múltiplos registros para esta data, escolher o mais confiável
            registros_unicos[data] = escolher_registro_mais_confiavel(lista_registros, estrategia)
    
    # Converter para lista e ordenar por data
    registros_ordenados = list(registros_unicos.values())
    registros_ordenados.sort(key=lambda r: converter_data(r.get("dataCotacao", "01/01/1900")))
    
    # Criar novo cache com registros corrigidos
    cache_corrigido = {"registros": registros_ordenados}
    
    # Estatísticas
    total_final = len(registros_ordenados)
    duplicatas_removidas = total_inicial - total_final - registros_invalidos
    
    print(f"\nEstatísticas da correção:")
    print(f"- Registros originais: {total_inicial}")
    print(f"- Registros inválidos (sem dataCotacao): {registros_invalidos}")
    print(f"- Duplicatas removidas: {duplicatas_removidas}")
    print(f"- Registros finais: {total_final}")
    
    # Mostrar algumas cotações depois da correção
    print("\nAmostra do cache DEPOIS da correção:")
    mostrar_cotacoes(registros_ordenados)
    
    # Salvar cache corrigido
    if not dry_run:
        print("\nSalvando cache corrigido...")
        sucesso = save_cache(cache_corrigido)
        
        if sucesso:
            print("Cache da Selic apurada corrigido e salvo com sucesso!")
        else:
            print("Erro ao salvar o cache corrigido.")
    else:
        print("\nModo simulação: cache não foi salvo.")
    
    return cache_corrigido

def verificar_ordenacao(cache):
    """Verifica se o cache está corretamente ordenado"""
    if not cache or "registros" not in cache:
        return
    
    registros = cache["registros"]
    if len(registros) <= 1:
        return
    
    data_anterior = None
    todas_ordenadas = True
    erro_em = None
    
    for i, registro in enumerate(registros):
        data_atual = converter_data(registro.get("dataCotacao", ""))
        if data_anterior is not None and data_atual < data_anterior:
            todas_ordenadas = False
            erro_em = (i-1, i)
            break
        data_anterior = data_atual
    
    print(f"\nVerificação de ordenação:")
    if todas_ordenadas:
        print("- Registros estão corretamente ordenados por data crescente ✓")
    else:
        print("- ERRO: Registros não estão ordenados corretamente!")
        if erro_em:
            i1, i2 = erro_em
            print(f"  Erro entre os registros {i1} e {i2}:")
            print(f"  - Registro {i1}: {registros[i1].get('dataCotacao')}")
            print(f"  - Registro {i2}: {registros[i2].get('dataCotacao')}")

def verificar_unicidade(cache):
    """Verifica se não há duplicatas de dataCotacao no cache"""
    if not cache or "registros" not in cache:
        return
    
    registros = cache["registros"]
    duplicatas, _ = verificar_duplicatas(registros)
    
    print(f"\nVerificação de unicidade:")
    if not duplicatas:
        print("- Cada data possui exatamente uma cotação ✓")
    else:
        print(f"- ERRO: Encontradas {len(duplicatas)} datas com múltiplas cotações!")
        for data, contagem in sorted(duplicatas.items())[:5]:
            print(f"  - {data}: {contagem} ocorrências")

def init_argparse():
    """Inicializa o parser de argumentos de linha de comando"""
    parser = argparse.ArgumentParser(description='Corrige o cache de Selic apurada, removendo duplicatas e ordenando por data.')
    parser.add_argument('--estrategia', type=str, choices=['recente', 'maior_fator', 'menor_fator'], default='recente',
                        help='Estratégia para escolher entre registros duplicados (padrão: recente)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Executa em modo simulação sem salvar alterações')
    return parser

if __name__ == "__main__":
    # Configurar argumentos de linha de comando
    parser = init_argparse()
    args = parser.parse_args()
    
    # Criar diretório de backups se não existir
    os.makedirs(CACHE_BACKUP_DIR, exist_ok=True)
    
    # Corrigir cache
    cache_corrigido = corrigir_cache(estrategia=args.estrategia, dry_run=args.dry_run)
    
    # Verificações finais
    if cache_corrigido:
        verificar_ordenacao(cache_corrigido)
        verificar_unicidade(cache_corrigido)
        
        print("\nProcesso de correção concluído!") 