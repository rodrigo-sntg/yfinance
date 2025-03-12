from datetime import datetime, timedelta
from app.selic import ensure_rates_in_cache, ensure_non_business_day_in_cache
from app.holidays import is_business_day
from app.cache import get_cached_rates, save_cache
from app.logger import logger
import logging

# Tabela Regressiva do IOF (apenas para os primeiros 30 dias)
IOF_TABELA_REGRESSIVA = {
    1: 96, 2: 93, 3: 90, 4: 86, 5: 83, 6: 80, 7: 76, 8: 73, 9: 70, 10: 66,
    11: 63, 12: 60, 13: 56, 14: 53, 15: 50, 16: 46, 17: 43, 18: 40, 19: 36,
    20: 33, 21: 30, 22: 26, 23: 20, 24: 16, 25: 13, 26: 10, 27: 6,
    28: 3, 29: 0, 30: 0
}

def calcular_impostos_taxas(valor_investido, fator_composto, dias_totais, taxa_admin=0, taxa_custodia=0):
    """
    Calcula Imposto de Renda (IR), taxas da corretora e IOF.

    Args:
        valor_investido (float): Valor inicial investido.
        fator_composto (float): Fator de rentabilidade ao longo do período.
        dias_totais (int): Número total de dias da aplicação.
        taxa_admin (float): Taxa de administração anual (%).
        taxa_custodia (float): Taxa de custódia anual (%).

    Returns:
        dict: Dicionário com valores de impostos, taxas e rendimento líquido.
    """
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
    if dias_totais < 30:
        iof_percentual = IOF_TABELA_REGRESSIVA.get(dias_totais, 0)  # Obtém o percentual do IOF na tabela
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
        "rendimento_liquido": rendimento_liquido,
        "imposto_renda": imposto_renda,
        "taxa_admin_valor": taxa_admin_valor,
        "taxa_custodia_valor": taxa_custodia_valor,
        "iof": iof,
        "aliquota_ir": aliquota_ir * 100  # Convertida para percentual
    }

def calcular_rendimento(data_inicial, valor_investido, data_final=None, taxa_admin=0, taxa_custodia=0, incluir_impostos=True):
    """
    Calcula o rendimento de um investimento com base na taxa Selic no período especificado,
    incluindo impostos (IR e IOF) e taxas administrativas.
    
    Args:
        data_inicial (datetime.date): Data inicial do investimento
        valor_investido (float): Valor inicial investido
        data_final (datetime.date, optional): Data final do cálculo. Se None, usa o dia anterior à data atual.
        taxa_admin (float, optional): Taxa de administração anual (%). Padrão é 0.
        taxa_custodia (float, optional): Taxa de custódia anual (%). Padrão é 0.
        incluir_impostos (bool, optional): Se deve incluir cálculo de IR e IOF. Padrão é True.
        
    Returns:
        dict: Resultado do cálculo contendo valores brutos, líquidos, impostos, taxas e estatísticas
    """
    # Define a data final como o dia anterior à data atual se não informada
    if data_final is None:
        data_final = (datetime.now() - timedelta(days=1)).date()
        
    logger.info(f"Período de cálculo: {data_inicial} até {data_final}")
    logger.info(f"Valor inicial: R$ {valor_investido:.2f}, Taxa admin: {taxa_admin}%, Taxa custódia: {taxa_custodia}%, Incluir impostos: {incluir_impostos}")
    
    # Verificação de quantos dias serão calculados
    dias_totais = (data_final - data_inicial).days + 1
    logger.info(f"Total de dias a serem considerados no cálculo: {dias_totais}")

    # Utilizamos a versão otimizada de ensure_rates_in_cache que verifica eficientemente
    # se as taxas estão no cache e só busca as taxas que não estão disponíveis
    logger.info(f"Carregando taxas para o período {data_inicial} a {data_final}")
    taxas_diarias = ensure_rates_in_cache(data_inicial, data_final)
    logger.info(f"Taxas carregadas com sucesso, iniciando cálculo")

    # Cálculo de juros compostos
    fator_composto = 1.0
    dias_compostos = 0  # Dias com taxa > 0
    dias_sem_rendimento = 0  # Dias com taxa = 0 (não úteis)
    dias_sem_taxa = 0  # Dias sem taxa disponível
    current_date = data_inicial
    
    # Para diagnóstico
    fatores_utilizados = []
    
    # Cria um dicionário para taxas ISO para busca eficiente
    taxas_iso = {}
    for dt, taxa in taxas_diarias.items():
        if hasattr(dt, 'strftime'):
            taxas_iso[dt.strftime('%Y-%m-%d')] = taxa
    
    while current_date <= data_final:
        current_date_iso = current_date.strftime('%Y-%m-%d')
        
        # Verifica primeiro no dicionário taxas_iso (mais eficiente)
        if current_date_iso in taxas_iso:
            fator_diario = taxas_iso[current_date_iso]
            if fator_diario > 0:
                # Dia útil com taxa disponível
                fator_composto *= fator_diario
                dias_compostos += 1
                fatores_utilizados.append({
                    "data": current_date_iso,
                    "fator": fator_diario,
                    "tipo": "dia_util"
                })
                logger.debug(f"Dia {current_date_iso}: Fator diário = {fator_diario}, Fator acumulado = {fator_composto}")
            else:
                # Dia não útil (taxa = 0)
                dias_sem_rendimento += 1
                fatores_utilizados.append({
                    "data": current_date_iso,
                    "fator": 0,
                    "tipo": "dia_nao_util"
                })
                logger.debug(f"Dia {current_date_iso}: Dia não útil, fator = 0")
        # Também verifica diretamente no dicionário taxas_diarias (compatibilidade)
        elif current_date in taxas_diarias:
            fator_diario = taxas_diarias[current_date]
            if fator_diario > 0:
                # Dia útil com taxa disponível
                fator_composto *= fator_diario
                dias_compostos += 1
                fatores_utilizados.append({
                    "data": current_date_iso,
                    "fator": fator_diario,
                    "tipo": "dia_util"
                })
                logger.debug(f"Dia {current_date_iso}: Fator diário = {fator_diario}, Fator acumulado = {fator_composto}")
            else:
                # Dia não útil (taxa = 0)
                dias_sem_rendimento += 1
                fatores_utilizados.append({
                    "data": current_date_iso,
                    "fator": 0,
                    "tipo": "dia_nao_util"
                })
                logger.debug(f"Dia {current_date_iso}: Dia não útil, fator = 0")
        else:
            # Improvável que chegue aqui se ensure_rates_in_cache estiver funcionando corretamente
            # Dia sem taxa disponível (erro ou API indisponível)
            dias_sem_taxa += 1
            fatores_utilizados.append({
                "data": current_date_iso,
                "fator": 1.0,
                "tipo": "desconhecido"
            })
            logger.warning(f"Dia {current_date_iso}: Taxa não encontrada, usando fator 1.0")
        
        current_date += timedelta(days=1)

    if dias_sem_taxa > 0:
        logger.warning(f"Atenção: {dias_sem_taxa} dias sem taxa Selic disponível no período calculado")

    # Cálculo do valor final e rendimento bruto
    valor_final_bruto = valor_investido * fator_composto
    rendimento_bruto = valor_final_bruto - valor_investido
    rendimento_percentual_bruto = (rendimento_bruto / valor_investido) * 100
    
    logger.info(f"Cálculo concluído: Valor inicial={valor_investido}, Fator composto={fator_composto}, Valor final bruto={valor_final_bruto}")
    logger.info(f"Rendimento bruto: R$ {rendimento_bruto:.2f} ({rendimento_percentual_bruto:.2f}%)")

    # Resultado básico (sem impostos e taxas)
    resultado = {
        "data_inicial": data_inicial.strftime('%Y-%m-%d'),
        "data_final": data_final.strftime('%Y-%m-%d'),
        "valor_investido": valor_investido,
        "valor_final_bruto": valor_final_bruto,
        "rendimento_bruto": rendimento_bruto,
        "rendimento_percentual_bruto": rendimento_percentual_bruto,
        "fator_composto": fator_composto,
        "dias_compostos": dias_compostos,  # Dias úteis com taxa > 0
        "dias_sem_rendimento": dias_sem_rendimento,  # Dias não úteis com taxa = 0
        "dias_sem_taxa": dias_sem_taxa,  # Dias sem taxa disponível
        "dias_totais": dias_totais  # Total de dias no período
    }
    
    # Se for para incluir impostos e taxas, calcula e adiciona ao resultado
    if incluir_impostos:
        logger.info(f"Calculando impostos e taxas (Taxa admin: {taxa_admin}%, Taxa custódia: {taxa_custodia}%)")
        
        # Calcula impostos e taxas
        impostos_taxas = calcular_impostos_taxas(
            valor_investido=valor_investido,
            fator_composto=fator_composto,
            dias_totais=dias_totais,
            taxa_admin=taxa_admin,
            taxa_custodia=taxa_custodia
        )
        
        # Adiciona ao resultado
        resultado.update({
            "valor_final_liquido": impostos_taxas["valor_final_liquido"],
            "rendimento_liquido": impostos_taxas["rendimento_liquido"],
            "imposto_renda": impostos_taxas["imposto_renda"],
            "taxa_admin_valor": impostos_taxas["taxa_admin_valor"],
            "taxa_custodia_valor": impostos_taxas["taxa_custodia_valor"],
            "iof": impostos_taxas["iof"],
            "aliquota_ir": impostos_taxas["aliquota_ir"],
            "taxa_admin_percentual": taxa_admin,
            "taxa_custodia_percentual": taxa_custodia
        })
        
        # Calcula o rendimento líquido percentual
        rendimento_liquido = resultado["rendimento_liquido"]
        rendimento_percentual_liquido = (rendimento_liquido / valor_investido) * 100
        resultado["rendimento_percentual_liquido"] = rendimento_percentual_liquido
        
        logger.info(f"Rendimento líquido: R$ {rendimento_liquido:.2f} ({rendimento_percentual_liquido:.2f}%)")
        logger.info(f"IR ({impostos_taxas['aliquota_ir']}%): R$ {impostos_taxas['imposto_renda']:.2f}, "
                   f"Taxa Admin: R$ {impostos_taxas['taxa_admin_valor']:.2f}, "
                   f"IOF: R$ {impostos_taxas['iof']:.2f}")
    
    # Adiciona fatores detalhados para diagnóstico se estiver em modo DEBUG
    if logger.isEnabledFor(logging.DEBUG):
        resultado["fatores_detalhados"] = fatores_utilizados
    
    return resultado

def analisar_investimento(data_inicial, valor_investido, data_final=None):
    """
    Realiza uma análise detalhada de um investimento, incluindo estatísticas sobre dias úteis e não úteis.
    
    Args:
        data_inicial (datetime.date): Data inicial do investimento
        valor_investido (float): Valor inicial investido
        data_final (datetime.date, optional): Data final do cálculo. Se None, usa o dia anterior à data atual.
        
    Returns:
        dict: Análise detalhada do investimento com estatísticas
    """
    # Define a data final como o dia anterior à data atual se não informada
    if data_final is None:
        data_final = (datetime.now() - timedelta(days=1)).date()
        
    logger.info(f"Período de análise: {data_inicial} até {data_final}")
    
    # Verificação de quantos dias serão analisados
    dias_totais = (data_final - data_inicial).days + 1
    logger.info(f"Total de dias a serem analisados: {dias_totais}")
    
    # Usamos a função ensure_rates_in_cache otimizada que verifica o cache
    # e busca apenas as taxas que não estão disponíveis
    logger.info(f"Carregando taxas para o período {data_inicial} a {data_final}")
    taxas_diarias = ensure_rates_in_cache(data_inicial, data_final)
    logger.info(f"Taxas carregadas com sucesso para o período de análise")
    
    # Cria um dicionário auxiliar para taxas no formato ISO (mais eficiente para busca)
    taxas_iso = {}
    for dt, taxa in taxas_diarias.items():
        if hasattr(dt, 'strftime'):
            taxas_iso[dt.strftime('%Y-%m-%d')] = taxa
    
    # Estatísticas por tipo de dia
    dias_uteis_count = 0
    dias_nao_uteis_count = 0
    dias_feriados_count = 0
    
    fator_acumulado_total = 1.0
    fator_acumulado_util = 1.0
    
    dias_com_detalhes = []
    
    # Lista com todas as datas no período
    current_date = data_inicial
    while current_date <= data_final:
        current_date_iso = current_date.strftime('%Y-%m-%d')
        dia_util = is_business_day(current_date)
        
        item = {
            "data": current_date_iso,
            "dia_semana": current_date.strftime('%A'),
            "dia_util_calendario": dia_util
        }
        
        # Primeiro verifica no dicionário taxas_iso (mais eficiente)
        if current_date_iso in taxas_iso:
            fator = taxas_iso[current_date_iso]
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
        # Verifica também diretamente em taxas_diarias para compatibilidade
        elif current_date in taxas_diarias:
            fator = taxas_diarias[current_date]
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
            # Dia sem taxa disponível - isso não deveria acontecer se ensure_rates_in_cache funcionou corretamente
            item["tipo"] = "sem_taxa"
            item["rendimento"] = False
            logger.warning(f"Data {current_date_iso} sem taxa disponível no cache, mesmo após tentativa de atualização")
        
        dias_com_detalhes.append(item)
        current_date += timedelta(days=1)
    
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
            "data_inicial": data_inicial.strftime('%Y-%m-%d'),
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
    
    logger.info(f"Análise de investimento concluída: {dias_uteis_count} dias úteis, {dias_nao_uteis_count} dias não úteis, {dias_feriados_count} feriados")
    
    return resultado, dias_com_detalhes 