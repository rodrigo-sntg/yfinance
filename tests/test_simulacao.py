import json
import pytest
from app import create_app
from app.routes import calcular_simulacao

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_calcular_simulacao():
    """Testa a função de cálculo de simulação de investimentos"""
    resultado = calcular_simulacao(
        investimento_inicial=10000,
        aporte_mensal=1000,
        anos=1,
        retorno_anual=0.10,
        taxa_administracao=0.01,
        aliquota_imposto=0.15,
        inflacao_anual=0.04
    )
    
    # Verifica se a função retorna os campos esperados
    assert "resumo" in resultado
    assert "historico_mensal" in resultado
    
    # Verifica se o resumo contém todos os campos esperados
    resumo = resultado["resumo"]
    assert "valor_final_bruto" in resumo
    assert "total_investido" in resumo
    assert "total_de_rendimentos_brutos" in resumo
    assert "total_de_taxas_de_administracao" in resumo
    assert "total_de_impostos" in resumo
    assert "valor_final_liquido" in resumo
    assert "valor_final_liquido_ajustado_pela_inflacao" in resumo
    assert "retorno_anualizado_liquido_pct" in resumo
    assert "retorno_anualizado_ajustado_pela_inflacao_pct" in resumo
    assert "frequencia_aporte" in resumo
    assert "rendimento_dividendos_anual_pct" in resumo
    
    # Verifica se o histórico mensal tem o número correto de meses
    assert len(resultado["historico_mensal"]) == 12
    
    # Verifica valores específicos
    assert resumo["total_investido"] == 22000  # 10000 inicial + 12 * 1000
    assert resumo["valor_final_bruto"] > resumo["total_investido"]
    assert resumo["valor_final_liquido"] < resumo["valor_final_bruto"]
    assert resumo["frequencia_aporte"] == "monthly"
    assert resumo["rendimento_dividendos_anual_pct"] == 0.0

def test_calcular_simulacao_com_dividendos():
    """Testa a função de cálculo com dividendos"""
    resultado = calcular_simulacao(
        investimento_inicial=10000,
        aporte_mensal=1000,
        anos=1,
        retorno_anual=0.10,
        taxa_administracao=0.01,
        aliquota_imposto=0.15,
        inflacao_anual=0.04,
        dividend_yield=0.04  # 4% ao ano
    )
    
    # Verifica campos relacionados a dividendos
    resumo = resultado["resumo"]
    assert resumo["total_de_dividendos"] > 0
    assert resumo["total_de_impostos_dividendos"] > 0
    assert resumo["rendimento_dividendos_anual_pct"] == 4.0
    
    # Verifica se todos os meses têm dividendos
    for mes in resultado["historico_mensal"]:
        assert "dividendo" in mes
        assert "dividendo_pct" in mes
        assert "imposto_dividendos" in mes
        assert mes["dividendo"] > 0

def test_calcular_simulacao_frequencia_aporte():
    """Testa diferentes frequências de aporte"""
    # Teste com aporte trimestral
    resultado_trimestral = calcular_simulacao(
        investimento_inicial=10000,
        aporte_mensal=3000,  # 3000 a cada 3 meses = 1000 por mês em média
        anos=1,
        retorno_anual=0.10,
        taxa_administracao=0.01,
        aliquota_imposto=0.15,
        inflacao_anual=0.04,
        frequencia_aporte="quarterly"  # Trimestral
    )
    
    # Teste com aporte mensal equivalente
    resultado_mensal = calcular_simulacao(
        investimento_inicial=10000,
        aporte_mensal=1000,  # 1000 por mês
        anos=1,
        retorno_anual=0.10,
        taxa_administracao=0.01,
        aliquota_imposto=0.15,
        inflacao_anual=0.04,
        frequencia_aporte="monthly"  # Mensal
    )
    
    # Teste sem aportes
    resultado_sem_aporte = calcular_simulacao(
        investimento_inicial=10000,
        aporte_mensal=0,
        anos=1,
        retorno_anual=0.10,
        taxa_administracao=0.01,
        aliquota_imposto=0.15,
        inflacao_anual=0.04,
        frequencia_aporte="none"  # Sem aportes
    )
    
    # Verificações
    assert resultado_trimestral["resumo"]["frequencia_aporte"] == "quarterly"
    assert resultado_mensal["resumo"]["frequencia_aporte"] == "monthly"
    assert resultado_sem_aporte["resumo"]["frequencia_aporte"] == "none"
    
    # Verifica que apenas alguns meses têm aportes no caso trimestral
    meses_com_aporte_trimestral = [mes for mes in resultado_trimestral["historico_mensal"] if mes["aporte_no_mes"] > 0]
    assert len(meses_com_aporte_trimestral) == 4  # Meses 3, 6, 9 e 12
    
    # Verifica que todos os meses têm aportes no caso mensal
    meses_com_aporte_mensal = [mes for mes in resultado_mensal["historico_mensal"] if mes["aporte_no_mes"] > 0]
    assert len(meses_com_aporte_mensal) == 12
    
    # Verifica que nenhum mês tem aporte no caso sem aportes
    meses_com_aporte_sem = [mes for mes in resultado_sem_aporte["historico_mensal"] if mes["aporte_no_mes"] > 0]
    assert len(meses_com_aporte_sem) == 0
    
    # Os totais investidos devem ser aproximadamente iguais (+/- 1%)
    assert resultado_trimestral["resumo"]["total_investido"] == 22000  # 10000 + 4 * 3000
    assert resultado_mensal["resumo"]["total_investido"] == 22000  # 10000 + 12 * 1000
    assert resultado_sem_aporte["resumo"]["total_investido"] == 10000  # Apenas investimento inicial

def test_simulacao_endpoint(client):
    """Testa o endpoint de simulação de investimentos"""
    dados = {
        "investimento_inicial": 10000,
        "aporte_mensal": 1000,
        "anos": 1,
        "retorno_anual": 0.10,
        "taxa_administracao": 0.01,
        "aliquota_imposto": 0.15,
        "inflacao_anual": 0.04
    }
    
    response = client.post("/simulacao", json=dados)
    assert response.status_code == 200
    
    resposta = json.loads(response.data)
    assert "sucesso" in resposta
    assert resposta["sucesso"] == True
    assert "resumo" in resposta
    
    # Testa valores específicos
    resumo = resposta["resumo"]
    assert resumo["total_investido"] == 22000
    assert resumo["valor_final_bruto"] > resumo["total_investido"]
    assert resumo["frequencia_aporte"] == "monthly"  # Padrão
    
    # Testa sem histórico mensal
    assert "historico_mensal" not in resposta
    
    # Testa com histórico mensal
    dados["detalhes"] = True
    response = client.post("/simulacao", json=dados)
    assert response.status_code == 200
    
    resposta = json.loads(response.data)
    assert "historico_mensal" in resposta
    assert len(resposta["historico_mensal"]) == 12

def test_simulacao_endpoint_novos_parametros(client):
    """Testa o endpoint de simulação com os novos parâmetros"""
    dados = {
        "investimento_inicial": 10000,
        "aporte_mensal": 1000,
        "anos": 1,
        "retorno_anual": 0.10,
        "taxa_administracao": 0.01,
        "aliquota_imposto": 0.15,
        "inflacao_anual": 0.04,
        "frequencia_aporte": "quarterly",
        "dividend_yield": 0.03
    }
    
    response = client.post("/simulacao", json=dados)
    assert response.status_code == 200
    
    resposta = json.loads(response.data)
    resumo = resposta["resumo"]
    
    # Testa valores específicos
    assert resumo["frequencia_aporte"] == "quarterly"
    assert resumo["rendimento_dividendos_anual_pct"] == 3.0
    assert resumo["total_de_dividendos"] > 0
    
    # Testa com frequência inválida
    dados["frequencia_aporte"] = "invalid"
    response = client.post("/simulacao", json=dados)
    assert response.status_code == 400
    
    # Testa com dividend yield negativo
    dados["frequencia_aporte"] = "monthly"
    dados["dividend_yield"] = -0.01
    response = client.post("/simulacao", json=dados)
    assert response.status_code == 400

def test_simulacao_endpoint_validacao(client):
    """Testa validação de parâmetros no endpoint de simulação"""
    # Parâmetro faltando
    dados = {
        "investimento_inicial": 10000,
        "aporte_mensal": 1000,
        "anos": 1,
        "retorno_anual": 0.10,
        "taxa_administracao": 0.01,
        "aliquota_imposto": 0.15
        # falta inflacao_anual
    }
    
    response = client.post("/simulacao", json=dados)
    assert response.status_code == 400
    
    # Valor inválido
    dados = {
        "investimento_inicial": 10000,
        "aporte_mensal": 1000,
        "anos": 0,  # inválido
        "retorno_anual": 0.10,
        "taxa_administracao": 0.01,
        "aliquota_imposto": 0.15,
        "inflacao_anual": 0.04
    }
    
    response = client.post("/simulacao", json=dados)
    assert response.status_code == 400
    
    # Alíquota fora do intervalo
    dados = {
        "investimento_inicial": 10000,
        "aporte_mensal": 1000,
        "anos": 1,
        "retorno_anual": 0.10,
        "taxa_administracao": 0.01,
        "aliquota_imposto": 1.5,  # inválido
        "inflacao_anual": 0.04
    }
    
    response = client.post("/simulacao", json=dados)
    assert response.status_code == 400 