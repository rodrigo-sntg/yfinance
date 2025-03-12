import os
import json
import glob
from datetime import datetime, timedelta
from app.config import CACHE_FILE, HOLIDAYS_CACHE_FILE, CACHE_BACKUP_DIR
from app.logger import logger

def load_cache():
    """
    Carrega o cache de taxas Selic do arquivo.
    Se o arquivo não existir ou ocorrer um erro, retorna um cache vazio.
    
    Returns:
        dict: Dados do cache com a chave 'registros' contendo uma lista de registros
    """
    try:
        if os.path.exists(CACHE_FILE):
            logger.debug(f"Carregando cache do arquivo: {CACHE_FILE}")
            with open(CACHE_FILE, "r") as f:
                try:
                    cache = json.load(f)
                    num_registros = len(cache.get("registros", []))
                    logger.debug(f"Cache carregado com sucesso: {num_registros} registros encontrados")
                    return cache
                except json.JSONDecodeError as e:
                    logger.error(f"Erro ao decodificar o arquivo de cache: {e}")
                    logger.warning("Criando um novo cache vazio devido a erro no arquivo existente")
                    # Faz backup do arquivo de cache corrompido
                    os.makedirs(CACHE_BACKUP_DIR, exist_ok=True)
                    backup_file = os.path.join(CACHE_BACKUP_DIR, f"selic_corrupto_{datetime.now().strftime('%Y%m%d%H%M%S')}.json")
                    try:
                        os.rename(CACHE_FILE, backup_file)
                        logger.info(f"Backup do cache corrompido criado: {backup_file}")
                    except Exception as e:
                        logger.error(f"Não foi possível criar backup do cache corrompido: {e}")
        else:
            logger.info(f"Arquivo de cache não encontrado: {CACHE_FILE}")
    except Exception as e:
        logger.error(f"Erro ao tentar carregar o cache: {e}")
    
    logger.debug("Retornando cache vazio")
    return {"registros": []}

def clean_old_backups(max_days=30):
    """
    Remove backups antigos, mantendo apenas os últimos 'max_days' dias.
    
    Args:
        max_days (int): Número máximo de dias para manter backups
        
    Returns:
        int: Número de arquivos removidos
    """
    if not os.path.exists(CACHE_BACKUP_DIR):
        return 0
        
    # Data limite para manter backups
    data_limite = (datetime.now() - timedelta(days=max_days)).strftime('%Y%m%d')
    
    # Padrões para arquivos de backup
    padroes = [
        os.path.join(CACHE_BACKUP_DIR, "selic_backup_*.json"),
        os.path.join(CACHE_BACKUP_DIR, "feriados_backup_*.json")
    ]
    
    arquivos_removidos = 0
    
    for padrao in padroes:
        # Lista todos os arquivos de backup
        arquivos = glob.glob(padrao)
        
        for arquivo in arquivos:
            # Extrai a data do nome do arquivo (formato: backup_YYYYMMDD.json)
            try:
                nome_arquivo = os.path.basename(arquivo)
                # Extrai a data no formato YYYYMMDD
                data_arquivo = nome_arquivo.split('_')[2].split('.')[0]
                
                # Remove arquivo se for mais antigo que a data limite
                if data_arquivo < data_limite:
                    os.remove(arquivo)
                    logger.debug(f"Backup antigo removido: {arquivo}")
                    arquivos_removidos += 1
            except Exception as e:
                logger.warning(f"Erro ao processar arquivo de backup para limpeza: {arquivo} - {e}")
    
    if arquivos_removidos > 0:
        logger.info(f"Limpeza de backups concluída: {arquivos_removidos} arquivos antigos removidos")
    
    return arquivos_removidos

def save_cache(data):
    """
    Salva os dados do cache em um arquivo JSON e cria um backup diário.
    Verifica se os dados são diferentes antes de salvar para evitar atualizações desnecessárias.
    
    Args:
        data (dict): Dados do cache com a chave 'registros' contendo uma lista de registros
    
    Returns:
        bool: True se salvou com sucesso, False caso contrário
    """
    try:
        # Verifica se há dados para salvar
        registros = data.get("registros", [])
        if not registros:
            logger.warning("Tentativa de salvar cache sem registros")
            return False
            
        # Verifica se o arquivo atual existe
        if os.path.exists(CACHE_FILE):
            # Carrega o cache atual para comparar
            try:
                with open(CACHE_FILE, 'r') as f:
                    cache_atual = json.load(f)
                    registros_atuais = cache_atual.get("registros", [])
                    
                    # Verifica se o número de registros é o mesmo
                    if len(registros) == len(registros_atuais):
                        # Mapeia os registros atuais por data para comparação rápida
                        registros_atuais_por_data = {}
                        for reg in registros_atuais:
                            data_str = reg.get("dataCotacao")
                            if data_str:
                                registros_atuais_por_data[data_str] = reg
                        
                        # Verifica se todos os registros novos já existem e são idênticos
                        registros_diferentes = False
                        for reg in registros:
                            data_str = reg.get("dataCotacao")
                            if data_str not in registros_atuais_por_data:
                                registros_diferentes = True
                                break
                            # Verifica se o fator diário é diferente
                            if reg.get("fatorDiario") != registros_atuais_por_data[data_str].get("fatorDiario"):
                                registros_diferentes = True
                                break
                        
                        if not registros_diferentes:
                            logger.info("Nenhuma alteração detectada no cache, pulando salvamento")
                            return True
            except Exception as e:
                logger.warning(f"Erro ao comparar cache atual, prosseguindo com salvamento: {e}")
        
        # Cria um arquivo temporário primeiro para evitar corromper o cache em caso de erro
        temp_file = f"{CACHE_FILE}.tmp"
        with open(temp_file, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
        # Se chegou até aqui, o arquivo temporário foi criado com sucesso
        # Agora substituímos o arquivo original
        if os.path.exists(CACHE_FILE):
            # Cria diretório de backup se não existir
            os.makedirs(CACHE_BACKUP_DIR, exist_ok=True)
            
            # Cria backup diário (apenas um backup por dia)
            data_atual = datetime.now().strftime('%Y%m%d')
            backup_diario = os.path.join(CACHE_BACKUP_DIR, f"selic_backup_{data_atual}.json")
            
            # Verifica se já existe um backup para hoje
            if not os.path.exists(backup_diario):
                try:
                    # Cria uma cópia do arquivo atual como backup diário
                    with open(CACHE_FILE, 'r') as orig_file, open(backup_diario, 'w') as backup_file:
                        backup_file.write(orig_file.read())
                    logger.info(f"Backup diário do cache criado: {backup_diario}")
                    
                    # Limpa backups antigos a cada novo backup diário
                    clean_old_backups()
                except Exception as e:
                    logger.warning(f"Não foi possível criar backup diário do cache: {e}")
            else:
                logger.debug(f"Backup diário já existe para hoje: {backup_diario}")
        
        # Agora move o arquivo temporário para o lugar do original
        os.replace(temp_file, CACHE_FILE)
        
        num_registros = len(data.get("registros", []))
        logger.info(f"Cache atualizado com sucesso: {num_registros} registros salvos")
        return True
    except IOError as e:
        logger.error(f"Erro de I/O ao salvar cache: {e}")
    except Exception as e:
        logger.error(f"Erro desconhecido ao salvar cache: {e}")
    
    logger.warning("Falha ao salvar o cache atualizado")
    return False

def get_cached_rates():
    """
    Carrega as taxas Selic do cache e as organiza em um dicionário.
    
    Returns:
        tuple: (taxas_diarias, registros)
            - taxas_diarias: dicionário com data como chave e fator diário como valor
            - registros: lista de registros de taxas Selic originais do cache
    """
    logger.debug("Carregando taxas Selic do cache")
    try:
        cache = load_cache()
        registros = cache.get("registros", [])
        logger.debug(f"Cache carregado com {len(registros)} registros")
        
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
                logger.warning(f"Erro ao processar registro de taxa: {e}. Registro: {registro}")
            except TypeError as e:
                registros_com_erro += 1
                logger.warning(f"Erro de tipo ao processar registro: {e}. Registro: {registro}")
            except Exception as e:
                registros_com_erro += 1
                logger.warning(f"Erro desconhecido ao processar registro: {e}")
        
        if registros_com_erro > 0:
            logger.warning(f"{registros_com_erro} registros com erro foram ignorados ao carregar o cache")
        
        logger.debug(f"Cache processado: {registros_processados} taxas diárias válidas carregadas")
        return taxas_diarias, registros
    except Exception as e:
        logger.error(f"Erro ao carregar cache de taxas: {e}")
        return {}, []

def load_holidays_cache():
    """
    Carrega o cache de feriados do arquivo.
    Se o arquivo não existir ou ocorrer um erro, retorna um cache vazio.
    
    Returns:
        dict: Dados do cache com anos como chaves e listas de feriados como valores
    """
    try:
        if os.path.exists(HOLIDAYS_CACHE_FILE):
            logger.debug(f"Carregando cache de feriados do arquivo: {HOLIDAYS_CACHE_FILE}")
            with open(HOLIDAYS_CACHE_FILE, "r") as f:
                try:
                    cache = json.load(f)
                    num_anos = len(cache.keys())
                    logger.debug(f"Cache de feriados carregado com sucesso: {num_anos} anos encontrados")
                    return cache
                except json.JSONDecodeError as e:
                    logger.error(f"Erro ao decodificar o arquivo de cache de feriados: {e}")
                    logger.warning("Criando um novo cache de feriados vazio devido a erro no arquivo existente")
                    # Faz backup do arquivo de cache corrompido
                    os.makedirs(CACHE_BACKUP_DIR, exist_ok=True)
                    backup_file = os.path.join(CACHE_BACKUP_DIR, f"feriados_corrupto_{datetime.now().strftime('%Y%m%d%H%M%S')}.json")
                    try:
                        os.rename(HOLIDAYS_CACHE_FILE, backup_file)
                        logger.info(f"Backup do cache de feriados corrompido criado: {backup_file}")
                    except Exception as e:
                        logger.error(f"Não foi possível criar backup do cache de feriados corrompido: {e}")
        else:
            logger.info(f"Arquivo de cache de feriados não encontrado: {HOLIDAYS_CACHE_FILE}")
    except Exception as e:
        logger.error(f"Erro ao tentar carregar o cache de feriados: {e}")
    
    logger.debug("Retornando cache de feriados vazio")
    return {}

def save_holidays_cache(data):
    """
    Salva os dados do cache de feriados em um arquivo JSON e cria um backup diário.
    
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
            # Cria diretório de backup se não existir
            os.makedirs(CACHE_BACKUP_DIR, exist_ok=True)
            
            # Cria backup diário (apenas um backup por dia)
            data_atual = datetime.now().strftime('%Y%m%d')
            backup_diario = os.path.join(CACHE_BACKUP_DIR, f"feriados_backup_{data_atual}.json")
            
            # Verifica se já existe um backup para hoje
            if not os.path.exists(backup_diario):
                try:
                    # Cria uma cópia do arquivo atual como backup diário
                    with open(HOLIDAYS_CACHE_FILE, 'r') as orig_file, open(backup_diario, 'w') as backup_file:
                        backup_file.write(orig_file.read())
                    logger.info(f"Backup diário do cache de feriados criado: {backup_diario}")
                    
                    # Limpa backups antigos a cada novo backup diário
                    clean_old_backups()
                except Exception as e:
                    logger.warning(f"Não foi possível criar backup diário do cache de feriados: {e}")
            else:
                logger.debug(f"Backup diário do cache de feriados já existe para hoje: {backup_diario}")
        
        # Agora move o arquivo temporário para o lugar do original
        os.replace(temp_file, HOLIDAYS_CACHE_FILE)
        
        num_anos = len(data.keys())
        logger.info(f"Cache de feriados atualizado com sucesso: {num_anos} anos salvos")
        return True
    except IOError as e:
        logger.error(f"Erro de I/O ao salvar cache de feriados: {e}")
    except Exception as e:
        logger.error(f"Erro desconhecido ao salvar cache de feriados: {e}")
    
    logger.warning("Falha ao salvar o cache de feriados atualizado")
    return False 

def update_cache_with_new_rate(new_rate):
    """
    Atualiza o cache com uma nova taxa SELIC.

    Se já existir um registro para a data indicada em new_rate,
    o registro é atualizado caso os valores sejam diferentes;
    caso contrário, o novo registro é adicionado ao cache.
    Ao final, os registros são ordenados por data (ascendente).

    Args:
        new_rate (dict): Dicionário contendo os dados da taxa, devendo ter ao menos a chave "dataCotacao"
                         (formato "dd/mm/YYYY"), "fatorDiario", "isBusinessDay" e "reason" (opcional).

    Returns:
        bool: True se o cache foi atualizado (ou se não houve alteração necessária), False em caso de erro.
    """
    try:
        cache = load_cache()
        registros = cache.get("registros", [])
        data_nova = new_rate.get("dataCotacao")
        if not data_nova:
            logger.error("A nova taxa não possui a chave 'dataCotacao'.")
            return False

        updated = False
        found = False

        # Procura por um registro existente para a mesma data
        for idx, reg in enumerate(registros):
            if reg.get("dataCotacao") == data_nova:
                found = True
                # Atualiza se houver diferença em algum campo importante
                if (reg.get("fatorDiario") != new_rate.get("fatorDiario") or
                    reg.get("isBusinessDay") != new_rate.get("isBusinessDay") or
                    reg.get("reason") != new_rate.get("reason")):
                    registros[idx] = new_rate
                    updated = True
                    logger.info(f"Registro para {data_nova} atualizado no cache.")
                else:
                    logger.info(f"Registro para {data_nova} já existe com os mesmos valores. Nenhuma atualização realizada.")
                break

        # Se não encontrou, adiciona o novo registro
        if not found:
            registros.append(new_rate)
            updated = True
            logger.info(f"Novo registro para {data_nova} adicionado ao cache.")

        # Ordena os registros pela data (formato "dd/mm/YYYY")
        try:
            registros.sort(key=lambda r: datetime.strptime(r.get("dataCotacao"), '%d/%m/%Y'))
            logger.debug("Registros ordenados com sucesso.")
        except Exception as e:
            logger.error(f"Erro ao ordenar os registros: {e}")

        # Atualiza o cache e salva se houve alteração
        if updated:
            cache["registros"] = registros
            if save_cache(cache):
                logger.info("Cache salvo com sucesso após atualização.")
                return True
            else:
                logger.error("Falha ao salvar o cache após atualização.")
                return False
        else:
            logger.info("Nenhuma alteração realizada no cache.")
            return True
    except Exception as e:
        logger.error(f"Erro ao atualizar o cache com a nova taxa: {e}")
        return False
