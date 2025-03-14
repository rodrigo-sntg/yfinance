# API de Simulação de Investimentos

Esta API permite simular investimentos a longo prazo com diferentes taxas de retorno, impostos e inflação.

## Endpoint Disponível

### POST /simulacao

Realiza uma simulação de investimento a longo prazo, considerando aportes periódicos, taxas de administração, impostos, inflação e dividendos.

**Corpo da Requisição (JSON):**

```json
{
  "investimento_inicial": 10000,
  "aporte_mensal": 1000,
  "anos": 20,
  "retorno_anual": 0.10,
  "taxa_administracao": 0.005,
  "aliquota_imposto": 0.15,
  "inflacao_anual": 0.045,
  "frequencia_aporte": "monthly",
  "dividend_yield": 0.03,
  "detalhes": false
}
```

**Parâmetros:**

- `investimento_inicial` (obrigatório): Valor inicial a ser investido (float)
- `aporte_mensal` (obrigatório): Valor a ser aportado periodicamente (float)
- `anos` (obrigatório): Duração do investimento em anos (int)
- `retorno_anual` (obrigatório): Taxa de retorno anual esperada (float, em decimal - ex: 0.10 para 10%)
- `taxa_administracao` (obrigatório): Taxa de administração anual (float, em decimal - ex: 0.005 para 0.5%)
- `aliquota_imposto` (obrigatório): Alíquota de imposto sobre o rendimento (float, em decimal - ex: 0.15 para 15%)
- `inflacao_anual` (obrigatório): Taxa de inflação anual esperada (float, em decimal - ex: 0.045 para 4.5%)
- `frequencia_aporte` (opcional): Frequência dos aportes (string, default: "monthly")
  - Valores válidos: "monthly" (mensal), "bimonthly" (bimestral), "quarterly" (trimestral), "semiannually" (semestral), "annually" (anual), "none" (sem aportes)
- `dividend_yield` (opcional): Rendimento anual em dividendos (float, em decimal - ex: 0.03 para 3%, default: 0)
- `detalhes` (opcional): Se true, retorna o histórico mensal completo (boolean, default: false)

## Frequências de Aporte

A frequência de aporte determina o intervalo com que novos valores são adicionados ao investimento. 
O valor fornecido no parâmetro `aporte_mensal` será aplicado conforme a frequência escolhida.

| Frequência      | Código           | Descrição                                   | Aportes por ano | Intervalo (meses) |
|-----------------|------------------|---------------------------------------------|-----------------|-------------------|
| Mensal          | "monthly"        | Aportes realizados todos os meses           | 12              | 1                 |
| Bimestral       | "bimonthly"      | Aportes realizados a cada 2 meses           | 6               | 2                 |
| Trimestral      | "quarterly"      | Aportes realizados a cada 3 meses           | 4               | 3                 |
| Semestral       | "semiannually"   | Aportes realizados a cada 6 meses           | 2               | 6                 |
| Anual           | "annually"       | Aportes realizados uma vez por ano          | 1               | 12                |
| Sem aportes     | "none"           | Apenas investimento inicial, sem aportes    | 0               | -                 |

**Importante:** Para todas as frequências, o valor especificado em `aporte_mensal` é o valor a ser investido em cada aporte individual, não um valor mensal que será dividido.

**Exemplos:**
- Se você configurar `aporte_mensal: 1000` com `frequencia_aporte: "monthly"`, serão investidos R$ 1.000,00 a cada mês (total de R$ 12.000,00 por ano)
- Se você configurar `aporte_mensal: 3000` com `frequencia_aporte: "quarterly"`, serão investidos R$ 3.000,00 a cada trimestre (total de R$ 12.000,00 por ano)
- Se você configurar `aporte_mensal: 5000` com `frequencia_aporte: "none"`, não serão realizados aportes adicionais, apenas o investimento inicial

**Exemplo de Resposta (sem detalhes):**

```json
{
  "sucesso": true,
  "resumo": {
    "valor_final_bruto": 1198376.78,
    "total_investido": 250000.00,
    "total_de_rendimentos_brutos": 948376.78,
    "total_de_dividendos": 325410.55,
    "total_de_taxas_de_administracao": 25000.00,
    "total_de_impostos_rendimentos": 142256.52,
    "total_de_impostos_dividendos": 48811.58,
    "total_de_impostos": 191068.10,
    "valor_final_liquido": 1031120.26,
    "valor_final_liquido_ajustado_pela_inflacao": 424562.97,
    "retorno_anualizado_liquido_pct": 7.33,
    "retorno_anualizado_ajustado_pela_inflacao_pct": 2.71,
    "frequencia_aporte": "monthly",
    "rendimento_dividendos_anual_pct": 3.0
  }
}
```

**Exemplo de Resposta (com detalhes):**

A resposta inclui todos os elementos acima mais o campo `historico_mensal`, que contém um array com os dados de cada mês da simulação:

```json
{
  "sucesso": true,
  "resumo": {
    // Mesmo conteúdo do exemplo anterior
  },
  "historico_mensal": [
    {
      "mes": 1,
      "valor_investido": 11000.00,
      "rendimento": 79.17,
      "rendimento_pct": 0.79,
      "dividendo": 24.85,
      "dividendo_pct": 0.25,
      "saldo_bruto": 11104.02,
      "saldo_liquido": 11085.36,
      "retorno_acumulado": 85.36,
      "taxa_de_administracao": 4.17,
      "imposto": 15.60,
      "imposto_rendimento": 11.88,
      "imposto_dividendos": 3.73,
      "rendimento_liquido": 84.25,
      "aporte_no_mes": 1000.00
    },
    // ... outros meses
    {
      "mes": 240,
      "valor_investido": 250000.00,
      "rendimento": 9521.96,
      "rendimento_pct": 0.79,
      "dividendo": 2985.94,
      "dividendo_pct": 0.25,
      "saldo_bruto": 1210884.68,
      "saldo_liquido": 1038064.04,
      "retorno_acumulado": 788064.04,
      "taxa_de_administracao": 500.83,
      "imposto": 1876.18,
      "imposto_rendimento": 1428.29,
      "imposto_dividendos": 447.89,
      "rendimento_liquido": 10130.89,
      "aporte_no_mes": 1000.00
    }
  ]
}
```

**Códigos de Retorno:**

- `200 OK`: Simulação realizada com sucesso
- `400 Bad Request`: Parâmetros inválidos ou faltantes
- `500 Internal Server Error`: Erro no servidor ao processar a simulação

## Fórmulas Utilizadas

### Taxa de Retorno Mensal
```
retorno_mensal = (1 + (retorno_anual - taxa_administracao)) ^ (1/12) - 1
```

### Taxa de Dividendos Mensal
```
dividend_yield_mensal = (1 + dividend_yield) ^ (1/12) - 1
```

### Juros Compostos
Para cada mês, o saldo é atualizado com:
```
rendimento = saldo_atual * retorno_mensal
dividendo = saldo_atual * dividend_yield_mensal
taxa_adm = saldo_atual * (taxa_administracao / 12)
imposto_rendimento = rendimento * aliquota_imposto
imposto_dividendos = dividendo * aliquota_imposto
imposto_total = imposto_rendimento + imposto_dividendos
rendimento_liquido = rendimento + dividendo - imposto_total - taxa_adm

# Se for mês de aporte conforme a frequência
aporte_no_mes = aporte_mensal (se for mês de aporte) ou 0 (caso contrário)

saldo_bruto += rendimento + dividendo + aporte_no_mes
saldo_liquido += rendimento_liquido + aporte_no_mes
```

### CAGR (Taxa Composta de Crescimento Anual)
```
cagr_liquido = (montante_final_liquido / total_investido) ^ (1 / anos) - 1
cagr_real = (montante_final_real / total_investido) ^ (1 / anos) - 1
```

### Ajuste pela Inflação
```
montante_final_real = montante_final_liquido / ((1 + inflacao_anual) ^ anos)
```

## Exemplos de Uso

### Simulação Básica com Aportes Mensais
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

### Simulação com Dividendos e Aportes Trimestrais
```shell
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
    "inflacao_anual": 0.05,
    "frequencia_aporte": "none",
    "dividend_yield": 0
  }'
```

### Simulação de Investimento em Ações com Dividendos e Aportes Semestrais
```shell
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

## Observações

1. Os valores monetários são retornados sem formatação de moeda, sendo responsabilidade do cliente aplicar a formatação adequada.
2. A taxa de administração é descontada diretamente da taxa de retorno anual para cálculo do retorno efetivo.
3. O imposto é calculado tanto sobre os rendimentos quanto sobre os dividendos, utilizando a mesma alíquota.
4. O ajuste pela inflação considera o efeito acumulado da inflação ao longo de todo o período de investimento.
5. Para aportes não mensais, o valor em `aporte_mensal` é o valor a ser aportado em cada período definido por `frequencia_aporte`.
6. Esta simulação é uma aproximação e não deve ser utilizada como única fonte para decisões financeiras reais. 