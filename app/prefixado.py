import math
from datetime import datetime, timedelta, date
from typing import Dict, Any, Optional, Tuple

from app.holidays import is_business_day
from app.logger import logger

def calcular_investimento_prefixado(
    data_inicial: datetime.date,
    valor_investido: float,
    taxa_anual: float,
    data_final: datetime.date,
    taxa_admin: float = 0.0,
    taxa_custodia: float = 0.0,
    incluir_impostos: bool = True,
    regime: str = "diario"
) -> Dict[str, Any]:
    """
    Calcula o rendimento de um investimento pré-fixado (como Tesouro Direto)
    
    Args:
        data_inicial: Data de início do investimento
        valor_investido: Valor inicial investido
        taxa_anual: Taxa de juros anual (em decimal, ex: 0.105 para 10.5%)
        data_final: Data final do investimento
        taxa_admin: Taxa de administração anual (em decimal)
        taxa_custodia: Taxa de custódia anual (em decimal)
        incluir_impostos: Se deve calcular impostos (IR e IOF)
        regime: Regime de capitalização ('diario' ou 'anual')
        
    Returns:
        Dicionário com os detalhes do cálculo e valores finais, incluindo situação atual em um campo adicional
    """
    logger.info(f"Calculando investimento pré-fixado de R$ {valor_investido:.2f} "
                f"de {data_inicial.isoformat()} até {data_final.isoformat()}")
    
    # Obter a data atual para cálculo até hoje
    data_atual = date.today()
    
    # Verificar se a data_atual é posterior à data_inicial e anterior à data_final
    if data_atual <= data_inicial:
        logger.warning("A data atual é anterior ou igual à data inicial. Apenas a simulação até a data final será calculada.")
        apenas_simulacao_final = True
    elif data_atual >= data_final:
        logger.warning("A data atual é posterior ou igual à data final. Apenas a simulação até a data final será calculada.")
        apenas_simulacao_final = True
    else:
        apenas_simulacao_final = False
    
    # Calcular resultado até a data final
    resultado_completo = calcular_periodo(
        data_inicial=data_inicial,
        data_final=data_final,
        valor_investido=valor_investido,
        taxa_anual=taxa_anual,
        taxa_admin=taxa_admin,
        taxa_custodia=taxa_custodia,
        incluir_impostos=incluir_impostos,
        regime=regime
    )
    
    resultado_atual = calcular_periodo(
        data_inicial=data_inicial,
        data_final=data_atual,
        valor_investido=valor_investido,
        taxa_anual=taxa_anual,
        taxa_admin=taxa_admin,
        taxa_custodia=taxa_custodia,
        incluir_impostos=incluir_impostos,
        regime=regime
    )
    # Adicionar situação atual como um campo separado
    resultado_completo["situacao_atual"] = resultado_atual
    
    return resultado_completo


def calcular_periodo(
    data_inicial: datetime.date,
    data_final: datetime.date,
    valor_investido: float,
    taxa_anual: float,
    taxa_admin: float = 0.0,
    taxa_custodia: float = 0.0,
    incluir_impostos: bool = True,
    regime: str = "diario"
) -> Dict[str, Any]:
    """
    Calcula o rendimento de um investimento pré-fixado para um período específico
    
    Args:
        data_inicial: Data de início do investimento
        data_final: Data final para o cálculo
        valor_investido: Valor inicial investido
        taxa_anual: Taxa de juros anual (em decimal, ex: 0.105 para 10.5%)
        taxa_admin: Taxa de administração anual (em decimal)
        taxa_custodia: Taxa de custódia anual (em decimal)
        incluir_impostos: Se deve calcular impostos (IR e IOF)
        regime: Regime de capitalização ('diario' ou 'anual')
        
    Returns:
        Dicionário com os detalhes do cálculo e valores finais
    """
    # Calcular número de dias no período
    dias_totais = (data_final - data_inicial).days
    if dias_totais <= 0:
        raise ValueError("O período de investimento deve ter pelo menos 1 dia.")
    
    # Calcular número de dias úteis no período
    dias_uteis = 0
    for i in range(dias_totais + 1):
        data_atual = data_inicial + timedelta(days=i)
        if is_business_day(data_atual):
            dias_uteis += 1
    
    logger.debug(f"Período de {dias_totais} dias totais, com {dias_uteis} dias úteis")
    
    # Calcular rendimento bruto com base no regime escolhido
    if regime == "anual":
        # Capitalização anual - FV = PV * (1 + r)^t
        anos_fracionados = dias_totais / 365.0
        valor_bruto = valor_investido * ((1 + taxa_anual) ** anos_fracionados)
        rendimento_bruto = valor_bruto - valor_investido
    else:  # regime == "diario"
        # Capitalização diária - com correção usando math.exp para maior precisão
        # Calculamos taxa diária equivalente (considerando 252 dias úteis por ano)
        taxa_diaria = math.exp(math.log(1 + taxa_anual) / 252) - 1
        
        # Calcular taxa efetiva para o período (apenas dias úteis)
        valor_bruto = valor_investido * ((1 + taxa_diaria) ** dias_uteis)
        rendimento_bruto = valor_bruto - valor_investido
    
    # Calcular taxa de administração para o período
    taxa_admin_periodo = taxa_admin * (dias_totais / 365.0)
    valor_taxa_admin = valor_investido * taxa_admin_periodo
    
    # Calcular taxa de custódia para o período
    taxa_custodia_periodo = taxa_custodia * (dias_totais / 365.0)
    valor_taxa_custodia = valor_investido * taxa_custodia_periodo
    
    # Total de taxas
    total_taxas = valor_taxa_admin + valor_taxa_custodia
    
    # Cálculo de impostos (se solicitado)
    imposto_renda = 0.0
    imposto_iof = 0.0
    aliquota_ir = 0.0
    aliquota_iof = 0.0
    total_impostos = 0.0
    
    if incluir_impostos and rendimento_bruto > 0:
        # Calcular a base tributável (rendimento bruto menos taxas)
        base_tributavel = max(0, rendimento_bruto - total_taxas)
        
        # Calcular alíquota do IR com base no prazo
        aliquota_ir = 0.225  # Padrão para períodos até 180 dias
        
        if dias_totais > 720:
            aliquota_ir = 0.15  # Acima de 720 dias
        elif dias_totais > 360:
            aliquota_ir = 0.175  # Entre 361 e 720 dias
        elif dias_totais > 180:
            aliquota_ir = 0.20  # Entre 181 e 360 dias
        
        # Calcular IR sobre a base tributável
        imposto_renda = base_tributavel * aliquota_ir
        
        # Calcular IOF regressivo (se aplicável - até 30 dias)
        if dias_totais <= 30:
            # Tabela regressiva do IOF
            aliquota_iof = max(0, (30 - dias_totais) / 30) * 0.96 + 0.04
            imposto_iof = base_tributavel * aliquota_iof
        
        total_impostos = imposto_renda + imposto_iof
    
    # Calcular valor líquido
    valor_liquido = valor_bruto - total_impostos - total_taxas
    rendimento_liquido = valor_liquido - valor_investido
    
    # Preparar resultado detalhado
    resultado = {
        "valor_investido": valor_investido,
        "data_inicial": data_inicial.isoformat(),
        "data_final": data_final.isoformat(),
        "dias_totais": dias_totais,
        "dias_uteis": dias_uteis,
        "taxa_anual": taxa_anual * 100,  # Volta para percentual
        "regime_capitalizacao": regime,
        "rendimento_bruto": rendimento_bruto,
        "valor_final_bruto": valor_bruto,
        "taxa_administracao": taxa_admin * 100,  # Volta para percentual
        "valor_taxa_administracao": valor_taxa_admin,
        "taxa_custodia": taxa_custodia * 100,  # Volta para percentual
        "valor_taxa_custodia": valor_taxa_custodia,
        "total_taxas": total_taxas,
        "valor_final_liquido": valor_liquido,
        "rendimento_liquido": rendimento_liquido,
        "rendimento_liquido_percentual": (rendimento_liquido / valor_investido) * 100
    }
    
    # Incluir informações de impostos se solicitado
    if incluir_impostos:
        resultado.update({
            "aliquota_ir": aliquota_ir * 100,  # Volta para percentual
            "imposto_renda": imposto_renda,
            "aliquota_iof": aliquota_iof * 100 if dias_totais <= 30 else 0,  # Volta para percentual
            "imposto_iof": imposto_iof,
            "total_impostos": total_impostos
        })
    
    # Adicionar resumo simplificado para fácil consumo
    resultado["resumo"] = {
        "valor_final_bruto": round(valor_bruto, 2),
        "valor_final_liquido": round(valor_liquido, 2),
        "rendimento_liquido": round(rendimento_liquido, 2),
        "impostos_totais": round(total_impostos, 2),
        "taxas_totais": round(total_taxas, 2),
        "rendimento_percentual": round((rendimento_liquido / valor_investido) * 100, 2)
    }
    
    logger.info(f"Investimento calculado: valor final bruto R$ {valor_bruto:.2f}, "
                f"valor final líquido R$ {valor_liquido:.2f}")
    
    return resultado


def calcular_aliquota_ir(dias: int) -> float:
    """
    Calcula a alíquota de IR com base no prazo do investimento
    
    Args:
        dias: Número de dias do investimento
        
    Returns:
        Alíquota de IR em decimal
    """
    if dias > 720:
        return 0.15  # Acima de 720 dias
    elif dias > 360:
        return 0.175  # Entre 361 e 720 dias
    elif dias > 180:
        return 0.20  # Entre 181 e 360 dias
    else:
        return 0.225  # Até 180 dias


def calcular_aliquota_iof(dias: int) -> float:
    """
    Calcula a alíquota de IOF com base no prazo do investimento
    
    Args:
        dias: Número de dias do investimento
        
    Returns:
        Alíquota de IOF em decimal
    """
    if dias > 30:
        return 0.0
    
    # Tabela regressiva do IOF
    return max(0, (30 - dias) / 30) * 0.96 + 0.04 