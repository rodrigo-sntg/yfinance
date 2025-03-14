import logging
import math
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

def calcular_simulacao(
    investimento_inicial, 
    aporte_mensal, 
    anos, 
    retorno_anual, 
    taxa_administracao, 
    aliquota_imposto,
    inflacao_anual,
    frequencia_aporte="monthly",
    dividend_yield=0,
    detalhes=False
):
    """
    Calcula uma simulação de investimento a longo prazo, considerando aportes periódicos,
    taxas de administração, impostos, inflação e dividendos.
    
    Args:
        investimento_inicial (float): Valor inicial a ser investido
        aporte_mensal (float): Valor a ser aportado periodicamente
        anos (int): Duração do investimento em anos
        retorno_anual (float): Taxa de retorno anual esperada (em decimal, ex: 0.10 para 10%)
        taxa_administracao (float): Taxa de administração anual (em decimal, ex: 0.005 para 0.5%)
        aliquota_imposto (float): Alíquota de imposto sobre o rendimento (em decimal, ex: 0.15 para 15%)
        inflacao_anual (float): Taxa de inflação anual esperada (em decimal, ex: 0.04 para 4%)
        frequencia_aporte (str): Frequência dos aportes (monthly, bimonthly, quarterly, semiannually, annually, none)
        dividend_yield (float): Rendimento anual em dividendos (em decimal, ex: 0.03 para 3%)
        detalhes (bool): Se True, retorna o histórico mensal completo
        
    Returns:
        dict: Dicionário com os resultados da simulação, incluindo valores totais e histórico mensal
    """
    logger.info(f"Iniciando simulação de investimento com os seguintes parâmetros:")
    logger.info(f"Investimento inicial: R$ {investimento_inicial:.2f}")
    logger.info(f"Aporte periódico: R$ {aporte_mensal:.2f} ({frequencia_aporte})")
    logger.info(f"Período: {anos} anos")
    logger.info(f"Retorno anual esperado: {retorno_anual*100:.2f}%")
    logger.info(f"Taxa de administração: {taxa_administracao*100:.2f}%")
    logger.info(f"Dividend Yield anual: {dividend_yield*100:.2f}%")
    logger.info(f"Alíquota de imposto: {aliquota_imposto*100:.2f}%")
    logger.info(f"Inflação anual estimada: {inflacao_anual*100:.2f}%")
    
    # Total de meses
    total_meses = anos * 12
    
    # Calcular taxa mensal equivalente (retorno líquido de taxa de administração)
    retorno_mensal = (1 + (retorno_anual - taxa_administracao)) ** (1/12) - 1
    
    # Calcular taxa mensal equivalente para dividendos
    dividend_yield_mensal = (1 + dividend_yield) ** (1/12) - 1
    
    # Mapeamento de frequência de aportes para meses
    frequencia_mapeamento = {
        "monthly": 1,  # Todo mês
        "bimonthly": 2,  # A cada 2 meses
        "quarterly": 3,  # A cada 3 meses
        "semiannually": 6,  # A cada 6 meses
        "annually": 12,  # A cada 12 meses
        "none": 0  # Sem aportes
    }
    
    # Verificar se a frequência é válida
    if frequencia_aporte not in frequencia_mapeamento:
        logger.error(f"Frequência de aporte inválida: {frequencia_aporte}")
        raise ValueError(f"Frequência de aporte inválida. Opções válidas: {', '.join(frequencia_mapeamento.keys())}")
    
    frequencia_meses = frequencia_mapeamento[frequencia_aporte]
    
    # Inicializar variáveis
    saldo_bruto = investimento_inicial
    saldo_liquido = investimento_inicial
    total_investido = investimento_inicial
    total_taxas_admin = 0
    total_impostos_rendimentos = 0
    total_impostos_dividendos = 0
    total_impostos = 0
    total_dividendos = 0
    historico_mensal = []
    
    # Simular mês a mês
    for mes in range(1, total_meses + 1):
        # Calcular rendimento do mês
        rendimento = saldo_bruto * retorno_mensal
        
        # Calcular dividendos do mês
        dividendo = saldo_bruto * dividend_yield_mensal
        
        # Calcular taxas de administração
        taxa_adm = saldo_bruto * (taxa_administracao / 12)
        
        # Calcular impostos sobre rendimentos e dividendos
        imposto_rendimento = rendimento * aliquota_imposto
        imposto_dividendos = dividendo * aliquota_imposto
        imposto = imposto_rendimento + imposto_dividendos
        
        # Determinar se há aporte neste mês
        aporte_no_mes = 0
        if frequencia_aporte != "none" and mes % frequencia_meses == 0:
            aporte_no_mes = aporte_mensal
            total_investido += aporte_no_mes
        
        # Calcular rendimento líquido (rendimentos + dividendos - impostos - taxas)
        rendimento_liquido = rendimento + dividendo - imposto - taxa_adm
        
        # Atualizar saldos
        saldo_bruto += rendimento + dividendo + aporte_no_mes
        saldo_liquido += rendimento_liquido + aporte_no_mes
        
        # Atualizar totais
        total_taxas_admin += taxa_adm
        total_impostos_rendimentos += imposto_rendimento
        total_impostos_dividendos += imposto_dividendos
        total_impostos += imposto
        total_dividendos += dividendo
        
        # Registrar histórico mensal se solicitado
        if detalhes:
            historico_mensal.append({
                "mes": mes,
                "valor_investido": total_investido,
                "rendimento": rendimento,
                "rendimento_pct": (rendimento / saldo_bruto) * 100,
                "dividendo": dividendo,
                "dividendo_pct": (dividendo / saldo_bruto) * 100,
                "saldo_bruto": saldo_bruto,
                "saldo_liquido": saldo_liquido,
                "retorno_acumulado": saldo_liquido - total_investido,
                "taxa_de_administracao": taxa_adm,
                "imposto": imposto,
                "imposto_rendimento": imposto_rendimento,
                "imposto_dividendos": imposto_dividendos,
                "rendimento_liquido": rendimento_liquido,
                "aporte_no_mes": aporte_no_mes
            })
    
    # Calcular valor ajustado pela inflação
    valor_ajustado_inflacao = saldo_liquido / ((1 + inflacao_anual) ** anos)
    
    # Calcular retorno anualizado (CAGR)
    cagr_liquido = (saldo_liquido / total_investido) ** (1 / anos) - 1
    cagr_real = (valor_ajustado_inflacao / total_investido) ** (1 / anos) - 1
    
    # Calcular rendimentos brutos totais
    total_rendimentos_brutos = saldo_bruto - total_investido
    
    # Montar resumo
    resumo = {
        "valor_final_bruto": saldo_bruto,
        "total_investido": total_investido,
        "total_de_rendimentos_brutos": total_rendimentos_brutos,
        "total_de_dividendos": total_dividendos,
        "total_de_taxas_de_administracao": total_taxas_admin,
        "total_de_impostos_rendimentos": total_impostos_rendimentos,
        "total_de_impostos_dividendos": total_impostos_dividendos,
        "total_de_impostos": total_impostos,
        "valor_final_liquido": saldo_liquido,
        "valor_final_liquido_ajustado_pela_inflacao": valor_ajustado_inflacao,
        "retorno_anualizado_liquido_pct": cagr_liquido * 100,
        "retorno_anualizado_ajustado_pela_inflacao_pct": cagr_real * 100,
        "frequencia_aporte": frequencia_aporte,
        "rendimento_dividendos_anual_pct": dividend_yield * 100
    }
    
    # Registrar resultados
    logger.info(f"Resultado da simulação após {anos} anos:")
    logger.info(f"Valor final bruto: R$ {saldo_bruto:.2f}")
    logger.info(f"Valor final líquido: R$ {saldo_liquido:.2f}")
    logger.info(f"Valor final ajustado pela inflação: R$ {valor_ajustado_inflacao:.2f}")
    logger.info(f"Total investido: R$ {total_investido:.2f}")
    logger.info(f"Total de rendimentos: R$ {total_rendimentos_brutos:.2f}")
    logger.info(f"Total de dividendos: R$ {total_dividendos:.2f}")
    logger.info(f"Total de impostos: R$ {total_impostos:.2f}")
    logger.info(f"Retorno anualizado líquido: {cagr_liquido*100:.2f}%")
    logger.info(f"Retorno anualizado real (após inflação): {cagr_real*100:.2f}%")
    
    # Retornar resultados
    resultados = {
        "sucesso": True,
        "resumo": resumo
    }
    
    if detalhes:
        resultados["historico_mensal"] = historico_mensal
    
    return resultados 