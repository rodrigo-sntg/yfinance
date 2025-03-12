import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, date
from app.holidays import fetch_holidays_for_year, get_holidays_for_year, is_business_day, preload_holidays_for_period


class TestHolidays(unittest.TestCase):
    """Testes para as funções de manipulação de feriados"""

    def setUp(self):
        # Configuração comum para todos os testes
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
            },
            {
                "date": "2023-12-25",
                "name": "Natal",
                "type": "national"
            }
        ]
        
        self.mock_holidays_cache = {
            "2023": self.mock_holidays,
            "2022": [
                {
                    "date": "2022-12-25",
                    "name": "Natal",
                    "type": "national"
                }
            ]
        }

    @patch('requests.get')
    def test_fetch_holidays_for_year_success(self, mock_get):
        # Configura o mock para simular uma resposta bem-sucedida
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_holidays
        mock_get.return_value = mock_response
        
        # Executa a função
        result = fetch_holidays_for_year(2023)
        
        # Verifica o resultado
        self.assertEqual(result, self.mock_holidays)
        mock_get.assert_called_once()
        mock_response.json.assert_called_once()

    @patch('requests.get')
    def test_fetch_holidays_for_year_api_error(self, mock_get):
        # Configura o mock para simular uma resposta com erro
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        # Executa a função
        result = fetch_holidays_for_year(2023)
        
        # Verifica se retorna uma lista vazia quando há erro na API
        self.assertEqual(result, [])
        mock_get.assert_called_once()
        mock_response.json.assert_not_called()

    @patch('requests.get')
    def test_fetch_holidays_for_year_connection_error(self, mock_get):
        # Configura o mock para simular erro de conexão
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError("Erro de conexão")
        
        # Executa a função
        result = fetch_holidays_for_year(2023)
        
        # Verifica se retorna uma lista vazia quando há erro de conexão
        self.assertEqual(result, [])
        mock_get.assert_called_once()

    @patch('app.holidays.load_holidays_cache')
    @patch('app.holidays.fetch_holidays_for_year')
    @patch('app.holidays.save_holidays_cache')
    def test_get_holidays_for_year_from_cache(self, mock_save_cache, mock_fetch, mock_load_cache):
        # Configura os mocks para simular feriados já existentes no cache
        mock_load_cache.return_value = self.mock_holidays_cache
        
        # Executa a função
        result = get_holidays_for_year(2023)
        
        # Verifica se retorna os feriados do cache e não chama a API
        self.assertEqual(result, self.mock_holidays)
        mock_load_cache.assert_called_once()
        mock_fetch.assert_not_called()
        mock_save_cache.assert_not_called()

    @patch('app.holidays.load_holidays_cache')
    @patch('app.holidays.fetch_holidays_for_year')
    @patch('app.holidays.save_holidays_cache')
    def test_get_holidays_for_year_from_api(self, mock_save_cache, mock_fetch, mock_load_cache):
        # Configura os mocks para simular feriados não existentes no cache
        mock_load_cache.return_value = {"2022": []} # Só tem 2022 no cache
        mock_fetch.return_value = self.mock_holidays
        
        # Executa a função
        result = get_holidays_for_year(2023)
        
        # Verifica se busca na API e atualiza o cache
        self.assertEqual(result, self.mock_holidays)
        mock_load_cache.assert_called_once()
        mock_fetch.assert_called_once()
        mock_save_cache.assert_called_once()

    @patch('app.holidays.get_holidays_for_year')
    def test_is_business_day_weekend(self, mock_get_holidays):
        # Testa sábado (índice 5)
        saturday = date(2023, 7, 1)  # Um sábado
        self.assertFalse(is_business_day(saturday))
        
        # Testa domingo (índice 6)
        sunday = date(2023, 7, 2)  # Um domingo
        self.assertFalse(is_business_day(sunday))
        
        # Verifica que não tentou buscar feriados para finais de semana
        mock_get_holidays.assert_not_called()

    @patch('app.holidays.get_holidays_for_year')
    def test_is_holiday(self, mock_get_holidays):
        """Testa a função is_holiday para detectar feriados"""
        # Configura mock para simular um feriado
        holiday_date = date(2023, 1, 1)  # Um feriado
        mock_get_holidays.return_value = self.mock_holidays
        
        # Executa a função
        from app.holidays import is_holiday
        eh_feriado, nome_feriado = is_holiday(holiday_date)
        
        # Verifica os resultados
        self.assertTrue(eh_feriado)
        self.assertEqual(nome_feriado, "Confraternização Universal")
        
        # Verifica se a função foi chamada com o ano correto
        mock_get_holidays.assert_called_with(2023)
        
        # Testa com uma data que não é feriado
        non_holiday_date = date(2023, 1, 2)  # Não é feriado
        eh_feriado, nome_feriado = is_holiday(non_holiday_date)
        
        # Verifica os resultados
        self.assertFalse(eh_feriado)
        self.assertIsNone(nome_feriado)

    @patch('app.holidays.is_holiday')
    def test_is_business_day_holiday(self, mock_is_holiday):
        """Testa is_business_day para um feriado"""
        # Configura o mock para simular que a data é um feriado
        mock_is_holiday.return_value = (True, "Confraternização Universal")
        
        # Testa para uma data que é feriado (mas não é fim de semana)
        holiday_date = date(2023, 1, 2)  # Uma segunda-feira
        
        # Executa a função
        result = is_business_day(holiday_date)
        
        # Verifica que identifica corretamente como não sendo dia útil
        self.assertFalse(result)
        
        # Verifica se o mock foi chamado
        mock_is_holiday.assert_called_once_with(holiday_date)

    @patch('app.holidays.get_holidays_for_year')
    def test_is_business_day_working_day(self, mock_get_holidays):
        # Configura mock para simular um dia útil (sem feriado)
        working_date = date(2023, 7, 3)  # Uma segunda-feira que não é feriado
        mock_get_holidays.return_value = self.mock_holidays
        
        # Executa a função
        result = is_business_day(working_date)
        
        # Verifica se identifica corretamente o dia útil
        self.assertTrue(result)
        mock_get_holidays.assert_called_once_with(2023)

    @patch('app.holidays.load_holidays_cache')
    @patch('app.holidays.fetch_holidays_for_year')
    @patch('app.holidays.save_holidays_cache')
    def test_preload_holidays_for_period(self, mock_save_cache, mock_fetch, mock_load_cache):
        # Configura os mocks
        mock_load_cache.return_value = {"2022": []}  # Só tem 2022 no cache
        mock_fetch.return_value = self.mock_holidays
        
        # Executa a função
        start_date = date(2022, 12, 1)
        end_date = date(2024, 1, 31)
        result = preload_holidays_for_period(start_date, end_date)
        
        # Verifica se carregou feriados para todos os anos do período
        mock_load_cache.assert_called_once()
        # Deve chamar fetch para 2023 e 2024, já que 2022 já está no cache
        self.assertEqual(mock_fetch.call_count, 2)
        mock_save_cache.assert_called_once()


if __name__ == '__main__':
    unittest.main() 