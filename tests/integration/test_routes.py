import unittest
import json
from datetime import datetime, date, timedelta
from unittest.mock import patch, MagicMock
from app import create_app


class TestAPIRoutes(unittest.TestCase):
    """Testes de integração para as rotas da API"""

    def setUp(self):
        """Configura a aplicação de teste antes de cada teste"""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # Mock das taxas para testes
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
            {"dataCotacao": "08/07/2023", "fatorDiario": "0", "isBusinessDay": False, "reason": "FINAL_DE_SEMANA"},
            {"dataCotacao": "09/07/2023", "fatorDiario": "0", "isBusinessDay": False, "reason": "FINAL_DE_SEMANA"}
        ]
        
        # Mock dos feriados
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

    def test_ping_endpoint(self):
        """Testa o endpoint /ping"""
        response = self.client.get('/ping')
        
        # Verifica o status e o conteúdo da resposta
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["message"], "Service is running")

    @patch('app.routes.get_cached_rates')
    @patch('app.routes.ensure_rates_in_cache')
    @patch('app.routes.get_holidays_for_year')
    def test_selic_apurada_dia_util(self, mock_get_holidays, mock_ensure_rates, mock_get_cached_rates):
        """Testa o endpoint /selic/apurada para um dia útil"""
        # Configura os mocks
        mock_get_cached_rates.return_value = (self.mock_taxas, self.mock_registros)
        mock_ensure_rates.return_value = self.mock_taxas
        mock_get_holidays.return_value = self.mock_holidays
        
        # Executa a requisição
        response = self.client.get('/selic/apurada?data=2023-07-03')  # Segunda-feira
        
        # Verifica o status e o conteúdo da resposta
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["dataCotacao"], "2023-07-03")
        self.assertEqual(data["fatorDiario"], 1.000123)
        self.assertTrue(data["diaUtil"])

    @patch('app.routes.get_cached_rates')
    @patch('app.routes.ensure_rates_in_cache')
    @patch('app.routes.get_holidays_for_year')
    def test_selic_apurada_final_semana(self, mock_get_holidays, mock_ensure_rates, mock_get_cached_rates):
        """Testa o endpoint /selic/apurada para um final de semana"""
        # Configura os mocks
        mock_get_cached_rates.return_value = (self.mock_taxas, self.mock_registros)
        mock_ensure_rates.return_value = self.mock_taxas
        mock_get_holidays.return_value = self.mock_holidays
        
        # Executa a requisição
        response = self.client.get('/selic/apurada?data=2023-07-08')  # Sábado
        
        # Verifica o status e o conteúdo da resposta
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["dataCotacao"], "2023-07-08")
        self.assertEqual(data["fatorDiario"], 0)
        self.assertFalse(data["diaUtil"])
        self.assertEqual(data["tipoNaoUtil"], "FINAL_DE_SEMANA")

    @patch('app.routes.get_cached_rates')
    @patch('app.routes.ensure_rates_in_cache')
    @patch('app.routes.get_holidays_for_year')
    def test_selic_apurada_feriado(self, mock_get_holidays, mock_ensure_rates, mock_get_cached_rates):
        """Testa o endpoint /selic/apurada para um feriado"""
        # Configura os mocks
        mock_taxas = self.mock_taxas.copy()
        mock_taxas[date(2023, 1, 1)] = 0.0  # Feriado de Ano Novo
        
        mock_registros = self.mock_registros.copy()
        mock_registros.append({
            "dataCotacao": "01/01/2023",
            "fatorDiario": "0",
            "isBusinessDay": False,
            "reason": "FERIADO: Confraternização Universal"
        })
        
        mock_get_cached_rates.return_value = (mock_taxas, mock_registros)
        mock_ensure_rates.return_value = mock_taxas
        mock_get_holidays.return_value = self.mock_holidays
        
        # Executa a requisição
        response = self.client.get('/selic/apurada?data=2023-01-01')  # Feriado
        
        # Verifica o status e o conteúdo da resposta
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["dataCotacao"], "2023-01-01")
        self.assertEqual(data["fatorDiario"], 0)
        self.assertFalse(data["diaUtil"])
        self.assertEqual(data["tipoNaoUtil"], "FERIADO")
        self.assertEqual(data["nomeFeriado"], "Confraternização Universal")

    @patch('app.routes.get_cached_rates')
    @patch('app.routes.ensure_rates_in_cache')
    @patch('app.routes.get_holidays_for_year')
    def test_selic_apurada_formato_invalido(self, mock_get_holidays, mock_ensure_rates, mock_get_cached_rates):
        """Testa o endpoint /selic/apurada com formato de data inválido"""
        # Executa a requisição com formato inválido
        response = self.client.get('/selic/apurada?data=03-07-2023')  # Formato inválido
        
        # Verifica o status e o conteúdo da resposta de erro
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)

    @patch('app.investimento.calcular_rendimento')
    def test_investimento_endpoint(self, mock_calcular_rendimento):
        """Testa o endpoint /investimento"""
        # Configura o mock
        resultado_mock = {
            "data_inicial": "2023-07-03",
            "data_final": "2023-07-07",
            "valor_investido": 1000.0,
            "valor_final": 1000.63,
            "rendimento": 0.63,
            "rendimento_percentual": 0.063,
            "fator_composto": 1.000633,
            "dias_compostos": 5,
            "dias_sem_rendimento": 0,
            "dias_sem_taxa": 0,
            "dias_totais": 5
        }
        mock_calcular_rendimento.return_value = resultado_mock
        
        # Executa a requisição
        response = self.client.get('/investimento?data=2023-07-03&valor=1000&data_final=2023-07-07')
        
        # Verifica o status e o conteúdo da resposta
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data, resultado_mock)
        
        # Verifica se a função foi chamada com os parâmetros corretos
        # Os parâmetros são convertidos para os tipos corretos na função
        mock_calcular_rendimento.assert_called_once()
        args, kwargs = mock_calcular_rendimento.call_args
        self.assertEqual(args[0], date(2023, 7, 3))  # data_inicial
        self.assertEqual(args[1], 1000.0)            # valor_investido
        self.assertEqual(args[2], date(2023, 7, 7))  # data_final

    @patch('app.investimento.calcular_rendimento')
    def test_investimento_endpoint_sem_data_final(self, mock_calcular_rendimento):
        """Testa o endpoint /investimento sem o parâmetro data_final"""
        # Configura o mock
        resultado_mock = {
            "data_inicial": "2023-07-03",
            "data_final": "2023-07-09",  # Assume que a data atual é 10/07/2023
            "valor_investido": 1000.0,
            "valor_final": 1000.63,
            "rendimento": 0.63,
            "rendimento_percentual": 0.063,
            "fator_composto": 1.000633,
            "dias_compostos": 5,
            "dias_sem_rendimento": 2,
            "dias_sem_taxa": 0,
            "dias_totais": 7
        }
        mock_calcular_rendimento.return_value = resultado_mock
        
        # Executa a requisição sem o parâmetro data_final
        response = self.client.get('/investimento?data=2023-07-03&valor=1000')
        
        # Verifica o status e o conteúdo da resposta
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data, resultado_mock)
        
        # Verifica se a função foi chamada com os parâmetros corretos
        mock_calcular_rendimento.assert_called_once()
        args, kwargs = mock_calcular_rendimento.call_args
        self.assertEqual(args[0], date(2023, 7, 3))  # data_inicial
        self.assertEqual(args[1], 1000.0)            # valor_investido
        self.assertIsNone(args[2])                   # data_final = None

    @patch('app.investimento.calcular_rendimento')
    def test_investimento_endpoint_parametros_invalidos(self, mock_calcular_rendimento):
        """Testa o endpoint /investimento com parâmetros inválidos"""
        # Testa sem os parâmetros obrigatórios
        response = self.client.get('/investimento')
        self.assertEqual(response.status_code, 400)
        
        # Testa com data inválida
        response = self.client.get('/investimento?data=data-invalida&valor=1000')
        self.assertEqual(response.status_code, 400)
        
        # Testa com valor não numérico
        response = self.client.get('/investimento?data=2023-07-03&valor=mil')
        self.assertEqual(response.status_code, 400)
        
        # Verifica se a função não foi chamada em nenhum caso
        mock_calcular_rendimento.assert_not_called()

    @patch('app.investimento.analisar_investimento')
    def test_analisar_investimento_endpoint(self, mock_analisar_investimento):
        """Testa o endpoint /investimento/analise"""
        # Configura o mock
        resultado_mock = {
            "dados_investimento": {
                "data_inicial": "2023-07-03",
                "data_final": "2023-07-09",
                "valor_investido": 1000.0,
                "valor_final": 1000.63,
                "rendimento": 0.63,
                "rendimento_percentual": 0.063
            },
            "estatisticas_periodo": {
                "dias_totais": 7,
                "dias_uteis": 5,
                "dias_nao_uteis": 2,
                "dias_feriados": 0,
                "fator_acumulado_total": 1.000633,
                "fator_acumulado_apenas_uteis": 1.000633,
                "rendimento_diario_medio_total": 0.009,
                "rendimento_diario_medio_util": 0.0126
            },
            "analise_rendimento_por_dias": {
                "valor_final_considerando_todos_dias": 1000.63,
                "valor_final_apenas_dias_uteis": 1000.63,
                "diferenca_valor_final": 0.0
            }
        }
        
        detalhes_mock = [
            {
                "data": "2023-07-03",
                "dia_semana": "Monday",
                "dia_util_calendario": True,
                "tipo": "dia_util",
                "rendimento": True,
                "fator_diario": 1.000123
            },
            # Outros dias omitidos para brevidade
        ]
        
        mock_analisar_investimento.return_value = (resultado_mock, detalhes_mock)
        
        # Executa a requisição sem solicitar detalhes
        response = self.client.get('/investimento/analise?data=2023-07-03&valor=1000&data_final=2023-07-09')
        
        # Verifica o status e o conteúdo da resposta
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data, resultado_mock)  # Sem detalhes_diarios
        
        # Executa a requisição solicitando detalhes
        response = self.client.get('/investimento/analise?data=2023-07-03&valor=1000&data_final=2023-07-09&detalhar=true')
        
        # Verifica que agora inclui os detalhes diários
        data = json.loads(response.data)
        self.assertIn("detalhes_diarios", data)
        self.assertEqual(data["detalhes_diarios"], detalhes_mock)

    @patch('app.routes.get_holidays_for_year')
    @patch('app.routes.get_cached_rates')
    @patch('app.routes.ensure_rates_in_cache')
    def test_dia_util_endpoint(self, mock_ensure_rates, mock_get_cached_rates, mock_get_holidays):
        """Testa o endpoint /dia-util"""
        # Configura os mocks
        mock_get_cached_rates.return_value = (self.mock_taxas, self.mock_registros)
        mock_ensure_rates.return_value = self.mock_taxas
        mock_get_holidays.return_value = self.mock_holidays
        
        # Testa para um dia útil (segunda-feira)
        response = self.client.get('/dia-util?data=2023-07-03')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["eh_dia_util_calendario"])
        self.assertTrue(data["eh_dia_util_financeiro"])
        self.assertFalse(data["eh_final_semana"])
        self.assertFalse(data["eh_feriado"])
        
        # Testa para um final de semana (sábado)
        response = self.client.get('/dia-util?data=2023-07-08')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertFalse(data["eh_dia_util_calendario"])
        self.assertFalse(data["eh_dia_util_financeiro"])
        self.assertTrue(data["eh_final_semana"])
        self.assertFalse(data["eh_feriado"])
        
        # Configura mock para testar um feriado
        mock_get_holidays.return_value = [
            {
                "date": "2023-07-03",  # Faz o dia 03/07 ser um feriado para o teste
                "name": "Feriado Teste",
                "type": "national"
            }
        ]
        
        # Testa para um feriado
        response = self.client.get('/dia-util?data=2023-07-03')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertFalse(data["eh_dia_util_calendario"])
        self.assertFalse(data["eh_dia_util_financeiro"])
        self.assertFalse(data["eh_final_semana"])
        self.assertTrue(data["eh_feriado"])
        self.assertEqual(data["feriado"]["nome"], "Feriado Teste")
        
        # Testa com data inválida
        response = self.client.get('/dia-util?data=data-invalida')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)


if __name__ == '__main__':
    unittest.main() 