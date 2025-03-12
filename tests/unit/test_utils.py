import unittest
from datetime import date
from app.utils import parse_date, safe_float


class TestUtils(unittest.TestCase):
    """Testes para as funções utilitárias"""

    def test_parse_date_valid(self):
        """Testa parse_date com uma data válida"""
        # Executa a função com data válida
        result = parse_date("2023-07-03")
        
        # Verifica o resultado
        self.assertIsInstance(result, date)
        self.assertEqual(result.year, 2023)
        self.assertEqual(result.month, 7)
        self.assertEqual(result.day, 3)

    def test_parse_date_invalid_format(self):
        """Testa parse_date com uma data em formato inválido"""
        # Executa a função com formato inválido
        result = parse_date("03/07/2023")  # Formato DD/MM/YYYY em vez de YYYY-MM-DD
        
        # Verifica que retorna None para formato inválido
        self.assertIsNone(result)

    def test_parse_date_invalid_date(self):
        """Testa parse_date com uma data inexistente"""
        # Executa a função com uma data inexistente
        result = parse_date("2023-02-30")  # 30 de fevereiro não existe
        
        # Verifica que retorna None para data inexistente
        self.assertIsNone(result)

    def test_parse_date_non_string(self):
        """Testa parse_date com input que não é string"""
        # Executa a função com input que não é string
        result = parse_date(12345)
        
        # Verifica que retorna None
        self.assertIsNone(result)

    def test_safe_float_valid(self):
        """Testa safe_float com valor numérico válido"""
        # Testa com valores válidos
        self.assertEqual(safe_float("123.45"), 123.45)
        self.assertEqual(safe_float("0"), 0.0)
        self.assertEqual(safe_float("-10.5"), -10.5)
        
        # Testa com valores já numéricos
        self.assertEqual(safe_float(123.45), 123.45)
        self.assertEqual(safe_float(0), 0.0)

    def test_safe_float_invalid(self):
        """Testa safe_float com valores inválidos"""
        # Testa com strings não numéricas
        self.assertIsNone(safe_float("abc"))
        self.assertIsNone(safe_float("123abc"))
        
        # Testa com valores None ou vazios
        self.assertIsNone(safe_float(None))
        self.assertIsNone(safe_float(""))


if __name__ == '__main__':
    unittest.main() 