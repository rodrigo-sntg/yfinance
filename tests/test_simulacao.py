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
    
    # Verifica se o histórico mensal tem o número correto de meses
    assert len(resultado["historico_mensal"]) == 12
    
    # Verifica valores específicos
    assert resumo["total_investido"] == 22000  # 10000 inicial + 12 * 1000
    assert resumo["valor_final_bruto"] > resumo["total_investido"]
    assert resumo["valor_final_liquido"] < resumo["valor_final_bruto"]

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
    
    # Testa sem histórico mensal
    assert "historico_mensal" not in resposta
    
    # Testa com histórico mensal
    dados["detalhes"] = True
    response = client.post("/simulacao", json=dados)
    assert response.status_code == 200
    
    resposta = json.loads(response.data)
    assert "historico_mensal" in resposta
    assert len(resposta["historico_mensal"]) == 12

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