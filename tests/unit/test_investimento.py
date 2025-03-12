import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, date, timedelta
from app.investimento import calcular_rendimento, analisar_investimento


class TestInvestimento(unittest.TestCase):
    """Testes para as funções de cálculo de investimento"""

    def setUp(self):
        # Configuração comum para todos os testes
        self.data_inicial = date(2023, 7, 3)  # Segunda-feira
        self.data_final = date(2023, 7, 7)  # Sexta-feira
        self.valor_investido = 1000.0
        
        # Mock de taxas para os dias do teste
        self.mock_taxas = {
            date(2023, 7, 3): 1.000123,  # Segunda-feira (útil)
            date(2023, 7, 4): 1.000125,  # Terça-feira (útil)
            date(2023, 7, 5): 1.000127,  # Quarta-feira (útil)
            date(2023, 7, 6): 1.000128,  # Quinta-feira (útil)
            date(2023, 7, 7): 1.000130,  # Sexta-feira (útil)
            date(2023, 7, 8): 0.0,       # Sábado (não útil)
            date(2023, 7, 9): 0.0        # Domingo (não útil)
        }
        
        # Mock de registros originais
        self.mock_registros = [
            {"dataCotacao": "03/07/2023", "fatorDiario": "1.000123"},
            {"dataCotacao": "04/07/2023", "fatorDiario": "1.000125"},
            {"dataCotacao": "05/07/2023", "fatorDiario": "1.000127"},
            {"dataCotacao": "06/07/2023", "fatorDiario": "1.000128"},
            {"dataCotacao": "07/07/2023", "fatorDiario": "1.000130"},
            {"dataCotacao": "08/07/2023", "fatorDiario": "0"},
            {"dataCotacao": "09/07/2023", "fatorDiario": "0"}
        ]

    @patch('app.investimento.get_cached_rates')
    @patch('app.investimento.ensure_non_business_day_in_cache')
    @patch('app.investimento.ensure_rates_in_cache')
    @patch('app.investimento.is_business_day')
    @patch('app.investimento.save_cache')
    def test_calcular_rendimento_dias_uteis(self, mock_save_cache, mock_is_business, 
                                         mock_ensure_rates, mock_ensure_non_business, mock_get_cached_rates):
        """Testa o cálculo de rendimento para um período com apenas dias úteis"""
        # Configura os mocks
        mock_get_cached_rates.return_value = (self.mock_taxas, self.mock_registros)
        mock_ensure_non_business.return_value = (False, None, None)  # Simula que nenhum dia não útil foi adicionado
        mock_ensure_rates.return_value = self.mock_taxas
        
        # Executa a função
        resultado = calcular_rendimento(self.data_inicial, self.valor_investido, self.data_final)
        
        # Verifica o resultado
        self.assertEqual(resultado["data_inicial"], self.data_inicial.strftime('%Y-%m-%d'))
        self.assertEqual(resultado["data_final"], self.data_final.strftime('%Y-%m-%d'))
        self.assertEqual(resultado["valor_investido"], self.valor_investido)
        
        # Calcula o fator composto esperado: 1.000123 * 1.000125 * 1.000127 * 1.000128 * 1.000130
        fator_esperado = 1.000123 * 1.000125 * 1.000127 * 1.000128 * 1.000130
        valor_final_esperado = self.valor_investido * fator_esperado
        rendimento_esperado = valor_final_esperado - self.valor_investido
        rendimento_percentual_esperado = (rendimento_esperado / self.valor_investido) * 100
        
        # Verifica os valores calculados (com tolerância para erro de ponto flutuante)
        self.assertAlmostEqual(resultado["fator_composto"], fator_esperado, places=8)
        self.assertAlmostEqual(resultado["valor_final"], valor_final_esperado, places=2)
        self.assertAlmostEqual(resultado["rendimento"], rendimento_esperado, places=2)
        self.assertAlmostEqual(resultado["rendimento_percentual"], rendimento_percentual_esperado, places=2)
        
        # Verifica as contagens de dias
        self.assertEqual(resultado["dias_compostos"], 5)  # 5 dias úteis
        self.assertEqual(resultado["dias_sem_rendimento"], 0)  # 0 dias não úteis (não incluídos no período)
        self.assertEqual(resultado["dias_sem_taxa"], 0)  # 0 dias sem taxa
        self.assertEqual(resultado["dias_totais"], 5)  # 5 dias totais

    @patch('app.investimento.get_cached_rates')
    @patch('app.investimento.ensure_non_business_day_in_cache')
    @patch('app.investimento.ensure_rates_in_cache')
    @patch('app.investimento.is_business_day')
    @patch('app.investimento.save_cache')
    def test_calcular_rendimento_com_dias_nao_uteis(self, mock_save_cache, mock_is_business, 
                                                 mock_ensure_rates, mock_ensure_non_business, mock_get_cached_rates):
        """Testa o cálculo de rendimento para um período incluindo dias não úteis (fim de semana)"""
        # Configura os mocks
        mock_get_cached_rates.return_value = (self.mock_taxas, self.mock_registros)
        
        # Simula que todos os dias já estão no cache (incluindo não úteis)
        mock_ensure_non_business.return_value = (False, None, None)
        mock_ensure_rates.return_value = self.mock_taxas
        
        # Executa a função com um período que inclui o fim de semana
        data_final_com_fds = date(2023, 7, 9)  # Domingo
        resultado = calcular_rendimento(self.data_inicial, self.valor_investido, data_final_com_fds)
        
        # Verifica o resultado
        self.assertEqual(resultado["data_inicial"], self.data_inicial.strftime('%Y-%m-%d'))
        self.assertEqual(resultado["data_final"], data_final_com_fds.strftime('%Y-%m-%d'))
        self.assertEqual(resultado["valor_investido"], self.valor_investido)
        
        # Calcula o fator composto esperado (apenas dias úteis: segunda a sexta)
        fator_esperado = 1.000123 * 1.000125 * 1.000127 * 1.000128 * 1.000130
        valor_final_esperado = self.valor_investido * fator_esperado
        rendimento_esperado = valor_final_esperado - self.valor_investido
        rendimento_percentual_esperado = (rendimento_esperado / self.valor_investido) * 100
        
        # Verifica os valores calculados
        self.assertAlmostEqual(resultado["fator_composto"], fator_esperado, places=8)
        self.assertAlmostEqual(resultado["valor_final"], valor_final_esperado, places=2)
        self.assertAlmostEqual(resultado["rendimento"], rendimento_esperado, places=2)
        self.assertAlmostEqual(resultado["rendimento_percentual"], rendimento_percentual_esperado, places=2)
        
        # Verifica as contagens de dias
        self.assertEqual(resultado["dias_compostos"], 5)  # 5 dias úteis
        self.assertEqual(resultado["dias_sem_rendimento"], 2)  # 2 dias não úteis (sábado e domingo)
        self.assertEqual(resultado["dias_sem_taxa"], 0)  # 0 dias sem taxa
        self.assertEqual(resultado["dias_totais"], 7)  # 7 dias totais

    @patch('app.investimento.get_cached_rates')
    @patch('app.investimento.ensure_non_business_day_in_cache')
    @patch('app.investimento.ensure_rates_in_cache')
    @patch('app.investimento.is_business_day')
    @patch('app.investimento.save_cache')
    def test_calcular_rendimento_data_final_none(self, mock_save_cache, mock_is_business, 
                                              mock_ensure_rates, mock_ensure_non_business, mock_get_cached_rates):
        """Testa o cálculo de rendimento quando data_final é None (deve usar dia anterior à data atual)"""
        # Configura os mocks
        mock_get_cached_rates.return_value = (self.mock_taxas, self.mock_registros)
        mock_ensure_non_business.return_value = (False, None, None)
        mock_ensure_rates.return_value = self.mock_taxas
        
        # Define um patch temporário para datetime.now() para testar comportamento com data_final=None
        with patch('app.investimento.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 7, 10, 12, 0)  # Uma segunda-feira
            mock_datetime.strptime = datetime.strptime
            
            # Executa a função com data_final=None
            resultado = calcular_rendimento(self.data_inicial, self.valor_investido, None)
            
            # Verifica que a data final foi definida como o dia anterior à "data atual"
            self.assertEqual(resultado["data_final"], "2023-07-09")  # Domingo (dia anterior à segunda-feira)

    @patch('app.investimento.calcular_rendimento')
    def test_analisar_investimento(self, mock_calcular_rendimento):
        """Testa a função de análise de investimento"""
        # Configura o mock para calcular_rendimento
        mock_resultado = {
            "data_inicial": "2023-07-03",
            "data_final": "2023-07-09",
            "valor_investido": 1000.0,
            "valor_final": 1005.0,
            "rendimento": 5.0,
            "rendimento_percentual": 0.5,
            "dias_totais": 7,
            "dias_compostos": 5,
            "dias_sem_rendimento": 2,
            "dias_sem_taxa": 0,
            "fator_composto": 1.005
        }
        mock_calcular_rendimento.return_value = mock_resultado
        
        # Executa a função
        data_inicial = date(2023, 7, 3)  # Segunda-feira
        data_final = date(2023, 7, 9)  # Domingo
        resultado, detalhes = analisar_investimento(data_inicial, 1000.0, data_final)
        
        # Verifica apenas os campos essenciais do resultado
        self.assertEqual(resultado["dados_investimento"]["data_inicial"], "2023-07-03")
        self.assertEqual(resultado["dados_investimento"]["data_final"], "2023-07-09")
        self.assertEqual(resultado["dados_investimento"]["valor_investido"], 1000.0)
        
        # Verifica que há detalhes diários
        self.assertIsInstance(detalhes, list)


if __name__ == '__main__':
    unittest.main() 