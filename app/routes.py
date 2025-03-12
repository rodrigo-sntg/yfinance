from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
import json

from app.utils import parse_date, safe_float
from app.holidays import is_business_day, get_holidays_for_year
from app.cache import get_cached_rates, save_cache
from app.selic import ensure_rates_in_cache, ensure_non_business_day_in_cache
from app.investimento import calcular_rendimento, analisar_investimento
from app.logger import logger

# Cria o blueprint para as rotas
api_bp = Blueprint('api', __name__)

@api_bp.route('/selic/apurada', methods=['GET'])
def get_selic_apurada():
    """
    Endpoint para buscar a taxa Selic apurada para uma data específica
    
    Parâmetros:
      - data: Data para verificação (YYYY-MM-DD)
    """
    # Log da requisição
    ip_origem = request.remote_addr
    logger.info(f"Requisição de taxa Selic apurada recebida de {ip_origem}")
    
    requested_date = request.args.get('data')
    logger.info(f"Parâmetro recebido: data={requested_date}")
    
    if not requested_date:
        # Se não for informado, usa o dia anterior
        requested_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        logger.info(f"Data não informada, usando data padrão: {requested_date}")
        
    try:
        target_date = datetime.strptime(requested_date, '%Y-%m-%d').date()
        logger.debug(f"Data convertida: {target_date}")
    except ValueError:
        erro_msg = "Formato de data inválido. Use YYYY-MM-DD."
        logger.warning(f"Erro de validação: {erro_msg} Valor recebido: {requested_date}")
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
            logger.info(f"Data solicitada {requested_date} é um final de semana.")
        else:
            logger.info(f"Data solicitada {requested_date} é um feriado: {nome_feriado}.")
    
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
        foi_adicionado, _, _ = ensure_non_business_day_in_cache(target_date, taxas_diarias, registros_unicos, datas_registradas)
        if foi_adicionado:
            cache_updated = True
    
    # Se atualizamos o cache, salvamos
    if cache_updated:
        all_registros = registros_originais.copy()
        all_registros.extend(registros_unicos)
        save_cache({"registros": all_registros})
        if eh_feriado:
            logger.info(f"Cache atualizado com feriado: {target_date.strftime('%Y-%m-%d')} - {nome_feriado}")
        else:
            logger.info(f"Cache atualizado com dia não útil: {target_date.strftime('%Y-%m-%d')}")
    
    if target_date in taxas_diarias:
        # Taxa encontrada no cache
        fator_diario = taxas_diarias[target_date]
        
        # Se o dia não é útil mas temos uma taxa > 0, algo pode estar errado
        # mas respeitamos o que está no cache 
        if not dia_util and fator_diario > 0:
            logger.warning(f"Data {requested_date} é um dia não útil mas tem taxa > 0 no cache: {fator_diario}")
        
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
            logger.info(f"Feriado {requested_date} ({nome_feriado}) não encontrado em cache. Retornando taxa 0.")
        else:
            logger.info(f"Dia não útil {requested_date} não encontrado em cache. Retornando taxa 0.")
        
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
    logger.info(f"Taxa para dia útil {requested_date} não encontrada no cache. Buscando na API.")
    
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
        logger.warning(f"Erro: {erro_msg} Data: {requested_date}")
        return jsonify({"error": erro_msg}), 404

@api_bp.route('/investimento', methods=['GET'])
def investimento_endpoint():
    """
    Calcula o valor atualizado de um investimento com base na Selic diária,
    incluindo impostos e taxas administrativas.
    
    Parâmetros:
      - data: data de início do investimento (YYYY-MM-DD)
      - valor: valor investido inicial (float)
      - data_final: data final do investimento (opcional, padrão é o dia anterior à data atual)
      - taxa_admin: taxa de administração anual em % (opcional, padrão é 0)
      - taxa_custodia: taxa de custódia anual em % (opcional, padrão é 0)
      - incluir_impostos: se deve incluir cálculo de IR e IOF (opcional, padrão é true)
    """
    # Log da requisição recebida
    ip_origem = request.remote_addr
    logger.info(f"Requisição de cálculo de investimento recebida de {ip_origem}")
    
    data_inicial_str = request.args.get('data')
    valor_investido_str = request.args.get('valor')
    data_final_str = request.args.get('data_final')
    
    # Novos parâmetros para impostos e taxas
    taxa_admin_str = request.args.get('taxa_admin', '0')
    taxa_custodia_str = request.args.get('taxa_custodia', '0')
    incluir_impostos_str = request.args.get('incluir_impostos', 'true')
    
    logger.info(f"Parâmetros recebidos: data={data_inicial_str}, valor={valor_investido_str}, data_final={data_final_str}, "
                f"taxa_admin={taxa_admin_str}, taxa_custodia={taxa_custodia_str}, incluir_impostos={incluir_impostos_str}")
    
    if not data_inicial_str or not valor_investido_str:
        erro_msg = "Os parâmetros 'data' e 'valor' são obrigatórios."
        logger.warning(f"Requisição inválida: {erro_msg}")
        return jsonify({"error": erro_msg}), 400

    # Valida a data inicial
    data_inicial = parse_date(data_inicial_str)
    if not data_inicial:
        erro_msg = "Formato de data inicial inválido. Use YYYY-MM-DD."
        logger.warning(f"Erro de validação: {erro_msg} Valor recebido: {data_inicial_str}")
        return jsonify({"error": erro_msg}), 400

    # Valida o valor investido
    valor_investido = safe_float(valor_investido_str)
    if valor_investido is None:
        erro_msg = "Valor investido deve ser numérico."
        logger.warning(f"Erro de validação: {erro_msg} Valor recebido: {valor_investido_str}")
        return jsonify({"error": erro_msg}), 400
        
    # Valida a taxa de administração
    taxa_admin = safe_float(taxa_admin_str)
    if taxa_admin is None:
        erro_msg = "Taxa de administração deve ser numérica."
        logger.warning(f"Erro de validação: {erro_msg} Valor recebido: {taxa_admin_str}")
        return jsonify({"error": erro_msg}), 400
        
    # Valida a taxa de custódia
    taxa_custodia = safe_float(taxa_custodia_str)
    if taxa_custodia is None:
        erro_msg = "Taxa de custódia deve ser numérica."
        logger.warning(f"Erro de validação: {erro_msg} Valor recebido: {taxa_custodia_str}")
        return jsonify({"error": erro_msg}), 400
        
    # Determina se deve incluir impostos
    incluir_impostos = incluir_impostos_str.lower() in ['true', 't', '1', 'sim', 's', 'yes', 'y']

    # Define a data final
    data_final = None
    if data_final_str:
        data_final = parse_date(data_final_str)
        if not data_final:
            erro_msg = "Formato de data final inválido. Use YYYY-MM-DD."
            logger.warning(f"Erro de validação: {erro_msg} Valor recebido: {data_final_str}")
            return jsonify({"error": erro_msg}), 400
    else:
        # Se não fornecida, usa o dia anterior à data atual
        data_final = (datetime.now() - timedelta(days=1)).date()
        
    if data_inicial > data_final:
        erro_msg = "A data de início deve ser anterior à data final."
        logger.warning(f"Erro de validação: {erro_msg} Data inicial: {data_inicial}, Data final: {data_final}")
        return jsonify({"error": erro_msg}), 400

    # Calcula o investimento com os novos parâmetros
    resultado = calcular_rendimento(
        data_inicial, 
        valor_investido, 
        data_final,
        taxa_admin=taxa_admin, 
        taxa_custodia=taxa_custodia, 
        incluir_impostos=incluir_impostos
    )
        
    logger.info(f"Investimento calculado: valor final bruto R$ {resultado.get('valor_final_bruto', 0)}, "
                f"valor final líquido R$ {resultado.get('valor_final_liquido', 0)}, "
                f"rendimento líquido R$ {resultado.get('rendimento_liquido', 0)}")
    return jsonify(resultado)

@api_bp.route('/investimento/analise', methods=['GET'])
def analisar_investimento_endpoint():
    """
    Realiza uma análise detalhada de investimento com estatísticas sobre dias úteis e não úteis.
    
    Parâmetros:
      - data: data de início do investimento (YYYY-MM-DD)
      - valor: valor investido inicial (float)
      - data_final: data final do investimento (opcional)
      - detalhar: se deve incluir detalhes diários (opcional, True/False)
    """
    # Log da requisição recebida
    ip_origem = request.remote_addr
    logger.info(f"Requisição de análise de investimento recebida de {ip_origem}")
    
    data_inicial_str = request.args.get('data')
    valor_investido_str = request.args.get('valor')
    data_final_str = request.args.get('data_final')
    detalhar = request.args.get('detalhar', 'false').lower() == 'true'
    
    logger.info(f"Parâmetros recebidos: data={data_inicial_str}, valor={valor_investido_str}, data_final={data_final_str}, detalhar={detalhar}")
    
    if not data_inicial_str or not valor_investido_str:
        erro_msg = "Os parâmetros 'data' e 'valor' são obrigatórios."
        logger.warning(f"Requisição inválida: {erro_msg}")
        return jsonify({"error": erro_msg}), 400

    # Valida a data inicial
    data_inicial = parse_date(data_inicial_str)
    if not data_inicial:
        erro_msg = "Formato de data inicial inválido. Use YYYY-MM-DD."
        logger.warning(f"Erro de validação: {erro_msg} Valor recebido: {data_inicial_str}")
        return jsonify({"error": erro_msg}), 400

    # Valida o valor investido
    valor_investido = safe_float(valor_investido_str)
    if valor_investido is None:
        erro_msg = "Valor investido deve ser numérico."
        logger.warning(f"Erro de validação: {erro_msg} Valor recebido: {valor_investido_str}")
        return jsonify({"error": erro_msg}), 400

    # Define a data final
    data_final = None
    if data_final_str:
        data_final = parse_date(data_final_str)
        if not data_final:
            erro_msg = "Formato de data final inválido. Use YYYY-MM-DD."
            logger.warning(f"Erro de validação: {erro_msg} Valor recebido: {data_final_str}")
            return jsonify({"error": erro_msg}), 400
    
    # Analisa o investimento
    resultado, dias_com_detalhes = analisar_investimento(data_inicial, valor_investido, data_final)
    
    # Incluir detalhes dia a dia se solicitado
    if detalhar:
        resultado["detalhes_diarios"] = dias_com_detalhes
    
    logger.info(f"Análise de investimento concluída: valor final R$ {resultado['dados_investimento']['valor_final']}")
    return jsonify(resultado)

@api_bp.route('/dia-util', methods=['GET'])
def verificar_dia_util():
    """
    Verifica se uma data é um dia útil (não é final de semana ou feriado).
    
    Parâmetros:
      - data: Data para verificação (YYYY-MM-DD)
    """
    # Log da requisição recebida
    ip_origem = request.remote_addr
    logger.info(f"Requisição de verificação de dia útil recebida de {ip_origem}")
    
    requested_date = request.args.get('data')
    logger.info(f"Parâmetro recebido: data={requested_date}")
    
    if not requested_date:
        # Se não for informado, usa o dia atual
        requested_date = datetime.now().strftime('%Y-%m-%d')
        logger.info(f"Data não informada, usando data atual: {requested_date}")
        
    try:
        data = datetime.strptime(requested_date, '%Y-%m-%d').date()
        logger.debug(f"Data convertida: {data}")
    except ValueError:
        erro_msg = "Formato de data inválido. Use YYYY-MM-DD."
        logger.warning(f"Erro de validação: {erro_msg} Valor recebido: {requested_date}")
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
        adicionar_ao_cache, fator, _ = ensure_non_business_day_in_cache(data, taxas_diarias, registros_unicos, datas_registradas)
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
                    logger.warning(f"Data {data.strftime('%Y-%m-%d')} deveria ser dia útil mas tem fator 0. Possível feriado não cadastrado.")
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
        logger.info(f"Cache atualizado com dia não útil: {data.strftime('%Y-%m-%d')}")
    
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
    
    logger.info(f"Resultado da verificação de dia útil: {json.dumps(resultado, default=str)}")
    return jsonify(resultado)

@api_bp.route('/ping')
def healthcheck():
    """
    Endpoint para verificação de saúde da API
    """
    return jsonify({"status": "ok", "message": "Service is running"}), 200 