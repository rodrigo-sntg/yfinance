# Exemplos de Requisições CURL

Este documento contém exemplos de requisições CURL para testar a API.

## Informações do Stock

### Obter Dados de um Ticker
```bash
curl -X GET "http://localhost:5000/stock/PETR4.SA" -H "accept: application/json"
```

### Obter Dados de Múltiplos Tickers
```bash
curl -X POST "http://localhost:5000/stocks" \
  -H "Content-Type: application/json" \
  -d '{"tickers": ["PETR4.SA", "VALE3.SA", "ITUB4.SA"]}'
```

### Verificar se um Ticker existe
```bash
curl -X GET "http://localhost:5000/stock/validate/PETR4.SA" -H "accept: application/json"
```

## Informações de Investimentos

### Calcular Rendimento
```bash
curl -X POST "http://localhost:5000/investimento" \
  -H "Content-Type: application/json" \
  -d '{
    "data_inicial": "2023-01-01",
    "valor_investido": 1000.00,
    "data_final": "2023-03-01",
    "taxa_admin": 0.0025,
    "taxa_custodia": 0.00,
    "incluir_impostos": true
  }'
```

### Analisar Investimento
```bash
curl -X POST "http://localhost:5000/investimento/analisar" \
  -H "Content-Type: application/json" \
  -d '{
    "data_inicial": "2023-01-01",
    "valor_investido": 1000.00,
    "data_final": "2023-03-01"
  }'
```

### Simulação de Investimento com Aportes Mensais
```bash
curl -X POST "http://localhost:5001/simulacao" \
  -H "Content-Type: application/json" \
  -d '{
    "investimento_inicial": 10000,
    "aporte_mensal": 1000,
    "anos": 20,
    "retorno_anual": 0.10,
    "taxa_administracao": 0.005,
    "aliquota_imposto": 0.15,
    "inflacao_anual": 0.045
  }'
```

### Simulação de Investimento com Dividendos e Aportes Trimestrais
```bash
curl -X POST "http://localhost:5001/simulacao" \
  -H "Content-Type: application/json" \
  -d '{
    "investimento_inicial": 10000,
    "aporte_mensal": 3000,
    "anos": 20,
    "retorno_anual": 0.10,
    "taxa_administracao": 0.005,
    "aliquota_imposto": 0.15,
    "inflacao_anual": 0.045,
    "frequencia_aporte": "quarterly",
    "dividend_yield": 0.03,
    "detalhes": true
  }'
```

### Simulação de Investimento em Renda Fixa Sem Aportes
```bash
curl -X POST "http://localhost:5001/simulacao" \
  -H "Content-Type: application/json" \
  -d '{
    "investimento_inicial": 50000,
    "aporte_mensal": 0,
    "anos": 5,
    "retorno_anual": 0.11,
    "taxa_administracao": 0.002,
    "aliquota_imposto": 0.15,
    "inflacao_anual": 0.05,
    "frequencia_aporte": "none",
    "dividend_yield": 0
  }'
```

### Simulação de Investimento em Ações com Dividendos e Aportes Semestrais
```bash
curl -X POST "http://localhost:5001/simulacao" \
  -H "Content-Type: application/json" \
  -d '{
    "investimento_inicial": 5000,
    "aporte_mensal": 3000,
    "anos": 30,
    "retorno_anual": 0.15,
    "taxa_administracao": 0.02,
    "aliquota_imposto": 0.15,
    "inflacao_anual": 0.04,
    "frequencia_aporte": "semiannually",
    "dividend_yield": 0.045
  }'
```

### Simulação de Investimento em Renda Fixa
```shell
curl -X POST "http://localhost:5001/simulacao" \
  -H "Content-Type: application/json" \
  -d '{
    "investimento_inicial": 50000,
    "aporte_mensal": 0,
    "anos": 5,
    "retorno_anual": 0.11,
    "taxa_administracao": 0.002,
    "aliquota_imposto": 0.15,
    "inflacao_anual": 0.05
  }'
```

### Simulação de Investimento em Renda Variável de Longo Prazo
```shell
curl -X POST "http://localhost:5001/simulacao" \
  -H "Content-Type: application/json" \
  -d '{
    "investimento_inicial": 5000,
    "aporte_mensal": 500,
    "anos": 30,
    "retorno_anual": 0.15,
    "taxa_administracao": 0.02,
    "aliquota_imposto": 0.15,
    "inflacao_anual": 0.04
  }'
``` 