#!/usr/bin/env python3
"""
Script para visualizar o cache atual da SELIC apurada.
Permite diferentes tipos de visualização e filtragem dos dados.
"""

import sys
import os
from datetime import datetime, date, timedelta
import json
import argparse
import calendar
from tabulate import tabulate

# Importa as funções necessárias do módulo app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.cache import get_cached_rates
from app.holidays import is_holiday, is_business_day
from app.logger import logger

def parse_arguments():
    """Parse os argumentos da linha de comando."""
    parser = argparse.ArgumentParser(description='Visualiza o cache atual da SELIC apurada.')
    parser.add_argument('--formato', type=str, choices=['lista', 'tabela', 'mensal', 'estatisticas'], default='estatisticas',
                      help='Formato de visualização (padrão: estatisticas)')
    parser.add_argument('--filtro', type=str, choices=['todos', 'uteis', 'nao-uteis', 'feriados', 'finais-semana'], default='todos',
                      help='Filtro de dias a mostrar (padrão: todos)')
    parser.add_argument('--data-inicial', type=str, default=None,
                      help='Data inicial no formato DD/MM/YYYY (padrão: primeiro registro)')
    parser.add_argument('--data-final', type=str, default=None,
                      help='Data final no formato DD/MM/YYYY (padrão: último registro)')
    parser.add_argument('--mes', type=int, default=None,
                      help='Mês específico para visualização (1-12)')
    parser.add_argument('--ano', type=int, default=None,
                      help='Ano específico para visualização')
    parser.add_argument('--limit', type=int, default=10,
                      help='Limite de registros a mostrar (padrão: 10)')
    parser.add_argument('--verbose', action='store_true',
                      help='Mostra informações detalhadas durante a execução')
    
    return parser.parse_args()

def converter_data(data_str):
    """Converte uma string de data para um objeto date."""
    return datetime.strptime(data_str, '%d/%m/%Y').date()

def classificar_dia(data, taxa):
    """Classifica o dia conforme seu tipo."""
    if data.weekday() >= 5:
        return "Final de Semana"
    
    eh_feriado, nome_feriado = is_holiday(data)
    if eh_feriado:
        return f"Feriado: {nome_feriado}"
    
    if taxa == 0:
        return "Não Útil (Outro)"
    
    return "Dia Útil"

def filtrar_registros(taxas_diarias, filtro, data_inicial=None, data_final=None, mes=None, ano=None):
    """Filtra os registros conforme os critérios especificados."""
    # Converte para lista de tuplas (data, taxa)
    registros = list(taxas_diarias.items())
    registros.sort(key=lambda x: x[0])  # Ordena por data
    
    # Filtra por período
    if data_inicial:
        registros = [(d, t) for d, t in registros if d >= data_inicial]
    
    if data_final:
        registros = [(d, t) for d, t in registros if d <= data_final]
    
    # Filtra por mês/ano
    if mes and ano:
        registros = [(d, t) for d, t in registros if d.month == mes and d.year == ano]
    elif mes:
        registros = [(d, t) for d, t in registros if d.month == mes]
    elif ano:
        registros = [(d, t) for d, t in registros if d.year == ano]
    
    # Filtra por tipo de dia
    if filtro == 'uteis':
        registros = [(d, t) for d, t in registros if is_business_day(d)]
    elif filtro == 'nao-uteis':
        registros = [(d, t) for d, t in registros if not is_business_day(d)]
    elif filtro == 'feriados':
        registros = [(d, t) for d, t in registros if not d.weekday() >= 5 and not is_business_day(d)]
    elif filtro == 'finais-semana':
        registros = [(d, t) for d, t in registros if d.weekday() >= 5]
    
    return registros

def mostrar_lista(registros, limit=10):
    """Mostra os registros em formato de lista."""
    print("\n=== LISTA DE TAXAS SELIC APURADAS ===")
    
    total = len(registros)
    if total == 0:
        print("Nenhum registro encontrado com os critérios especificados.")
        return
    
    print(f"Total de registros: {total}")
    
    if total <= limit * 2:
        # Mostra todos os registros
        for data, taxa in registros:
            tipo = classificar_dia(data, taxa)
            print(f"{data.strftime('%d/%m/%Y')} ({tipo}): {taxa:.8f}")
    else:
        # Mostra primeiros e últimos registros
        print("\n=== PRIMEIROS REGISTROS ===")
        for data, taxa in registros[:limit]:
            tipo = classificar_dia(data, taxa)
            print(f"{data.strftime('%d/%m/%Y')} ({tipo}): {taxa:.8f}")
        
        print("\n=== ÚLTIMOS REGISTROS ===")
        for data, taxa in registros[-limit:]:
            tipo = classificar_dia(data, taxa)
            print(f"{data.strftime('%d/%m/%Y')} ({tipo}): {taxa:.8f}")

def mostrar_tabela(registros, limit=10):
    """Mostra os registros em formato tabular."""
    if not registros:
        print("Nenhum registro encontrado com os critérios especificados.")
        return
    
    total = len(registros)
    print(f"\n=== TABELA DE TAXAS SELIC APURADAS (Total: {total}) ===\n")
    
    # Prepara os dados
    table_data = []
    dias_para_mostrar = []
    
    if total <= limit * 2:
        dias_para_mostrar = registros
    else:
        dias_para_mostrar = registros[:limit] + registros[-limit:]
    
    for data, taxa in dias_para_mostrar:
        tipo = classificar_dia(data, taxa)
        tipo_curto = tipo[:15] + "..." if len(tipo) > 18 else tipo
        table_data.append([
            data.strftime('%d/%m/%Y'),
            data.strftime('%a'),  # Dia da semana abreviado
            tipo_curto,
            f"{taxa:.8f}"
        ])
    
    # Mostra a tabela
    headers = ["Data", "Dia", "Tipo", "Taxa Selic"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))

def mostrar_mensal(registros, mes=None, ano=None):
    """Mostra os registros em formato de calendário mensal."""
    if not registros:
        print("Nenhum registro encontrado com os critérios especificados.")
        return
    
    # Se não especificou mês/ano, usa o mês/ano do primeiro registro
    if not mes or not ano:
        if registros:
            first_date = registros[0][0]
            mes = mes or first_date.month
            ano = ano or first_date.year
        else:
            hoje = date.today()
            mes = mes or hoje.month
            ano = ano or hoje.year
    
    # Converte para dicionário para acesso rápido
    taxas_dict = {data: taxa for data, taxa in registros}
    
    # Obtém calendário do mês
    cal = calendar.monthcalendar(ano, mes)
    nome_mes = calendar.month_name[mes]
    
    print(f"\n=== TAXAS SELIC PARA {nome_mes.upper()} DE {ano} ===\n")
    
    # Cabeçalho
    headers = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]
    print("{:^9} {:^9} {:^9} {:^9} {:^9} {:^9} {:^9}".format(*headers))
    
    # Conteúdo do calendário
    for semana in cal:
        linha = []
        for dia in semana:
            if dia == 0:
                linha.append(" " * 9)
                continue
                
            data_atual = date(ano, mes, dia)
            
            # Verifica se temos a taxa para esta data
            if data_atual in taxas_dict:
                taxa = taxas_dict[data_atual]
                # Formata a célula
                if taxa > 0:
                    valor = f"{dia:2d}\n{taxa:.6f}"
                else:
                    # Se é dia não útil, mostra diferente
                    if data_atual.weekday() >= 5:
                        valor = f"{dia:2d}\n(Fim Sem)"
                    else:
                        eh_feriado, _ = is_holiday(data_atual)
                        if eh_feriado:
                            valor = f"{dia:2d}\n(Feriado)"
                        else:
                            valor = f"{dia:2d}\n(Não Útil)"
            else:
                valor = f"{dia:2d}\n(s/ taxa)"
            
            linha.append(f"{valor:^9}")
        
        print("{} {} {} {} {} {} {}".format(*linha))
        print()  # Linha em branco entre semanas

def mostrar_estatisticas(registros):
    """Mostra estatísticas dos registros."""
    if not registros:
        print("Nenhum registro encontrado com os critérios especificados.")
        return
    
    # Extrai datas e valores
    datas = [data for data, _ in registros]
    taxas = [taxa for _, taxa in registros]
    
    # Estatísticas básicas
    data_inicial = min(datas)
    data_final = max(datas)
    total_dias = len(registros)
    
    dias_uteis = sum(1 for data, taxa in registros if taxa > 0)
    dias_nao_uteis = sum(1 for data, taxa in registros if taxa == 0)
    
    # Taxas não-zero para cálculos estatísticos
    taxas_nao_zero = [t for t in taxas if t > 0]
    if taxas_nao_zero:
        media = sum(taxas_nao_zero) / len(taxas_nao_zero)
        minima = min(taxas_nao_zero)
        maxima = max(taxas_nao_zero)
    else:
        media = minima = maxima = 0
    
    # Contagem por tipo de dia
    finais_semana = sum(1 for data, _ in registros if data.weekday() >= 5)
    feriados = sum(1 for data, _ in registros if data.weekday() < 5 and not is_business_day(data))
    
    # Mostra resultados
    print("\n=== ESTATÍSTICAS DA LISTA SELIC APURADA ===\n")
    
    print(f"Período: {data_inicial.strftime('%d/%m/%Y')} a {data_final.strftime('%d/%m/%Y')}")
    print(f"Total de dias: {total_dias}")
    print(f"Dias úteis: {dias_uteis} ({dias_uteis/total_dias*100:.1f}%)")
    print(f"Dias não úteis: {dias_nao_uteis} ({dias_nao_uteis/total_dias*100:.1f}%)")
    print(f"  - Finais de semana: {finais_semana} ({finais_semana/total_dias*100:.1f}%)")
    print(f"  - Feriados: {feriados} ({feriados/total_dias*100:.1f}%)")
    
    if taxas_nao_zero:
        print("\nEstatísticas das taxas (apenas dias úteis):")
        print(f"  - Taxa média: {media:.8f}")
        print(f"  - Taxa mínima: {minima:.8f}")
        print(f"  - Taxa máxima: {maxima:.8f}")
    
    # Consistência dos registros
    dias_periodo = (data_final - data_inicial).days + 1
    if dias_periodo != total_dias:
        print(f"\n⚠️ ALERTA: O período deveria ter {dias_periodo} dias, mas foram encontrados {total_dias} registros.")
        print(f"    Há {dias_periodo - total_dias} dias faltantes no período.")

def main():
    """Função principal do script."""
    args = parse_arguments()
    
    # Configura o logger para maior verbosidade se solicitado
    if args.verbose:
        logger.setLevel('DEBUG')
    
    # Carrega as taxas atuais
    taxas_diarias, _ = get_cached_rates()
    print(f"Cache carregado com {len(taxas_diarias)} registros.")
    
    # Converte datas se especificadas
    data_inicial = converter_data(args.data_inicial) if args.data_inicial else None
    data_final = converter_data(args.data_final) if args.data_final else None
    
    # Filtra os registros
    registros = filtrar_registros(
        taxas_diarias, 
        args.filtro, 
        data_inicial, 
        data_final, 
        args.mes, 
        args.ano
    )
    
    # Mostra os resultados no formato solicitado
    if args.formato == 'lista':
        mostrar_lista(registros, args.limit)
    elif args.formato == 'tabela':
        try:
            mostrar_tabela(registros, args.limit)
        except ImportError:
            print("Erro: O módulo 'tabulate' não está instalado. Instale com 'pip install tabulate'.")
            mostrar_lista(registros, args.limit)
    elif args.formato == 'mensal':
        mostrar_mensal(registros, args.mes, args.ano)
    else:  # estatisticas
        mostrar_estatisticas(registros)

if __name__ == "__main__":
    main() 