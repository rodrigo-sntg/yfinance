#!/usr/bin/env python3
"""
Script de exemplo para demonstrar o cálculo de rendimento da SELIC com impostos e taxas.
Este script mostra como usar as funções implementadas para calcular o rendimento líquido
de um investimento, considerando Imposto de Renda, taxas de administração e IOF.
"""

import sys
import os
from datetime import datetime, date, timedelta
import json
from decimal import Decimal, ROUND_DOWN

# Adiciona o diretório raiz do projeto ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importa as funções necessárias
from app.selic import calcular_rendimento_selic, ensure_rates_in_cache
from app.logger import logger

def formatar_valor(valor):
    """Formata um valor monetário com duas casas decimais."""
    return f"R$ {valor:.2f}"

def main():
    """Função principal para demonstrar o cálculo de rendimento com taxas."""
    # Configura a data inicial e final
    data_inicial = date(2023, 1, 1)
    data_final = date(2023, 12, 31)
    
    # Valor inicial do investimento
    valor_inicial = 10000.00
    
    # Taxa de administração (em % ao ano)
    taxa_admin = 0.5  # 0.5% ao ano
    
    print("=" * 80)
    print(f"SIMULAÇÃO DE RENDIMENTO SELIC COM IMPOSTOS E TAXAS")
    print("=" * 80)
    print(f"Período: {data_inicial.strftime('%d/%m/%Y')} a {data_final.strftime('%d/%m/%Y')}")
    print(f"Valor inicial: {formatar_valor(valor_inicial)}")
    print(f"Taxa de administração: {taxa_admin}% a.a.")
    print("-" * 80)
    
    # Garante que todas as taxas para o período estão no cache
    print("Carregando taxas SELIC do período...")
    taxas_diarias = ensure_rates_in_cache(data_inicial, data_final)
    print(f"Taxas carregadas: {len(taxas_diarias)} registros")
    
    # Calcula o rendimento com diferentes taxas de administração
    taxas_simulacao = [0, 0.5, 1.0, 1.5, 2.0]
    
    print("\nRESULTADOS COMPARATIVOS COM DIFERENTES TAXAS DE ADMINISTRAÇÃO:")
    print("-" * 80)
    print(f"{'Taxa Admin (%)':^15} | {'Valor Final':^15} | {'Rendimento':^15} | {'IR (%)':^8} | {'IR (R$)':^12} | {'Taxa Admin (R$)':^15}")
    print("-" * 80)
    
    for taxa in taxas_simulacao:
        # Calcula o rendimento com a taxa atual
        resultado = calcular_rendimento_selic(
            valor_inicial=valor_inicial,
            start_date=data_inicial,
            end_date=data_final,
            taxa_admin=taxa,
            taxa_custodia=0,
            taxas_diarias=taxas_diarias
        )
        
        # Extrai os valores para exibição
        valor_final = resultado["valor_final_liquido"]
        rendimento = resultado["lucro_liquido"]
        aliquota_ir = resultado["aliquota_ir"]
        imposto_renda = resultado["imposto_renda"]
        taxa_admin_valor = resultado["taxa_admin_valor"]
        
        # Exibe a linha de resultado
        print(f"{taxa:^15.2f} | {formatar_valor(valor_final):^15} | {formatar_valor(rendimento):^15} | {aliquota_ir:^8.1f} | {formatar_valor(imposto_renda):^12} | {formatar_valor(taxa_admin_valor):^15}")
    
    print("-" * 80)
    
    # Exibe resultados detalhados com a taxa de administração selecionada
    taxa_selecionada = 0.5
    print(f"\nRESULTADO DETALHADO COM TAXA DE {taxa_selecionada}% a.a.:")
    print("-" * 80)
    
    resultado_detalhado = calcular_rendimento_selic(
        valor_inicial=valor_inicial,
        start_date=data_inicial,
        end_date=data_final,
        taxa_admin=taxa_selecionada,
        taxa_custodia=0,
        taxas_diarias=taxas_diarias
    )
    
    # Formata e exibe os resultados detalhados
    dias_totais = resultado_detalhado["dias_totais"]
    dias_uteis = resultado_detalhado["dias_uteis"]
    fator_composto = resultado_detalhado["fator_composto"]
    
    print(f"Período total: {dias_totais} dias ({dias_uteis} dias úteis)")
    print(f"Fator de rentabilidade: {fator_composto:.8f}")
    print()
    print(f"Valor investido: {formatar_valor(resultado_detalhado['valor_investido'])}")
    print(f"Rendimento bruto: {formatar_valor(resultado_detalhado['lucro_bruto'])}")
    print(f"Alíquota de IR: {resultado_detalhado['aliquota_ir']:.1f}%")
    print(f"Imposto de Renda: {formatar_valor(resultado_detalhado['imposto_renda'])}")
    print(f"Taxa de administração: {formatar_valor(resultado_detalhado['taxa_admin_valor'])}")
    print(f"IOF: {formatar_valor(resultado_detalhado['iof'])}")
    print("-" * 40)
    print(f"Rendimento líquido: {formatar_valor(resultado_detalhado['lucro_liquido'])}")
    print(f"Valor final líquido: {formatar_valor(resultado_detalhado['valor_final_liquido'])}")
    
    # Calcula o rendimento equivalente em % ao ano
    dias_ano = 365
    rendimento_percentual = (resultado_detalhado['fator_composto'] - 1) * 100
    rendimento_anual = ((resultado_detalhado['fator_composto'] ** (dias_ano / dias_totais)) - 1) * 100
    
    rendimento_liquido_percentual = (resultado_detalhado['valor_final_liquido'] / resultado_detalhado['valor_investido'] - 1) * 100
    rendimento_liquido_anual = ((resultado_detalhado['valor_final_liquido'] / resultado_detalhado['valor_investido']) ** (dias_ano / dias_totais) - 1) * 100
    
    print("\nRENTABILIDADE:")
    print(f"Rentabilidade bruta no período: {rendimento_percentual:.2f}%")
    print(f"Rentabilidade bruta anualizada: {rendimento_anual:.2f}% a.a.")
    print(f"Rentabilidade líquida no período: {rendimento_liquido_percentual:.2f}%")
    print(f"Rentabilidade líquida anualizada: {rendimento_liquido_anual:.2f}% a.a.")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main() 