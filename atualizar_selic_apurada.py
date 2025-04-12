#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import requests
import datetime
import time
from datetime import datetime, timedelta

# Configuração do arquivo de cache
CACHE_FILE = 'selic_apurada_cache.json'
# Tamanho máximo recomendado para consulta (em dias)
MAX_DIAS_CONSULTA = 365

def formatar_data(data):
    """Formata uma data para o padrão DD/MM/YYYY."""
    if isinstance(data, str):
        return data
    return data.strftime('%d/%m/%Y')

def converter_data_string_para_datetime(data_str):
    """Converte uma string de data no formato DD/MM/YYYY para um objeto datetime."""
    try:
        return datetime.strptime(data_str, '%d/%m/%Y')
    except ValueError:
        return None

def obter_dados_selic(data_inicial, data_final, max_tentativas=3):
    """Consulta a API do BCB para obter dados da Selic Apurada."""
    url = 'https://www3.bcb.gov.br/novoselic/rest/taxaSelicApurada/pub/search'
    
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7,es;q=0.6',
        'cache-control': 'no-cache',
        'content-type': 'application/json;charset=UTF-8',
        'origin': 'https://www3.bcb.gov.br',
        'pragma': 'no-cache',
        'referer': 'https://www3.bcb.gov.br/novoselic/pesquisa-taxa-apurada.jsp',
        'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest'
    }
    
    params = {
        'parametrosOrdenacao': '[]',
        'page': 1,
        'pageSize': 1000  # Otimizado para obter maior quantidade de registros
    }
    
    data = {
        'dataInicial': formatar_data(data_inicial),
        'dataFinal': formatar_data(data_final)
    }
    
    for tentativa in range(max_tentativas):
        try:
            response = requests.post(url, headers=headers, params=params, json=data)
            response.raise_for_status()
            resultado = response.json()
            
            # Verifica se a resposta contém dados válidos
            if "registros" in resultado:
                return resultado
            else:
                print(f"API não retornou registros na tentativa {tentativa + 1}. Tentando novamente...")
                time.sleep(2)  # Aguarda 2 segundos antes de tentar novamente
        except Exception as e:
            print(f"Erro ao consultar API do BCB (tentativa {tentativa + 1}): {e}")
            if tentativa < max_tentativas - 1:
                print("Tentando novamente em 5 segundos...")
                time.sleep(5)
            else:
                print("Número máximo de tentativas atingido.")
                return None
    
    return None

def carregar_cache():
    """Carrega o arquivo de cache se existir."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Erro ao carregar cache: {e}")
            return {'registros': []}
    else:
        return {'registros': []}

def salvar_cache(cache):
    """Salva os dados no arquivo de cache."""
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=4)
        print(f"Cache atualizado com sucesso em {CACHE_FILE}")
    except Exception as e:
        print(f"Erro ao salvar cache: {e}")

def adicionar_dias_nao_uteis_e_feriados(cache, inicio, fim, datas_com_dados):
    """Adiciona registros para dias não úteis (feriados e fins de semana) e dias sem dados."""
    data_atual = inicio
    
    # Mapeia os dias da semana para nomes em português
    dias_semana = {
        0: "Segunda-feira",
        1: "Terça-feira",
        2: "Quarta-feira",
        3: "Quinta-feira",
        4: "Sexta-feira",
        5: "Sábado-feira",
        6: "Domingo-feira"
    }
    
    datas_existentes = {r["dataCotacao"] for r in cache["registros"]}
    
    novos_registros = []
    while data_atual <= fim:
        data_str = formatar_data(data_atual)
        
        # Verifica se a data já existe no cache
        if data_str not in datas_existentes:
            # Fins de semana (5=sábado, 6=domingo)
            if data_atual.weekday() >= 5:
                registro = {
                    "dataCotacao": data_str,
                    "fatorDiario": "0",
                    "isBusinessDay": False,
                    "reason": f"FINAL_DE_SEMANA: {dias_semana[data_atual.weekday()]}"
                }
                novos_registros.append(registro)
            # Dia útil sem dados (possível feriado)
            elif data_str not in datas_com_dados:
                registro = {
                    "dataCotacao": data_str,
                    "fatorDiario": "0",
                    "isBusinessDay": False,
                    "reason": "FERIADO: Sem dados disponíveis para esta data"
                }
                novos_registros.append(registro)
        
        data_atual += timedelta(days=1)
    
    # Adiciona os novos registros ao cache
    cache["registros"].extend(novos_registros)
    return cache

def dividir_periodo_em_chunks(inicio, fim, max_dias=MAX_DIAS_CONSULTA):
    """Divide um período em chunks menores para evitar problemas com a API."""
    chunks = []
    data_atual = inicio
    
    while data_atual <= fim:
        data_final_chunk = min(data_atual + timedelta(days=max_dias - 1), fim)
        chunks.append((data_atual, data_final_chunk))
        data_atual = data_final_chunk + timedelta(days=1)
    
    return chunks

def eh_registro_valido(registro):
    """Verifica se um registro contém dados válidos da Selic."""
    # Verifica se é dia não útil (não precisamos verificar valores)
    if registro.get("isBusinessDay") is False:
        return False
        
    # Obtém o valor do fatorDiario, tratando strings
    fator_diario = registro.get("fatorDiario")
    if isinstance(fator_diario, str):
        try:
            fator_diario = float(fator_diario)
        except (ValueError, TypeError):
            return False
    
    # Verifica se o fator diário é um número válido e maior que zero
    if not isinstance(fator_diario, (int, float)) or float(fator_diario) <= 0:
        return False
        
    # Verifica se há taxa anual maior que zero
    taxa_anual = registro.get("taxaAnual", 0)
    if not isinstance(taxa_anual, (int, float)) or float(taxa_anual) <= 0:
        return False
    
    return True

def encontrar_ultima_data_valida(registros):
    """Encontra a última data válida no cache que tem dados reais."""
    # Ordena os registros por data (mais recente para mais antigo)
    registros_ordenados = sorted(
        registros,
        key=lambda x: converter_data_string_para_datetime(x["dataCotacao"]) or datetime.min,
        reverse=True
    )
    
    # Procura o primeiro registro válido (mais recente)
    for registro in registros_ordenados:
        if eh_registro_valido(registro):
            return converter_data_string_para_datetime(registro["dataCotacao"])
    
    # Se não encontrar nenhum registro válido, retorna uma data padrão
    return datetime(2000, 1, 1)

def identificar_registros_invalidos(cache, data_inicial, data_final):
    """Identifica registros inválidos ou suspeitos no cache dentro do período especificado."""
    registros_invalidos = []
    
    for registro in cache["registros"]:
        data = converter_data_string_para_datetime(registro["dataCotacao"])
        
        # Verifica se a data está no período
        if data and data_inicial <= data <= data_final:
            # Verifica se o registro está marcado como dia útil mas não tem dados válidos
            if registro.get("isBusinessDay") is True and not eh_registro_valido(registro):
                registros_invalidos.append(registro["dataCotacao"])
            # Também inclui dados marcados como indisponíveis na API
            elif registro.get("isBusinessDay") is False and registro.get("reason", "").startswith(("API_UNAVAILABLE", "API_OBSERVACAO")):
                registros_invalidos.append(registro["dataCotacao"])
    
    return registros_invalidos

def atualizar_selic_apurada(forcar_atualizacao=False, dias_para_verificar=30):
    """Função principal para atualizar o cache da Selic Apurada."""
    print("Iniciando atualização da Selic Apurada...")
    
    # Obtém a data de ontem (data de corte)
    data_ontem = datetime.now() - timedelta(days=1)
    
    # Carrega o cache atual
    cache = carregar_cache()
    
    # Verifica se existem registros no cache
    if not cache["registros"]:
        print("Cache vazio. Iniciando com dados desde 01/01/2000...")
        data_inicial = datetime(2000, 1, 1)
    else:
        if forcar_atualizacao:
            # Verifica os registros dos últimos X dias para identificar problemas
            data_verificacao_inicio = data_ontem - timedelta(days=dias_para_verificar)
            registros_invalidos = identificar_registros_invalidos(cache, data_verificacao_inicio, data_ontem)
            
            if registros_invalidos:
                print(f"Encontrados {len(registros_invalidos)} registros com problemas nos últimos {dias_para_verificar} dias.")
                if registros_invalidos:
                    datas_invalidas = sorted([converter_data_string_para_datetime(d) for d in registros_invalidos])
                    data_inicial = datas_invalidas[0]  # Usa a primeira data inválida como ponto de partida
                    print(f"Forçando atualização a partir de: {formatar_data(data_inicial)}")
            else:
                # Se não encontrar problemas, usa a lógica normal
                ultima_data_valida = encontrar_ultima_data_valida(cache["registros"])
                print(f"Última data válida encontrada: {formatar_data(ultima_data_valida)}")
                data_inicial = ultima_data_valida + timedelta(days=1)
        else:
            # Lógica normal de detecção da última data válida
            ultima_data_valida = encontrar_ultima_data_valida(cache["registros"])
            print(f"Última data válida encontrada: {formatar_data(ultima_data_valida)}")
            data_inicial = ultima_data_valida + timedelta(days=1)
    
    # Se a data inicial for posterior à data de ontem, não há o que atualizar
    if data_inicial > data_ontem:
        print(f"Cache já está atualizado até {formatar_data(data_ontem)}. Nada a fazer.")
        return
    
    print(f"Período para atualização: de {formatar_data(data_inicial)} até {formatar_data(data_ontem)}")
    
    # Identifica registros a serem removidos (registros inválidos dentro do período a ser atualizado)
    # Salva a lista atual de registros antes da atualização
    registro_anterior = []
    for r in cache["registros"]:
        data = converter_data_string_para_datetime(r["dataCotacao"])
        if not data or data < data_inicial or data > data_ontem:
            registro_anterior.append(r)  # Mantém registros fora do período
    
    # Atualiza o cache apenas com registros fora do período de atualização
    cache["registros"] = registro_anterior
    
    # Mapeia as datas existentes no cache (após a remoção dos registros a serem atualizados)
    datas_existentes = {r["dataCotacao"] for r in cache["registros"]}
    
    # Divide o período em chunks para evitar problemas com a API
    chunks = dividir_periodo_em_chunks(data_inicial, data_ontem)
    
    novos_registros = []
    datas_com_dados = set()
    
    for i, (inicio_chunk, fim_chunk) in enumerate(chunks):
        print(f"Consultando chunk {i+1}/{len(chunks)}: de {formatar_data(inicio_chunk)} até {formatar_data(fim_chunk)}...")
        
        # Consulta a API do BCB
        resultado = obter_dados_selic(inicio_chunk, fim_chunk)
        
        if not resultado or "registros" not in resultado:
            print(f"Nenhum dado obtido para o período {formatar_data(inicio_chunk)} a {formatar_data(fim_chunk)}.")
            continue
        
        # Adiciona todos os registros retornados pela API (sem filtrar por data existente)
        registros_chunk = resultado["registros"]
        
        # Adiciona o flag isBusinessDay = True para todos os registros retornados pela API
        for registro in registros_chunk:
            registro["isBusinessDay"] = True
            datas_com_dados.add(registro["dataCotacao"])
        
        novos_registros.extend(registros_chunk)
        print(f"Obtidos {len(registros_chunk)} registros para o período.")
        
        # Aguarda um pouco para não sobrecarregar a API
        if i < len(chunks) - 1:
            time.sleep(1)
    
    print(f"Total de {len(novos_registros)} registros obtidos da API.")
    
    # Adiciona os novos registros ao cache
    cache["registros"].extend(novos_registros)
    
    # Adiciona registros para dias não úteis e dias sem dados (possíveis feriados)
    cache = adicionar_dias_nao_uteis_e_feriados(cache, data_inicial, data_ontem, datas_com_dados)
    
    # Ordena os registros por data (mais antiga para mais recente)
    cache["registros"] = sorted(
        cache["registros"], 
        key=lambda x: converter_data_string_para_datetime(x["dataCotacao"]) or datetime.min
    )
    
    # Salva o cache atualizado
    salvar_cache(cache)
    
    print("Atualização concluída com sucesso!")

if __name__ == "__main__":
    # Força a atualização dos registros, verificando os últimos 30 dias
    atualizar_selic_apurada(forcar_atualizacao=True, dias_para_verificar=30)
