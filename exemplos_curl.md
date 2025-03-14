## Simulação de Investimentos

### Simulação Básica
```shell
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

### Exemplo de Resposta:
```json
{
  "sucesso": true,
  "resumo": {
    "valor_final_bruto": 1198376.78,
    "total_investido": 250000.00,
    "total_de_rendimentos_brutos": 948376.78,
    "total_de_taxas_de_administracao": 25000.00,
    "total_de_impostos": 142256.52,
    "valor_final_liquido": 1031120.26,
    "valor_final_liquido_ajustado_pela_inflacao": 424562.97,
    "retorno_anualizado_liquido_pct": 7.33,
    "retorno_anualizado_ajustado_pela_inflacao_pct": 2.71
  }
}
```

### Simulação com Histórico Mensal
```shell
curl -X POST "http://localhost:5001/simulacao" \
  -H "Content-Type: application/json" \
  -d '{
    "investimento_inicial": 10000,
    "aporte_mensal": 1000,
    "anos": 20,
    "retorno_anual": 0.10,
    "taxa_administracao": 0.005,
    "aliquota_imposto": 0.15,
    "inflacao_anual": 0.045,
    "detalhes": true
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