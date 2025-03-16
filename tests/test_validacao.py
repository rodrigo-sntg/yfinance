import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock

from app.validacao import (
    validar_data,
    validar_numero,
    validar_booleano,
    validar_opcao
)

class TestValidacao(unittest.TestCase):
    """Testes para as funções de validação de parâmetros"""
    
    def test_validar_data_valida(self):
        """Testa validação de uma data válida"""
        data, erro = validar_data("2023-01-15", "data_teste")
        self.assertIsNotNone(data)
        self.assertIsNone(erro)
        self.assertEqual(data.year, 2023)
        self.assertEqual(data.month, 1)
        self.assertEqual(data.day, 15)
    
    def test_validar_data_invalida(self):
        """Testa validação de uma data inválida"""
        data, erro = validar_data("2023/01/15", "data_teste")
        self.assertIsNone(data)
        self.assertIsNotNone(erro)
        
        data, erro = validar_data("15-01-2023", "data_teste")  # Formato invertido
        self.assertIsNone(data)
        self.assertIsNotNone(erro)
        
        data, erro = validar_data("abcd", "data_teste")  # Não é uma data
        self.assertIsNone(data)
        self.assertIsNotNone(erro)
    
    def test_validar_data_vazia_obrigatoria(self):
        """Testa validação de uma data vazia quando é obrigatória"""
        data, erro = validar_data("", "data_teste", obrigatorio=True)
        self.assertIsNone(data)
        self.assertIsNotNone(erro)
    
    def test_validar_data_vazia_opcional(self):
        """Testa validação de uma data vazia quando é opcional"""
        data, erro = validar_data("", "data_teste", obrigatorio=False)
        self.assertIsNone(data)
        self.assertIsNone(erro)
    
    def test_validar_numero_valido(self):
        """Testa validação de um número válido"""
        numero, erro = validar_numero("10.5", "numero_teste")
        self.assertIsNotNone(numero)
        self.assertIsNone(erro)
        self.assertEqual(numero, 10.5)
    
    def test_validar_numero_invalido(self):
        """Testa validação de um número inválido"""
        numero, erro = validar_numero("abc", "numero_teste")
        self.assertIsNone(numero)
        self.assertIsNotNone(erro)
    
    def test_validar_numero_vazio_obrigatorio(self):
        """Testa validação de um número vazio quando é obrigatório"""
        numero, erro = validar_numero("", "numero_teste", obrigatorio=True)
        self.assertIsNone(numero)
        self.assertIsNotNone(erro)
    
    def test_validar_numero_vazio_opcional(self):
        """Testa validação de um número vazio quando é opcional"""
        numero, erro = validar_numero("", "numero_teste", obrigatorio=False)
        self.assertEqual(numero, 0.0)
        self.assertIsNone(erro)
    
    def test_validar_numero_com_limites(self):
        """Testa validação de um número com limites mínimo e máximo"""
        # Dentro dos limites
        numero, erro = validar_numero("50", "numero_teste", min_valor=0, max_valor=100)
        self.assertEqual(numero, 50)
        self.assertIsNone(erro)
        
        # Abaixo do mínimo
        numero, erro = validar_numero("-10", "numero_teste", min_valor=0, max_valor=100)
        self.assertIsNone(numero)
        self.assertIsNotNone(erro)
        
        # Acima do máximo
        numero, erro = validar_numero("150", "numero_teste", min_valor=0, max_valor=100)
        self.assertIsNone(numero)
        self.assertIsNotNone(erro)
    
    def test_validar_numero_percentual(self):
        """Testa validação e conversão de um número percentual"""
        numero, erro = validar_numero("10.5", "taxa_teste", converter_percentual=True)
        self.assertEqual(numero, 0.105)
        self.assertIsNone(erro)
    
    def test_validar_booleano(self):
        """Testa validação de valores booleanos"""
        self.assertTrue(validar_booleano("true", "bool_teste"))
        self.assertTrue(validar_booleano("True", "bool_teste"))
        self.assertTrue(validar_booleano("t", "bool_teste"))
        self.assertTrue(validar_booleano("1", "bool_teste"))
        self.assertTrue(validar_booleano("sim", "bool_teste"))
        self.assertTrue(validar_booleano("s", "bool_teste"))
        self.assertTrue(validar_booleano("yes", "bool_teste"))
        self.assertTrue(validar_booleano("y", "bool_teste"))
        
        self.assertFalse(validar_booleano("false", "bool_teste"))
        self.assertFalse(validar_booleano("False", "bool_teste"))
        self.assertFalse(validar_booleano("f", "bool_teste"))
        self.assertFalse(validar_booleano("0", "bool_teste"))
        self.assertFalse(validar_booleano("nao", "bool_teste"))
        self.assertFalse(validar_booleano("n", "bool_teste"))
        self.assertFalse(validar_booleano("no", "bool_teste"))
        self.assertFalse(validar_booleano("qualquer-outra-coisa", "bool_teste"))
    
    def test_validar_opcao_valida(self):
        """Testa validação de uma opção válida"""
        opcao, erro = validar_opcao("diario", ["diario", "anual"], "regime_teste")
        self.assertEqual(opcao, "diario")
        self.assertIsNone(erro)
        
        # Deve normalizar para lowercase
        opcao, erro = validar_opcao("DIARIO", ["diario", "anual"], "regime_teste")
        self.assertEqual(opcao, "diario")
        self.assertIsNone(erro)
    
    def test_validar_opcao_invalida(self):
        """Testa validação de uma opção inválida"""
        opcao, erro = validar_opcao("mensal", ["diario", "anual"], "regime_teste")
        self.assertIsNone(opcao)
        self.assertIsNotNone(erro)
    
    def test_validar_opcao_vazia_com_padrao(self):
        """Testa validação de uma opção vazia quando há valor padrão"""
        opcao, erro = validar_opcao("", ["diario", "anual"], "regime_teste", valor_padrao="diario")
        self.assertEqual(opcao, "diario")
        self.assertIsNone(erro)
    
    def test_validar_opcao_vazia_sem_padrao(self):
        """Testa validação de uma opção vazia quando não há valor padrão"""
        opcao, erro = validar_opcao("", ["diario", "anual"], "regime_teste")
        self.assertIsNone(opcao)
        self.assertIsNotNone(erro)


if __name__ == '__main__':
    unittest.main() 