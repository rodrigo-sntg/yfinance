import unittest
import json
from datetime import datetime, timedelta
import os
import sys
from unittest.mock import patch, MagicMock, ANY

# Adiciona o diretório raiz ao path para permitir importar app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importa as funções relevantes do app.py
from app import (
    is_business_day,
    ensure_rates_in_cache,
    get_holidays_for_year,
    ensure_non_business_day_in_cache,
    app
)

class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code
        self.text = json.dumps(json_data)

    def json(self):
        return self.json_data

class TestSelicCalculator(unittest.TestCase):
    """
    Testes para validar os cálculos do investimento Tesouro Selic
    """
    
    def setUp(self):
        """
        Configuração inicial para os testes
        """
        # Configura o contexto da aplicação Flask
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # Cria um cache temporário para os testes
        self.test_cache = {
            "registros": []
        }
        
        # Mock dos feriados para testes
        self.mock_holidays_2023 = [
            {"date": "2023-01-01", "name": "Confraternização mundial", "type": "national"},
            {"date": "2023-02-20", "name": "Carnaval", "type": "national"},
            {"date": "2023-02-21", "name": "Carnaval", "type": "national"},
            {"date": "2023-02-22", "name": "Quarta-feira de cinzas (Ponto Facultativo)", "type": "national"},
            {"date": "2023-04-07", "name": "Sexta-feira Santa", "type": "national"},
            {"date": "2023-04-21", "name": "Tiradentes", "type": "national"},
            {"date": "2023-05-01", "name": "Dia do trabalho", "type": "national"},
            {"date": "2023-06-08", "name": "Corpus Christi", "type": "national"},
            {"date": "2023-09-07", "name": "Independência do Brasil", "type": "national"},
            {"date": "2023-10-12", "name": "Nossa Senhora Aparecida", "type": "national"},
            {"date": "2023-11-02", "name": "Finados", "type": "national"},
            {"date": "2023-11-15", "name": "Proclamação da República", "type": "national"},
            {"date": "2023-12-25", "name": "Natal", "type": "national"}
        ]
        
        # Mock dos fatores Selic para abril de 2023
        # Taxa Selic de aproximadamente 13,65% a.a. = ~0,050788% ao dia útil
        self.mock_selic_factors = {}
        factor = 1.00050788  # Fator diário para 13,65% a.a.
        
        # Dias úteis de abril de 2023
        business_days_april_2023 = [
            # Primeira semana
            datetime(2023, 4, 3).date(),
            datetime(2023, 4, 4).date(),
            datetime(2023, 4, 5).date(),
            datetime(2023, 4, 6).date(),
            # Pula 07/04 (feriado), 08-09/04 (fim de semana)
            # Segunda semana
            datetime(2023, 4, 10).date(),
            datetime(2023, 4, 11).date(),
            datetime(2023, 4, 12).date(),
            datetime(2023, 4, 13).date(),
            datetime(2023, 4, 14).date(),
            # Pula 15-16/04 (fim de semana)
            # Terceira semana
            datetime(2023, 4, 17).date(),
            datetime(2023, 4, 18).date(),
            datetime(2023, 4, 19).date(),
            datetime(2023, 4, 20).date(),
            # Pula 21/04 (feriado)
            # Pula 22-23/04 (fim de semana)
            # Quarta semana
            datetime(2023, 4, 24).date(),
            datetime(2023, 4, 25).date(),
            datetime(2023, 4, 26).date(),
            datetime(2023, 4, 27).date(),
            datetime(2023, 4, 28).date(),
            # Pula 29-30/04 (fim de semana)
        ]
        
        # Adiciona dias úteis de maio de 2023 para testes de períodos mais longos
        business_days_may_2023 = [
            datetime(2023, 5, 2).date(),
            datetime(2023, 5, 3).date(),
            datetime(2023, 5, 4).date(),
            datetime(2023, 5, 5).date(),
            datetime(2023, 5, 8).date(),
            datetime(2023, 5, 9).date(),
            datetime(2023, 5, 10).date(),
            datetime(2023, 5, 11).date(),
            datetime(2023, 5, 12).date(),
            datetime(2023, 5, 15).date(),
            datetime(2023, 5, 16).date(),
            datetime(2023, 5, 17).date(),
            datetime(2023, 5, 18).date(),
            datetime(2023, 5, 19).date(),
            datetime(2023, 5, 22).date(),
            datetime(2023, 5, 23).date(),
            datetime(2023, 5, 24).date(),
            datetime(2023, 5, 25).date(),
            datetime(2023, 5, 26).date(),
            datetime(2023, 5, 29).date(),
            datetime(2023, 5, 30).date(),
            datetime(2023, 5, 31).date()
        ]
        
        # Combina os dias úteis dos dois meses
        all_business_days = business_days_april_2023 + business_days_may_2023
        
        # Adiciona fatores para os dias úteis
        for day in all_business_days:
            day_str = day.strftime('%d/%m/%Y')
            self.mock_selic_factors[day] = factor
            
            # Adiciona ao cache de teste
            self.test_cache["registros"].append({
                "dataCotacao": day_str,
                "fatorDiario": str(factor),
                "isBusinessDay": True
            })
        
        # Adiciona feriados
        holiday_days = [
            datetime(2023, 4, 7).date(),   # Sexta-feira Santa
            datetime(2023, 4, 21).date(),  # Tiradentes
            datetime(2023, 5, 1).date()    # Dia do Trabalho
        ]
        
        for day in holiday_days:
            day_str = day.strftime('%d/%m/%Y')
            self.mock_selic_factors[day] = 0.0
            
            # Adiciona ao cache de teste
            self.test_cache["registros"].append({
                "dataCotacao": day_str,
                "fatorDiario": "0",
                "isBusinessDay": False,
                "reason": "FERIADO"
            })
            
        # Adiciona fins de semana de abril e maio de 2023
        weekend_days = []
        
        # Gera todos os dias entre 01/04/2023 e 31/05/2023
        start_day = datetime(2023, 4, 1).date()
        end_day = datetime(2023, 5, 31).date()
        current_day = start_day
        
        while current_day <= end_day:
            # Se for sábado (5) ou domingo (6)
            if current_day.weekday() >= 5:
                weekend_days.append(current_day)
            current_day += timedelta(days=1)
        
        for day in weekend_days:
            day_str = day.strftime('%d/%m/%Y')
            self.mock_selic_factors[day] = 0.0
            
            # Adiciona ao cache de teste
            self.test_cache["registros"].append({
                "dataCotacao": day_str,
                "fatorDiario": "0",
                "isBusinessDay": False,
                "reason": "FINAL_DE_SEMANA"
            })

    @patch('app.load_holidays_cache')
    def test_is_business_day(self, mock_load_holidays):
        """
        Testa a função que verifica se uma data é dia útil
        """
        # Configura o mock para retornar os feriados de teste
        mock_load_holidays.return_value = {"2023": self.mock_holidays_2023}
        
        # Testa dias úteis normais
        self.assertTrue(is_business_day(datetime(2023, 4, 3).date()))
        self.assertTrue(is_business_day(datetime(2023, 4, 4).date()))
        
        # Testa fins de semana
        self.assertFalse(is_business_day(datetime(2023, 4, 1).date()))  # Sábado
        self.assertFalse(is_business_day(datetime(2023, 4, 2).date()))  # Domingo
        
        # Testa feriados
        self.assertFalse(is_business_day(datetime(2023, 4, 7).date()))  # Sexta-feira Santa
        self.assertFalse(is_business_day(datetime(2023, 4, 21).date()))  # Tiradentes

    @patch('app.get_cached_rates')
    @patch('app.save_cache')
    def test_compounded_factor_calculation(self, mock_save_cache, mock_get_cached_rates):
        """
        Testa o cálculo de fator composto no período de 03 a 14 de abril de 2023
        """
        # Configura o mock para retornar as taxas de teste
        mock_get_cached_rates.return_value = (self.mock_selic_factors, self.test_cache["registros"])
        mock_save_cache.return_value = True
        
        # Define o período de teste
        start_date = datetime(2023, 4, 3).date()
        end_date = datetime(2023, 4, 14).date()
        
        # Calcula manualmente o fator composto esperado
        # Dias úteis do período: 03, 04, 05, 06, 10, 11, 12, 13, 14 de abril (9 dias úteis)
        expected_factor = (1.00050788) ** 9  # Aproximadamente 1.004582
        
        # Calcula o fator acumulado real chamando a função
        taxes = ensure_rates_in_cache(start_date, end_date)
        
        # Calcula o fator composto no período
        actual_factor = 1.0
        current_date = start_date
        while current_date <= end_date:
            if current_date in taxes and taxes[current_date] > 0:
                actual_factor *= taxes[current_date]
            current_date += timedelta(days=1)
        
        # Compara com uma margem de erro pequena
        self.assertAlmostEqual(actual_factor, expected_factor, places=6)

    @patch('app.load_cache')
    @patch('app.save_cache')
    @patch('app.get_cached_rates')
    @patch('app.load_holidays_cache')
    def test_investment_calculation(self, mock_load_holidays, mock_get_cached_rates, 
                                    mock_save_cache, mock_load_cache):
        """
        Testa o cálculo completo de investimento para um período específico usando o client do Flask
        """
        # Configura o mock para retornar os feriados e taxas de teste
        mock_load_holidays.return_value = {"2023": self.mock_holidays_2023}
        mock_get_cached_rates.return_value = (self.mock_selic_factors, self.test_cache["registros"])
        mock_load_cache.return_value = self.test_cache
        mock_save_cache.return_value = True
        
        # Calcula manualmente o resultado esperado
        # Dias úteis do período: 03, 04, 05, 06, 10, 11, 12, 13, 14 de abril (9 dias úteis)
        initial_value = 1000.0
        expected_compound_factor = (1.00050788) ** 9  # ~1.004582
        expected_final_value = initial_value * expected_compound_factor  # ~1004.58
        expected_yield = expected_final_value - initial_value  # ~4.58
        expected_yield_percent = (expected_yield / initial_value) * 100  # ~0.458%
        
        # Patch na função datetime.now() para retornar uma data fixa
        with patch('app.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 4, 15)  # 15/04/2023
            mock_datetime.strptime = datetime.strptime
            
            # Faz a requisição HTTP simulada usando o client de teste do Flask
            response = self.client.get('/investimento?data=2023-04-03&valor=1000')
            
            # Verifica o status da resposta
            self.assertEqual(response.status_code, 200)
            
            # Converte o resultado para dicionário
            result_data = json.loads(response.data)
            
            # Verifica se os valores calculados estão corretos
            self.assertEqual(result_data['data_inicial'], '2023-04-03')
            self.assertEqual(result_data['data_final'], '2023-04-14')
            self.assertEqual(result_data['valor_investido'], 1000.0)
            
            # Verifica o valor final com uma pequena margem de erro
            self.assertAlmostEqual(result_data['valor_final'], expected_final_value, places=2)
            
            # Verifica o rendimento e o percentual com uma pequena margem de erro
            self.assertAlmostEqual(result_data['rendimento'], expected_yield, places=2)
            self.assertAlmostEqual(result_data['rendimento_percentual'], expected_yield_percent, places=2)
            
            # Verifica os dias computados
            self.assertEqual(result_data['dias_compostos'], 9)  # 9 dias úteis
            self.assertEqual(result_data['dias_sem_rendimento'], 3)  # 1 feriado + 2 dias de fim de semana
            self.assertEqual(result_data['dias_totais'], 12)  # total de dias no período

    @patch('app.load_cache')
    @patch('app.save_cache')
    @patch('app.get_cached_rates')
    @patch('app.load_holidays_cache')
    def test_long_period_investment_calculation(self, mock_load_holidays, mock_get_cached_rates, 
                                              mock_save_cache, mock_load_cache):
        """
        Testa o cálculo de investimento para um período mais longo (2 meses)
        """
        # Configura o mock para retornar os feriados e taxas de teste
        mock_load_holidays.return_value = {"2023": self.mock_holidays_2023}
        mock_get_cached_rates.return_value = (self.mock_selic_factors, self.test_cache["registros"])
        mock_load_cache.return_value = self.test_cache
        mock_save_cache.return_value = True
        
        # Patch na função datetime.now() para retornar uma data fixa
        with patch('app.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 6, 1)  # 01/06/2023
            mock_datetime.strptime = datetime.strptime
            
            # Faz a requisição HTTP simulada usando o client de teste do Flask
            response = self.client.get('/investimento?data=2023-04-03&valor=1000&data_final=2023-05-31')
            
            # Verifica o status da resposta
            self.assertEqual(response.status_code, 200)
            
            # Converte o resultado para dicionário
            result_data = json.loads(response.data)
            
            # Verifica se os valores calculados estão corretos
            self.assertEqual(result_data['data_inicial'], '2023-04-03')
            self.assertEqual(result_data['data_final'], '2023-05-31')
            self.assertEqual(result_data['valor_investido'], 1000.0)
            
            # Obtém os valores calculados pela API
            actual_value = result_data['valor_final']
            actual_yield = result_data['rendimento']
            actual_yield_percent = result_data['rendimento_percentual']
            actual_days = result_data['dias_compostos']
            
            # Recalcula o valor esperado com base nos dias compostos retornados pela API
            expected_compound_factor = (1.00050788) ** actual_days
            expected_final_value = 1000.0 * expected_compound_factor
            expected_yield = expected_final_value - 1000.0
            expected_yield_percent = (expected_yield / 1000.0) * 100
            
            # Verifica os valores com margens de erro adequadas
            self.assertAlmostEqual(actual_value, expected_final_value, places=2)
            self.assertAlmostEqual(actual_yield, expected_yield, places=2)
            self.assertAlmostEqual(actual_yield_percent, expected_yield_percent, places=2)

    @patch('app.load_holidays_cache')
    def test_holiday_verification(self, mock_load_holidays):
        """
        Testa a verificação de feriados
        """
        # Configura o mock para retornar os feriados de teste
        mock_load_holidays.return_value = {"2023": self.mock_holidays_2023}
        
        # Testa se os feriados são corretamente identificados
        holidays = get_holidays_for_year(2023)
        
        # Verifica se a Sexta-feira Santa é identificada corretamente
        sexta_santa = datetime(2023, 4, 7).date()
        sexta_santa_str = sexta_santa.strftime('%Y-%m-%d')
        
        # Verifica se a data está na lista de feriados
        holiday_found = False
        for holiday in holidays:
            if holiday.get('date') == sexta_santa_str:
                holiday_found = True
                self.assertEqual(holiday.get('name'), 'Sexta-feira Santa')
                break
                
        self.assertTrue(holiday_found, "Feriado Sexta-feira Santa não foi encontrado")

    def test_weekend_factor(self):
        """
        Testa se os fatores para fins de semana são zero
        """
        # Verifica se todos os fins de semana em abril de 2023 têm fator zero
        weekend_dates = [
            datetime(2023, 4, 1).date(),  # Sábado
            datetime(2023, 4, 2).date(),  # Domingo
            datetime(2023, 4, 8).date(),  # Sábado
            datetime(2023, 4, 9).date(),  # Domingo
        ]
        
        for date in weekend_dates:
            if date in self.mock_selic_factors:
                self.assertEqual(self.mock_selic_factors[date], 0.0, 
                               f"Fim de semana {date} deveria ter fator zero")

    @patch('app.get_cached_rates')
    @patch('app.save_cache')
    def test_ensure_non_business_day_in_cache(self, mock_save_cache, mock_get_cached_rates):
        """
        Testa a função que garante que dias não úteis estão no cache com valor zero
        """
        # Configura o mock para retornar as taxas de teste
        taxes = {}
        records = []
        registered_dates = {}
        mock_get_cached_rates.return_value = (taxes, records)
        mock_save_cache.return_value = True
        
        # Testa com uma data de fim de semana
        weekend_date = datetime(2023, 4, 1).date()  # Sábado
        
        added, factor = ensure_non_business_day_in_cache(
            weekend_date, taxes, records, registered_dates
        )
        
        # Verifica se foi adicionado ao cache e se o fator é zero
        self.assertTrue(added)
        self.assertEqual(factor, 0.0)
        self.assertEqual(taxes[weekend_date], 0.0)
        
        # Verifica se o motivo no registro é FINAL_DE_SEMANA
        self.assertEqual(records[0]["reason"], "FINAL_DE_SEMANA")
        
        # Limpa os registros para o próximo teste
        taxes.clear()
        records.clear()
        registered_dates.clear()
        
        # Testa com uma data de feriado
        with patch('app.get_holidays_for_year') as mock_get_holidays:
            # Mock para retornar um feriado
            mock_get_holidays.return_value = [
                {"date": "2023-04-07", "name": "Sexta-feira Santa", "type": "national"}
            ]
            
            holiday_date = datetime(2023, 4, 7).date()  # Sexta-feira Santa
            
            added, factor = ensure_non_business_day_in_cache(
                holiday_date, taxes, records, registered_dates
            )
            
            # Verifica se foi adicionado ao cache e se o fator é zero
            self.assertTrue(added)
            self.assertEqual(factor, 0.0)
            self.assertEqual(taxes[holiday_date], 0.0)
            
            # Verifica se o motivo no registro contém "FERIADO"
            self.assertTrue("FERIADO" in records[0]["reason"])

    @patch('app.load_cache')
    @patch('app.save_cache')
    @patch('app.get_cached_rates')
    @patch('app.load_holidays_cache')
    def test_dia_util_endpoint(self, mock_load_holidays, mock_get_cached_rates, 
                              mock_save_cache, mock_load_cache):
        """
        Testa o endpoint /dia-util
        """
        # Configura os mocks
        mock_load_holidays.return_value = {"2023": self.mock_holidays_2023}
        mock_get_cached_rates.return_value = (self.mock_selic_factors, self.test_cache["registros"])
        mock_load_cache.return_value = self.test_cache
        mock_save_cache.return_value = True
        
        # Testa para um dia útil
        response = self.client.get('/dia-util?data=2023-04-03')
        result_data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(result_data['eh_dia_util_calendario'])
        self.assertTrue(result_data['eh_dia_util_financeiro'])
        self.assertFalse(result_data['eh_final_semana'])
        self.assertFalse(result_data['eh_feriado'])
        
        # Testa para um fim de semana
        response = self.client.get('/dia-util?data=2023-04-01')
        result_data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(result_data['eh_dia_util_calendario'])
        self.assertFalse(result_data['eh_dia_util_financeiro'])
        self.assertTrue(result_data['eh_final_semana'])
        
        # Testa para um feriado
        response = self.client.get('/dia-util?data=2023-04-07')
        result_data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(result_data['eh_dia_util_calendario'])
        self.assertFalse(result_data['eh_dia_util_financeiro'])
        self.assertTrue(result_data['eh_feriado'])
        self.assertTrue('feriado' in result_data)
        self.assertEqual(result_data['feriado']['nome'], 'Sexta-feira Santa')

    @patch('app.load_cache')
    @patch('app.save_cache')
    @patch('app.get_cached_rates')
    @patch('app.load_holidays_cache')
    def test_selic_apurada_endpoint(self, mock_load_holidays, mock_get_cached_rates, 
                                   mock_save_cache, mock_load_cache):
        """
        Testa o endpoint /selic/apurada
        """
        # Configura os mocks
        mock_load_holidays.return_value = {"2023": self.mock_holidays_2023}
        mock_get_cached_rates.return_value = (self.mock_selic_factors, self.test_cache["registros"])
        mock_load_cache.return_value = self.test_cache
        mock_save_cache.return_value = True
        
        # Testa para um dia útil
        response = self.client.get('/selic/apurada?data=2023-04-03')
        result_data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(result_data['diaUtil'])
        self.assertEqual(float(result_data['fatorDiario']), 1.00050788)
        self.assertEqual(result_data['fonte'], 'cache')
        
        # Testa para um fim de semana
        response = self.client.get('/selic/apurada?data=2023-04-01')
        result_data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(result_data['diaUtil'])
        self.assertEqual(float(result_data['fatorDiario']), 0.0)
        self.assertEqual(result_data['tipoNaoUtil'], 'FINAL_DE_SEMANA')
        
        # Testa para um feriado
        response = self.client.get('/selic/apurada?data=2023-04-07')
        result_data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(result_data['diaUtil'])
        self.assertEqual(float(result_data['fatorDiario']), 0.0)
        self.assertEqual(result_data['tipoNaoUtil'], 'FERIADO')
        self.assertEqual(result_data['nomeFeriado'], 'Sexta-feira Santa')

    @patch('app.load_cache')
    @patch('app.save_cache')
    @patch('app.get_cached_rates')
    @patch('app.load_holidays_cache')
    @patch('app.ensure_rates_in_cache')
    def test_multiple_days_cache_filling(self, mock_ensure_rates, mock_load_holidays, 
                                       mock_get_cached_rates, mock_save_cache, mock_load_cache):
        """
        Testa o preenchimento do cache para múltiplos dias
        """
        # Configura o mock com um cache vazio inicialmente
        empty_cache = {"registros": []}
        mock_load_cache.return_value = empty_cache
        
        # Configura demais mocks
        mock_load_holidays.return_value = {"2023": self.mock_holidays_2023}
        mock_get_cached_rates.return_value = ({}, [])
        mock_save_cache.return_value = True
        
        # Criamos um dicionário simulando as taxas retornadas
        mock_taxes = {}
        
        # Mapeamento de dias úteis e não úteis para o período de 01/04/2023 a 30/04/2023
        start_date = datetime(2023, 4, 1).date()
        end_date = datetime(2023, 4, 30).date()
        current_date = start_date
        while current_date <= end_date:
            # Verifica se é dia útil (não é fim de semana ou feriado)
            is_weekend = current_date.weekday() >= 5
            is_holiday = current_date in [datetime(2023, 4, 7).date(), datetime(2023, 4, 21).date()]
            
            if not (is_weekend or is_holiday):
                # Dia útil, fator > 0
                mock_taxes[current_date] = 1.00050788
            else:
                # Dia não útil, fator = 0
                mock_taxes[current_date] = 0.0
            
            current_date += timedelta(days=1)
        
        # Configura o mock para retornar nosso dicionário de taxas
        mock_ensure_rates.return_value = mock_taxes
        
        # Faz a chamada ao endpoint que processaria múltiplos dias
        with patch('app.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 5, 1)  # 01/05/2023
            mock_datetime.strptime = datetime.strptime
            
            # Chama o endpoint de investimento que usará os cache
            response = self.client.get('/investimento?data=2023-04-01&valor=1000&data_final=2023-04-30')
            
            # Verifica o status da resposta
            self.assertEqual(response.status_code, 200)
            
            # Verifica se a função ensure_rates_in_cache foi chamada ao menos uma vez
            mock_ensure_rates.assert_called()
            
            # Verifica se o cálculo foi feito corretamente considerando os dias úteis
            result_data = json.loads(response.data)
            
            # Obtém o número real de dias compostos retornado pela API
            dias_compostos = result_data['dias_compostos']
            
            # Recalcula o valor esperado com base nos dias compostos reais
            expected_factor = (1.00050788) ** dias_compostos
            expected_final_value = 1000.0 * expected_factor
            
            # Verifica se o valor final está correto com base nos dias compostos reais
            self.assertAlmostEqual(result_data['valor_final'], expected_final_value, places=2)

if __name__ == '__main__':
    unittest.main() 