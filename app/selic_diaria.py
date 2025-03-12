import os
import requests
import json
from datetime import datetime, date, timedelta
import time
from app.logger import logger
from app.config import CACHE_BACKUP_DIR, SELIC_DIARIA_CACHE_FILE, BCB_SELIC_DIARIA_API_URL

def load_selic_diaria_cache():
    """
    Carrega o cache de taxas Selic diárias do arquivo.
    Se o arquivo não existir ou ocorrer um erro, retorna um cache vazio.
    
    Returns:
        dict: Dados do cache com a chave 'conteudo' contendo uma lista de registros
    """
    try:
        if os.path.exists(SELIC_DIARIA_CACHE_FILE):
            logger.debug(f"Carregando cache de SELIC diária do arquivo: {SELIC_DIARIA_CACHE_FILE}")
            with open(SELIC_DIARIA_CACHE_FILE, "r") as f:
                try:
                    cache = json.load(f)
                    num_registros = len(cache.get("conteudo", []))
                    logger.debug(f"Cache de SELIC diária carregado com sucesso: {num_registros} registros encontrados")
                    return cache
                except json.JSONDecodeError as e:
                    logger.error(f"Erro ao decodificar o arquivo de cache de SELIC diária: {e}")
                    logger.warning("Criando um novo cache vazio devido a erro no arquivo existente")
                    # Faz backup do arquivo de cache corrompido
                    os.makedirs(CACHE_BACKUP_DIR, exist_ok=True)
                    backup_file = os.path.join(CACHE_BACKUP_DIR, f"selic_diaria_corrupto_{datetime.now().strftime('%Y%m%d%H%M%S')}.json")
                    try:
                        os.rename(SELIC_DIARIA_CACHE_FILE, backup_file)
                        logger.info(f"Backup do cache de SELIC diária corrompido criado: {backup_file}")
                    except Exception as e:
                        logger.error(f"Não foi possível criar backup do cache de SELIC diária corrompido: {e}")
        else:
            logger.info(f"Arquivo de cache de SELIC diária não encontrado: {SELIC_DIARIA_CACHE_FILE}")
    except Exception as e:
        logger.error(f"Erro ao tentar carregar o cache de SELIC diária: {e}")
    
    logger.debug("Retornando cache de SELIC diária vazio")
    return {"conteudo": []}

def save_selic_diaria_cache(data):
    """
    Salva o cache de taxas Selic diárias no arquivo.
    
    Args:
        data (dict): Dados do cache com a chave 'conteudo' contendo uma lista de registros
        
    Returns:
        bool: True se o cache foi salvo com sucesso, False caso contrário
    """
    try:
        logger.debug(f"Salvando cache de SELIC diária no arquivo: {SELIC_DIARIA_CACHE_FILE}")
        
        # Garante que o diretório existe
        os.makedirs(os.path.dirname(SELIC_DIARIA_CACHE_FILE) if os.path.dirname(SELIC_DIARIA_CACHE_FILE) else '.', exist_ok=True)
        
        # Faz backup do cache atual se existir
        if os.path.exists(SELIC_DIARIA_CACHE_FILE):
            os.makedirs(CACHE_BACKUP_DIR, exist_ok=True)
            backup_file = os.path.join(CACHE_BACKUP_DIR, f"selic_diaria_backup_{datetime.now().strftime('%Y%m%d%H%M%S')}.json")
            try:
                import shutil
                shutil.copy2(SELIC_DIARIA_CACHE_FILE, backup_file)
                logger.debug(f"Backup do cache de SELIC diária criado: {backup_file}")
            except Exception as e:
                logger.warning(f"Não foi possível criar backup do cache de SELIC diária: {e}")
        
        # Salva o novo cache
        with open(SELIC_DIARIA_CACHE_FILE, "w") as f:
            json.dump(data, f, indent=2)
        
        num_registros = len(data.get("conteudo", []))
        logger.info(f"Cache de SELIC diária salvo com sucesso: {num_registros} registros")
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar o cache de SELIC diária: {e}")
        return False

def get_cached_selic_diaria(data_str=None):
    """
    Obtém as taxas Selic diárias do cache.
    Se data_str for fornecida, retorna a taxa para essa data específica.
    
    Args:
        data_str (str, optional): Data no formato DD/MM/YYYY para buscar
        
    Returns:
        dict ou list: Taxa específica (dict) ou lista de todas as taxas (list)
    """
    cache = load_selic_diaria_cache()
    conteudo = cache.get("conteudo", [])
    
    if not data_str:
        logger.debug(f"Retornando todas as {len(conteudo)} taxas Selic diárias do cache")
        return conteudo
    
    # Busca pela data específica
    for item in conteudo:
        if item.get("data") == data_str:
            logger.debug(f"Taxa Selic diária encontrada no cache para a data {data_str}: {item}")
            return item
    
    logger.debug(f"Taxa Selic diária não encontrada no cache para a data {data_str}")
    return None

def convert_date_format(date_str, from_format="%Y-%m-%d", to_format="%d/%m/%Y"):
    """
    Converte uma string de data de um formato para outro
    
    Args:
        date_str (str): String de data no formato original
        from_format (str): Formato original da data
        to_format (str): Formato desejado para a data
        
    Returns:
        str: Data no formato desejado
    """
    try:
        dt = datetime.strptime(date_str, from_format)
        return dt.strftime(to_format)
    except Exception as e:
        logger.error(f"Erro ao converter formato de data {date_str}: {e}")
        return date_str

def fetch_selic_diaria(data_inicial, data_final):
    """
    Busca as taxas Selic diárias na API do BCB para um período.
    
    Args:
        data_inicial (str): Data inicial no formato DD/MM/YYYY
        data_final (str): Data final no formato DD/MM/YYYY
        
    Returns:
        dict: Resposta da API com as taxas Selic diárias
    """
    logger.info(f"Buscando taxas Selic diárias para o período de {data_inicial} a {data_final}")
    
    params = {
        "tronco": "estatisticas",
        "guidLista": "323626f4-c92f-46d6-bac7-55bf88f6430b",
        "dataInicial": data_inicial,
        "dataFinal": data_final,
        "serie": "432"
    }
    
    try:
        logger.debug(f"Enviando requisição para {BCB_SELIC_DIARIA_API_URL} com parâmetros: {params}")
        
        # Adiciona delay para não sobrecarregar a API
        time.sleep(1)
        
        response = requests.get(BCB_SELIC_DIARIA_API_URL, params=params)
        logger.debug(f"Status code da resposta: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            num_registros = len(data.get("conteudo", []))
            logger.info(f"Dados recebidos com sucesso: {num_registros} registros")
            return data
        else:
            logger.error(f"Erro na requisição: {response.status_code} - {response.text}")
            return {"conteudo": []}
            
    except Exception as e:
        logger.error(f"Exceção ao buscar taxas Selic diárias: {e}")
        return {"conteudo": []}

def ensure_selic_diaria_in_cache(data_inicial, data_final):
    """
    Verifica se as taxas Selic diárias para o período estão no cache.
    Se não estiverem, busca na API e atualiza o cache.
    
    Args:
        data_inicial (str): Data inicial no formato YYYY-MM-DD
        data_final (str): Data final no formato YYYY-MM-DD
        
    Returns:
        dict: Cache atualizado com as taxas Selic diárias
    """
    logger.info(f"Verificando disponibilidade de taxas Selic diárias para o período de {data_inicial} a {data_final}")
    
    # Converte as datas para o formato da API (DD/MM/YYYY)
    data_inicial_api = convert_date_format(data_inicial, "%Y-%m-%d", "%d/%m/%Y")
    data_final_api = convert_date_format(data_final, "%Y-%m-%d", "%d/%m/%Y")
    
    # Carrega o cache atual
    cache = load_selic_diaria_cache()
    conteudo = cache.get("conteudo", [])
    
    # Converte as datas para objetos date para comparação
    data_inicial_obj = datetime.strptime(data_inicial, "%Y-%m-%d").date()
    data_final_obj = datetime.strptime(data_final, "%Y-%m-%d").date()
    
    # Cria um dicionário com as datas presentes no cache
    datas_cache = {datetime.strptime(item["data"], "%d/%m/%Y").date(): item for item in conteudo}
    
    # Verifica quais datas estão faltando no cache
    datas_faltantes = []
    data_atual = data_inicial_obj
    while data_atual <= data_final_obj:
        if data_atual not in datas_cache:
            datas_faltantes.append(data_atual)
        data_atual += timedelta(days=1)
    
    if not datas_faltantes:
        logger.info(f"Todas as taxas Selic diárias para o período já estão no cache")
        return cache
    
    # Busca as datas faltantes na API
    logger.info(f"Buscando {len(datas_faltantes)} taxas Selic diárias faltantes na API")
    
    # Divide as datas faltantes em lotes para não sobrecarregar a API
    # A API do BCB tem um limite de datas que pode processar de uma vez
    LOTE_SIZE = 90  # 3 meses por vez
    
    lotes = []
    for i in range(0, len(datas_faltantes), LOTE_SIZE):
        lote = datas_faltantes[i:i+LOTE_SIZE]
        lotes.append((lote[0], lote[-1]))
    
    logger.debug(f"Dividindo a busca em {len(lotes)} lotes")
    
    novos_registros = []
    
    for lote_inicio, lote_fim in lotes:
        logger.debug(f"Buscando lote de {lote_inicio} a {lote_fim}")
        
        data_inicio_str = lote_inicio.strftime("%d/%m/%Y")
        data_fim_str = lote_fim.strftime("%d/%m/%Y")
        
        response = fetch_selic_diaria(data_inicio_str, data_fim_str)
        
        if "conteudo" in response and response["conteudo"]:
            logger.debug(f"Lote recebido com {len(response['conteudo'])} registros")
            novos_registros.extend(response["conteudo"])
        else:
            logger.warning(f"Nenhum dado recebido para o lote de {data_inicio_str} a {data_fim_str}")
        
        # Espera um pouco entre as requisições para não sobrecarregar a API
        time.sleep(2)
    
    # Atualiza o cache com os novos registros
    if novos_registros:
        # Cria um dicionário para facilitar a mesclagem, evitando duplicatas
        registros_dict = {item["data"]: item for item in conteudo}
        
        # Adiciona os novos registros
        for registro in novos_registros:
            registros_dict[registro["data"]] = registro
        
        # Converte de volta para lista e ordena por data
        conteudo_atualizado = list(registros_dict.values())
        conteudo_atualizado.sort(key=lambda x: datetime.strptime(x["data"], "%d/%m/%Y"))
        
        # Atualiza o cache
        cache["conteudo"] = conteudo_atualizado
        save_selic_diaria_cache(cache)
        
        logger.info(f"Cache atualizado com {len(novos_registros)} novos registros")
    else:
        logger.info("Nenhum novo registro para adicionar ao cache")
    
    return cache

def get_selic_diaria(data_str):
    """
    Obtém a taxa Selic diária para uma data específica.
    Se não estiver no cache, busca na API.
    
    Args:
        data_str (str): Data no formato YYYY-MM-DD
        
    Returns:
        dict: Taxa Selic diária para a data
    """
    # Converte a data para o formato do cache (DD/MM/YYYY)
    data_cache = convert_date_format(data_str, "%Y-%m-%d", "%d/%m/%Y")
    
    # Verifica se a data está no cache
    taxa = get_cached_selic_diaria(data_cache)
    
    if taxa:
        logger.info(f"Taxa Selic diária para {data_str} encontrada no cache: {taxa}")
        return taxa
    
    # Se não estiver no cache, busca na API
    logger.info(f"Taxa Selic diária para {data_str} não encontrada no cache, buscando na API")
    
    # Garante que a data está no cache
    ensure_selic_diaria_in_cache(data_str, data_str)
    
    # Tenta novamente do cache
    taxa = get_cached_selic_diaria(data_cache)
    
    if taxa:
        logger.info(f"Taxa Selic diária para {data_str} encontrada após atualização do cache: {taxa}")
        return taxa
    else:
        logger.warning(f"Taxa Selic diária para {data_str} não encontrada mesmo após busca na API")
        # Retorna um registro vazio para a data
        return {"data": data_cache, "valor": "0", "motivo": "Não disponível"} 