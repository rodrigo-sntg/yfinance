#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo para cálculo de investimentos em Tesouro IPCA+.
Inclui funções para obter dados do IPCA e calcular o rendimento
de títulos de Tesouro IPCA+, considerando impostos e taxas.
"""

import os
import json
import requests
from datetime import datetime, timedelta
import time
from app.investimento import calcular_impostos_taxas
from app.holidays import is_business_day, preload_holidays_for_period
from app.logger import logger

# Configuração do cache para dados do IPCA
IPCA_CACHE_FILE = os.path.join('cache', 'ipca_cache.json')
IPCA_API_URL = 'https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados'  # IPCA acumulado 12 meses
IPCA_MENSAL_API_URL = 'https://api.bcb.gov.br/dados/serie/bcdata.sgs.188/dados'  # IPCA mensal

# Cria o diretório de cache se não existir
os.makedirs(os.path.dirname(IPCA_CACHE_FILE), exist_ok=True)

def carregar_cache_ipca():
    """
    Carrega o cache de dados do IPCA se existir.
    """
    try:
        if os.path.exists(IPCA_CACHE_FILE):
            with open(IPCA_CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"ipca_acumulado": {}, "ipca_mensal": {}}
    except Exception as e:
        logger.error(f"Erro ao carregar cache do IPCA: {e}")
        return {"ipca_acumulado": {}, "ipca_mensal": {}}

def salvar_cache_ipca(cache):
    """
    Salva os dados do IPCA no arquivo de cache.
    """
    try:
        with open(IPCA_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=4)
        logger.info(f"Cache do IPCA atualizado com sucesso em {IPCA_CACHE_FILE}")
    except Exception as e:
        logger.error(f"Erro ao salvar cache do IPCA: {e}")

def obter_ipca_acumulado(data_inicial, data_final, max_tentativas=3):
    """
    Obtém a variação acumulada do IPCA entre data_inicial e data_final.
    Usa a API do Banco Central (SGS) - código 433 (IPCA acumulado 12 meses).
    
    Args:
        data_inicial (datetime.date): Data inicial do período
        data_final (datetime.date): Data final do período
        max_tentativas (int): Número máximo de tentativas em caso de falha
    
    Returns:
        float: Variação acumulada do IPCA no período em decimal (ex.: 0.05 para 5%)
    """
    # Converte datas para string no formato exigido pela API
    data_inicial_str = data_inicial.strftime('%d/%m/%Y')
    data_final_str = data_final.strftime('%d/%m/%Y')
    
    logger.info(f"Obtendo IPCA acumulado para o período: {data_inicial_str} a {data_final_str}")
    
    # Verifica se os dados já estão no cache
    cache = carregar_cache_ipca()
    cache_key = f"{data_inicial_str}_{data_final_str}"
    
    if cache_key in cache["ipca_acumulado"]:
        logger.info(f"IPCA acumulado encontrado no cache: {cache['ipca_acumulado'][cache_key]}")
        return cache["ipca_acumulado"][cache_key]
    
    # Se não está no cache, busca na API
    for tentativa in range(max_tentativas):
        try:
            url = f"{IPCA_API_URL}?formato=json&dataInicial={data_inicial_str}&dataFinal={data_final_str}"
            logger.debug(f"Enviando requisição para API do IPCA: {url}")
            
            response = requests.get(url)
            response.raise_for_status()
            dados = response.json()
            
            if not dados:
                logger.warning("Nenhum dado de IPCA retornado pela API")
                time.sleep(2)  # Aguarda antes da próxima tentativa
                continue
            
            # Calcula o IPCA acumulado no período
            # A API retorna uma lista de valores mensais, precisamos converter para uma taxa acumulada
            ipca_inicial = None
            ipca_final = None
            
            # Obtém o primeiro e o último valor disponíveis no período
            for item in dados:
                data_item = datetime.strptime(item["data"], "%d/%m/%Y").date()
                valor = float(item["valor"])
                
                if ipca_inicial is None or data_item < datetime.strptime(ipca_inicial["data"], "%d/%m/%Y").date():
                    ipca_inicial = item
                
                if ipca_final is None or data_item > datetime.strptime(ipca_final["data"], "%d/%m/%Y").date():
                    ipca_final = item
            
            if ipca_inicial and ipca_final:
                # Como a API 433 retorna o IPCA acumulado 12 meses, precisamos ajustar o cálculo
                # para obter o acumulado no período específico
                logger.info(f"Dados IPCA: inicial={ipca_inicial}, final={ipca_final}")
                
                # Vamos usar a API de IPCA mensal para calcular o acumulado no período
                url_mensal = f"{IPCA_MENSAL_API_URL}?formato=json&dataInicial={data_inicial_str}&dataFinal={data_final_str}"
                response_mensal = requests.get(url_mensal)
                response_mensal.raise_for_status()
                dados_mensal = response_mensal.json()
                
                # Calcula o IPCA acumulado composto para o período
                ipca_acumulado = 1.0
                for item in dados_mensal:
                    valor_mensal = float(item["valor"]) / 100.0  # Converte de percentual para decimal
                    ipca_acumulado *= (1 + valor_mensal)
                
                # Desconta 1 para obter a variação percentual em decimal
                ipca_acumulado = ipca_acumulado - 1.0
                
                logger.info(f"IPCA acumulado no período: {ipca_acumulado * 100:.4f}%")
                
                # Salva no cache
                cache["ipca_acumulado"][cache_key] = ipca_acumulado
                salvar_cache_ipca(cache)
                
                return ipca_acumulado
            else:
                logger.warning(f"Dados insuficientes para calcular IPCA acumulado. Tentativa {tentativa + 1}/{max_tentativas}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao obter dados do IPCA (tentativa {tentativa + 1}): {e}")
            time.sleep(5)  # Aguarda 5 segundos antes da próxima tentativa
        except Exception as e:
            logger.error(f"Erro inesperado ao processar dados do IPCA (tentativa {tentativa + 1}): {e}")
            time.sleep(5)
    
    # Se falhar todas as tentativas, retorna uma estimativa baseada na meta de inflação (3-6% ao ano)
    # Calcula com base em 4.5% ao ano proporcional ao período
    dias_totais = (data_final - data_inicial).days
    ipca_estimado = 0.045 * (dias_totais / 365)
    logger.warning(f"Usando estimativa de IPCA baseada na meta de inflação: {ipca_estimado * 100:.2f}%")
    return ipca_estimado

def calcular_rendimento_ipca(data_inicial, valor_investido, taxa_fixa_anual, data_final=None, taxa_admin=0, taxa_custodia=0.25, incluir_impostos=True):
    """
    Calcula o rendimento de um investimento no Tesouro IPCA+.
    
    Args:
        data_inicial (datetime.date): Data inicial do investimento.
        valor_investido (float): Valor inicial investido.
        taxa_fixa_anual (float): Taxa fixa anual do título (ex.: 5.0 para 5%).
        data_final (datetime.date, optional): Data final do cálculo. Se None, usa o dia anterior à data atual.
        taxa_admin (float, optional): Taxa de administração anual (%). Padrão é 0.
        taxa_custodia (float, optional): Taxa de custódia anual (%). Padrão é 0.25 (padrão Tesouro Direto).
        incluir_impostos (bool, optional): Se deve incluir cálculo de IR e IOF. Padrão é True.
        
    Returns:
        dict: Resultado do cálculo contendo valores brutos, líquidos, impostos, taxas e estatísticas.
    """
    # Define a data final como o dia anterior à data atual se não informada
    if data_final is None:
        data_final = (datetime.now() - timedelta(days=1)).date()
    elif isinstance(data_final, datetime):
        data_final = data_final.date()
    
    if isinstance(data_inicial, datetime):
        data_inicial = data_inicial.date()
        
    logger.info(f"Período de cálculo IPCA+: {data_inicial} até {data_final}")
    logger.info(f"Valor inicial: R$ {valor_investido:.2f}, Taxa fixa: {taxa_fixa_anual}%, Taxa admin: {taxa_admin}%, Taxa custódia: {taxa_custodia}%, Incluir impostos: {incluir_impostos}")
    
    # Pré-carrega feriados para todo o período
    preload_holidays_for_period(data_inicial, data_final)
    
    # Contar dias úteis no período (base: 252 dias úteis por ano)
    dias_uteis = 0
    current_date = data_inicial
    while current_date <= data_final:
        if is_business_day(current_date):
            dias_uteis += 1
        current_date += timedelta(days=1)
    
    dias_totais = (data_final - data_inicial).days + 1
    logger.info(f"Total de dias: {dias_totais}, Dias úteis: {dias_uteis}")
    
    # Obter IPCA acumulado no período
    ipca_acumulado = obter_ipca_acumulado(data_inicial, data_final)
    
    # Calcular a taxa combinada (IPCA + taxa fixa)
    taxa_fixa_decimal = taxa_fixa_anual / 100
    taxa_combinada_anual = (1 + ipca_acumulado) * (1 + taxa_fixa_decimal) - 1
    logger.info(f"Taxa combinada anual: {taxa_combinada_anual * 100:.4f}% (IPCA {ipca_acumulado * 100:.4f}% + Taxa fixa {taxa_fixa_anual}%)")
    
    # Converter para taxa diária (base: 252 dias úteis por ano)
    taxa_diaria = (1 + taxa_combinada_anual) ** (1 / 252) - 1
    
    # Calcular fator composto para os dias úteis
    fator_composto = (1 + taxa_diaria) ** dias_uteis
    logger.info(f"Fator composto: {fator_composto:.8f}")
    
    # Calcular valor final bruto
    valor_final_bruto = valor_investido * fator_composto
    rendimento_bruto = valor_final_bruto - valor_investido
    rendimento_percentual_bruto = (rendimento_bruto / valor_investido) * 100
    
    logger.info(f"Valor final bruto: R$ {valor_final_bruto:.2f}, Rendimento bruto: R$ {rendimento_bruto:.2f} ({rendimento_percentual_bruto:.2f}%)")
    
    # Resultado básico (sem impostos e taxas)
    resultado = {
        "data_inicial": data_inicial.strftime('%Y-%m-%d'),
        "data_final": data_final.strftime('%Y-%m-%d'),
        "valor_investido": valor_investido,
        "valor_final_bruto": valor_final_bruto,
        "rendimento_bruto": rendimento_bruto,
        "rendimento_percentual_bruto": rendimento_percentual_bruto,
        "fator_composto": fator_composto,
        "dias_uteis": dias_uteis,
        "dias_totais": dias_totais,
        "ipca_acumulado": ipca_acumulado * 100,  # Em percentual
        "taxa_fixa_anual": taxa_fixa_anual
    }
    
    # Se for para incluir impostos e taxas, calcula e adiciona ao resultado
    if incluir_impostos:
        logger.info(f"Calculando impostos e taxas (Taxa admin: {taxa_admin}%, Taxa custódia: {taxa_custodia}%)")
        
        # Reutilizar função existente para calcular impostos e taxas
        impostos_taxas = calcular_impostos_taxas(
            valor_investido=valor_investido,
            fator_composto=fator_composto,
            dias_totais=dias_totais,
            taxa_admin=taxa_admin,
            taxa_custodia=taxa_custodia
        )
        
        # Adicionar ao resultado
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
        
        # Calcular o rendimento líquido percentual
        rendimento_liquido = resultado["rendimento_liquido"]
        rendimento_percentual_liquido = (rendimento_liquido / valor_investido) * 100
        resultado["rendimento_percentual_liquido"] = rendimento_percentual_liquido
        
        logger.info(f"Rendimento líquido: R$ {rendimento_liquido:.2f} ({rendimento_percentual_liquido:.2f}%)")
        logger.info(f"IR ({impostos_taxas['aliquota_ir']}%): R$ {impostos_taxas['imposto_renda']:.2f}, "
                   f"Taxa Admin: R$ {impostos_taxas['taxa_admin_valor']:.2f}, "
                   f"Taxa Custódia: R$ {impostos_taxas['taxa_custodia_valor']:.2f}, "
                   f"IOF: R$ {impostos_taxas['iof']:.2f}")
    
    return resultado

def estimar_valor_futuro_ipca(data_inicial, valor_investido, taxa_fixa_anual, data_final, ipca_estimado_anual=4.5, taxa_admin=0, taxa_custodia=0.25, incluir_impostos=True):
    """
    Estima o valor futuro de um investimento no Tesouro IPCA+ com base em uma projeção do IPCA.
    
    Args:
        data_inicial (datetime.date): Data inicial do investimento.
        valor_investido (float): Valor inicial investido.
        taxa_fixa_anual (float): Taxa fixa anual do título (ex.: 5.0 para 5%).
        data_final (datetime.date): Data final para a projeção.
        ipca_estimado_anual (float): Projeção anual do IPCA em percentual (ex.: 4.5 para 4.5%).
        taxa_admin (float): Taxa de administração anual (%).
        taxa_custodia (float): Taxa de custódia anual (%).
        incluir_impostos (bool): Se deve incluir cálculo de IR e IOF.
        
    Returns:
        dict: Resultado da projeção contendo valores brutos, líquidos, impostos, taxas e estatísticas.
    """
    logger.info(f"Estimando valor futuro com IPCA projetado de {ipca_estimado_anual}% ao ano")
    
    if isinstance(data_inicial, datetime):
        data_inicial = data_inicial.date()
    if isinstance(data_final, datetime):
        data_final = data_final.date()
    
    # Calcula o número de dias no período
    dias_totais = (data_final - data_inicial).days + 1
    
    # Calcula o IPCA acumulado estimado para o período
    ipca_estimado = (1 + ipca_estimado_anual/100) ** (dias_totais/365) - 1
    
    # Pré-carrega feriados para todo o período
    preload_holidays_for_period(data_inicial, data_final)
    
    # Contar dias úteis no período
    dias_uteis = 0
    current_date = data_inicial
    while current_date <= data_final:
        if is_business_day(current_date):
            dias_uteis += 1
        current_date += timedelta(days=1)
    
    logger.info(f"Período de projeção: {dias_totais} dias totais, {dias_uteis} dias úteis")
    logger.info(f"IPCA estimado para o período: {ipca_estimado * 100:.4f}%")
    
    # Calcula a taxa combinada estimada (IPCA + taxa fixa)
    taxa_fixa_decimal = taxa_fixa_anual / 100
    taxa_combinada_anual = (1 + ipca_estimado) * (1 + taxa_fixa_decimal) - 1
    
    # Converte para taxa diária (base: 252 dias úteis por ano)
    taxa_diaria = (1 + taxa_combinada_anual) ** (1/252) - 1
    
    # Calcula o fator composto para os dias úteis
    fator_composto = (1 + taxa_diaria) ** dias_uteis
    
    # Calcula o valor final bruto estimado
    valor_final_bruto = valor_investido * fator_composto
    rendimento_bruto = valor_final_bruto - valor_investido
    rendimento_percentual_bruto = (rendimento_bruto / valor_investido) * 100
    
    # Resultado básico (sem impostos e taxas)
    resultado = {
        "data_inicial": data_inicial.strftime('%Y-%m-%d'),
        "data_final": data_final.strftime('%Y-%m-%d'),
        "valor_investido": valor_investido,
        "valor_final_bruto": valor_final_bruto,
        "rendimento_bruto": rendimento_bruto,
        "rendimento_percentual_bruto": rendimento_percentual_bruto,
        "fator_composto": fator_composto,
        "dias_uteis": dias_uteis,
        "dias_totais": dias_totais,
        "ipca_estimado": ipca_estimado * 100,  # Em percentual
        "ipca_estimado_anual": ipca_estimado_anual,
        "taxa_fixa_anual": taxa_fixa_anual,
        "eh_projecao": True
    }
    
    # Se for para incluir impostos e taxas, calcula e adiciona ao resultado
    if incluir_impostos:
        # Reutiliza a função existente para calcular impostos e taxas
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
    
    return resultado

# Exemplo de uso
if __name__ == "__main__":
    data_inicial = datetime(2024, 1, 1).date()
    data_final = datetime(2025, 4, 15).date()
    valor_investido = 10000.0  # R$ 10.000,00
    taxa_fixa_anual = 5.0  # 5% ao ano + IPCA
    
    resultado = calcular_rendimento_ipca(
        data_inicial=data_inicial,
        valor_investido=valor_investido,
        taxa_fixa_anual=taxa_fixa_anual,
        data_final=data_final,
        taxa_admin=0.0,  # Sem taxa de administração
        taxa_custodia=0.25,  # Taxa padrão do Tesouro Direto
        incluir_impostos=True
    )
    
    # Exibe resultados
    print("\n===== CÁLCULO DO TESOURO IPCA+ =====")
    print(f"Período: {data_inicial.strftime('%d/%m/%Y')} a {data_final.strftime('%d/%m/%Y')}")
    print(f"Valor Investido: R$ {resultado['valor_investido']:.2f}")
    print(f"IPCA acumulado no período: {resultado['ipca_acumulado']:.2f}%")
    print(f"Taxa fixa: {resultado['taxa_fixa_anual']:.2f}% ao ano")
    print(f"\nValor Final Bruto: R$ {resultado['valor_final_bruto']:.2f}")
    print(f"Rendimento Bruto: R$ {resultado['rendimento_bruto']:.2f} ({resultado['rendimento_percentual_bruto']:.2f}%)")
    
    if 'valor_final_liquido' in resultado:
        print(f"\nValor Final Líquido: R$ {resultado['valor_final_liquido']:.2f}")
        print(f"Rendimento Líquido: R$ {resultado['rendimento_liquido']:.2f} ({resultado['rendimento_percentual_liquido']:.2f}%)")
        print(f"\nDescontos:")
        print(f"Imposto de Renda: R$ {resultado['imposto_renda']:.2f} ({resultado['aliquota_ir']:.1f}%)")
        print(f"Taxa de Administração: R$ {resultado['taxa_admin_valor']:.2f}")
        print(f"Taxa de Custódia: R$ {resultado['taxa_custodia_valor']:.2f}")
        print(f"IOF: R$ {resultado['iof']:.2f}")
    
    print(f"\nEstatísticas:")
    print(f"Dias totais: {resultado['dias_totais']}")
    print(f"Dias úteis: {resultado['dias_uteis']}")
    print(f"Fator composto: {resultado['fator_composto']:.8f}")
    
    # Exemplo de projeção futura
    print("\n\n===== PROJEÇÃO FUTURA DO TESOURO IPCA+ =====")
    data_projecao = datetime(2028, 1, 1).date()
    
    projecao = estimar_valor_futuro_ipca(
        data_inicial=data_inicial,
        valor_investido=valor_investido,
        taxa_fixa_anual=taxa_fixa_anual,
        data_final=data_projecao,
        ipca_estimado_anual=4.5,  # Estimativa de 4.5% ao ano
        taxa_admin=0.0,
        taxa_custodia=0.25,
        incluir_impostos=True
    )
    
    print(f"Período de projeção: {data_inicial.strftime('%d/%m/%Y')} a {data_projecao.strftime('%d/%m/%Y')}")
    print(f"IPCA estimado: {projecao['ipca_estimado_anual']:.2f}% ao ano")
    print(f"IPCA acumulado estimado: {projecao['ipca_estimado']:.2f}%")
    print(f"\nValor Investido: R$ {projecao['valor_investido']:.2f}")
    print(f"Valor Final Bruto (estimado): R$ {projecao['valor_final_bruto']:.2f}")
    print(f"Rendimento Bruto (estimado): R$ {projecao['rendimento_bruto']:.2f} ({projecao['rendimento_percentual_bruto']:.2f}%)")
    
    if 'valor_final_liquido' in projecao:
        print(f"\nValor Final Líquido (estimado): R$ {projecao['valor_final_liquido']:.2f}")
        print(f"Rendimento Líquido (estimado): R$ {projecao['rendimento_liquido']:.2f} ({projecao['rendimento_percentual_liquido']:.2f}%)")
        print(f"\nDescontos estimados:")
        print(f"Imposto de Renda: R$ {projecao['imposto_renda']:.2f} ({projecao['aliquota_ir']:.1f}%)")
        print(f"Taxa de Administração: R$ {projecao['taxa_admin_valor']:.2f}")
        print(f"Taxa de Custódia: R$ {projecao['taxa_custodia_valor']:.2f}") 