#!/usr/bin/env python3
"""
Script para verificar se a lista de taxas SELIC apuradas está completa e correta.
Detecta possíveis dias faltantes e inconsistências nos valores.
"""

import sys
import os
from datetime import datetime, date, timedelta
import json
import argparse

# Importa as funções necessárias do módulo app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.selic import ensure_rates_in_cache
from app.cache import load_cache, save_cache, get_cached_rates
from app.holidays import is_holiday, is_business_day
from app.logger import logger

def parse_arguments():
    """Parse os argumentos da linha de comando."""
    parser = argparse.ArgumentParser(description='Verifica a completude e consistência da lista SELIC apurada.')
    parser.add_argument('--data-inicial', type=str, default='01/01/2023',
                      help='Data inicial no formato DD/MM/YYYY (padrão: 01/01/2023)')
    parser.add_argument('--data-final', type=str, default=None,
                      help='Data final no formato DD/MM/YYYY (padrão: data atual)')
    parser.add_argument('--corrigir', action='store_true',
                      help='Corrige automaticamente inconsistências encontradas')
    parser.add_argument('--mostrar-problemas', action='store_true',
                      help='Mostra detalhes dos problemas encontrados')
    parser.add_argument('--verbose', action='store_true',
                      help='Mostra informações detalhadas durante a execução')
    
    return parser.parse_args()

def converter_data(data_str):
    """Converte uma string de data para um objeto date."""
    return datetime.strptime(data_str, '%d/%m/%Y').date()

def verificar_dias_faltantes(taxas_diarias, data_inicial, data_final):
    """Verifica se existem dias faltantes no período."""
    dias_faltantes = []
    current_date = data_inicial
    
    while current_date <= data_final:
        if current_date not in taxas_diarias:
            dias_faltantes.append(current_date)
        current_date += timedelta(days=1)
    
    return dias_faltantes

def verificar_inconsistencias(taxas_diarias):
    """Verifica inconsistências nos valores das taxas."""
    inconsistencias = []
    
    for data, taxa in taxas_diarias.items():
        # Verifica se é dia útil
        if is_business_day(data):
            # Dia útil deveria ter taxa > 0
            if taxa == 0:
                inconsistencias.append({
                    "data": data,
                    "tipo": "dia_util_com_taxa_zero",
                    "descricao": f"Dia útil {data.strftime('%d/%m/%Y')} com taxa zero"
                })
        else:
            # Dia não útil deveria ter taxa 0
            if taxa > 0:
                inconsistencias.append({
                    "data": data,
                    "tipo": "dia_nao_util_com_taxa_positiva",
                    "descricao": f"Dia não útil {data.strftime('%d/%m/%Y')} com taxa positiva: {taxa}"
                })
            
            # Verifica se temos o motivo correto (final de semana ou feriado)
            if data.weekday() >= 5:  # Final de semana
                pass  # Tudo ok, é final de semana
            else:
                eh_feriado, nome_feriado = is_holiday(data)
                if not eh_feriado:
                    inconsistencias.append({
                        "data": data,
                        "tipo": "dia_util_marcado_como_nao_util",
                        "descricao": f"Dia {data.strftime('%d/%m/%Y')} marcado como não útil, mas não é final de semana nem feriado"
                    })
    
    return inconsistencias

def corrigir_problemas(dias_faltantes, inconsistencias, taxas_diarias):
    """Tenta corrigir problemas encontrados na lista."""
    if dias_faltantes:
        print(f"Adicionando {len(dias_faltantes)} dias faltantes ao cache...")
        data_inicial = min(dias_faltantes)
        data_final = max(dias_faltantes)
        
        try:
            taxas_diarias = ensure_rates_in_cache(data_inicial, data_final)
            print(f"Dias faltantes adicionados com sucesso!")
        except Exception as e:
            print(f"Erro ao adicionar dias faltantes: {e}")
    
    if inconsistencias:
        print(f"Corrigindo {len(inconsistencias)} inconsistências...")
        cache_alterado = False
        taxas_diarias, registros_originais = get_cached_rates()
        registros_corrigidos = []
        
        # Mapeia datas para IDs de registros
        registros_por_data = {}
        for registro in registros_originais:
            try:
                data_str = registro.get("dataCotacao")
                if data_str:
                    dt = datetime.strptime(data_str, '%d/%m/%Y').date()
                    registros_por_data[dt] = registro
            except Exception:
                pass
        
        # Corrige cada inconsistência
        for inconsistencia in inconsistencias:
            data = inconsistencia["data"]
            if data in registros_por_data:
                registro = registros_por_data[data]
                
                if inconsistencia["tipo"] == "dia_util_com_taxa_zero":
                    print(f"Removendo registro de dia útil com taxa zero: {data.strftime('%d/%m/%Y')}")
                    # Removemos o registro para que o sistema busque novamente
                    registros_por_data.pop(data)
                    cache_alterado = True
                    
                elif inconsistencia["tipo"] == "dia_nao_util_com_taxa_positiva":
                    print(f"Corrigindo taxa para zero em dia não útil: {data.strftime('%d/%m/%Y')}")
                    registro["fatorDiario"] = "0"
                    registro["isBusinessDay"] = False
                    
                    if data.weekday() >= 5:
                        registro["reason"] = "FINAL_DE_SEMANA"
                    else:
                        _, nome_feriado = is_holiday(data)
                        if nome_feriado:
                            registro["reason"] = f"FERIADO: {nome_feriado}"
                        else:
                            registro["reason"] = "DIA_NAO_UTIL"
                    
                    taxas_diarias[data] = 0.0
                    cache_alterado = True
                    
                elif inconsistencia["tipo"] == "dia_util_marcado_como_nao_util":
                    print(f"Removendo registro inconsistente: {data.strftime('%d/%m/%Y')}")
                    # Removemos o registro para que o sistema busque novamente
                    registros_por_data.pop(data)
                    cache_alterado = True
        
        # Salva o cache atualizado
        if cache_alterado:
            registros_corrigidos = list(registros_por_data.values())
            try:
                save_cache({"registros": registros_corrigidos})
                print(f"Cache atualizado com {len(registros_corrigidos)} registros após correção.")
                # Atualiza novamente as datas removidas
                data_inicial = min(inconsistencias, key=lambda x: x["data"])["data"]
                data_final = max(inconsistencias, key=lambda x: x["data"])["data"]
                taxas_diarias = ensure_rates_in_cache(data_inicial, data_final)
                print("Dados reconstruídos com sucesso!")
            except Exception as e:
                print(f"Erro ao salvar cache corrigido: {e}")
        else:
            print("Nenhuma alteração necessária no cache.")
    
    return taxas_diarias

def mostrar_resumo_verificacao(dias_faltantes, inconsistencias):
    """Mostra um resumo da verificação realizada."""
    print("\n=== RESUMO DA VERIFICAÇÃO ===")
    
    if not dias_faltantes and not inconsistencias:
        print("✅ Lista SELIC apurada completa e consistente!")
        return
    
    if dias_faltantes:
        print(f"❌ Encontrados {len(dias_faltantes)} dias faltantes:")
        if len(dias_faltantes) <= 10:
            for data in sorted(dias_faltantes):
                print(f"  - {data.strftime('%d/%m/%Y')}")
        else:
            for data in sorted(dias_faltantes)[:5]:
                print(f"  - {data.strftime('%d/%m/%Y')}")
            print(f"  - ...")
            for data in sorted(dias_faltantes)[-5:]:
                print(f"  - {data.strftime('%d/%m/%Y')}")
    
    if inconsistencias:
        print(f"❌ Encontradas {len(inconsistencias)} inconsistências:")
        
        # Agrupa por tipo
        por_tipo = {}
        for inc in inconsistencias:
            tipo = inc["tipo"]
            if tipo not in por_tipo:
                por_tipo[tipo] = []
            por_tipo[tipo].append(inc)
        
        # Mostra resumo por tipo
        for tipo, incs in por_tipo.items():
            print(f"  - {len(incs)} do tipo '{tipo}'")
        
        # Mostra detalhes se solicitado
        if len(inconsistencias) <= 20:
            print("\nDetalhes das inconsistências:")
            for inc in sorted(inconsistencias, key=lambda x: x["data"]):
                print(f"  - {inc['descricao']}")

def main():
    """Função principal do script."""
    args = parse_arguments()
    
    # Configura o logger para maior verbosidade se solicitado
    if args.verbose:
        logger.setLevel('DEBUG')
    
    # Define o período para verificação
    data_inicial = converter_data(args.data_inicial)
    
    if args.data_final:
        data_final = converter_data(args.data_final)
    else:
        data_final = date.today()
    
    print(f"Verificando lista SELIC apurada para o período de {data_inicial.strftime('%d/%m/%Y')} a {data_final.strftime('%d/%m/%Y')}")
    
    # Carrega as taxas atuais
    taxas_diarias, _ = get_cached_rates()
    print(f"Cache carregado com {len(taxas_diarias)} registros.")
    
    # Verifica dias faltantes
    dias_faltantes = verificar_dias_faltantes(taxas_diarias, data_inicial, data_final)
    print(f"Verificação de dias faltantes: {len(dias_faltantes)} dias faltando.")
    
    # Verifica inconsistências
    inconsistencias = verificar_inconsistencias(taxas_diarias)
    print(f"Verificação de inconsistências: {len(inconsistencias)} problemas encontrados.")
    
    # Mostra resumo da verificação
    if args.mostrar_problemas:
        mostrar_resumo_verificacao(dias_faltantes, inconsistencias)
    
    # Corrige problemas se solicitado
    if args.corrigir and (dias_faltantes or inconsistencias):
        print("\n=== INICIANDO CORREÇÃO DE PROBLEMAS ===")
        taxas_diarias = corrigir_problemas(dias_faltantes, inconsistencias, taxas_diarias)
        
        # Verifica novamente após correção
        dias_faltantes_apos = verificar_dias_faltantes(taxas_diarias, data_inicial, data_final)
        inconsistencias_apos = verificar_inconsistencias(taxas_diarias)
        
        print("\n=== RESULTADOS APÓS CORREÇÃO ===")
        print(f"Dias faltantes: {len(dias_faltantes)} → {len(dias_faltantes_apos)}")
        print(f"Inconsistências: {len(inconsistencias)} → {len(inconsistencias_apos)}")
        
        if not dias_faltantes_apos and not inconsistencias_apos:
            print("✅ Todos os problemas foram corrigidos com sucesso!")
        else:
            print("⚠️ Alguns problemas persistiram após a correção. Pode ser necessário executar o script novamente.")
    
    # Sugere próximos passos
    if not args.corrigir and (dias_faltantes or inconsistencias):
        print("\nPara corrigir os problemas encontrados, execute o script novamente com a opção --corrigir")

if __name__ == "__main__":
    main() 