from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, Optional, Union, List
from flask import request, jsonify

from app.utils import parse_date, safe_float
from app.logger import logger

def validar_data(data_str: str, nome_campo: str, obrigatorio: bool = True) -> Tuple[Optional[datetime.date], Optional[Tuple[Dict[str, str], int]]]:
    """
    Valida uma data no formato YYYY-MM-DD.
    
    Args:
        data_str: String com a data a ser validada
        nome_campo: Nome do campo para mensagens de erro
        obrigatorio: Se o campo é obrigatório
        
    Returns:
        Tupla com (data_validada, erro)
        Se houver erro, data_validada será None e erro conterá a resposta HTTP
    """
    if not data_str:
        if obrigatorio:
            erro_msg = f"O parâmetro '{nome_campo}' é obrigatório."
            logger.warning(f"Erro de validação: {erro_msg}")
            return None, (jsonify({"error": erro_msg}), 400)
        else:
            # Se não for obrigatório e não for fornecido, retorna None sem erro
            return None, None
    
    data = parse_date(data_str)
    if not data:
        erro_msg = f"Formato de data inválido para '{nome_campo}'. Use YYYY-MM-DD."
        logger.warning(f"Erro de validação: {erro_msg} Valor recebido: {data_str}")
        return None, (jsonify({"error": erro_msg}), 400)
    
    return data, None

def validar_numero(valor_str: str, nome_campo: str, obrigatorio: bool = True, min_valor: float = None, max_valor: float = None, 
                  converter_percentual: bool = False) -> Tuple[Optional[float], Optional[Tuple[Dict[str, str], int]]]:
    """
    Valida um valor numérico.
    
    Args:
        valor_str: String com o valor a ser validado
        nome_campo: Nome do campo para mensagens de erro
        obrigatorio: Se o campo é obrigatório
        min_valor: Valor mínimo permitido (opcional)
        max_valor: Valor máximo permitido (opcional)
        converter_percentual: Se deve converter de percentual para decimal (ex: 10.5% -> 0.105)
        
    Returns:
        Tupla com (valor_validado, erro)
        Se houver erro, valor_validado será None e erro conterá a resposta HTTP
    """
    if not valor_str:
        if obrigatorio:
            erro_msg = f"O parâmetro '{nome_campo}' é obrigatório."
            logger.warning(f"Erro de validação: {erro_msg}")
            return None, (jsonify({"error": erro_msg}), 400)
        else:
            # Se não for obrigatório e não for fornecido, usa o valor padrão 0
            return 0.0, None
    
    valor = safe_float(valor_str)
    if valor is None:
        erro_msg = f"O valor de '{nome_campo}' deve ser numérico."
        logger.warning(f"Erro de validação: {erro_msg} Valor recebido: {valor_str}")
        return None, (jsonify({"error": erro_msg}), 400)
    
    if min_valor is not None and valor < min_valor:
        erro_msg = f"O valor de '{nome_campo}' deve ser maior ou igual a {min_valor}."
        logger.warning(f"Erro de validação: {erro_msg} Valor recebido: {valor}")
        return None, (jsonify({"error": erro_msg}), 400)
    
    if max_valor is not None and valor > max_valor:
        erro_msg = f"O valor de '{nome_campo}' deve ser menor ou igual a {max_valor}."
        logger.warning(f"Erro de validação: {erro_msg} Valor recebido: {valor}")
        return None, (jsonify({"error": erro_msg}), 400)
    
    # Converter de percentual para decimal se necessário
    if converter_percentual:
        valor = valor / 100.0
    
    return valor, None

def validar_booleano(valor_str: str, nome_campo: str) -> bool:
    """
    Converte uma string para booleano.
    
    Args:
        valor_str: String a ser convertida
        nome_campo: Nome do campo (para logging)
        
    Returns:
        Valor booleano
    """
    resultado = valor_str.lower() in ['true', 't', '1', 'sim', 's', 'yes', 'y']
    logger.debug(f"Parâmetro '{nome_campo}' convertido: {valor_str} -> {resultado}")
    return resultado

def validar_opcao(valor: str, opcoes: List[str], nome_campo: str, valor_padrao: str = None) -> Tuple[str, Optional[Tuple[Dict[str, str], int]]]:
    """
    Valida se um valor está dentro das opções permitidas.
    
    Args:
        valor: Valor a ser validado
        opcoes: Lista de opções válidas
        nome_campo: Nome do campo para mensagens de erro
        valor_padrao: Valor padrão caso não seja fornecido
        
    Returns:
        Tupla com (valor_validado, erro)
        Se houver erro, erro conterá a resposta HTTP
    """
    if not valor:
        if valor_padrao:
            return valor_padrao, None
        else:
            erro_msg = f"O parâmetro '{nome_campo}' é obrigatório."
            logger.warning(f"Erro de validação: {erro_msg}")
            return None, (jsonify({"error": erro_msg}), 400)
    
    if valor.lower() not in opcoes:
        opcoes_str = "', '".join(opcoes)
        erro_msg = f"Valor inválido para '{nome_campo}'. Valores aceitos: '{opcoes_str}'."
        logger.warning(f"Erro de validação: {erro_msg} Valor recebido: {valor}")
        return None, (jsonify({"error": erro_msg}), 400)
    
    return valor.lower(), None

def validar_parametros_investimento_prefixado() -> Tuple[Dict[str, Any], Optional[Tuple[Dict[str, str], int]]]:
    """
    Valida e processa os parâmetros para cálculo de investimento pré-fixado.
    
    Returns:
        Tupla com (parâmetros_processados, erro_resposta)
        Se houver erro, parâmetros_processados será None e erro_resposta terá a resposta HTTP de erro
        Se validação for bem-sucedida, erro_resposta será None e parâmetros_processados terá os valores processados
    """
    # Obter parâmetros da requisição
    data_inicial_str = request.args.get('data')
    valor_investido_str = request.args.get('valor')
    taxa_anual_str = request.args.get('taxa_anual')
    data_final_str = request.args.get('data_final')
    taxa_admin_str = request.args.get('taxa_admin', '0')
    taxa_custodia_str = request.args.get('taxa_custodia', '0')
    incluir_impostos_str = request.args.get('incluir_impostos', 'true')
    regime_str = request.args.get('regime', 'diario')
    
    # Log dos parâmetros recebidos
    logger.info(f"Parâmetros recebidos: data={data_inicial_str}, valor={valor_investido_str}, " +
                f"taxa_anual={taxa_anual_str}, data_final={data_final_str}, " +
                f"taxa_admin={taxa_admin_str}, taxa_custodia={taxa_custodia_str}, " +
                f"incluir_impostos={incluir_impostos_str}, regime={regime_str}")
    
    # Validar parâmetros usando as funções auxiliares
    data_inicial, erro = validar_data(data_inicial_str, "data", obrigatorio=True)
    if erro:
        return None, erro
    
    valor_investido, erro = validar_numero(valor_investido_str, "valor", obrigatorio=True, min_valor=0)
    if erro:
        return None, erro
    
    taxa_anual, erro = validar_numero(taxa_anual_str, "taxa_anual", obrigatorio=True, min_valor=0, converter_percentual=True)
    if erro:
        return None, erro
    
    taxa_admin, erro = validar_numero(taxa_admin_str, "taxa_admin", obrigatorio=False, min_valor=0, converter_percentual=True)
    if erro:
        return None, erro
    
    taxa_custodia, erro = validar_numero(taxa_custodia_str, "taxa_custodia", obrigatorio=False, min_valor=0, converter_percentual=True)
    if erro:
        return None, erro
    
    regime, erro = validar_opcao(regime_str, ["diario", "anual"], "regime", valor_padrao="diario")
    if erro:
        return None, erro
    
    # A data final pode ser opcional
    data_final, erro = validar_data(data_final_str, "data_final", obrigatorio=False)
    if erro:
        return None, erro
    
    # Se a data final não foi fornecida, usa o dia anterior à data atual
    if not data_final:
        data_final = (datetime.now() - timedelta(days=1)).date()
    
    # Validar que a data inicial é anterior à data final
    if data_inicial > data_final:
        erro_msg = "A data de início deve ser anterior à data final."
        logger.warning(f"Erro de validação: {erro_msg} Data inicial: {data_inicial}, Data final: {data_final}")
        return None, (jsonify({"error": erro_msg}), 400)
    
    # Converter o parâmetro booleano
    incluir_impostos = validar_booleano(incluir_impostos_str, "incluir_impostos")
    
    # Se chegou até aqui, todos os parâmetros são válidos
    # Retorna um dicionário com os parâmetros processados
    params = {
        "data_inicial": data_inicial,
        "valor_investido": valor_investido,
        "taxa_anual": taxa_anual,
        "data_final": data_final,
        "taxa_admin": taxa_admin,
        "taxa_custodia": taxa_custodia,
        "incluir_impostos": incluir_impostos,
        "regime": regime
    }
    
    return params, None

def validar_parametros_investimento_ipca() -> Tuple[Dict[str, Any], Optional[Tuple[Dict[str, str], int]]]:
    """
    Valida e processa os parâmetros para cálculo de investimento em Tesouro IPCA+.
    
    Returns:
        Tupla com (parâmetros_processados, erro_resposta)
        Se houver erro, parâmetros_processados será None e erro_resposta terá a resposta HTTP de erro
        Se validação for bem-sucedida, erro_resposta será None e parâmetros_processados terá os valores processados
    """
    # Obter parâmetros da requisição
    data_inicial_str = request.args.get('data')
    valor_investido_str = request.args.get('valor')
    taxa_fixa_str = request.args.get('taxa_fixa')
    data_final_str = request.args.get('data_final')
    taxa_admin_str = request.args.get('taxa_admin', '0')
    taxa_custodia_str = request.args.get('taxa_custodia', '0.25')  # Padrão do Tesouro Direto
    incluir_impostos_str = request.args.get('incluir_impostos', 'true')
    projecao_str = request.args.get('projecao', 'false')
    ipca_estimado_str = request.args.get('ipca_estimado', '4.5')  # Projeção padrão de 4.5% ao ano
    
    # Log dos parâmetros recebidos
    logger.info(f"Parâmetros recebidos para investimento IPCA+: data={data_inicial_str}, valor={valor_investido_str}, " +
                f"taxa_fixa={taxa_fixa_str}, data_final={data_final_str}, " +
                f"taxa_admin={taxa_admin_str}, taxa_custodia={taxa_custodia_str}, " +
                f"incluir_impostos={incluir_impostos_str}, projecao={projecao_str}, ipca_estimado={ipca_estimado_str}")
    
    # Validar parâmetros usando as funções auxiliares
    data_inicial, erro = validar_data(data_inicial_str, "data", obrigatorio=True)
    if erro:
        return None, erro
    
    valor_investido, erro = validar_numero(valor_investido_str, "valor", obrigatorio=True, min_valor=0)
    if erro:
        return None, erro
    
    taxa_fixa, erro = validar_numero(taxa_fixa_str, "taxa_fixa", obrigatorio=True, min_valor=0)
    if erro:
        return None, erro
    
    taxa_admin, erro = validar_numero(taxa_admin_str, "taxa_admin", obrigatorio=False, min_valor=0)
    if erro:
        return None, erro
    
    taxa_custodia, erro = validar_numero(taxa_custodia_str, "taxa_custodia", obrigatorio=False, min_valor=0)
    if erro:
        return None, erro
    
    ipca_estimado, erro = validar_numero(ipca_estimado_str, "ipca_estimado", obrigatorio=False, min_valor=0)
    if erro:
        return None, erro
    
    # A data final pode ser opcional
    data_final, erro = validar_data(data_final_str, "data_final", obrigatorio=False)
    if erro:
        return None, erro
    
    # Se a data final não foi fornecida, usa o dia anterior à data atual
    if not data_final:
        data_final = (datetime.now() - timedelta(days=1)).date()
    
    # Validar que a data inicial é anterior à data final
    if data_inicial > data_final:
        erro_msg = "A data de início deve ser anterior à data final."
        logger.warning(f"Erro de validação: {erro_msg} Data inicial: {data_inicial}, Data final: {data_final}")
        return None, (jsonify({"error": erro_msg}), 400)
    
    # Converter os parâmetros booleanos
    incluir_impostos = validar_booleano(incluir_impostos_str, "incluir_impostos")
    usar_projecao = validar_booleano(projecao_str, "projecao")
    
    # Se chegou até aqui, todos os parâmetros são válidos
    # Retorna um dicionário com os parâmetros processados
    return {
        "data_inicial": data_inicial,
        "valor_investido": valor_investido,
        "taxa_fixa_anual": taxa_fixa,
        "data_final": data_final,
        "taxa_admin": taxa_admin,
        "taxa_custodia": taxa_custodia,
        "incluir_impostos": incluir_impostos,
        "usar_projecao": usar_projecao,
        "ipca_estimado_anual": ipca_estimado
    }, None 