import os
import json
import unittest
from unittest.mock import patch, mock_open, MagicMock
from datetime import datetime
from app.cache import load_cache, save_cache, get_cached_rates, load_holidays_cache, save_holidays_cache


class TestCache(unittest.TestCase):
    """Testes para as funções de manipulação de cache"""

    def setUp(self):
        # Configuração comum para todos os testes
        self.mock_cache_data = {
            "registros": [
                {
                    "dataCotacao": "01/07/2023",
                    "fatorDiario": "1.000123"
                },
                {
                    "dataCotacao": "02/07/2023",
                    "fatorDiario": "0"
                }
            ]
        }
        
        self.mock_holidays_data = {
            "2023": [
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
        }

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    def test_load_cache_file_exists(self, mock_json_load, mock_file_open, mock_exists):
        # Configura os mocks
        mock_exists.return_value = True
        mock_json_load.return_value = self.mock_cache_data
        
        # Executa a função
        result = load_cache()
        
        # Verifica o resultado
        self.assertEqual(result, self.mock_cache_data)
        mock_exists.assert_called_once()
        mock_file_open.assert_called_once()
        mock_json_load.assert_called_once()

    @patch('os.path.exists')
    def test_load_cache_file_not_exists(self, mock_exists):
        # Configura o mock para simular arquivo não existente
        mock_exists.return_value = False
        
        # Executa a função
        result = load_cache()
        
        # Verifica se retorna cache vazio quando arquivo não existe
        self.assertEqual(result, {"registros": []})
        mock_exists.assert_called_once()

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    def test_load_cache_json_error(self, mock_json_load, mock_file_open, mock_exists):
        # Configura os mocks para simular erro de JSON
        mock_exists.return_value = True
        mock_json_load.side_effect = json.JSONDecodeError("Erro", "", 0)
        
        # Executa a função
        result = load_cache()
        
        # Verifica se retorna cache vazio quando há erro no JSON
        self.assertEqual(result, {"registros": []})
        mock_exists.assert_called_once()
        mock_file_open.assert_called_once()

    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    @patch('os.path.exists')
    @patch('os.replace')
    def test_save_cache_success(self, mock_replace, mock_exists, mock_json_dump, mock_file_open):
        # Configura os mocks
        mock_exists.return_value = True
        
        # Executa a função
        result = save_cache(self.mock_cache_data)
        
        # Verifica o resultado
        self.assertTrue(result)
        mock_json_dump.assert_called_once()
        mock_replace.assert_called()  # Verifica se o arquivo temporário foi movido

    @patch('builtins.open')
    def test_save_cache_io_error(self, mock_open):
        # Configura o mock para lançar IOError
        mock_open.side_effect = IOError("Erro de I/O")
        
        # Executa a função
        result = save_cache(self.mock_cache_data)
        
        # Verifica se retorna False quando há erro de I/O
        self.assertFalse(result)

    @patch('app.cache.load_cache')
    def test_get_cached_rates(self, mock_load_cache):
        # Configura o mock para retornar dados de cache
        mock_load_cache.return_value = self.mock_cache_data
        
        # Executa a função
        taxas_diarias, registros = get_cached_rates()
        
        # Verifica o resultado
        self.assertEqual(len(taxas_diarias), 2)
        self.assertEqual(len(registros), 2)
        
        # Verifica se as datas foram convertidas corretamente
        data1 = datetime.strptime("01/07/2023", '%d/%m/%Y').date()
        data2 = datetime.strptime("02/07/2023", '%d/%m/%Y').date()
        
        self.assertIn(data1, taxas_diarias)
        self.assertIn(data2, taxas_diarias)
        self.assertEqual(taxas_diarias[data1], 1.000123)
        self.assertEqual(taxas_diarias[data2], 0.0)

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    def test_load_holidays_cache_file_exists(self, mock_json_load, mock_file_open, mock_exists):
        # Configura os mocks
        mock_exists.return_value = True
        mock_json_load.return_value = self.mock_holidays_data
        
        # Executa a função
        result = load_holidays_cache()
        
        # Verifica o resultado
        self.assertEqual(result, self.mock_holidays_data)
        mock_exists.assert_called_once()
        mock_file_open.assert_called_once()
        mock_json_load.assert_called_once()

    @patch('os.path.exists')
    def test_load_holidays_cache_file_not_exists(self, mock_exists):
        # Configura o mock para simular arquivo não existente
        mock_exists.return_value = False
        
        # Executa a função
        result = load_holidays_cache()
        
        # Verifica se retorna cache vazio quando arquivo não existe
        self.assertEqual(result, {})
        mock_exists.assert_called_once()

    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    @patch('os.path.exists')
    @patch('os.replace')
    def test_save_holidays_cache_success(self, mock_replace, mock_exists, mock_json_dump, mock_file_open):
        # Configura os mocks
        mock_exists.return_value = True
        
        # Executa a função
        result = save_holidays_cache(self.mock_holidays_data)
        
        # Verifica o resultado
        self.assertTrue(result)
        mock_json_dump.assert_called_once()
        mock_replace.assert_called()  # Verifica se o arquivo temporário foi movido


if __name__ == '__main__':
    unittest.main() 