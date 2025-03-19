import unittest
import json
from datetime import date
import pandas as pd

from app.aposentadoria import simular_aposentadoria

class TestAposentadoria(unittest.TestCase):
    
    def test_simulacao_basica(self):
        """Testa uma simulação básica com valores padrão"""
        resultado = simular_aposentadoria(
            idade_atual=30,
            idade_aposentadoria=60,
            patrimonio_inicial=100000,
            aportes_mensais=2000,
            retirada_mensal=8000,
            retorno_anual=0.08,
            inflacao_anual=0.04
        )
        
        # Verificar se os campos principais estão presentes
        self.assertIn("patrimonio_final", resultado)
        self.assertIn("idade_quando_acaba", resultado)
        self.assertIn("anos_aposentadoria", resultado)
        self.assertIn("evolucao_patrimonial", resultado)
        self.assertIn("parametros", resultado)
        
        # Verificar se os parâmetros foram armazenados corretamente
        self.assertEqual(resultado["parametros"]["idade_atual"], 30)
        self.assertEqual(resultado["parametros"]["idade_aposentadoria"], 60)
        self.assertEqual(resultado["parametros"]["patrimonio_inicial"], 100000)
        self.assertEqual(resultado["parametros"]["aportes_mensais"], 2000)
        self.assertEqual(resultado["parametros"]["retirada_mensal"], 8000)
        self.assertEqual(resultado["parametros"]["retorno_anual"], 8.0)  # Convertido para percentual
        self.assertEqual(resultado["parametros"]["inflacao_anual"], 4.0)  # Convertido para percentual
        
        # Verificar se a evolução patrimonial está correta
        evolucao = resultado["evolucao_patrimonial"]
        self.assertGreater(len(evolucao), 0)
        
        # O primeiro ano deve ter o patrimônio inicial
        self.assertEqual(evolucao[0]["idade"], 30)
        self.assertEqual(evolucao[0]["patrimonio"], 100000)
        self.assertEqual(evolucao[0]["fase"], "acumulacao")
        
        # O ano da aposentadoria deve ser o último da fase de acumulação
        ano_aposentadoria = next(e for e in evolucao if e["idade"] == 60)
        self.assertEqual(ano_aposentadoria["fase"], "acumulacao")
        
        # O ano após a aposentadoria deve ser o primeiro da fase de retirada
        ano_pos_aposentadoria = next(e for e in evolucao if e["idade"] == 61)
        self.assertEqual(ano_pos_aposentadoria["fase"], "retirada")
        
        # Verificar se o dinheiro acaba em algum momento ou se dura até o limite
        if resultado["idade_quando_acaba"] is not None:
            self.assertLessEqual(resultado["patrimonio_final"], 0)
            self.assertEqual(resultado["anos_aposentadoria"], 
                            resultado["idade_quando_acaba"] - resultado["parametros"]["idade_aposentadoria"])
        else:
            self.assertGreater(resultado["patrimonio_final"], 0)
            self.assertIsNone(resultado["anos_aposentadoria"])
    
    def test_sem_aportes(self):
        """Testa uma simulação sem aportes mensais"""
        resultado = simular_aposentadoria(
            idade_atual=40,
            idade_aposentadoria=65,
            patrimonio_inicial=1000000,
            aportes_mensais=0,
            retirada_mensal=5000,
            retorno_anual=0.07,
            inflacao_anual=0.03
        )
        
        # Verificar que a simulação completou corretamente
        self.assertIsNotNone(resultado["patrimonio_final"])
        
        # Evolução patrimonial deve ter entradas para cada ano
        evolucao = resultado["evolucao_patrimonial"]
        anos_acumulacao = 65 - 40 + 1  # +1 para incluir o ano atual
        self.assertGreaterEqual(len(evolucao), anos_acumulacao)
        
        # Verificar se o primeiro ano da fase de retirada tem idade = idade_aposentadoria + 1
        primeiro_ano_retirada = next(e for e in evolucao if e["fase"] == "retirada")
        self.assertEqual(primeiro_ano_retirada["idade"], 66)
    
    def test_retorno_inflacao_real(self):
        """Testa se o retorno real está sendo calculado corretamente"""
        retorno_anual = 0.10
        inflacao_anual = 0.05
        retorno_real_esperado = (1 + retorno_anual) / (1 + inflacao_anual) - 1
        
        resultado = simular_aposentadoria(
            idade_atual=30,
            idade_aposentadoria=35,
            patrimonio_inicial=100000,
            aportes_mensais=1000,
            retirada_mensal=2000,
            retorno_anual=retorno_anual,
            inflacao_anual=inflacao_anual
        )
        
        # Verificar se o retorno real foi calculado corretamente (com margem para arredondamentos)
        self.assertAlmostEqual(
            resultado["parametros"]["retorno_real"] / 100,  # Convertido de percentual para decimal
            retorno_real_esperado,
            places=5
        )
    
    def test_patrimonio_nunca_acaba(self):
        """Testa um cenário onde o patrimônio nunca acaba (retorno alto, retirada baixa)"""
        resultado = simular_aposentadoria(
            idade_atual=30,
            idade_aposentadoria=60,
            patrimonio_inicial=2000000,
            aportes_mensais=5000,
            retirada_mensal=5000,  # Retirada mensal baixa
            retorno_anual=0.10,    # Retorno alto
            inflacao_anual=0.04
        )
        
        # O patrimônio não deve acabar (deve ser null)
        self.assertIsNone(resultado["idade_quando_acaba"])
        self.assertIsNone(resultado["anos_aposentadoria"])
        
        # O patrimônio final deve ser positivo
        self.assertGreater(resultado["patrimonio_final"], 0)
        
        # A última entrada deve ter uma idade próxima ao limite (120 anos)
        ultima_entrada = resultado["evolucao_patrimonial"][-1]
        self.assertGreaterEqual(ultima_entrada["idade"], 120)
    
    def test_patrimonio_acaba_rapido(self):
        """Testa um cenário onde o patrimônio acaba rapidamente (retorno baixo, retirada alta)"""
        resultado = simular_aposentadoria(
            idade_atual=60,
            idade_aposentadoria=65,
            patrimonio_inicial=300000,
            aportes_mensais=0,
            retirada_mensal=10000,  # Retirada mensal alta
            retorno_anual=0.04,     # Retorno baixo
            inflacao_anual=0.04     # Inflação igual ao retorno (retorno real = 0)
        )
        
        # O patrimônio deve acabar
        self.assertIsNotNone(resultado["idade_quando_acaba"])
        
        # Com retorno real de 0%, o patrimônio deve durar aproximadamente 30 meses (2.5 anos)
        # 300000 / 10000 / 12 = 2.5 anos
        self.assertLessEqual(resultado["idade_quando_acaba"], 68)
        
        # Verificar que o patrimônio final é zero ou negativo
        self.assertLessEqual(resultado["patrimonio_final"], 0)


if __name__ == '__main__':
    unittest.main() 