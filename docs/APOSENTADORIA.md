# Simulação de Aposentadoria

Esta documentação descreve o endpoint `/simular/aposentadoria` que permite simular a evolução patrimonial ao longo do tempo, tanto na fase de acumulação até a aposentadoria quanto na fase de retirada após a aposentadoria.

## Endpoint

```
POST /simular/aposentadoria
```

## Descrição

Este endpoint calcula a evolução do patrimônio ano a ano, considerando:
1. **Fase de acumulação**: Período em que há aportes mensais até a idade de aposentadoria
2. **Fase de retirada**: Período após a aposentadoria em que há retiradas mensais até o patrimônio acabar (ou até idade limite)

O cálculo leva em consideração o retorno real dos investimentos (descontada a inflação) e retorna uma projeção detalhada da evolução patrimonial.

## Parâmetros

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `idade_atual` | inteiro | Idade atual do investidor |
| `idade_aposentadoria` | inteiro | Idade em que pretende se aposentar |
| `patrimonio_inicial` | decimal | Patrimônio atual em reais |
| `aportes_mensais` | decimal | Valor dos aportes mensais em reais durante a fase de acumulação |
| `retirada_mensal` | decimal | Valor que deseja retirar mensalmente após a aposentadoria |
| `retorno_anual` | decimal | Retorno anual esperado dos investimentos (decimal, ex: 0.08 para 8%) |
| `inflacao_anual` | decimal | Inflação anual esperada (decimal, ex: 0.04 para 4%) |

## Validações

- `idade_atual` deve estar entre 0 e 100 anos
- `idade_aposentadoria` deve ser maior que a idade atual
- `patrimonio_inicial`, `aportes_mensais` e `retirada_mensal` não podem ser negativos
- `retorno_anual` deve estar entre -50% e 100% (-0.5 e 1.0)
- `inflacao_anual` deve estar entre 0% e 50% (0 e 0.5)

## Resposta

A resposta inclui:

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `patrimonio_final` | decimal | Valor final do patrimônio após o último ano da simulação |
| `idade_quando_acaba` | inteiro ou null | Idade em que o dinheiro acabará (null se não acabar) |
| `anos_aposentadoria` | inteiro ou null | Quantos anos a aposentadoria durará (null se o dinheiro não acabar) |
| `evolucao_patrimonial` | array | Lista com a evolução do patrimônio ano a ano |
| `parametros` | objeto | Parâmetros usados na simulação |

### Objeto de Evolução Patrimonial

Cada item do array `evolucao_patrimonial` contém:

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `idade` | inteiro | Idade do investidor naquele ano |
| `patrimonio` | decimal | Valor do patrimônio naquele ano |
| `fase` | string | Se é "acumulacao" (antes da aposentadoria) ou "retirada" (após aposentadoria) |

## Exemplo de Requisição

```json
{
  "idade_atual": 30,
  "idade_aposentadoria": 60,
  "patrimonio_inicial": 100000,
  "aportes_mensais": 2000,
  "retirada_mensal": 8000,
  "retorno_anual": 0.08,
  "inflacao_anual": 0.04
}
```

## Exemplo de Resposta

```json
{
  "anos_aposentadoria": 36,
  "evolucao_patrimonial": [
    {
      "fase": "acumulacao",
      "idade": 30,
      "patrimonio": 100000.0
    },
    {
      "fase": "acumulacao",
      "idade": 31,
      "patrimonio": 148923.08
    },
    // ... outros anos da fase de acumulação ...
    {
      "fase": "acumulacao",
      "idade": 60,
      "patrimonio": 3287651.47
    },
    {
      "fase": "retirada",
      "idade": 61,
      "patrimonio": 3232462.08
    },
    // ... outros anos da fase de retirada ...
    {
      "fase": "retirada",
      "idade": 96,
      "patrimonio": 0.0
    }
  ],
  "idade_quando_acaba": 96,
  "parametros": {
    "aportes_mensais": 2000.0,
    "idade_aposentadoria": 60,
    "idade_atual": 30,
    "inflacao_anual": 4.0,
    "patrimonio_inicial": 100000.0,
    "retorno_anual": 8.0,
    "retorno_real": 3.85,
    "retirada_mensal": 8000.0
  },
  "patrimonio_final": 0.0
}
```

## Erros

| Código HTTP | Descrição |
|-------------|-----------|
| 400 | Erro de validação (parâmetros faltando ou inválidos) |
| 500 | Erro interno do servidor |

### Exemplo de Erro

```json
{
  "error": "Idade de aposentadoria deve ser maior que a idade atual"
}
```

## Observações

- O cálculo considera o retorno real dos investimentos (descontada a inflação), utilizando a fórmula: `retorno_real = (1 + retorno_anual) / (1 + inflacao_anual) - 1`
- A simulação considera aportes mensais durante a fase de acumulação e retiradas mensais durante a fase de aposentadoria
- A simulação continua até o dinheiro acabar ou até a idade de 120 anos (se o dinheiro não acabar)
- Se o patrimônio ultrapassar 1 bilhão de reais, a simulação também será interrompida para evitar problemas de performance 