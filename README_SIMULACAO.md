# API de Simulação de Investimentos

Esta API permite simular investimentos a longo prazo com diferentes taxas de retorno, impostos e inflação.

## Endpoint Disponível

### POST /simulacao

Realiza uma simulação de investimento a longo prazo, considerando aportes mensais, taxas de administração, impostos e inflação.

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
  "detalhes": false
}
```

**Parâmetros:**

- `investimento_inicial` (obrigatório): Valor inicial a ser investido (float)
- `aporte_mensal` (obrigatório): Valor a ser aportado mensalmente (float)
- `anos` (obrigatório): Duração do investimento em anos (int)
- `retorno_anual` (obrigatório): Taxa de retorno anual esperada (float, em decimal - ex: 0.10 para 10%)
- `taxa_administracao` (obrigatório): Taxa de administração anual (float, em decimal - ex: 0.005 para 0.5%)
- `aliquota_imposto` (obrigatório): Alíquota de imposto sobre o rendimento (float, em decimal - ex: 0.15 para 15%)
- `inflacao_anual` (obrigatório): Taxa de inflação anual esperada (float, em decimal - ex: 0.045 para 4.5%)
- `detalhes` (opcional): Se true, retorna o histórico mensal completo (boolean, default: false)

**Exemplo de Resposta (sem detalhes):**

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
      "saldo_bruto": 11079.17,
      "saldo_liquido": 11066.35,
      "retorno_acumulado": 66.35,
      "taxa_de_administracao": 4.17,
      "imposto": 11.88,
      "rendimento_liquido": 63.12
    },
    // ... outros meses
    {
      "mes": 240,
      "valor_investido": 250000.00,
      "rendimento": 9521.96,
      "rendimento_pct": 0.79,
      "saldo_bruto": 1198376.78,
      "saldo_liquido": 1031120.26,
      "retorno_acumulado": 781120.26,
      "taxa_de_administracao": 500.83,
      "imposto": 1428.29,
      "rendimento_liquido": 7592.84
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

### Juros Compostos
Para cada mês, o saldo é atualizado com:
```
rendimento = saldo_atual * retorno_mensal
taxa_adm = saldo_atual * (taxa_administracao / 12)
imposto = rendimento * aliquota_imposto
rendimento_liquido = rendimento - imposto - taxa_adm
saldo_bruto += rendimento + aporte_mensal
saldo_liquido += rendimento_liquido + aporte_mensal
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

## Observações

1. Os valores monetários são retornados sem formatação de moeda, sendo responsabilidade do cliente aplicar a formatação adequada.
2. A taxa de administração é descontada diretamente da taxa de retorno anual para cálculo do retorno efetivo.
3. O imposto é calculado apenas sobre os rendimentos, não sobre o valor total.
4. O ajuste pela inflação considera o efeito acumulado da inflação ao longo de todo o período de investimento.
5. Esta simulação é uma aproximação e não deve ser utilizada como única fonte para decisões financeiras reais. 