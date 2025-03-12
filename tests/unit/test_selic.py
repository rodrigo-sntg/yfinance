import unittest
from unittest.mock import patch, MagicMock, call
from datetime import datetime, date, timedelta
import requests
from app.selic import (
    fetch_selic_for_date, ensure_non_business_day_in_cache, ensure_rates_in_cache,
    get_cached_rates
)


class TestSelic(unittest.TestCase):
    """Testes para as funções de manipulação de taxas Selic"""

    def setUp(self):
        # Configuração comum para todos os testes
        self.mock_taxa = {
            "dataCotacao": "03/07/2023",
            "fatorDiario": "1.000123"
        }
        
        self.mock_api_response = {
            "registros": [self.mock_taxa]
        }
        
        self.mock_holidays = [
            {
                "date": "2023-01-01",
                "name": "Confraternização Universal",
                "type": "national"
            },
            {
                "date": "2023-04-21",
                "name": "Tiradentes",
                "type": "national"
            }
        ]

    @patch('requests.post')
    def test_fetch_selic_for_date_success(self, mock_post):
        # Configura o mock para simular uma resposta bem-sucedida
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_api_response
        mock_post.return_value = mock_response
        
        # Executa a função
        result = fetch_selic_for_date("03/07/2023")
        
        # Verifica o resultado
        self.assertEqual(result, self.mock_taxa)
        mock_post.assert_called_once()
        mock_response.json.assert_called_once()

    @patch('requests.post')
    def test_fetch_selic_for_date_api_error(self, mock_post):
        # Configura o mock para simular uma resposta com erro
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        # Executa a função
        result = fetch_selic_for_date("03/07/2023")
        
        # Verifica se retorna None quando há erro na API
        self.assertIsNone(result)
        mock_post.assert_called_once()
        mock_response.json.assert_not_called()

    @patch('requests.post')
    def test_fetch_selic_for_date_empty_response(self, mock_post):
        # Configura o mock para simular uma resposta vazia
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"registros": []}
        mock_post.return_value = mock_response
        
        # Executa a função
        result = fetch_selic_for_date("03/07/2023")
        
        # Verifica se retorna None quando a resposta não tem registros
        self.assertIsNone(result)
        mock_post.assert_called_once()
        mock_response.json.assert_called_once()

    @patch('requests.post')
    def test_fetch_selic_for_date_connection_error(self, mock_post):
        # Configura o mock para simular erro de conexão
        mock_post.side_effect = requests.exceptions.ConnectionError("Erro de conexão")
        
        # Executa a função
        result = fetch_selic_for_date("03/07/2023")
        
        # Verifica se retorna None quando há erro de conexão
        self.assertIsNone(result)
        mock_post.assert_called_once()

    @patch('app.selic.get_holidays_for_year')
    def test_ensure_non_business_day_in_cache_weekend(self, mock_get_holidays):
        """Testa se um final de semana é adicionado corretamente ao cache"""
        # Configura teste para um final de semana
        data = date(2023, 7, 1)  # Um sábado
        taxas_diarias = {}
        registros_unicos = []
        datas_registradas = {}
        
        # Executa a função
        foi_adicionado, taxa, motivo = ensure_non_business_day_in_cache(data, taxas_diarias, registros_unicos, datas_registradas)
        
        # Verifica se adicionou corretamente
        self.assertTrue(foi_adicionado)
        self.assertEqual(taxa, 0.0)
        self.assertEqual(len(registros_unicos), 1)
        self.assertEqual(registros_unicos[0]["fatorDiario"], "0")
        self.assertEqual(registros_unicos[0]["reason"], "FINAL_DE_SEMANA")
        
        # Não deve verificar se é feriado para finais de semana
        mock_get_holidays.assert_not_called()

    @patch('app.selic.is_holiday')
    def test_ensure_non_business_day_in_cache_holiday(self, mock_is_holiday):
        """Testa se um feriado é adicionado corretamente ao cache"""
        # Configura o mock para simular um feriado em 15/11/2023 (quarta-feira)
        mock_is_holiday.return_value = (True, "Proclamação da República")
        
        # Data de teste: 15/11/2023 (quarta-feira e feriado nacional)
        data_teste = date(2023, 11, 15)
        
        # Cria variáveis locais para o teste
        taxas_diarias = {}
        registros_unicos = []
        datas_registradas = {}
        
        # Executa a função
        foi_adicionado, taxa, motivo = ensure_non_business_day_in_cache(
            data_teste, taxas_diarias, registros_unicos, datas_registradas
        )
        
        # Verifica se o feriado foi adicionado ao cache
        self.assertTrue(foi_adicionado)
        self.assertEqual(taxa, 0.0)
        self.assertIn("FERIADO", motivo)
        
        # Verifica se o mock foi chamado corretamente
        mock_is_holiday.assert_called_once_with(data_teste)
        
        # Verifica se o registro foi adicionado ao cache
        self.assertEqual(len(registros_unicos), 1)
        self.assertEqual(registros_unicos[0]["fatorDiario"], "0")
        self.assertIn("FERIADO", registros_unicos[0]["reason"])

    @patch('app.selic.get_holidays_for_year')
    def test_ensure_non_business_day_in_cache_already_in_cache(self, mock_get_holidays):
        """Testa se um dia já no cache não é adicionado novamente"""
        # Configura teste para um dia já no cache
        data = date(2023, 7, 1)  # Um sábado
        taxas_diarias = {data: 0.0}  # Já está no cache
        registros_unicos = []
        datas_registradas = {}
        
        # Executa a função
        foi_adicionado, taxa, motivo = ensure_non_business_day_in_cache(data, taxas_diarias, registros_unicos, datas_registradas)
        
        # Verifica que não adicionou (pois já estava no cache)
        self.assertFalse(foi_adicionado)
        self.assertEqual(taxa, 0.0)
        self.assertIsNone(motivo)
        self.assertEqual(len(registros_unicos), 0)
        
        # Não deve verificar se é feriado se já está no cache
        mock_get_holidays.assert_not_called()

    @patch('app.selic.get_holidays_for_year')
    def test_ensure_non_business_day_in_cache_already_registered(self, mock_get_holidays):
        """Testa se um dia já registrado não é adicionado novamente aos registros"""
        # Configura teste para um dia já registrado
        data = date(2023, 7, 1)  # Um sábado
        taxas_diarias = {}
        registros_unicos = []
        datas_registradas = {data: True}  # Já está registrado
        
        # Executa a função
        foi_adicionado, taxa, motivo = ensure_non_business_day_in_cache(data, taxas_diarias, registros_unicos, datas_registradas)
        
        # Verifica que adicionou ao dicionário mas não aos registros
        self.assertFalse(foi_adicionado)
        self.assertIsNone(taxa)
        self.assertIsNone(motivo)
        self.assertEqual(len(registros_unicos), 0)
        
        # Não deve verificar se é feriado se já está registrado
        mock_get_holidays.assert_not_called()

    @patch('app.selic.is_holiday')
    def test_ensure_non_business_day_in_cache_working_day(self, mock_is_holiday):
        """Testa se um dia útil não é adicionado ao cache"""
        # Configura o mock para simular um dia que não é feriado
        mock_is_holiday.return_value = (False, None)
        
        # Data de teste: 03/07/2023 (segunda-feira, dia útil)
        data_teste = date(2023, 7, 3)
        
        # Cria variáveis locais para o teste
        taxas_diarias = {}
        registros_unicos = []
        datas_registradas = {}
        
        # Executa a função
        foi_adicionado, taxa, motivo = ensure_non_business_day_in_cache(
            data_teste, taxas_diarias, registros_unicos, datas_registradas
        )
        
        # Verifica que o dia útil não foi adicionado ao cache
        self.assertFalse(foi_adicionado)
        self.assertIsNone(taxa)
        self.assertIsNone(motivo)
        
        # Verifica se o mock foi chamado corretamente
        mock_is_holiday.assert_called_once_with(data_teste)
        
        # Verifica que o registro não foi adicionado ao cache
        self.assertEqual(len(registros_unicos), 0)

    @patch('app.selic.get_cached_rates')
    @patch('app.selic.preload_holidays_for_period')
    @patch('app.selic.is_business_day')
    @patch('app.selic.fetch_selic_for_date')
    @patch('app.selic.save_cache')
    def test_ensure_rates_in_cache_all_dates_cached(self, mock_save_cache, mock_fetch, mock_is_business, 
                                                  mock_preload, mock_get_cached_rates):
        # Configura os mocks
        start_date = date(2023, 7, 1)
        end_date = date(2023, 7, 3)
        
        # Mock para simular que todas as datas já estão no cache
        mock_get_cached_rates.return_value = (
            {
                start_date: 0.0,  # Sábado (não útil)
                start_date + timedelta(days=1): 0.0,  # Domingo (não útil)
                start_date + timedelta(days=2): 1.000123  # Segunda-feira (útil)
            },
            []
        )
        
        # Executa a função
        result = ensure_rates_in_cache(start_date, end_date)
        
        # Verifica se não precisou atualizar o cache nem buscar na API
        mock_save_cache.assert_not_called()
        mock_fetch.assert_not_called()
        mock_is_business.assert_not_called()
        
        # Verifica se retornou o dicionário correto
        self.assertEqual(len(result), 3)
        self.assertEqual(result[start_date], 0.0)
        self.assertEqual(result[start_date + timedelta(days=1)], 0.0)
        self.assertEqual(result[start_date + timedelta(days=2)], 1.000123)
        
        # Deve ter pré-carregado os feriados para o período
        mock_preload.assert_called_once()

    @patch('app.selic.get_cached_rates')
    @patch('app.selic.preload_holidays_for_period')
    @patch('app.selic.is_business_day')
    @patch('app.selic.fetch_selic_for_date')
    @patch('app.selic.save_cache')
    @patch('app.selic.ensure_non_business_day_in_cache')
    def test_ensure_rates_in_cache_some_missing_dates(self, mock_ensure_non_business, mock_save_cache, mock_fetch, 
                                                mock_is_business, mock_preload, mock_get_cached_rates):
        # Configura os mocks
        start_date = date(2023, 7, 1)
        end_date = date(2023, 7, 3)
        
        # Mock para simular que algumas datas estão faltando no cache
        mock_get_cached_rates.return_value = (
            {
                start_date: 0.0,  # Sábado (não útil)
                # falta o domingo
                # falta a segunda
            },
            []
        )
        
        # Configura ensure_non_business_day_in_cache para o domingo
        mock_ensure_non_business.return_value = (True, 0.0, "FINAL_DE_SEMANA")  # Adicionou o domingo
        
        # Configura is_business_day para identificar segunda-feira como dia útil
        mock_is_business.side_effect = lambda d: d.weekday() < 5 and d != start_date and d != start_date + timedelta(days=1)
        
        # Configura fetch_selic_for_date para retornar taxa para dia útil
        mock_fetch.return_value = {
            "dataCotacao": "03/07/2023",
            "fatorDiario": "1.000123"
        }
        
        # Executa a função
        result = ensure_rates_in_cache(start_date, end_date)
        
        # Verifica se atualizou o cache
        mock_save_cache.assert_called()
        
        # Deve ter verificado se cada dia é útil
        self.assertTrue(mock_is_business.called)


if __name__ == '__main__':
    unittest.main() 