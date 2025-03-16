import unittest
from datetime import datetime, timedelta
import math

from app.prefixado import (
    calcular_investimento_prefixado,
    calcular_aliquota_ir,
    calcular_aliquota_iof
)

class TestPrefixado(unittest.TestCase):
    """Testes para os cálculos de investimento pré-fixado"""
    
    def test_calculo_aliquota_ir(self):
        """Testa o cálculo das alíquotas de IR com base no prazo"""
        self.assertEqual(calcular_aliquota_ir(30), 0.225)  # Até 180 dias: 22.5%
        self.assertEqual(calcular_aliquota_ir(180), 0.225)  # Limite: 180 dias
        self.assertEqual(calcular_aliquota_ir(181), 0.20)  # 181 dias: 20%
        self.assertEqual(calcular_aliquota_ir(360), 0.20)  # Limite: 360 dias
        self.assertEqual(calcular_aliquota_ir(361), 0.175)  # 361 dias: 17.5%
        self.assertEqual(calcular_aliquota_ir(720), 0.175)  # Limite: 720 dias
        self.assertEqual(calcular_aliquota_ir(721), 0.15)  # Acima de 720 dias: 15%
        self.assertEqual(calcular_aliquota_ir(1000), 0.15)  # Bem acima de 720 dias: 15%
    
    def test_calculo_aliquota_iof(self):
        """Testa o cálculo das alíquotas de IOF com base no prazo"""
        self.assertAlmostEqual(calcular_aliquota_iof(1), 0.96 + 0.04)  # 1 dia: 100% IOF
        self.assertAlmostEqual(calcular_aliquota_iof(15), (0.5 * 0.96) + 0.04)  # 15 dias: ~50% IOF
        self.assertAlmostEqual(calcular_aliquota_iof(29), (1/30 * 0.96) + 0.04)  # 29 dias: ~7% IOF
        self.assertEqual(calcular_aliquota_iof(30), 0.04)  # 30 dias: 4% IOF
        self.assertEqual(calcular_aliquota_iof(31), 0.0)  # Acima de 30 dias: 0% IOF
    
    def test_calculo_investimento_regime_diario(self):
        """Testa o cálculo completo de um investimento com regime diário"""
        hoje = datetime.now().date()
        um_ano_atras = hoje - timedelta(days=365)
        
        # Simular investimento de R$ 1000 por um ano a 10% ao ano
        resultado = calcular_investimento_prefixado(
            data_inicial=um_ano_atras,
            valor_investido=1000.0,
            taxa_anual=0.10,  # 10% ao ano
            data_final=hoje,
            incluir_impostos=True,
            regime="diario"
        )
        
        # Verifica se tem todos os campos esperados
        self.assertIn("valor_investido", resultado)
        self.assertIn("data_inicial", resultado)
        self.assertIn("data_final", resultado)
        self.assertIn("taxa_anual", resultado)
        self.assertIn("regime_capitalizacao", resultado)
        self.assertIn("dias_totais", resultado)
        self.assertIn("dias_uteis", resultado)
        self.assertIn("rendimento_bruto", resultado)
        self.assertIn("imposto_renda", resultado)
        self.assertIn("valor_final_liquido", resultado)
        self.assertIn("resumo", resultado)
        
        # Verifica se o valor investido está correto
        self.assertEqual(resultado["valor_investido"], 1000.0)
        
        # Verifica se o regime de capitalização está correto
        self.assertEqual(resultado["regime_capitalizacao"], "diario")
        
        # Verifica se a taxa anual está correta (em percentual)
        self.assertEqual(resultado["taxa_anual"], 10.0)
        
        # Verifica se o rendimento bruto é positivo
        self.assertGreater(resultado["rendimento_bruto"], 0)
        
        # Verifica se o valor final é maior que o valor investido
        self.assertGreater(resultado["valor_final_bruto"], 1000.0)
        
        # Verifica se o imposto de renda foi calculado
        self.assertGreater(resultado["imposto_renda"], 0)
        
        # Verifica se tem o resumo
        self.assertIn("valor_final_bruto", resultado["resumo"])
        self.assertIn("rendimento_percentual", resultado["resumo"])
    
    def test_calculo_investimento_regime_anual(self):
        """Testa o cálculo completo de um investimento com regime anual"""
        hoje = datetime.now().date()
        um_ano_atras = hoje - timedelta(days=365)
        
        # Simular investimento de R$ 1000 por um ano a 10% ao ano
        resultado = calcular_investimento_prefixado(
            data_inicial=um_ano_atras,
            valor_investido=1000.0,
            taxa_anual=0.10,  # 10% ao ano
            data_final=hoje,
            incluir_impostos=True,
            regime="anual"
        )
        
        # Verifica se o regime de capitalização está correto
        self.assertEqual(resultado["regime_capitalizacao"], "anual")
        
        # Verifica se o valor final é próximo de 1100 (1000 * 1.10)
        # Não é exatamente 1100 porque o ano pode não ter exatamente 365 dias
        self.assertAlmostEqual(resultado["valor_final_bruto"], 1100.0, delta=5.0)
        
    def test_calculo_sem_impostos(self):
        """Testa o cálculo sem incluir impostos"""
        hoje = datetime.now().date()
        um_ano_atras = hoje - timedelta(days=365)
        
        resultado = calcular_investimento_prefixado(
            data_inicial=um_ano_atras,
            valor_investido=1000.0,
            taxa_anual=0.10,
            data_final=hoje,
            incluir_impostos=False
        )
        
        # Verifica que não tem impostos no resultado
        self.assertNotIn("imposto_renda", resultado)
        self.assertNotIn("imposto_iof", resultado)
        
        # O valor líquido deve ser maior quando não tem impostos
        self.assertGreater(resultado["valor_final_liquido"], 1000.0)
    
    def test_calculo_com_taxas(self):
        """Testa o cálculo com taxas de administração e custódia"""
        hoje = datetime.now().date()
        um_ano_atras = hoje - timedelta(days=365)
        
        # Com taxas
        resultado_com_taxas = calcular_investimento_prefixado(
            data_inicial=um_ano_atras,
            valor_investido=1000.0,
            taxa_anual=0.10,
            data_final=hoje,
            taxa_admin=0.02,  # 2% ao ano
            taxa_custodia=0.01,  # 1% ao ano
            incluir_impostos=False
        )
        
        # Sem taxas
        resultado_sem_taxas = calcular_investimento_prefixado(
            data_inicial=um_ano_atras,
            valor_investido=1000.0,
            taxa_anual=0.10,
            data_final=hoje,
            taxa_admin=0.0,
            taxa_custodia=0.0,
            incluir_impostos=False
        )
        
        # O resultado com taxas deve ser menor que o resultado sem taxas
        self.assertLess(resultado_com_taxas["valor_final_liquido"], 
                         resultado_sem_taxas["valor_final_liquido"])
        
        # Verifica se as taxas foram calculadas
        self.assertGreater(resultado_com_taxas["valor_taxa_administracao"], 0)
        self.assertGreater(resultado_com_taxas["valor_taxa_custodia"], 0)
    
    def test_erro_periodo_invalido(self):
        """Testa se lança erro para período inválido"""
        hoje = datetime.now().date()
        amanha = hoje + timedelta(days=1)
        
        # Período inválido (data final é anterior à data inicial)
        with self.assertRaises(ValueError):
            calcular_investimento_prefixado(
                data_inicial=hoje,
                valor_investido=1000.0,
                taxa_anual=0.10,
                data_final=hoje,  # Mesmo dia (0 dias)
                incluir_impostos=False
            )


if __name__ == '__main__':
    unittest.main() 