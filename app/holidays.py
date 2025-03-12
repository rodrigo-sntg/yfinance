import requests
from datetime import timedelta
from app.config import BRASIL_API_HOLIDAYS_URL
from app.cache import load_holidays_cache, save_holidays_cache
from app.logger import logger

def fetch_holidays_for_year(year):
    """
    Busca os feriados nacionais para um ano específico na API Brasil.
    
    Args:
        year (int): Ano para buscar os feriados
        
    Returns:
        list: Lista de feriados no formato {'date': 'YYYY-MM-DD', 'name': 'Nome do Feriado', 'type': 'tipo'}
              ou lista vazia em caso de erro
    """
    logger.info(f"Buscando feriados para o ano {year} na API Brasil")
    url = BRASIL_API_HOLIDAYS_URL.format(year=year)
    
    try:
        logger.debug(f"Enviando requisição para {url}")
        response = requests.get(url)
        
        logger.debug(f"Status code da resposta: {response.status_code}")
        
        if response.status_code == 200:
            holidays = response.json()
            logger.info(f"Feriados para {year} obtidos com sucesso: {len(holidays)} feriados encontrados")
            return holidays
        else:
            logger.error(f"Falha na requisição à API Brasil. Status code: {response.status_code}")
            if response.status_code != 404:  # Evita logar corpo de erro 404
                try:
                    error_msg = response.text[:500]  # Limita o tamanho do log
                    logger.error(f"Erro na resposta da API: {error_msg}")
                except Exception:
                    pass
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Erro de conexão ao buscar feriados para {year}: {e}")
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout ao buscar feriados para {year}: {e}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro na requisição ao buscar feriados para {year}: {e}")
    except Exception as e:
        logger.error(f"Erro desconhecido ao buscar feriados para {year}: {e}")
    
    logger.warning(f"Nenhum feriado encontrado para o ano {year}")
    return []

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
        logger.debug(f"Feriados para o ano {year} encontrados no cache")
        return holidays_cache[year_str]
    
    # Se não temos no cache, busca na API
    logger.info(f"Feriados para o ano {year} não encontrados no cache. Buscando na API...")
    holidays = fetch_holidays_for_year(year)
    
    if holidays:
        # Atualiza o cache com os novos feriados
        holidays_cache[year_str] = holidays
        save_holidays_cache(holidays_cache)
        logger.info(f"Cache de feriados atualizado com {len(holidays)} feriados para o ano {year}")
    
    return holidays

def is_holiday(date):
    """
    Verifica se uma data é um feriado nacional.
    
    Args:
        date (datetime.date): Data a ser verificada
        
    Returns:
        tuple: (eh_feriado, nome_feriado) onde:
            - eh_feriado (bool): True se for feriado, False caso contrário
            - nome_feriado (str or None): Nome do feriado ou None se não for feriado
    """
    # Obtém os feriados para o ano da data
    year = date.year
    date_str = date.strftime('%Y-%m-%d')  # Este é o formato usado no cache de feriados
    date_log_format = date.strftime('%d/%m/%Y')
    
    logger.info(f"Verificando se {date_log_format} é feriado... (formato ISO: {date_str})")
    
    # Obter diretamente do cache para evitar conversões desnecessárias
    holidays_cache = load_holidays_cache()
    year_str = str(year)
    
    # Verificar diretamente no cache de feriados
    if year_str in holidays_cache:
        for holiday in holidays_cache[year_str]:
            holiday_date = holiday.get('date')
            if holiday_date == date_str:
                nome_feriado = holiday.get('name')
                logger.info(f"Data {date_log_format} é feriado: {nome_feriado} (encontrado diretamente no cache)")
                return True, nome_feriado
    
    
    # Se não encontrou feriado, retorna False
    logger.debug(f"Data {date_log_format} não é feriado")
    return False, None

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
    eh_feriado, _ = is_holiday(date)
    return not eh_feriado

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
    logger.info(f"Pré-carregando feriados para o período de {start_date} a {end_date}")
    
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
        logger.info(f"Buscando feriados para {len(anos_faltantes)} anos: {anos_faltantes}")
        
        for ano in anos_faltantes:
            holidays = fetch_holidays_for_year(ano)
            if holidays:
                # Log detalhado dos feriados obtidos
                logger.info(f"Obtidos {len(holidays)} feriados para o ano {ano}:")
                semana_santa_encontrada = False
                dia_trabalho_encontrado = False
                
                for holiday in holidays:
                    holiday_date = holiday.get('date')
                    holiday_name = holiday.get('name')
                    logger.info(f"  - {holiday_date}: {holiday_name}")
                    
                    # Verifica especificamente se a Sexta-feira Santa está entre os feriados
                    if 'santa' in holiday_name.lower() or 'paix' in holiday_name.lower():
                        semana_santa_encontrada = True
                        logger.info(f"  => FERIADO DE SEMANA SANTA ENCONTRADO: {holiday_date} - {holiday_name}")
                    
                    # Verifica se o Dia do Trabalho está entre os feriados
                    if 'trabalho' in holiday_name.lower() or ('maio' in holiday_name.lower() and '1' in holiday_name):
                        dia_trabalho_encontrado = True
                        logger.info(f"  => FERIADO DO DIA DO TRABALHO ENCONTRADO: {holiday_date} - {holiday_name}")
                
                # Adiciona feriados importantes que podem estar faltando
                feriados_adicionados = []
                
                # Adiciona Sexta-feira Santa se não estiver presente
                if not semana_santa_encontrada and ano >= 2020:
                    logger.warning(f"A Sexta-feira Santa não foi encontrada nos feriados de {ano}!")
                    
                    # Adicionar Sexta-feira Santa manualmente para anos conhecidos
                    sexta_feira_santa = None
                    if ano == 2020:
                        sexta_feira_santa = "2020-04-10"
                    elif ano == 2021:
                        sexta_feira_santa = "2021-04-02"
                    elif ano == 2022:
                        sexta_feira_santa = "2022-04-15"
                    elif ano == 2023:
                        sexta_feira_santa = "2023-04-07"
                    elif ano == 2024:
                        sexta_feira_santa = "2024-03-29"
                    
                    if sexta_feira_santa:
                        logger.info(f"Adicionando Sexta-feira Santa manualmente para {ano}: {sexta_feira_santa}")
                        holidays.append({
                            'date': sexta_feira_santa,
                            'name': 'Sexta-feira Santa',
                            'type': 'national'
                        })
                        feriados_adicionados.append(f"Sexta-feira Santa ({sexta_feira_santa})")
                
                # Adiciona Dia do Trabalho se não estiver presente
                if not dia_trabalho_encontrado and ano >= 2020:
                    logger.warning(f"O Dia do Trabalho (1/5) não foi encontrado nos feriados de {ano}!")
                    dia_trabalho = f"{ano}-05-01"
                    logger.info(f"Adicionando Dia do Trabalho manualmente para {ano}: {dia_trabalho}")
                    holidays.append({
                        'date': dia_trabalho,
                        'name': 'Dia do Trabalho',
                        'type': 'national'
                    })
                    feriados_adicionados.append(f"Dia do Trabalho ({dia_trabalho})")
                
                if feriados_adicionados:
                    logger.info(f"Feriados adicionados manualmente para {ano}: {', '.join(feriados_adicionados)}")
                
                holidays_cache[str(ano)] = holidays
        
        # Salva o cache atualizado
        save_holidays_cache(holidays_cache)
        logger.info(f"Cache de feriados atualizado com feriados para {len(anos_faltantes)} anos")
    else:
        logger.info(f"Todos os {len(anos)} anos do período já estão no cache de feriados")
        
        # Verificação adicional para garantir que feriados importantes estejam no cache
        for ano in anos:
            ano_str = str(ano)
            if ano_str in holidays_cache:
                holidays = holidays_cache[ano_str]
                semana_santa_encontrada = False
                dia_trabalho_encontrado = False
                
                for holiday in holidays:
                    holiday_name = holiday.get('name', '')
                    holiday_date = holiday.get('date', '')
                    
                    # Verifica Sexta-feira Santa
                    if 'santa' in holiday_name.lower() or 'paix' in holiday_name.lower():
                        semana_santa_encontrada = True
                        logger.info(f"Sexta-feira Santa já em cache para {ano}: {holiday_date} - {holiday_name}")
                    
                    # Verifica Dia do Trabalho
                    if 'trabalho' in holiday_name.lower() or holiday_date == f"{ano}-05-01":
                        dia_trabalho_encontrado = True
                        logger.info(f"Dia do Trabalho já em cache para {ano}: {holiday_date} - {holiday_name}")
                
                # Adiciona feriados importantes se não estiverem presentes
                feriados_adicionados = []
                cache_atualizado = False
                
                # Adiciona Sexta-feira Santa
                if not semana_santa_encontrada and ano >= 2020:
                    logger.warning(f"A Sexta-feira Santa não foi encontrada no cache para {ano}!")
                    
                    # Adicionar Sexta-feira Santa manualmente para anos conhecidos
                    sexta_feira_santa = None
                    if ano == 2020:
                        sexta_feira_santa = "2020-04-10"
                    elif ano == 2021:
                        sexta_feira_santa = "2021-04-02"
                    elif ano == 2022:
                        sexta_feira_santa = "2022-04-15"
                    elif ano == 2023:
                        sexta_feira_santa = "2023-04-07"
                    elif ano == 2024:
                        sexta_feira_santa = "2024-03-29"
                    
                    if sexta_feira_santa:
                        logger.info(f"Adicionando Sexta-feira Santa manualmente para {ano}: {sexta_feira_santa}")
                        holidays.append({
                            'date': sexta_feira_santa,
                            'name': 'Sexta-feira Santa',
                            'type': 'national'
                        })
                        feriados_adicionados.append(f"Sexta-feira Santa ({sexta_feira_santa})")
                        cache_atualizado = True
                        
                # Adiciona Dia do Trabalho
                if not dia_trabalho_encontrado and ano >= 2020:
                    logger.warning(f"O Dia do Trabalho (1/5) não foi encontrado no cache para {ano}!")
                    dia_trabalho = f"{ano}-05-01"
                    logger.info(f"Adicionando Dia do Trabalho manualmente para {ano}: {dia_trabalho}")
                    holidays.append({
                        'date': dia_trabalho,
                        'name': 'Dia do Trabalho',
                        'type': 'national'
                    })
                    feriados_adicionados.append(f"Dia do Trabalho ({dia_trabalho})")
                    cache_atualizado = True
                
                # Atualiza o cache apenas se adicionamos algum feriado
                if cache_atualizado:
                    logger.info(f"Feriados adicionados manualmente para {ano}: {', '.join(feriados_adicionados)}")
                    holidays_cache[ano_str] = holidays
                    save_holidays_cache(holidays_cache)
                    logger.info(f"Cache de feriados atualizado para {ano}")
    
    return holidays_cache 