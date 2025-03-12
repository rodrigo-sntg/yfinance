import os
import logging
import json
from datetime import datetime, timedelta
import ssl
from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import numpy as np

# Configuração do logging
log_dir = "logs"
log_file = os.path.join(log_dir, "app.log")
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Arquivo do cache de taxas Selic
CACHE_FILE = "selic_apurada_cache.json"

# Arquivo do cache de feriados
HOLIDAYS_CACHE_FILE = "feriados_cache.json"

# URL da API do Banco Central
BCB_API_URL = "https://www3.bcb.gov.br/novoselic/rest/taxaSelicApurada/pub/search?parametrosOrdenacao=%5B%5D&page=1&pageSize=20"

# URL da API Brasil para consulta de feriados
BRASIL_API_HOLIDAYS_URL = "https://brasilapi.com.br/api/feriados/v1/{year}"

app = Flask(__name__)

# Função para carregar o cache de feriados
def load_holidays_cache():
    """
    Carrega o cache de feriados do arquivo.
    Se o arquivo não existir ou ocorrer um erro, retorna um cache vazio.
    
    Returns:
        dict: Dados do cache com anos como chaves e listas de feriados como valores
    """
    try:
        if os.path.exists(HOLIDAYS_CACHE_FILE):
            logging.debug(f"Carregando cache de feriados do arquivo: {HOLIDAYS_CACHE_FILE}")
            with open(HOLIDAYS_CACHE_FILE, "r") as f:
                try:
                    cache = json.load(f)
                    num_anos = len(cache.keys())
                    logging.debug(f"Cache de feriados carregado com sucesso: {num_anos} anos encontrados")
                    return cache
                except json.JSONDecodeError as e:
                    logging.error(f"Erro ao decodificar o arquivo de cache de feriados: {e}")
                    logging.warning("Criando um novo cache de feriados vazio devido a erro no arquivo existente")
                    # Faz backup do arquivo de cache corrompido
                    backup_file = f"{HOLIDAYS_CACHE_FILE}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    try:
                        os.rename(HOLIDAYS_CACHE_FILE, backup_file)
                        logging.info(f"Backup do cache de feriados corrompido criado: {backup_file}")
                    except Exception as e:
                        logging.error(f"Não foi possível criar backup do cache de feriados corrompido: {e}")
        else:
            logging.info(f"Arquivo de cache de feriados não encontrado: {HOLIDAYS_CACHE_FILE}")
    except Exception as e:
        logging.error(f"Erro ao tentar carregar o cache de feriados: {e}")
    
    logging.debug("Retornando cache de feriados vazio")
    return {}

# Função para salvar o cache de feriados atualizado
def save_holidays_cache(data):
    """
    Salva os dados do cache de feriados em um arquivo JSON.
    
    Args:
        data (dict): Dados do cache com anos como chaves e listas de feriados como valores
    
    Returns:
        bool: True se salvou com sucesso, False caso contrário
    """
    try:
        # Cria um arquivo temporário primeiro para evitar corromper o cache em caso de erro
        temp_file = f"{HOLIDAYS_CACHE_FILE}.tmp"
        with open(temp_file, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
        # Se chegou até aqui, o arquivo temporário foi criado com sucesso
        # Agora substituímos o arquivo original
        if os.path.exists(HOLIDAYS_CACHE_FILE):
            # Cria backup antes de substituir
            backup_file = f"{HOLIDAYS_CACHE_FILE}.bak"
            try:
                os.replace(HOLIDAYS_CACHE_FILE, backup_file)
                logging.debug(f"Backup do cache de feriados anterior criado: {backup_file}")
            except Exception as e:
                logging.warning(f"Não foi possível criar backup do cache de feriados anterior: {e}")
        
        # Agora move o arquivo temporário para o lugar do original
        os.replace(temp_file, HOLIDAYS_CACHE_FILE)
        
        num_anos = len(data.keys())
        logging.info(f"Cache de feriados atualizado com sucesso: {num_anos} anos salvos")
        return True
    except IOError as e:
        logging.error(f"Erro de I/O ao salvar cache de feriados: {e}")
    except Exception as e:
        logging.error(f"Erro desconhecido ao salvar cache de feriados: {e}")
    
    logging.warning("Falha ao salvar o cache de feriados atualizado")
    return False

# Função para buscar feriados de um ano específico na API Brasil
def fetch_holidays_for_year(year):
    """
    Busca os feriados nacionais para um ano específico na API Brasil.
    
    Args:
        year (int): Ano para buscar os feriados
        
    Returns:
        list: Lista de feriados no formato {'date': 'YYYY-MM-DD', 'name': 'Nome do Feriado', 'type': 'tipo'}
              ou lista vazia em caso de erro
    """
    logging.info(f"Buscando feriados para o ano {year} na API Brasil")
    url = BRASIL_API_HOLIDAYS_URL.format(year=year)
    
    try:
        logging.debug(f"Enviando requisição para {url}")
        response = requests.get(url)
        
        logging.debug(f"Status code da resposta: {response.status_code}")
        
        if response.status_code == 200:
            holidays = response.json()
            logging.info(f"Feriados para {year} obtidos com sucesso: {len(holidays)} feriados encontrados")
            return holidays
        else:
            logging.error(f"Falha na requisição à API Brasil. Status code: {response.status_code}")
            if response.status_code != 404:  # Evita logar corpo de erro 404
                try:
                    error_msg = response.text[:500]  # Limita o tamanho do log
                    logging.error(f"Erro na resposta da API: {error_msg}")
                except Exception:
                    pass
    except requests.exceptions.ConnectionError as e:
        logging.error(f"Erro de conexão ao buscar feriados para {year}: {e}")
    except requests.exceptions.Timeout as e:
        logging.error(f"Timeout ao buscar feriados para {year}: {e}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro na requisição ao buscar feriados para {year}: {e}")
    except json.JSONDecodeError as e:
        logging.error(f"Erro ao decodificar JSON da resposta: {e}")
    except Exception as e:
        logging.error(f"Erro desconhecido ao buscar feriados para {year}: {e}")
    
    logging.warning(f"Nenhum feriado encontrado para o ano {year}")
    return []

# Função para obter os feriados de um ano, buscando no cache ou na API se necessário
def get_holidays_for_year(year):
    """
    Obtém os feriados para um ano específico, buscando primeiro no cache e, 
    se não encontrado, consultando a API e atualizando o cache.
    
    Args:
        year (int): Ano para obter os feriados
        
    Returns:
        list: Lista de feriados no formato {'date': 'YYYY-MM-DD', 'name': 'Nome do Feriado', 'type': 'tipo'}
    """
    # Carrega o cache de feriados
    holidays_cache = load_holidays_cache()
    year_str = str(year)
    
    # Verifica se já temos os feriados para esse ano no cache
    if year_str in holidays_cache:
        logging.debug(f"Feriados para o ano {year} encontrados no cache")
        return holidays_cache[year_str]
    
    # Se não temos no cache, busca na API
    logging.info(f"Feriados para o ano {year} não encontrados no cache. Buscando na API...")
    holidays = fetch_holidays_for_year(year)
    
    if holidays:
        # Atualiza o cache com os novos feriados
        holidays_cache[year_str] = holidays
        save_holidays_cache(holidays_cache)
        logging.info(f"Cache de feriados atualizado com {len(holidays)} feriados para o ano {year}")
    
    return holidays

# Função para verificar se uma data é dia útil (considerando finais de semana e feriados)
def is_business_day(date):
    """
    Verifica se uma data é um dia útil, considerando finais de semana e feriados nacionais.
    
    Args:
        date (datetime.date): Data a ser verificada
        
    Returns:
        bool: True se for dia útil, False caso contrário
    """
    # Primeiro verifica se é final de semana (0 = Segunda, ..., 5 = Sábado, 6 = Domingo)
    if date.weekday() >= 5:  # Se for sábado ou domingo
        return False
    
    # Depois verifica se é feriado
    year = date.year
    date_str = date.strftime('%Y-%m-%d')
    
    # Obtém os feriados para o ano da data
    holidays = get_holidays_for_year(year)
    
    # Verifica se a data está na lista de feriados
    for holiday in holidays:
        if holiday.get('date') == date_str:
            return False  # É feriado, não é dia útil
    
    return True  # Não é final de semana nem feriado, é dia útil

# Função para carregar o cache existente
def load_cache():
    """
    Carrega o cache de taxas Selic do arquivo.
    Se o arquivo não existir ou ocorrer um erro, retorna um cache vazio.
    
    Returns:
        dict: Dados do cache com a chave 'registros' contendo uma lista de registros
    """
    try:
        if os.path.exists(CACHE_FILE):
            logging.debug(f"Carregando cache do arquivo: {CACHE_FILE}")
            with open(CACHE_FILE, "r") as f:
                try:
                    cache = json.load(f)
                    num_registros = len(cache.get("registros", []))
                    logging.debug(f"Cache carregado com sucesso: {num_registros} registros encontrados")
                    return cache
                except json.JSONDecodeError as e:
                    logging.error(f"Erro ao decodificar o arquivo de cache: {e}")
                    logging.warning("Criando um novo cache vazio devido a erro no arquivo existente")
                    # Faz backup do arquivo de cache corrompido
                    backup_file = f"{CACHE_FILE}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    try:
                        os.rename(CACHE_FILE, backup_file)
                        logging.info(f"Backup do cache corrompido criado: {backup_file}")
                    except Exception as e:
                        logging.error(f"Não foi possível criar backup do cache corrompido: {e}")
        else:
            logging.info(f"Arquivo de cache não encontrado: {CACHE_FILE}")
    except Exception as e:
        logging.error(f"Erro ao tentar carregar o cache: {e}")
    
    logging.debug("Retornando cache vazio")
    return {"registros": []}

# Função para salvar o cache atualizado
def save_cache(data):
    """
    Salva os dados do cache em um arquivo JSON.
    
    Args:
        data (dict): Dados do cache com a chave 'registros' contendo uma lista de registros
    
    Returns:
        bool: True se salvou com sucesso, False caso contrário
    """
    try:
        # Cria um arquivo temporário primeiro para evitar corromper o cache em caso de erro
        temp_file = f"{CACHE_FILE}.tmp"
        with open(temp_file, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
        # Se chegou até aqui, o arquivo temporário foi criado com sucesso
        # Agora substituímos o arquivo original
        if os.path.exists(CACHE_FILE):
            # Cria backup antes de substituir
            backup_file = f"{CACHE_FILE}.bak"
            try:
                os.replace(CACHE_FILE, backup_file)
                logging.debug(f"Backup do cache anterior criado: {backup_file}")
            except Exception as e:
                logging.warning(f"Não foi possível criar backup do cache anterior: {e}")
        
        # Agora move o arquivo temporário para o lugar do original
        os.replace(temp_file, CACHE_FILE)
        
        num_registros = len(data.get("registros", []))
        logging.info(f"Cache atualizado com sucesso: {num_registros} registros salvos")
        return True
    except IOError as e:
        logging.error(f"Erro de I/O ao salvar cache: {e}")
    except Exception as e:
        logging.error(f"Erro desconhecido ao salvar cache: {e}")
    
    logging.warning("Falha ao salvar o cache atualizado")
    return False

# Função para obter as taxas do cache e organizar em um dicionário
def get_cached_rates():
    """
    Carrega as taxas Selic do cache e as organiza em um dicionário.
    
    Returns:
        tuple: (taxas_diarias, registros)
            - taxas_diarias: dicionário com data como chave e fator diário como valor
            - registros: lista de registros de taxas Selic originais do cache
    """
    logging.debug("Carregando taxas Selic do cache")
    try:
        cache = load_cache()
        registros = cache.get("registros", [])
        logging.debug(f"Cache carregado com {len(registros)} registros")
        
        taxas_diarias = {}
        registros_processados = 0
        registros_com_erro = 0
        
        for registro in registros:
            try:
                dt = datetime.strptime(registro.get("dataCotacao"), '%d/%m/%Y').date()
                fator_diario = float(registro.get("fatorDiario"))
                taxas_diarias[dt] = fator_diario
                registros_processados += 1
            except ValueError as e:
                registros_com_erro += 1
                logging.warning(f"Erro ao processar registro de taxa: {e}. Registro: {registro}")
            except TypeError as e:
                registros_com_erro += 1
                logging.warning(f"Erro de tipo ao processar registro: {e}. Registro: {registro}")
            except Exception as e:
                registros_com_erro += 1
                logging.warning(f"Erro desconhecido ao processar registro: {e}")
        
        if registros_com_erro > 0:
            logging.warning(f"{registros_com_erro} registros com erro foram ignorados ao carregar o cache")
        
        logging.debug(f"Cache processado: {registros_processados} taxas diárias válidas carregadas")
        return taxas_diarias, registros
    except Exception as e:
        logging.error(f"Erro ao carregar cache de taxas: {e}")
        return {}, []

# Função para buscar a taxa Selic de um dia na API do BC
def fetch_selic_for_date(date_str):
    logging.info(f"Buscando taxa Selic para a data {date_str} na API do BC")
    payload = {"dataInicial": date_str, "dataFinal": date_str}
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "Accept": "application/json, text/plain, */*"
    }
    try:
        logging.debug(f"Enviando requisição para {BCB_API_URL}")
        response = requests.post(BCB_API_URL, json=payload, headers=headers)
        
        logging.debug(f"Status code da resposta: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if "registros" in data and len(data["registros"]) > 0:
                taxa = data["registros"][0]
                logging.info(f"Taxa Selic para {date_str} obtida com sucesso: {taxa.get('fatorDiario')}")
                return taxa
            else:
                logging.warning(f"Resposta da API não contém registros para a data {date_str}")
        else:
            logging.error(f"Falha na requisição à API do BC. Status code: {response.status_code}")
            if response.status_code != 404:  # Evita logar corpo de erro 404 que pode ser muito grande
                try:
                    error_msg = response.text[:500]  # Limita o tamanho do log
                    logging.error(f"Erro na resposta da API: {error_msg}")
                except Exception:
                    pass
    except requests.exceptions.ConnectionError as e:
        logging.error(f"Erro de conexão ao buscar taxa Selic para {date_str}: {e}")
    except requests.exceptions.Timeout as e:
        logging.error(f"Timeout ao buscar taxa Selic para {date_str}: {e}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro na requisição ao buscar taxa Selic para {date_str}: {e}")
    except json.JSONDecodeError as e:
        logging.error(f"Erro ao decodificar JSON da resposta: {e}")
    except Exception as e:
        logging.error(f"Erro desconhecido ao buscar taxa Selic para {date_str}: {e}")
    
    logging.warning(f"Nenhuma taxa Selic encontrada para a data {date_str}")
    return None

# Função para garantir que todas as taxas diárias estejam no cache,
# realizando deduplicação dos registros existentes.
def ensure_rates_in_cache(start_date, end_date):
    # Carrega todas as taxas existentes do cache atual
    taxas_diarias, registros_originais = get_cached_rates()
    logging.info(f"Cache carregado com {len(taxas_diarias)} taxas diárias")

    # Mapeia datas para IDs de registros para garantir unicidade
    datas_registradas = {}
    registros_unicos = []
    
    # Primeiro passo: identificar registros únicos do cache original
    for registro in registros_originais:
        try:
            data_str = registro.get("dataCotacao")
            if not data_str:
                continue
                
            dt = datetime.strptime(data_str, '%d/%m/%Y').date()
            
            # Registra apenas se esta data ainda não foi registrada
            if dt not in datas_registradas:
                datas_registradas[dt] = True
                registros_unicos.append(registro)
                # Garante que a taxa está no dicionário
                try:
                    taxas_diarias[dt] = float(registro.get("fatorDiario"))
                except Exception as e:
                    logging.error(f"Erro ao extrair fator diário para {data_str}: {e}")
        except Exception as e:
            logging.warning(f"Erro ao processar registro do cache: {e}")
    
    logging.debug(f"Após deduplicação: {len(registros_unicos)} registros únicos de {len(registros_originais)} originais")

    cache_updated = False
    taxas_buscadas = 0
    dias_nao_uteis = 0
    current_date = start_date
    
    # Log de diagnóstico
    logging.info(f"Verificando taxas no período de {start_date} a {end_date}")
    
    # Pré-carrega todos os feriados para o período
    logging.debug("Pré-carregando feriados para o período...")
    preload_holidays_for_period(start_date, end_date)
    logging.debug("Feriados pré-carregados com sucesso")
    
    # Pré-processamento: primeiro adicionamos todos os dias não úteis ao cache
    # Isso evita fazer verificações e buscas desnecessárias para esses dias
    logging.debug("Pré-identificando dias não úteis no período...")
    temp_date = start_date
    dias_nao_uteis_pre = 0
    dias_feriados_pre = 0
    while temp_date <= end_date:
        foi_adicionado, _ = ensure_non_business_day_in_cache(temp_date, taxas_diarias, registros_unicos, datas_registradas)
        if foi_adicionado:
            cache_updated = True
            dias_nao_uteis_pre += 1
            
            # Verifica se foi adicionado por ser feriado
            if temp_date.weekday() < 5:  # Se não é final de semana
                dias_feriados_pre += 1
                
        temp_date += timedelta(days=1)
    
    if dias_nao_uteis_pre > 0:
        if dias_feriados_pre > 0:
            logging.info(f"Pré-identificados {dias_nao_uteis_pre} dias não úteis no período ({dias_feriados_pre} feriados), já adicionados ao cache")
        else:
            logging.info(f"Pré-identificados {dias_nao_uteis_pre} dias não úteis no período, já adicionados ao cache")
    
    # Segundo passo: buscar apenas datas que não temos no cache e são dias úteis
    while current_date <= end_date:
        # Verifica se a data já está no cache de taxas
        if current_date not in taxas_diarias:
            # Verifica novamente se é dia útil (caso não tenha sido identificado no pré-processamento)
            if not is_business_day(current_date):
                # Se for um dia não útil (final de semana ou feriado), define fator como 0
                missing_date_str = current_date.strftime('%d/%m/%Y')
                
                # Determina o motivo de não ser dia útil
                if current_date.weekday() >= 5:
                    reason = "FINAL_DE_SEMANA"
                    logging.info(f"Dia {missing_date_str} é um final de semana. Definindo taxa como 0.")
                else:
                    # Verifica se é feriado
                    year = current_date.year
                    date_str = current_date.strftime('%Y-%m-%d')
                    feriado_nome = None
                    
                    # Obtém os feriados para o ano
                    holidays = get_holidays_for_year(year)
                    
                    # Verifica se a data está na lista de feriados
                    for holiday in holidays:
                        if holiday.get('date') == date_str:
                            feriado_nome = holiday.get('name')
                            break
                    
                    if feriado_nome:
                        reason = f"FERIADO: {feriado_nome}"
                        logging.info(f"Dia {missing_date_str} é um feriado ({feriado_nome}). Definindo taxa como 0.")
                    else:
                        reason = "DIA_NAO_UTIL_DESCONHECIDO"
                        logging.info(f"Dia {missing_date_str} não é um dia útil por motivo desconhecido. Definindo taxa como 0.")
                
                # Cria um registro para o dia não útil
                non_business_day_record = {
                    "dataCotacao": missing_date_str,
                    "fatorDiario": "0",
                    "isBusinessDay": False,
                    "reason": reason
                }
                
                taxas_diarias[current_date] = 0.0
                
                # Só adiciona ao cache se não tivermos esta data
                if current_date not in datas_registradas:
                    registros_unicos.append(non_business_day_record)
                    datas_registradas[current_date] = True
                    cache_updated = True
                    dias_nao_uteis += 1
            else:
                # É um dia útil, busca na API normalmente
                missing_date_str = current_date.strftime('%d/%m/%Y')
                logging.info(f"Taxa para {missing_date_str} não encontrada em cache. Buscando na API...")
                
                # Busca a taxa na API
                new_rate = fetch_selic_for_date(missing_date_str)
                taxas_buscadas += 1
                
                if new_rate:
                    try:
                        fator_diario = float(new_rate.get("fatorDiario"))
                        taxas_diarias[current_date] = fator_diario
                        
                        # Adiciona a flag de dia útil
                        new_rate["isBusinessDay"] = True
                        
                        # Só adiciona ao cache se não tivermos esta data
                        if current_date not in datas_registradas:
                            registros_unicos.append(new_rate)
                            datas_registradas[current_date] = True
                            cache_updated = True
                            logging.info(f"Taxa para {missing_date_str} adicionada ao cache: {fator_diario}")
                        else:
                            logging.warning(f"Taxa para {missing_date_str} já existia no cache mas não no dicionário de taxas")
                    except Exception as e:
                        logging.error(f"Erro ao processar nova taxa para {missing_date_str}: {e}")
                else:
                    # Se a API não retornou taxa mas é dia útil, pode ser um feriado
                    # ou a API pode estar indisponível
                    logging.warning(f"Taxa para {missing_date_str} não disponível na API do BC. Verificando se é um feriado ou problema na API.")
                    
                    # Verifica se é feriado
                    year = current_date.year
                    date_str = current_date.strftime('%Y-%m-%d')
                    feriado_nome = None
                    
                    # Obtém os feriados para o ano
                    holidays = get_holidays_for_year(year)
                    
                    # Verifica se a data está na lista de feriados
                    for holiday in holidays:
                        if holiday.get('date') == date_str:
                            feriado_nome = holiday.get('name')
                            break
                    
                    # Define o motivo apropriado
                    if feriado_nome:
                        reason = f"FERIADO: {feriado_nome}"
                        logging.info(f"Data {missing_date_str} identificada como feriado ({feriado_nome}) após falha na API.")
                    else:
                        reason = "API_UNAVAILABLE"
                        logging.warning(f"Taxa para {missing_date_str} não disponível na API do BC e não é um feriado conhecido. Possível problema na API.")
                    
                    # Assume como dia não útil se não conseguir a taxa
                    non_business_day_record = {
                        "dataCotacao": missing_date_str,
                        "fatorDiario": "0",
                        "isBusinessDay": False,
                        "reason": reason
                    }
                    
                    taxas_diarias[current_date] = 0.0
                    
                    # Só adiciona ao cache se não tivermos esta data
                    if current_date not in datas_registradas:
                        registros_unicos.append(non_business_day_record)
                        datas_registradas[current_date] = True
                        cache_updated = True
                        dias_nao_uteis += 1
        else:
            logging.debug(f"Taxa para {current_date.strftime('%d/%m/%Y')} encontrada em cache: {taxas_diarias[current_date]}")
        
        current_date += timedelta(days=1)

    # Só atualiza o cache se houve mudanças
    if cache_updated:
        logging.info(f"Cache atualizado: {taxas_buscadas} novas taxas para dias úteis, {dias_nao_uteis + dias_nao_uteis_pre} dias não úteis")
        save_cache({"registros": registros_unicos})
    else:
        logging.info("Nenhuma nova taxa foi adicionada ao cache")
        
    return taxas_diarias

# Função auxiliar para adicionar dias não úteis ao cache de forma proativa
def ensure_non_business_day_in_cache(date, taxas_diarias, registros_unicos, datas_registradas):
    """
    Verifica se a data é um dia não útil e, se for, garante que esteja no cache com valor zero.
    
    Args:
        date (datetime.date): Data a ser verificada
        taxas_diarias (dict): Dicionário com as taxas diárias já carregadas
        registros_unicos (list): Lista de registros únicos para o cache
        datas_registradas (dict): Dicionário de datas já registradas no cache
        
    Returns:
        tuple: (foi_adicionado, taxa_diaria)
            - foi_adicionado: True se a data foi adicionada ao cache, False caso contrário
            - taxa_diaria: Valor da taxa diária (0.0 para dias não úteis)
    """
    # Se a data já está no cache, não precisamos fazer nada
    if date in taxas_diarias:
        return False, taxas_diarias[date]
    
    # Verifica se é final de semana
    eh_final_semana = date.weekday() >= 5
    
    # Se não for final de semana, verifica se é feriado
    eh_feriado = False
    nome_feriado = None
    if not eh_final_semana:
        # Verifica se é feriado
        year = date.year
        date_str = date.strftime('%Y-%m-%d')
        
        # Obtém os feriados para o ano
        holidays = get_holidays_for_year(year)
        
        # Verifica se a data está na lista de feriados
        for holiday in holidays:
            if holiday.get('date') == date_str:
                eh_feriado = True
                nome_feriado = holiday.get('name')
                break
    
    # Se for final de semana ou feriado, adiciona ao cache com valor zero
    if eh_final_semana or eh_feriado:
        date_str = date.strftime('%d/%m/%Y')
        
        # Define o motivo
        if eh_final_semana:
            reason = "FINAL_DE_SEMANA"
            logging.debug(f"Adicionando final de semana {date_str} ao cache com taxa zero")
        else:
            reason = f"FERIADO: {nome_feriado}"
            logging.debug(f"Adicionando feriado {date_str} ({nome_feriado}) ao cache com taxa zero")
        
        # Cria registro para o dia não útil
        non_business_day = {
            "dataCotacao": date_str,
            "fatorDiario": "0",
            "isBusinessDay": False,
            "reason": reason
        }
        
        # Adiciona ao dicionário de taxas
        taxas_diarias[date] = 0.0
        
        # Adiciona ao cache apenas se não estiver registrado
        if date not in datas_registradas:
            registros_unicos.append(non_business_day)
            datas_registradas[date] = True
            return True, 0.0
            
    return False, None

# Função para pré-carregar feriados de um período
def preload_holidays_for_period(start_date, end_date):
    """
    Pré-carrega os feriados para todo o período entre start_date e end_date.
    Isso garante que os feriados estejam disponíveis no cache para operações subsequentes.
    
    Args:
        start_date (datetime.date): Data inicial do período
        end_date (datetime.date): Data final do período
        
    Returns:
        dict: Dicionário com anos como chaves e listas de feriados como valores
    """
    logging.info(f"Pré-carregando feriados para o período de {start_date} a {end_date}")
    
    # Identifica todos os anos no período
    start_year = start_date.year
    end_year = end_date.year
    anos = list(range(start_year, end_year + 1))
    
    # Carrega o cache atual
    holidays_cache = load_holidays_cache()
    anos_faltantes = []
    
    # Identifica quais anos precisam ser buscados
    for ano in anos:
        if str(ano) not in holidays_cache:
            anos_faltantes.append(ano)
    
    # Busca os feriados para os anos faltantes
    if anos_faltantes:
        logging.info(f"Buscando feriados para {len(anos_faltantes)} anos: {anos_faltantes}")
        
        for ano in anos_faltantes:
            holidays = fetch_holidays_for_year(ano)
            if holidays:
                holidays_cache[str(ano)] = holidays
        
        # Salva o cache atualizado
        save_holidays_cache(holidays_cache)
        logging.info(f"Cache de feriados atualizado com feriados para {len(anos_faltantes)} anos")
    else:
        logging.info(f"Todos os {len(anos)} anos do período já estão no cache de feriados")
    
    return holidays_cache

# Endpoint para buscar a taxa Selic apurada para uma data específica
@app.route('/selic/apurada', methods=['GET'])
def get_selic_apurada():
    # Log da requisição
    ip_origem = request.remote_addr
    logging.info(f"Requisição de taxa Selic apurada recebida de {ip_origem}")
    
    requested_date = request.args.get('data')
    logging.info(f"Parâmetro recebido: data={requested_date}")
    
    if not requested_date:
        # Se não for informado, usa o dia anterior
        requested_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        logging.info(f"Data não informada, usando data padrão: {requested_date}")
        
    try:
        target_date = datetime.strptime(requested_date, '%Y-%m-%d').date()
        logging.debug(f"Data convertida: {target_date}")
    except ValueError:
        erro_msg = "Formato de data inválido. Use YYYY-MM-DD."
        logging.warning(f"Erro de validação: {erro_msg} Valor recebido: {requested_date}")
        return jsonify({"error": erro_msg}), 400

    # Verifica se é final de semana
    eh_final_semana = target_date.weekday() >= 5
    
    # Verifica se é feriado
    eh_feriado = False
    nome_feriado = None
    
    # Se não for final de semana, verifica se é feriado
    if not eh_final_semana:
        # Obtém os feriados para o ano
        year = target_date.year
        date_str = target_date.strftime('%Y-%m-%d')
        
        # Pré-carrega os feriados para o ano
        holidays = get_holidays_for_year(year)
        
        # Verifica se a data está na lista de feriados
        for holiday in holidays:
            if holiday.get('date') == date_str:
                eh_feriado = True
                nome_feriado = holiday.get('name')
                break
    
    # Determina se é dia útil (não é final de semana nem feriado)
    dia_util = not (eh_final_semana or eh_feriado)
    
    # Se não for dia útil, registra o motivo
    if not dia_util:
        if eh_final_semana:
            logging.info(f"Data solicitada {requested_date} é um final de semana.")
        else:
            logging.info(f"Data solicitada {requested_date} é um feriado: {nome_feriado}.")
    
    # Primeiro, verifica se já temos a taxa no cache
    taxas_diarias, registros_originais = get_cached_rates()
    
    # Prepara estruturas para possível atualização do cache
    datas_registradas = {}
    registros_unicos = []
    
    # Mapeia datas já registradas
    for registro in registros_originais:
        try:
            dt_str = registro.get("dataCotacao")
            if dt_str:
                dt = datetime.strptime(dt_str, '%d/%m/%Y').date()
                datas_registradas[dt] = True
        except Exception:
            continue
    
    # Se não for dia útil, tenta adicionar ao cache imediatamente
    cache_updated = False
    if not dia_util:
        foi_adicionado, _ = ensure_non_business_day_in_cache(target_date, taxas_diarias, registros_unicos, datas_registradas)
        if foi_adicionado:
            cache_updated = True
    
    # Se atualizamos o cache, salvamos
    if cache_updated:
        all_registros = registros_originais.copy()
        all_registros.extend(registros_unicos)
        save_cache({"registros": all_registros})
        if eh_feriado:
            logging.info(f"Cache atualizado com feriado: {target_date.strftime('%Y-%m-%d')} - {nome_feriado}")
        else:
            logging.info(f"Cache atualizado com dia não útil: {target_date.strftime('%Y-%m-%d')}")
    
    if target_date in taxas_diarias:
        # Taxa encontrada no cache
        fator_diario = taxas_diarias[target_date]
        
        # Se o dia não é útil mas temos uma taxa > 0, algo pode estar errado
        # mas respeitamos o que está no cache 
        if not dia_util and fator_diario > 0:
            logging.warning(f"Data {requested_date} é um dia não útil mas tem taxa > 0 no cache: {fator_diario}")
        
        # Prepara resposta com informações adicionais sobre feriados
        response = {
            "dataCotacao": target_date.strftime('%Y-%m-%d'),
            "fatorDiario": fator_diario,
            "diaUtil": dia_util,
            "fonte": "cache"
        }
        
        # Adiciona informações sobre o tipo de dia não útil
        if not dia_util:
            if eh_final_semana:
                response["tipoNaoUtil"] = "FINAL_DE_SEMANA"
            elif eh_feriado:
                response["tipoNaoUtil"] = "FERIADO"
                response["nomeFeriado"] = nome_feriado
        
        return jsonify(response)
    
    # Se não temos no cache e é um dia não útil, retornamos taxa 0 sem buscar na API
    if not dia_util:
        if eh_feriado:
            logging.info(f"Feriado {requested_date} ({nome_feriado}) não encontrado em cache. Retornando taxa 0.")
        else:
            logging.info(f"Dia não útil {requested_date} não encontrado em cache. Retornando taxa 0.")
        
        # Garante que a taxa está no cache
        taxas_diarias = ensure_rates_in_cache(target_date, target_date)
        
        # Prepara resposta com informações adicionais
        response = {
            "dataCotacao": target_date.strftime('%Y-%m-%d'),
            "fatorDiario": 0,
            "diaUtil": False,
            "fonte": "calculado"
        }
        
        # Adiciona informações sobre o tipo de dia não útil
        if eh_final_semana:
            response["tipoNaoUtil"] = "FINAL_DE_SEMANA"
        elif eh_feriado:
            response["tipoNaoUtil"] = "FERIADO"
            response["nomeFeriado"] = nome_feriado
        
        return jsonify(response)
    
    # Se chegou aqui, é dia útil não encontrado no cache, busca na API
    logging.info(f"Taxa para dia útil {requested_date} não encontrada no cache. Buscando na API.")
    
    # Garante que a taxa está no cache para a data solicitada (vai buscar na API se necessário)
    taxas_diarias = ensure_rates_in_cache(target_date, target_date)
    
    if target_date in taxas_diarias:
        fator_diario = taxas_diarias[target_date]
        # Se é dia útil mas a taxa é 0, pode ser um feriado não cadastrado
        is_holiday = (dia_util and fator_diario == 0)
        
        # Prepara resposta
        response = {
            "dataCotacao": target_date.strftime('%Y-%m-%d'),
            "fatorDiario": fator_diario,
            "diaUtil": (dia_util and not is_holiday),
            "fonte": "api"
        }
        
        # Se for um possível feriado não cadastrado
        if is_holiday:
            response["tipoNaoUtil"] = "POSSIVEL_FERIADO"
            response["avisoFeriado"] = "Esta data pode ser um feriado não cadastrado ou houve falha na API"
        
        return jsonify(response)
    else:
        erro_msg = "Nenhuma taxa Selic encontrada para essa data."
        logging.warning(f"Erro: {erro_msg} Data: {requested_date}")
        return jsonify({"error": erro_msg}), 404

# Endpoint para calcular o investimento atualizado
@app.route('/investimento', methods=['GET'])
def calcular_investimento():
    """
    Calcula o valor atualizado de um investimento com base na Selic diária.
    Parâmetros:
      - data: data de início do investimento (YYYY-MM-DD)
      - valor: valor investido inicial (float)
    """
    # Log da requisição recebida
    ip_origem = request.remote_addr
    logging.info(f"Requisição de cálculo de investimento recebida de {ip_origem}")
    
    data_inicial_str = request.args.get('data')
    valor_investido_str = request.args.get('valor')
    logging.info(f"Parâmetros recebidos: data={data_inicial_str}, valor={valor_investido_str}")
    
    if not data_inicial_str or not valor_investido_str:
        erro_msg = "Os parâmetros 'data' e 'valor' são obrigatórios."
        logging.warning(f"Requisição inválida: {erro_msg}")
        return jsonify({"error": erro_msg}), 400

    try:
        data_inicial = datetime.strptime(data_inicial_str, '%Y-%m-%d').date()
        logging.debug(f"Data inicial convertida: {data_inicial}")
    except ValueError:
        erro_msg = "Formato de data inválido. Use YYYY-MM-DD."
        logging.warning(f"Erro de validação: {erro_msg} Valor recebido: {data_inicial_str}")
        return jsonify({"error": erro_msg}), 400

    try:
        valor_investido = float(valor_investido_str)
        logging.debug(f"Valor investido convertido: {valor_investido}")
    except ValueError:
        erro_msg = "Valor investido deve ser numérico."
        logging.warning(f"Erro de validação: {erro_msg} Valor recebido: {valor_investido_str}")
        return jsonify({"error": erro_msg}), 400

    # Define a data final como o dia anterior à data atual
    data_final = (datetime.now() - timedelta(days=1)).date()
    logging.info(f"Período de cálculo: {data_inicial} até {data_final}")
    
    if data_inicial > data_final:
        erro_msg = "A data de início deve ser anterior à data final."
        logging.warning(f"Erro de validação: {erro_msg} Data inicial: {data_inicial}, Data final: {data_final}")
        return jsonify({"error": erro_msg}), 400

    # Verificação de quantos dias serão calculados
    dias_totais = (data_final - data_inicial).days + 1
    logging.info(f"Total de dias a serem considerados no cálculo: {dias_totais}")

    # Lista de todas as datas no período
    datas_necessarias = [data_inicial + timedelta(days=i) for i in range(dias_totais)]
    
    # Carrega o cache atual
    taxas_diarias, registros_originais = get_cached_rates()
    
    # Prepara estruturas para possível atualização do cache
    datas_registradas = {}
    registros_unicos = []
    
    # Mapeia datas já registradas
    for registro in registros_originais:
        try:
            dt_str = registro.get("dataCotacao")
            if dt_str:
                dt = datetime.strptime(dt_str, '%d/%m/%Y').date()
                datas_registradas[dt] = True
        except Exception:
            continue
    
    # Pré-identifica dias não úteis para todo o período
    dias_nao_uteis_adicionados = 0
    cache_updated = False
    
    for data in datas_necessarias:
        # Tenta identificar dias não úteis e adicionar ao cache
        foi_adicionado, _ = ensure_non_business_day_in_cache(data, taxas_diarias, registros_unicos, datas_registradas)
        if foi_adicionado:
            cache_updated = True
            dias_nao_uteis_adicionados += 1
            # Adiciona ao registro de datas registradas para evitar duplicação
            datas_registradas[data] = True
    
    # Se houve atualizações no cache com dias não úteis, salvamos
    if cache_updated:
        all_registros = registros_originais.copy()
        all_registros.extend(registros_unicos)
        save_cache({"registros": all_registros})
        logging.info(f"Cache atualizado com {dias_nao_uteis_adicionados} dias não úteis identificados proativamente")
    
    # Verifica quais datas ainda estão faltando no cache após pré-identificação dos dias não úteis
    datas_faltantes = [d for d in datas_necessarias if d not in taxas_diarias]
    
    # Se ainda houver datas faltantes, buscamos apenas essas datas
    if datas_faltantes:
        logging.info(f"Encontradas {len(datas_necessarias) - len(datas_faltantes)} de {dias_totais} taxas necessárias em cache.")
        logging.info(f"Faltam taxas para {len(datas_faltantes)} dias. Buscando dados...")
        
        # Filtra apenas os dias úteis que estão faltando, pois os não úteis já foram adicionados
        datas_uteis_faltantes = [d for d in datas_faltantes if is_business_day(d)]
        
        if datas_uteis_faltantes:
            # Se ainda houver dias úteis faltando, buscamos na API apenas para esses dias
            logging.info(f"Buscando dados apenas para {len(datas_uteis_faltantes)} dias úteis faltantes")
            
            # Ordena as datas faltantes
            datas_uteis_faltantes.sort()
            
            # Agrupa datas contíguas para minimizar as consultas
            grupos_datas = []
            grupo_atual = []
            
            for data in datas_uteis_faltantes:
                if not grupo_atual or (data - grupo_atual[-1]).days == 1:
                    grupo_atual.append(data)
                else:
                    grupos_datas.append(grupo_atual)
                    grupo_atual = [data]
            
            if grupo_atual:
                grupos_datas.append(grupo_atual)
            
            # Busca taxas para cada grupo de datas contíguas
            for grupo in grupos_datas:
                start_group = grupo[0]
                end_group = grupo[-1]
                logging.info(f"Buscando taxas para o período de {start_group} a {end_group}")
                taxas_diarias = ensure_rates_in_cache(start_group, end_group)
    else:
        logging.info(f"Todas as {dias_totais} taxas necessárias já estão disponíveis em cache. Não é necessário buscar dados.")
    
    # Verifica se todas as datas agora têm taxas
    dias_com_taxa = sum(1 for d in datas_necessarias if d in taxas_diarias)
    dias_uteis = sum(1 for d in datas_necessarias if d in taxas_diarias and taxas_diarias[d] > 0)
    dias_nao_uteis = sum(1 for d in datas_necessarias if d in taxas_diarias and taxas_diarias[d] == 0)
    
    logging.info(f"Cálculo utilizará {dias_com_taxa} de {dias_totais} dias com taxas disponíveis")
    logging.info(f"Total de dias úteis: {dias_uteis}, dias não úteis: {dias_nao_uteis}")

    # Cálculo de juros compostos
    logging.info("Iniciando cálculo de juros compostos")
    fator_composto = 1.0
    dias_compostos = 0  # Dias com taxa > 0
    dias_sem_rendimento = 0  # Dias com taxa = 0 (não úteis)
    dias_sem_taxa = 0  # Dias sem taxa disponível
    current_date = data_inicial
    
    # Para diagnóstico
    fatores_utilizados = []
    
    while current_date <= data_final:
        if current_date in taxas_diarias:
            fator_diario = taxas_diarias[current_date]
            if fator_diario > 0:
                # Dia útil com taxa disponível
                fator_composto *= fator_diario
                dias_compostos += 1
                fatores_utilizados.append({
                    "data": current_date.strftime('%Y-%m-%d'),
                    "fator": fator_diario,
                    "tipo": "dia_util"
                })
                logging.debug(f"Dia {current_date}: Fator diário = {fator_diario}, Fator acumulado = {fator_composto}")
            else:
                # Dia não útil (taxa = 0)
                dias_sem_rendimento += 1
                fatores_utilizados.append({
                    "data": current_date.strftime('%Y-%m-%d'),
                    "fator": 0,
                    "tipo": "dia_nao_util"
                })
                logging.debug(f"Dia {current_date}: Dia não útil, fator = 0")
        else:
            # Dia sem taxa disponível (erro ou API indisponível)
            dias_sem_taxa += 1
            fatores_utilizados.append({
                "data": current_date.strftime('%Y-%m-%d'),
                "fator": 1.0,
                "tipo": "desconhecido"
            })
            logging.debug(f"Dia {current_date}: Taxa não encontrada, usando fator 1.0")
        
        current_date += timedelta(days=1)

    if dias_sem_taxa > 0:
        logging.warning(f"Atenção: {dias_sem_taxa} dias sem taxa Selic disponível no período calculado")

    valor_final = valor_investido * fator_composto
    rendimento = valor_final - valor_investido
    rendimento_percentual = (rendimento / valor_investido) * 100
    
    logging.info(f"Cálculo concluído: Valor inicial={valor_investido}, Fator composto={fator_composto}, Valor final={valor_final}")
    logging.info(f"Rendimento: R$ {rendimento:.2f} ({rendimento_percentual:.2f}%)")

    resultado = {
        "data_inicial": data_inicial_str,
        "data_final": data_final.strftime('%Y-%m-%d'),
        "valor_investido": valor_investido,
        "valor_final": round(valor_final, 2),
        "rendimento": round(rendimento, 2),
        "rendimento_percentual": round(rendimento_percentual, 2),
        "fator_composto": round(fator_composto, 8),
        "dias_compostos": dias_compostos,  # Dias úteis com taxa > 0
        "dias_sem_rendimento": dias_sem_rendimento,  # Dias não úteis com taxa = 0
        "dias_sem_taxa": dias_sem_taxa,  # Dias sem taxa disponível
        "dias_totais": dias_totais  # Total de dias no período
    }
    
    # Adiciona fatores detalhados para diagnóstico se estiver em modo DEBUG
    if logging.getLogger().isEnabledFor(logging.DEBUG):
        resultado["fatores_detalhados"] = fatores_utilizados
        
    logging.info(f"Retornando resultado do cálculo: {json.dumps(resultado, default=str)}")
    return jsonify(resultado)

# Endpoint para análise detalhada de investimento
@app.route('/investimento/analise', methods=['GET'])
def analisar_investimento():
    """
    Realiza uma análise detalhada de investimento com estatísticas sobre dias úteis e não úteis.
    Parâmetros:
      - data: data de início do investimento (YYYY-MM-DD)
      - valor: valor investido inicial (float)
    """
    # Log da requisição recebida
    ip_origem = request.remote_addr
    logging.info(f"Requisição de análise de investimento recebida de {ip_origem}")
    
    data_inicial_str = request.args.get('data')
    valor_investido_str = request.args.get('valor')
    logging.info(f"Parâmetros recebidos: data={data_inicial_str}, valor={valor_investido_str}")
    
    if not data_inicial_str or not valor_investido_str:
        erro_msg = "Os parâmetros 'data' e 'valor' são obrigatórios."
        logging.warning(f"Requisição inválida: {erro_msg}")
        return jsonify({"error": erro_msg}), 400

    try:
        data_inicial = datetime.strptime(data_inicial_str, '%Y-%m-%d').date()
        logging.debug(f"Data inicial convertida: {data_inicial}")
    except ValueError:
        erro_msg = "Formato de data inválido. Use YYYY-MM-DD."
        logging.warning(f"Erro de validação: {erro_msg} Valor recebido: {data_inicial_str}")
        return jsonify({"error": erro_msg}), 400

    try:
        valor_investido = float(valor_investido_str)
        logging.debug(f"Valor investido convertido: {valor_investido}")
    except ValueError:
        erro_msg = "Valor investido deve ser numérico."
        logging.warning(f"Erro de validação: {erro_msg} Valor recebido: {valor_investido_str}")
        return jsonify({"error": erro_msg}), 400

    # Define a data final como o dia anterior à data atual
    data_final = (datetime.now() - timedelta(days=1)).date()
    logging.info(f"Período de análise: {data_inicial} até {data_final}")
    
    if data_inicial > data_final:
        erro_msg = "A data de início deve ser anterior à data final."
        logging.warning(f"Erro de validação: {erro_msg} Data inicial: {data_inicial}, Data final: {data_final}")
        return jsonify({"error": erro_msg}), 400

    # Verificação de quantos dias serão analisados
    dias_totais = (data_final - data_inicial).days + 1
    logging.info(f"Total de dias a serem considerados na análise: {dias_totais}")

    # Lista de todas as datas no período
    datas_necessarias = [data_inicial + timedelta(days=i) for i in range(dias_totais)]
    
    # Carrega o cache atual
    taxas_diarias, registros_originais = get_cached_rates()
    
    # Prepara estruturas para possível atualização do cache
    datas_registradas = {}
    registros_unicos = []
    
    # Mapeia datas já registradas
    for registro in registros_originais:
        try:
            dt_str = registro.get("dataCotacao")
            if dt_str:
                dt = datetime.strptime(dt_str, '%d/%m/%Y').date()
                datas_registradas[dt] = True
        except Exception:
            continue
    
    # Pré-identifica dias não úteis para todo o período
    dias_nao_uteis_adicionados = 0
    cache_updated = False
    
    for data in datas_necessarias:
        # Tenta identificar dias não úteis e adicionar ao cache
        foi_adicionado, _ = ensure_non_business_day_in_cache(data, taxas_diarias, registros_unicos, datas_registradas)
        if foi_adicionado:
            cache_updated = True
            dias_nao_uteis_adicionados += 1
            # Adiciona ao registro de datas registradas para evitar duplicação
            datas_registradas[data] = True
    
    # Se houve atualizações no cache com dias não úteis, salvamos
    if cache_updated:
        all_registros = registros_originais.copy()
        all_registros.extend(registros_unicos)
        save_cache({"registros": all_registros})
        logging.info(f"Cache atualizado com {dias_nao_uteis_adicionados} dias não úteis identificados proativamente")
    
    # Verifica quais datas estão faltando no cache após pré-identificação
    datas_faltantes = [d for d in datas_necessarias if d not in taxas_diarias]
    
    # Se ainda houver datas faltantes, buscamos apenas os dias úteis
    if datas_faltantes:
        # Filtra apenas os dias úteis que estão faltando
        datas_uteis_faltantes = [d for d in datas_faltantes if is_business_day(d)]
        
        if datas_uteis_faltantes:
            # Busca taxas para dias úteis faltantes
            logging.info(f"Buscando taxas para {len(datas_uteis_faltantes)} dias úteis faltantes")
            # Busca taxas para todo o período para simplificar
            taxas_diarias = ensure_rates_in_cache(data_inicial, data_final)
    
    # Estatísticas por tipo de dia
    dias_uteis_count = 0
    dias_nao_uteis_count = 0
    dias_feriados_count = 0
    
    fator_acumulado_total = 1.0
    fator_acumulado_util = 1.0
    
    dias_com_detalhes = []
    
    # Análise dia a dia
    for data in datas_necessarias:
        dia_util = is_business_day(data)
        
        item = {
            "data": data.strftime('%Y-%m-%d'),
            "dia_semana": data.strftime('%A'),
            "dia_util_calendario": dia_util
        }
        
        if data in taxas_diarias:
            fator = taxas_diarias[data]
            item["fator_diario"] = fator
            
            # Atualiza o fator acumulado total
            fator_acumulado_total *= fator
            
            if fator > 0:
                # É um dia útil para rendimento
                dias_uteis_count += 1
                item["tipo"] = "dia_util"
                item["rendimento"] = True
                
                # Atualiza o fator acumulado dos dias úteis
                fator_acumulado_util *= fator
            else:
                # É um dia não útil (taxa = 0)
                if dia_util:
                    # Se o calendário diz que é útil mas a taxa é 0, é provavelmente um feriado
                    dias_feriados_count += 1
                    item["tipo"] = "feriado"
                else:
                    # Fim de semana
                    dias_nao_uteis_count += 1
                    item["tipo"] = "fim_de_semana"
                
                item["rendimento"] = False
        else:
            # Dia sem taxa disponível
            item["tipo"] = "sem_taxa"
            item["rendimento"] = False
        
        dias_com_detalhes.append(item)
    
    # Calcular valores finais
    valor_final_total = valor_investido * fator_acumulado_total
    rendimento_total = valor_final_total - valor_investido
    rendimento_percentual_total = (rendimento_total / valor_investido) * 100
    
    # Calcular o rendimento apenas dos dias úteis
    valor_final_util = valor_investido * fator_acumulado_util
    rendimento_util = valor_final_util - valor_investido
    rendimento_percentual_util = (rendimento_util / valor_investido) * 100
    
    # Calcular estatísticas diárias médias 
    rendimento_diario_medio_total = rendimento_percentual_total / dias_totais if dias_totais > 0 else 0
    rendimento_diario_medio_util = rendimento_percentual_util / dias_uteis_count if dias_uteis_count > 0 else 0
    
    # Resultado da análise
    resultado = {
        "dados_investimento": {
            "data_inicial": data_inicial_str,
            "data_final": data_final.strftime('%Y-%m-%d'),
            "valor_investido": valor_investido,
            "valor_final": round(valor_final_total, 2),
            "rendimento": round(rendimento_total, 2),
            "rendimento_percentual": round(rendimento_percentual_total, 2)
        },
        "estatisticas_periodo": {
            "dias_totais": dias_totais,
            "dias_uteis": dias_uteis_count,
            "dias_nao_uteis": dias_nao_uteis_count,
            "dias_feriados": dias_feriados_count,
            "fator_acumulado_total": round(fator_acumulado_total, 8),
            "fator_acumulado_apenas_uteis": round(fator_acumulado_util, 8),
            "rendimento_diario_medio_total": round(rendimento_diario_medio_total, 6),
            "rendimento_diario_medio_util": round(rendimento_diario_medio_util, 6)
        },
        "analise_rendimento_por_dias": {
            "valor_final_considerando_todos_dias": round(valor_final_total, 2),
            "valor_final_apenas_dias_uteis": round(valor_final_util, 2),
            "diferenca_valor_final": round(valor_final_total - valor_final_util, 2)
        }
    }
    
    # Incluir detalhes dia a dia se solicitado
    detalhar = request.args.get('detalhar', 'false').lower() == 'true'
    if detalhar:
        resultado["detalhes_diarios"] = dias_com_detalhes
    
    logging.info(f"Análise de investimento concluída: {dias_uteis_count} dias úteis, {dias_nao_uteis_count} dias não úteis, {dias_feriados_count} feriados")
    
    return jsonify(resultado)

# Endpoint para verificar se uma data é um dia útil
@app.route('/dia-util', methods=['GET'])
def verificar_dia_util():
    """
    Verifica se uma data é um dia útil (não é final de semana ou feriado).
    Parâmetros:
      - data: Data para verificação (YYYY-MM-DD)
    """
    # Log da requisição recebida
    ip_origem = request.remote_addr
    logging.info(f"Requisição de verificação de dia útil recebida de {ip_origem}")
    
    requested_date = request.args.get('data')
    logging.info(f"Parâmetro recebido: data={requested_date}")
    
    if not requested_date:
        # Se não for informado, usa o dia atual
        requested_date = datetime.now().strftime('%Y-%m-%d')
        logging.info(f"Data não informada, usando data atual: {requested_date}")
        
    try:
        data = datetime.strptime(requested_date, '%Y-%m-%d').date()
        logging.debug(f"Data convertida: {data}")
    except ValueError:
        erro_msg = "Formato de data inválido. Use YYYY-MM-DD."
        logging.warning(f"Erro de validação: {erro_msg} Valor recebido: {requested_date}")
        return jsonify({"error": erro_msg}), 400

    # Verifica se é fim de semana
    eh_final_semana = data.weekday() >= 5
    
    # Verifica se é um feriado
    eh_feriado = False
    info_feriado = None
    
    # Busca informações de feriado se não for fim de semana
    if not eh_final_semana:
        # Obtém os feriados para o ano
        year = data.year
        date_str = data.strftime('%Y-%m-%d')
        holidays = get_holidays_for_year(year)
        
        # Verifica se a data está na lista de feriados
        for holiday in holidays:
            if holiday.get('date') == date_str:
                eh_feriado = True
                info_feriado = holiday
                break
    
    # O dia só é útil se não for fim de semana e não for feriado
    dia_util_calendario = not (eh_final_semana or eh_feriado)
    
    # Busca as taxas do cache
    taxas_diarias, registros_originais = get_cached_rates()
    
    # Prepara estruturas para possível atualização do cache
    datas_registradas = {}
    registros_unicos = []
    
    # Prepara mapeamento das datas já registradas para evitar duplicações
    for registro in registros_originais:
        try:
            dt_str = registro.get("dataCotacao")
            if dt_str:
                dt = datetime.strptime(dt_str, '%d/%m/%Y').date()
                datas_registradas[dt] = True
        except Exception:
            continue
    
    # Usa nossa função auxiliar para verificar e adicionar ao cache se for dia não útil
    cache_updated = False
    fator = None
    
    if not dia_util_calendario:
        # Se já sabemos que não é dia útil, podemos adicionar diretamente ao cache
        adicionar_ao_cache, fator = ensure_non_business_day_in_cache(data, taxas_diarias, registros_unicos, datas_registradas)
        if adicionar_ao_cache:
            cache_updated = True
    
    # Se a data estiver no cache após a verificação, usamos o valor do cache
    if data in taxas_diarias:
        fator = taxas_diarias[data]
        dia_util_financeiro = (fator > 0)
    else:
        # Se não está no cache e não é dia não útil conhecido, verificamos na API
        if dia_util_calendario:
            # É um dia útil pelo calendário, busca na API
            taxas_diarias = ensure_rates_in_cache(data, data)
            
            if data in taxas_diarias:
                fator = taxas_diarias[data]
                dia_util_financeiro = (fator > 0)
                
                # Se o fator é 0 mas deveria ser dia útil, pode ser um feriado não cadastrado ou problema na API
                if fator == 0 and dia_util_calendario:
                    logging.warning(f"Data {data.strftime('%Y-%m-%d')} deveria ser dia útil mas tem fator 0. Possível feriado não cadastrado.")
                    eh_feriado = True
            else:
                # Se ainda não temos, assumimos pelo calendário
                fator = None
                dia_util_financeiro = dia_util_calendario
        else:
            # É um dia não útil pelo calendário, deve ter sido adicionado ao cache
            if data not in taxas_diarias:
                # Garante que esteja no cache
                taxas_diarias = ensure_rates_in_cache(data, data)
            
            fator = taxas_diarias.get(data, 0.0)
            dia_util_financeiro = False
    
    # Se atualizamos o cache com novos registros, salvamos
    if cache_updated and registros_unicos:
        all_registros = registros_originais.copy()
        all_registros.extend(registros_unicos)
        save_cache({"registros": all_registros})
        logging.info(f"Cache atualizado com dia não útil: {data.strftime('%Y-%m-%d')}")
    
    # Resultado da verificação
    resultado = {
        "data": requested_date,
        "dia_semana": data.strftime('%A'),
        "eh_dia_util_calendario": dia_util_calendario,
        "eh_dia_util_financeiro": dia_util_financeiro,
        "eh_final_semana": eh_final_semana,
        "eh_feriado": eh_feriado
    }
    
    # Se for feriado, adiciona detalhes
    if eh_feriado and info_feriado:
        resultado["feriado"] = {
            "nome": info_feriado.get('name'),
            "tipo": info_feriado.get('type')
        }
    
    # Se temos o fator, incluímos na resposta
    if fator is not None:
        resultado["fator_diario"] = fator
        
    # Se temos a taxa completa, incluímos detalhes adicionais
    if data in taxas_diarias:
        for registro in registros_originais:
            try:
                if datetime.strptime(registro.get("dataCotacao"), '%d/%m/%Y').date() == data:
                    # Remove o fator diário pois já incluímos acima
                    detalhes = {k: v for k, v in registro.items() if k != "fatorDiario"}
                    resultado["detalhes_taxa"] = detalhes
                    break
            except Exception:
                pass
    
    logging.info(f"Resultado da verificação de dia útil: {json.dumps(resultado, default=str)}")
    return jsonify(resultado)

@app.route('/ping')
def healthcheck():
    return jsonify({"status": "ok", "message": "Service is running"}), 200

if __name__ == '__main__':
    
    app.run(host='0.0.0.0', port=5001, debug=True)
