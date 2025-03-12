import requests
from datetime import datetime, timedelta
import time
from app.config import BCB_API_URL
from app.cache import load_cache, save_cache, get_cached_rates, update_cache_with_new_rate
from app.holidays import is_business_day, preload_holidays_for_period, get_holidays_for_year, is_holiday
from app.logger import logger

def fetch_selic_for_date(date_str):
    """
    Busca a taxa Selic de um dia na API do BC.
    
    Args:
        date_str (str): Data no formato DD/MM/YYYY
    
    Returns:
        dict: Informações da taxa Selic ou None se não encontrada
    """
    logger.info(f"Buscando taxa Selic para a data {date_str} na API do BC")
    payload = {"dataInicial": date_str, "dataFinal": date_str}
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "Accept": "application/json, text/plain, */*"
    }
    try:
        logger.debug(f"Enviando requisição para {BCB_API_URL}")
        response = requests.post(BCB_API_URL, json=payload, headers=headers)
        
        logger.debug(f"Status code da resposta: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if "registros" in data and len(data["registros"]) > 0:
                if "observacoes" in data:
                    # Se há observações, é porque não é um dia útil (pode ter sido ajustado para o próximo dia útil)
                    # Vamos tratar como um dia não útil com taxa zero
                    observacoes = data.get("observacoes", [])
                    obs_texto = "; ".join(observacoes) if isinstance(observacoes, list) else str(observacoes)
                    
                    logger.info(f"Taxa Selic para {date_str} tem observações: {obs_texto}")
                    
                    # Criamos um registro semelhante ao de um feriado ou dia não útil
                    non_business_day = {
                        "dataCotacao": date_str,
                        "fatorDiario": "0",
                        "isBusinessDay": False,
                        "reason": f"API_OBSERVACAO: {obs_texto}"
                    }
                    
                    # Retornamos o registro para que seja adicionado ao cache
                    return non_business_day
                    
                taxa = data["registros"][0]
                logger.info(f"Taxa Selic para {date_str} obtida com sucesso: {taxa.get('fatorDiario')}")
                
                # Adiciona a flag de dia útil ao registro
                taxa["isBusinessDay"] = True
                
                return taxa
            else:
                logger.warning(f"Resposta da API não contém registros para a data {date_str}")
        else:
            logger.error(f"Falha na requisição à API do BC. Status code: {response.status_code}")
            if response.status_code != 404:  # Evita logar corpo de erro 404 que pode ser muito grande
                try:
                    error_msg = response.text[:500]  # Limita o tamanho do log
                    logger.error(f"Erro na resposta da API: {error_msg}")
                except Exception:
                    pass
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Erro de conexão ao buscar taxa Selic para {date_str}: {e}")
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout ao buscar taxa Selic para {date_str}: {e}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro na requisição ao buscar taxa Selic para {date_str}: {e}")
    except Exception as e:
        logger.error(f"Erro desconhecido ao buscar taxa Selic para {date_str}: {e}")
    
    logger.warning(f"Nenhuma taxa Selic encontrada para a data {date_str}")
    return None

def ensure_non_business_day_in_cache(date, taxas_diarias, registros_unicos, datas_registradas):
    """
    Verifica se a data é um dia não útil e, se for, garante que esteja no cache com valor zero.
    
    Args:
        date (datetime.date): Data a ser verificada
        taxas_diarias (dict): Dicionário com as taxas diárias já carregadas
        registros_unicos (list): Lista de registros únicos para o cache
        datas_registradas (dict): Dicionário de datas já registradas no cache (no formato ISO)
        
    Returns:
        tuple: (foi_adicionado, taxa_diaria, motivo)
            - foi_adicionado: True se a data foi adicionada ao cache, False caso contrário
            - taxa_diaria: Valor da taxa diária (0.0 para dias não úteis)
            - motivo: Motivo pelo qual a data não é um dia útil, ou None se for um dia útil
    """
    date_str = date.strftime('%d/%m/%Y')  # Formato de exibição
    date_iso = date.strftime('%Y-%m-%d')  # Formato ISO para comparações
    
    logger.debug(f"Verificando se {date_str} ({date_iso}) é dia não útil...")
    
    # Verificação eficiente: primeiro verifica se a data já está em datas_registradas
    if date_iso in datas_registradas:
        logger.debug(f"Data {date_str} já está registrada em datas_registradas")
        return False, None, None
    
    # Verifica se a data já está no cache usando a chave ISO
    # Verificação mais eficiente do que iterar sobre as chaves do dicionário
    if date in taxas_diarias:
        taxa_existente = taxas_diarias[date]
        logger.debug(f"Data {date_str} já está no cache com taxa {taxa_existente}")
        return False, taxa_existente, None
    
    # Verificação para objetos datetime em taxas_diarias (compatibilidade)
    for dt, taxa in taxas_diarias.items():
        if hasattr(dt, 'strftime') and dt.strftime('%Y-%m-%d') == date_iso:
            logger.debug(f"Data {date_str} já está no cache com taxa {taxa}")
            return False, taxa, None
    
    # Verifica se a data já existe em registros_unicos (para evitar duplicação)
    for registro in registros_unicos:
        try:
            reg_data_str = registro.get("dataCotacao")
            if not reg_data_str:
                continue
                
            # Converte para formato ISO para comparação consistente
            reg_date = datetime.strptime(reg_data_str, '%d/%m/%Y').date()
            reg_date_iso = reg_date.strftime('%Y-%m-%d')
            
            if reg_date_iso == date_iso:
                try:
                    fator = float(registro.get("fatorDiario", "0"))
                    logger.debug(f"Data {date_str} já existe em registros_unicos com taxa {fator}")
                    return False, fator, None
                except (ValueError, TypeError):
                    logger.debug(f"Data {date_str} já existe em registros_unicos mas fator não pôde ser extraído")
                    return False, None, None
        except Exception as e:
            logger.warning(f"Erro ao processar registro em registros_unicos: {e}")
            continue
    
    # Verifica se é final de semana
    eh_final_semana = date.weekday() >= 5
    
    # Log detalhado para depuração
    if eh_final_semana:
        dia_semana = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'][date.weekday()]
        logger.info(f"Data {date_str} é {dia_semana}-feira (weekday={date.weekday()}), identificada como final de semana")
    
    # Se não for final de semana, verifica se é feriado
    eh_feriado = False
    nome_feriado = None
    if not eh_final_semana:
        # Verifica se é feriado
        logger.debug(f"Verificando se {date_str} ({date_iso}) é feriado...")
        eh_feriado, nome_feriado = is_holiday(date)
        logger.info(f"Resultado da verificação para {date_str}: eh_feriado={eh_feriado}, nome_feriado={nome_feriado}")
    
    # Se for final de semana ou feriado, adiciona ao cache com valor zero
    if eh_final_semana or eh_feriado:
        # Define o motivo
        if eh_final_semana:
            dia_semana = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'][date.weekday()]
            reason = f"FINAL_DE_SEMANA: {dia_semana}-feira"
            logger.info(f"Adicionando final de semana {date_str} ao cache com taxa zero")
        else:
            reason = f"FERIADO: {nome_feriado}"
            logger.info(f"Adicionando feriado {date_str} ({nome_feriado}) ao cache com taxa zero")
        
        # Cria registro para o dia não útil
        non_business_day = {
            "dataCotacao": date_str,
            "fatorDiario": "0",
            "isBusinessDay": False,
            "reason": reason
        }
        
        # Adiciona ao dicionário de taxas
        taxas_diarias[date] = 0.0
        
        # Verifica uma última vez que a data não está no cache e nem nos registros
        if date_iso not in datas_registradas:
            # Verifica se a data já foi adicionada a registros_unicos por data ISO
            data_ja_adicionada = False
            for reg in registros_unicos:
                try:
                    reg_data_str = reg.get("dataCotacao")
                    if reg_data_str:
                        reg_date = datetime.strptime(reg_data_str, '%d/%m/%Y').date()
                        reg_date_iso = reg_date.strftime('%Y-%m-%d')
                        if reg_date_iso == date_iso:
                            data_ja_adicionada = True
                            break
                except Exception:
                    continue
            
            if not data_ja_adicionada:
                registros_unicos.append(non_business_day)
                datas_registradas[date_iso] = True
                logger.debug(f"Adicionado com sucesso ao cache: {date_str} ({reason})")
                return True, 0.0, reason
            else:
                logger.debug(f"Data {date_str} já estava em registros_unicos, não adicionada novamente")
        else:
            logger.debug(f"Data {date_str} já estava registrada, não adicionada novamente")
    else:
        logger.debug(f"Data {date_str} não é final de semana nem feriado conhecido")
            
    return False, None, None

def ensure_rates_in_cache(start_date, end_date):
    """
    Garante que todas as taxas diárias estejam no cache para o período especificado,
    realizando deduplicação dos registros existentes.
    
    Args:
        start_date (datetime.date): Data inicial do período
        end_date (datetime.date): Data final do período
        
    Returns:
        dict: Dicionário com as taxas diárias para o período
    """
    # Carrega todas as taxas existentes do cache atual
    taxas_diarias, registros_originais = get_cached_rates()
    logger.info(f"Cache carregado com {len(taxas_diarias)} taxas diárias")

    # Dicionário para rastrear datas por formato ISO (mais eficiente para busca)
    # A chave é a data ISO (YYYY-MM-DD), o valor é a taxa
    taxas_por_data_iso = {}
    
    # Dicionário para mapear datas ISO para objetos datetime.date
    # (para manter compatibilidade com o código existente)
    datas_cache_iso = {}
    
    # Dicionário para rastrear quais datas já estão registradas
    # A chave é a data ISO (YYYY-MM-DD)
    datas_registradas = {}
    
    # Lista de registros únicos (após deduplicação)
    registros_unicos = []
    
    # Primeiro passo: Processar os registros do cache e preencher os dicionários auxiliares
    for registro in registros_originais:
        try:
            data_str = registro.get("dataCotacao")
            if not data_str:
                continue
                
            # Converte para datetime.date para manipulação
            dt = datetime.strptime(data_str, '%d/%m/%Y').date()
            
            # Cria chave ISO para comparações (formato padronizado)
            data_iso = dt.strftime('%Y-%m-%d')
            
            # Armazena a taxa diretamente no dicionário de taxas por data ISO
            try:
                fator_diario = float(registro.get("fatorDiario", "0"))
                taxas_por_data_iso[data_iso] = fator_diario
                taxas_diarias[dt] = fator_diario  # Mantém compatibilidade
                datas_cache_iso[data_iso] = dt    # Mapeia ISO -> datetime
            except (ValueError, TypeError) as e:
                logger.error(f"Erro ao extrair fator diário para {data_str}: {e}")
                continue
                
            # Registra apenas se esta data ainda não foi registrada
            if data_iso not in datas_registradas:
                datas_registradas[data_iso] = True
                registros_unicos.append(registro)
            else:
                logger.debug(f"Registro duplicado descartado para data {data_str}")
        except Exception as e:
            logger.warning(f"Erro ao processar registro do cache: {e}")
    
    logger.debug(f"Após deduplicação: {len(registros_unicos)} registros únicos de {len(registros_originais)} originais")
    logger.info(f"Total de datas únicas no cache: {len(datas_registradas)}")

    # Verificação rápida: se todas as datas necessárias já estão no cache, retornamos imediatamente
    dias_totais = (end_date - start_date).days + 1
    datas_faltantes = []
    
    # Verifica rapidamente se todas as datas estão no cache usando o formato padronizado
    for i in range(dias_totais):
        data = start_date + timedelta(days=i)
        data_iso = data.strftime('%Y-%m-%d')
        
        # Verifica se a data está em taxas_por_data_iso (formato padronizado)
        if data_iso not in taxas_por_data_iso:
            datas_faltantes.append(data)
    
    if not datas_faltantes:
        logger.info(f"Todas as {dias_totais} datas do período já estão no cache. Retornando imediatamente.")
        return taxas_diarias
    else:
        logger.info(f"Faltam {len(datas_faltantes)} datas no cache de um total de {dias_totais} datas necessárias.")

    cache_updated = False
    taxas_buscadas = 0
    dias_nao_uteis = 0
    
    # Log de diagnóstico
    logger.info(f"Verificando taxas no período de {start_date} a {end_date}")
    
    # Pré-carrega todos os feriados para o período
    logger.info("Pré-carregando feriados para o período...")
    holidays_cache = preload_holidays_for_period(start_date, end_date)
    num_feriados = sum(len(holidays_cache.get(str(year), [])) for year in range(start_date.year, end_date.year + 1))
    logger.info(f"Feriados pré-carregados com sucesso: {num_feriados} feriados no total")
    
    # Conjunto auxiliar para armazenar feriados em formato ISO
    holiday_dates_iso = set()
    
    # Extrai e prepara os feriados para verificação rápida
    for year in range(start_date.year, end_date.year + 1):
        year_str = str(year)
        if year_str in holidays_cache:
            for holiday in holidays_cache[year_str]:
                holiday_date = holiday.get('date', '')
                if holiday_date:
                    holiday_dates_iso.add(holiday_date)  # Já está no formato ISO: YYYY-MM-DD
    
    logger.info(f"Total de feriados extraídos para verificação rápida: {len(holiday_dates_iso)}")
    
    # Processa cada data que falta no cache
    datas_novas = []
    for current_date in datas_faltantes:
        current_date_str = current_date.strftime('%d/%m/%Y')  # Formato de exibição
        current_date_iso = current_date.strftime('%Y-%m-%d')  # Formato padronizado para comparações
        
        # Verificação final: confirma que a data não foi adicionada durante o processamento
        if current_date_iso in datas_registradas:
            logger.debug(f"Data {current_date_str} já foi registrada durante o processamento, pulando")
            continue
            
        if current_date_iso in taxas_por_data_iso:
            logger.debug(f"Data {current_date_str} já foi adicionada à taxas_por_data_iso, pulando")
            continue
        
        # Log detalhado para diagnóstico de datas específicas
        if current_date.day in [1, 2, 7, 15, 25]:  # Dias específicos para diagnóstico
            logger.info(f"DIAGNÓSTICO DETALHADO PARA {current_date_str}:")
            logger.info(f"  - Está em taxas_por_data_iso? {current_date_iso in taxas_por_data_iso}")
            logger.info(f"  - Está em datas_registradas? {current_date_iso in datas_registradas}")
            logger.info(f"  - É final de semana? {current_date.weekday() >= 5}")
            logger.info(f"  - Está em holiday_dates_iso? {current_date_iso in holiday_dates_iso}")
        
        
        # Verificação rápida para feriados conhecidos usando o conjunto auxiliar
        if current_date_iso in holiday_dates_iso:
            logger.info(f"Data {current_date_str} encontrada diretamente no conjunto de feriados")
            
            # Determinar o nome do feriado
            nome_feriado = "Feriado Nacional"
            year_str = str(current_date.year)
            for holiday in holidays_cache.get(year_str, []):
                if holiday.get('date') == current_date_iso:
                    nome_feriado = holiday.get('name', "Feriado Nacional")
                    break
            
            # Adiciona ao cache como feriado
            reason = f"FERIADO: {nome_feriado}"
            
            non_business_day = {
                "dataCotacao": current_date_str,
                "fatorDiario": "0",
                "isBusinessDay": False,
                "reason": reason
            }
            
            # Atualiza os dicionários
            taxas_diarias[current_date] = 0.0
            taxas_por_data_iso[current_date_iso] = 0.0
            datas_cache_iso[current_date_iso] = current_date
            
            datas_novas.append(non_business_day)
            datas_registradas[current_date_iso] = True
            cache_updated = True
            dias_nao_uteis += 1
            
            logger.info(f"Feriado {current_date_str} adicionado ao cache: {reason}")
            continue
        
        # Verificação para finais de semana
        if current_date.weekday() >= 5:  # 5=Sábado, 6=Domingo
            logger.info(f"Detectado final de semana: {current_date_str} - Marcando com taxa zero")
            
            # Adiciona ao cache como final de semana
            dia_semana = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'][current_date.weekday()]
            reason = f"FINAL_DE_SEMANA: {dia_semana}-feira"
            
            non_business_day = {
                "dataCotacao": current_date_str,
                "fatorDiario": "0",
                "isBusinessDay": False,
                "reason": reason
            }
            
            # Atualiza os dicionários
            taxas_diarias[current_date] = 0.0
            taxas_por_data_iso[current_date_iso] = 0.0
            datas_cache_iso[current_date_iso] = current_date
            
            datas_novas.append(non_business_day)
            datas_registradas[current_date_iso] = True
            cache_updated = True
            dias_nao_uteis += 1
            
            logger.info(f"Final de semana {current_date_str} adicionado ao cache: {reason}")
            continue
        
            
        # Verificação adicional para feriados utilizando a função is_holiday
        eh_feriado, nome_feriado = is_holiday(current_date)
        if eh_feriado:
            logger.info(f"Data {current_date_str} identificada como feriado ({nome_feriado}) pela função is_holiday")
            reason = f"FERIADO: {nome_feriado}"
            
            non_business_day = {
                "dataCotacao": current_date_str,
                "fatorDiario": "0",
                "isBusinessDay": False,
                "reason": reason
            }
            
            # Atualiza os dicionários
            taxas_diarias[current_date] = 0.0
            taxas_por_data_iso[current_date_iso] = 0.0
            datas_cache_iso[current_date_iso] = current_date
            
            datas_novas.append(non_business_day)
            datas_registradas[current_date_iso] = True
            cache_updated = True
            dias_nao_uteis += 1
            
            logger.info(f"Feriado {current_date_str} adicionado ao cache: {reason}")
            continue
        
        # Se chegou aqui, é um dia útil que ainda não está no cache
        # Verifica mais uma vez se a data já foi registrada (para evitar chamadas duplicadas à API)
        if current_date_iso in taxas_por_data_iso or current_date_iso in datas_registradas:
            logger.info(f"Data {current_date_str} já está registrada, pulando chamada à API")
            continue
        
        # Se uma verificação literal para os registros nos novos registros também
        if any(reg.get("dataCotacao") == current_date_str for reg in datas_novas):
            logger.info(f"Data {current_date_str} já adicionada aos novos registros, pulando chamada à API")
            continue
            
        # Busca a taxa na API
        missing_date_str = current_date_str
        logger.info(f"Taxa para {missing_date_str} não encontrada em cache e é dia útil. Buscando na API...")
        new_rate = fetch_selic_for_date(missing_date_str)
        taxas_buscadas += 1
        
        if new_rate:
            try:
                # Verifica se é um dia não útil (com isBusinessDay=False) retornado pela função fetch_selic_for_date
                if new_rate.get("isBusinessDay") == False:
                    # É um dia não útil (feriado, final de semana ou com observações)
                    logger.info(f"Data {missing_date_str} identificada como dia não útil: {new_rate.get('reason', 'Sem razão especificada')}")
                    
                    # Adiciona ao cache com fator zero
                    taxas_diarias[current_date] = 0.0
                    taxas_por_data_iso[current_date_iso] = 0.0
                    datas_cache_iso[current_date_iso] = current_date
                    
                    datas_novas.append(new_rate)
                    # Atualiza o cache com o dia não útil imediatamente
                    update_cache_with_new_rate(new_rate)
                    datas_registradas[current_date_iso] = True
                    cache_updated = True
                    dias_nao_uteis += 1
                else:
                    # É um dia útil normal com taxa válida
                    fator_diario = float(new_rate.get("fatorDiario"))
                    
                    # Atualiza os dicionários
                    taxas_diarias[current_date] = fator_diario
                    taxas_por_data_iso[current_date_iso] = fator_diario
                    datas_cache_iso[current_date_iso] = current_date
                    
                    datas_novas.append(new_rate)
                    # Atualiza o cache com a nova taxa imediatamente
                    update_cache_with_new_rate(new_rate)
                    datas_registradas[current_date_iso] = True
                    cache_updated = True
                    logger.info(f"Taxa para {missing_date_str} adicionada ao cache: {fator_diario}")
            except Exception as e:
                logger.error(f"Erro ao processar nova taxa para {missing_date_str}: {e}")
        else:
            # Se a API não retornou taxa mas é dia útil, pode ser um feriado
            # ou a API pode estar indisponível
            logger.warning(f"Taxa para {missing_date_str} não disponível na API do BC. Verificando se é um feriado ou problema na API.")
            
            # Verifica se é feriado novamente, com mais detalhes
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
                logger.info(f"Data {missing_date_str} identificada como feriado ({feriado_nome}) após falha na API.")
            else:
                # Verificação adicional para possíveis feriados que não estão na API
                if current_date.weekday() == 4:  # Sexta-feira
                    # Dias próximos à Páscoa, verificar se pode ser Sexta-feira Santa
                    if current_date.month == 4 and (current_date.day >= 5 and current_date.day <= 15):
                        reason = "FERIADO: Sexta-feira Santa (provável)"
                        logger.info(f"Data {missing_date_str} identificada como provável Sexta-feira Santa.")
                    else:
                        reason = "API_UNAVAILABLE"
                        logger.warning(f"Taxa para {missing_date_str} não disponível na API do BC e não é um feriado conhecido. Possível problema na API.")
                else:
                    reason = "API_UNAVAILABLE"
                    logger.warning(f"Taxa para {missing_date_str} não disponível na API do BC e não é um feriado conhecido. Possível problema na API.")
            
            # Assume como dia não útil se não conseguir a taxa
            non_business_day_record = {
                "dataCotacao": missing_date_str,
                "fatorDiario": "0",
                "isBusinessDay": False,
                "reason": reason
            }
            
            # Atualiza os dicionários
            taxas_diarias[current_date] = 0.0
            taxas_por_data_iso[current_date_iso] = 0.0
            datas_cache_iso[current_date_iso] = current_date
            
            datas_novas.append(non_business_day_record)
            datas_registradas[current_date_iso] = True
            cache_updated = True
            dias_nao_uteis += 1
        
    # Só atualiza o cache se houve mudanças
    if cache_updated:
        logger.info(f"Cache atualizado: {taxas_buscadas} novas taxas para dias úteis, {dias_nao_uteis} dias não úteis")
        
        # Verifica se há novos registros realmente para salvar
        if len(datas_novas) == 0:
            logger.info("Nenhum registro novo para adicionar ao cache - cancelando atualização")
            cache_updated = False
            return taxas_diarias
            
        # Cria um dicionário para controle de datas únicas usando o formato padronizado
        datas_unicas = {}
        registros_finais = []
        
        # Processa registros originais
        for registro in registros_unicos:
            try:
                data_str = registro.get("dataCotacao")
                if data_str:
                    # Usa o formato ISO para garantir unicidade
                    data_obj = datetime.strptime(data_str, '%d/%m/%Y').date()
                    data_iso = data_obj.strftime('%Y-%m-%d')
                    
                    if data_iso not in datas_unicas:
                        datas_unicas[data_iso] = True
                        registros_finais.append(registro)
                    else:
                        logger.debug(f"Registro duplicado descartado para data {data_str} (ISO: {data_iso})")
            except Exception as e:
                logger.warning(f"Erro ao processar registro original: {e}")
                continue
                
        # Adiciona os novos registros
        for registro in datas_novas:
            try:
                data_str = registro.get("dataCotacao")
                if data_str:
                    # Usa o formato ISO para garantir unicidade
                    data_obj = datetime.strptime(data_str, '%d/%m/%Y').date()
                    data_iso = data_obj.strftime('%Y-%m-%d')
                    
                    if data_iso not in datas_unicas:
                        datas_unicas[data_iso] = True
                        registros_finais.append(registro)
                    else:
                        logger.debug(f"Novo registro duplicado descartado para data {data_str} (ISO: {data_iso})")
            except Exception as e:
                logger.warning(f"Erro ao processar novo registro: {e}")
                continue
        
        # Registra o número real de registros únicos
        logger.info(f"Total de registros únicos a serem salvos: {len(registros_finais)} (originais: {len(registros_unicos)}, novos: {len(datas_novas)})")
        
        # Ordena os registros por data antes de salvar
        try:
            registros_finais.sort(key=lambda r: datetime.strptime(r.get("dataCotacao", "01/01/2000"), '%d/%m/%Y'))
            logger.info(f"Registros ordenados por data com sucesso")
        except Exception as e:
            logger.error(f"Erro ao ordenar registros por data: {e}")
        
        # Só salva se houver novos registros e registros únicos
        if len(registros_finais) > len(registros_originais):
            save_cache({"registros": registros_finais})
            logger.info(f"Cache atualizado com {len(registros_finais) - len(registros_originais)} novos registros. Total: {len(registros_finais)}")
        else:
            logger.info("Nenhum novo registro para adicionar após eliminação de duplicatas - cancelando atualização")
    else:
        logger.info("Nenhuma nova taxa foi adicionada ao cache")
        
    return taxas_diarias

def calcular_impostos_taxas(valor_investido, fator_composto, dias_totais, taxa_admin=0, taxa_custodia=0, ioftable=None):
    """
    Calcula Imposto de Renda (IR), taxas da corretora e IOF.

    Args:
        valor_investido (float): Valor inicial investido.
        fator_composto (float): Fator de rentabilidade ao longo do período.
        dias_totais (int): Número total de dias da aplicação.
        taxa_admin (float): Taxa de administração anual (%).
        taxa_custodia (float): Taxa de custódia anual (%).
        ioftable (dict): Tabela regressiva do IOF para os primeiros 30 dias.

    Returns:
        dict: Dicionário com valores de impostos, taxas e rendimento líquido.
    """
    # Inicializa a tabela de IOF se não fornecida
    if ioftable is None:
        ioftable = {
            1: 96, 2: 93, 3: 90, 4: 86, 5: 83, 6: 80, 7: 76, 8: 73, 9: 70, 10: 66,
            11: 63, 12: 60, 13: 56, 14: 53, 15: 50, 16: 46, 17: 43, 18: 40, 19: 36,
            20: 33, 21: 30, 22: 26, 23: 23, 24: 20, 25: 16, 26: 13, 27: 10, 28: 6,
            29: 3, 30: 0
        }

    # Cálculo do valor final bruto (antes dos descontos)
    valor_final = valor_investido * fator_composto
    lucro_bruto = valor_final - valor_investido

    # Definição da alíquota de IR conforme prazo da aplicação
    if dias_totais <= 180:
        aliquota_ir = 0.225
    elif dias_totais <= 360:
        aliquota_ir = 0.20
    elif dias_totais <= 720:
        aliquota_ir = 0.175
    else:
        aliquota_ir = 0.15

    # Cálculo do IR sobre o lucro
    imposto_renda = lucro_bruto * aliquota_ir

    # Cálculo da Taxa de Administração (cobrada sobre o capital investido)
    taxa_admin_valor = (valor_investido * (taxa_admin / 100)) * (dias_totais / 365)

    # Cálculo da Taxa de Custódia (se aplicável)
    taxa_custodia_valor = (valor_investido * (taxa_custodia / 100)) * (dias_totais / 365)

    # Cálculo do IOF, se aplicável (regressivo até 30 dias)
    iof = 0
    if dias_totais < 30 and ioftable:
        iof_percentual = ioftable.get(dias_totais, 0)  # Obtém o percentual do IOF na tabela
        iof = lucro_bruto * (iof_percentual / 100)

    # Cálculo do rendimento líquido
    rendimento_liquido = lucro_bruto - imposto_renda - taxa_admin_valor - taxa_custodia_valor - iof
    valor_final_liquido = valor_investido + rendimento_liquido

    # Exibição dos valores calculados
    return {
        "valor_investido": valor_investido,
        "valor_final_bruto": valor_final,
        "valor_final_liquido": valor_final_liquido,
        "lucro_bruto": lucro_bruto,
        "lucro_liquido": rendimento_liquido,
        "imposto_renda": imposto_renda,
        "taxa_admin_valor": taxa_admin_valor,
        "taxa_custodia_valor": taxa_custodia_valor,
        "iof": iof,
        "aliquota_ir": aliquota_ir * 100  # Convertida para percentual
    }

def calcular_rendimento_bruto(valor_inicial, start_date, end_date, taxas_diarias=None):
    """
    Calcula o rendimento bruto de um valor aplicado na taxa SELIC
    para o período especificado.
    
    Args:
        valor_inicial (float): Valor inicial do investimento
        start_date (datetime.date): Data inicial do período
        end_date (datetime.date): Data final do período
        taxas_diarias (dict, optional): Dicionário com as taxas diárias pré-carregadas
            
    Returns:
        tuple: (valor_final, fator_composto, dias_totais, dias_uteis)
            - valor_final (float): Valor final do investimento
            - fator_composto (float): Fator de rentabilidade composto no período
            - dias_totais (int): Número total de dias do período
            - dias_uteis (int): Número de dias úteis do período
    """
    # Se não foram fornecidas taxas, busca no cache
    if taxas_diarias is None:
        taxas_diarias = ensure_rates_in_cache(start_date, end_date)
    
    logger.info(f"Calculando rendimento para o período de {start_date} a {end_date}")
    
    # Inicializa contadores e valores
    dias_totais = 0
    dias_uteis = 0
    fator_composto = 1.0
    valor_final = valor_inicial
    current_date = start_date
    
    # Log dos valores iniciais
    logger.debug(f"Valor inicial: {valor_inicial:.2f}")
    logger.debug(f"Taxas diárias carregadas: {len(taxas_diarias)} datas")
    
    # Processa cada dia do período
    while current_date <= end_date:
        dias_totais += 1
        current_date_iso = current_date.strftime('%Y-%m-%d')
        
        # Verifica se a data existe nas taxas diárias
        taxa_encontrada = False
        for dt in taxas_diarias.keys():
            if hasattr(dt, 'strftime') and dt.strftime('%Y-%m-%d') == current_date_iso:
                taxa_diaria = taxas_diarias[dt]
                taxa_encontrada = True
                
                # Só conta como dia útil se a taxa for maior que zero
                if taxa_diaria > 0:
                    dias_uteis += 1
                    # Aplica o fator diário
                    fator_composto *= taxa_diaria
                    logger.debug(f"Data {current_date}: Taxa diária = {taxa_diaria:.8f}, Fator acumulado = {fator_composto:.8f}")
                else:
                    logger.debug(f"Data {current_date}: Dia não útil (taxa = {taxa_diaria})")
                break
        
        if not taxa_encontrada:
            logger.warning(f"Taxa não encontrada para {current_date}. Assumindo dia não útil.")
        
        current_date += timedelta(days=1)
    
    # Calcula o valor final
    valor_final = valor_inicial * fator_composto
    logger.info(f"Cálculo finalizado: Valor final = {valor_final:.2f}, Fator composto = {fator_composto:.8f}")
    logger.info(f"Período: {dias_totais} dias totais, {dias_uteis} dias úteis")
    
    return valor_final, fator_composto, dias_totais, dias_uteis

def calcular_rendimento_selic(valor_inicial, start_date, end_date, taxa_admin=0, taxa_custodia=0, taxas_diarias=None):
    """
    Calcula o rendimento completo de um valor aplicado na taxa SELIC,
    incluindo impostos e taxas administrativas.
    
    Args:
        valor_inicial (float): Valor inicial do investimento
        start_date (datetime.date): Data inicial do período
        end_date (datetime.date): Data final do período
        taxa_admin (float): Taxa de administração anual (%)
        taxa_custodia (float): Taxa de custódia anual (%)
        taxas_diarias (dict, optional): Dicionário com as taxas diárias pré-carregadas
            
    Returns:
        dict: Dicionário completo com valores brutos, líquidos, impostos e taxas
    """
    # Calcula o rendimento bruto
    valor_final_bruto, fator_composto, dias_totais, dias_uteis = calcular_rendimento_bruto(
        valor_inicial, start_date, end_date, taxas_diarias
    )
    
    # Calcula impostos e taxas
    resultado_completo = calcular_impostos_taxas(
        valor_investido=valor_inicial, 
        fator_composto=fator_composto,
        dias_totais=dias_totais,
        taxa_admin=taxa_admin,
        taxa_custodia=taxa_custodia
    )
    
    # Adiciona informações extras
    resultado_completo.update({
        "dias_totais": dias_totais,
        "dias_uteis": dias_uteis,
        "fator_composto": fator_composto,
        "data_inicial": start_date.strftime('%d/%m/%Y'),
        "data_final": end_date.strftime('%d/%m/%Y'),
        "taxa_admin_percentual": taxa_admin,
        "taxa_custodia_percentual": taxa_custodia
    })
    
    logger.info(f"Rendimento líquido calculado: R$ {resultado_completo['lucro_liquido']:.2f}")
    logger.info(f"Valor final líquido: R$ {resultado_completo['valor_final_liquido']:.2f}")
    
    return resultado_completo 