# Documentação do Endpoint de Investimento Prefixado

## Visão Geral

O endpoint `/investimento/prefixado` permite calcular o rendimento de investimentos com taxas prefixadas, como CDBs, LCIs, Tesouro Direto Prefixado, e outros títulos com taxas definidas no momento da aplicação.

## Parâmetros

### Parâmetros Obrigatórios

| Parâmetro | Tipo | Descrição |
|-----------|------|------------|
| `data` | string | Data de início do investimento (formato YYYY-MM-DD) |
| `valor` | decimal | Valor inicial investido (ex: 1000.50) |
| `taxa_anual` | decimal | Taxa de juros anual em percentual (ex: 10.5 para 10,5% ao ano) |

### Parâmetros Opcionais

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|------------|
| `data_final` | string | Não | Data final do investimento (padrão: dia anterior à data atual) |
| `taxa_admin` | decimal | Não | Taxa de administração anual em percentual (padrão: 0) |
| `taxa_custodia` | decimal | Não | Taxa de custódia anual em percentual (padrão: 0) |
| `incluir_impostos` | boolean | Não | Se deve incluir cálculo de IR e IOF (padrão: true) |
| `regime` | string | Não | Regime de capitalização: 'diario' ou 'anual' (padrão: 'diario') |

## Lógica de Cálculo

### Regime Diário (padrão)

No regime de capitalização diária, o cálculo considera os dias úteis entre a data inicial e a data final:

1. A taxa anual é convertida para uma taxa diária equivalente usando a fórmula: `taxa_diária = exp(log(1 + taxa_anual) / 252) - 1`
2. A taxa é aplicada apenas nos dias úteis: `valor_bruto = valor_investido * (1 + taxa_diária) ^ dias_úteis`

### Regime Anual

No regime de capitalização anual, o cálculo considera o período total em anos:

1. O número de dias é convertido para anos: `anos = dias_totais / 365`
2. A taxa é aplicada de forma anual: `valor_bruto = valor_investido * (1 + taxa_anual) ^ anos`

### Cálculo de Impostos

#### Imposto de Renda (IR)

O IR é calculado sobre o rendimento com alíquotas regressivas:

| Prazo | Alíquota |
|-------|----------|
| Até 180 dias | 22,5% |
| De 181 a 360 dias | 20% |
| De 361 a 720 dias | 17,5% |
| Acima de 720 dias | 15% |

#### Imposto sobre Operações Financeiras (IOF)

O IOF é aplicado apenas para resgates em até 30 dias, com alíquota regressiva:

- É calculado como: `(30 - dias) / 30 * 96% + 4%`
- Para 1 dia: 100% do rendimento
- Para 30 dias: 4% do rendimento
- Acima de 30 dias: não há cobrança

## Estrutura de Resposta

A resposta é um objeto JSON que contém dois conjuntos de resultados:

1. **situacao_atual**: Contém os cálculos considerando o período da data inicial até a data atual (hoje)
2. **simulacao_completa**: Contém os cálculos considerando o período completo (da data inicial até a data final informada)

> Nota: O campo **situacao_atual** só estará presente se a data atual estiver entre a data inicial e a data final. Caso contrário, apenas o campo **simulacao_completa** será retornado.

Cada conjunto de resultados contém os seguintes campos:

| Campo | Tipo | Descrição |
|-------|------|------------|
| `valor_investido` | decimal | Valor inicial investido |
| `data_inicial` | string | Data de início do investimento (formato ISO) |
| `data_final` | string | Data final do investimento (formato ISO) |
| `dias_totais` | integer | Número total de dias do período |
| `dias_uteis` | integer | Número de dias úteis no período |
| `taxa_anual` | decimal | Taxa anual em percentual |
| `regime_capitalizacao` | string | Regime de capitalização utilizado ('diario' ou 'anual') |
| `rendimento_bruto` | decimal | Rendimento bruto (sem descontar impostos e taxas) |
| `valor_final_bruto` | decimal | Valor final bruto (sem descontar impostos e taxas) |
| `taxa_administracao` | decimal | Taxa de administração anual em percentual |
| `valor_taxa_administracao` | decimal | Valor cobrado de taxa de administração |
| `taxa_custodia` | decimal | Taxa de custódia anual em percentual |
| `valor_taxa_custodia` | decimal | Valor cobrado de taxa de custódia |
| `total_taxas` | decimal | Total de taxas cobradas |
| `aliquota_ir` | decimal | Alíquota de IR aplicada (percentual) |
| `imposto_renda` | decimal | Valor de IR cobrado |
| `aliquota_iof` | decimal | Alíquota de IOF aplicada (percentual, se aplicável) |
| `imposto_iof` | decimal | Valor de IOF cobrado (se aplicável) |
| `total_impostos` | decimal | Total de impostos cobrados |
| `valor_final_liquido` | decimal | Valor final líquido (após descontar impostos e taxas) |
| `rendimento_liquido` | decimal | Rendimento líquido (após descontar impostos e taxas) |
| `rendimento_liquido_percentual` | decimal | Rendimento líquido em percentual |

### Campo Resumo

Cada conjunto de resultados também inclui o campo `resumo` que contém um objeto com valores arredondados para facilitar o consumo por frontends:

```
{
  "resumo": {
    "valor_final_bruto": 1249.90,
    "valor_final_liquido": 1212.42,
    "rendimento_liquido": 212.42,
    "impostos_totais": 37.49,
    "taxas_totais": 0.0,
    "rendimento_percentual": 21.24
  }
}
```

## Exemplos de Uso

### Exemplo básico
curl -X GET "http://localhost:5000/investimento/prefixado?data=2023-01-01&valor=1000&taxa_anual=10.5"

### Exemplo com taxas administrativas
curl -X GET "http://localhost:5000/investimento/prefixado?data=2023-01-01&valor=1000&taxa_anual=10.5&taxa_admin=0.5&taxa_custodia=0.3"

### Exemplo sem cálculo de impostos
curl -X GET "http://localhost:5000/investimento/prefixado?data=2023-01-01&valor=1000&taxa_anual=10.5&incluir_impostos=false"

### Exemplo completo com todos os parâmetros
curl -X GET "http://localhost:5000/investimento/prefixado?data=2023-01-01&valor=10000&taxa_anual=12.5&data_final=2025-01-01&taxa_admin=0.5&taxa_custodia=0.3&incluir_impostos=true&regime=diario"

## Exemplo de Resposta Completa

```json
{
  "situacao_atual": {
    "aliquota_iof": 0,
    "aliquota_ir": 17.5,
    "data_final": "2024-03-15",
    "data_inicial": "2023-01-01",
    "dias_totais": 439,
    "dias_uteis": 304,
    "imposto_iof": 0.0,
    "imposto_renda": 18.74,
    "regime_capitalizacao": "diario",
    "rendimento_bruto": 107.14,
    "rendimento_liquido": 88.4,
    "rendimento_liquido_percentual": 8.84,
    "resumo": {
      "impostos_totais": 18.74,
      "rendimento_liquido": 88.4,
      "rendimento_percentual": 8.84,
      "taxas_totais": 0.0,
      "valor_final_bruto": 1107.14,
      "valor_final_liquido": 1088.4
    },
    "taxa_administracao": 0.0,
    "taxa_anual": 10.5,
    "taxa_custodia": 0.0,
    "total_impostos": 18.74,
    "total_taxas": 0.0,
    "valor_final_bruto": 1107.14,
    "valor_final_liquido": 1088.4,
    "valor_investido": 1000.0,
    "valor_taxa_administracao": 0.0,
    "valor_taxa_custodia": 0.0
  },
  "simulacao_completa": {
    "aliquota_iof": 0,
    "aliquota_ir": 15.0,
    "data_final": "2025-03-14",
    "data_inicial": "2023-01-01",
    "dias_totais": 803,
    "dias_uteis": 563,
    "imposto_iof": 0.0,
    "imposto_renda": 37.49,
    "regime_capitalizacao": "diario",
    "rendimento_bruto": 249.9,
    "rendimento_liquido": 212.41,
    "rendimento_liquido_percentual": 21.24,
    "resumo": {
      "impostos_totais": 37.49,
      "rendimento_liquido": 212.42,
      "rendimento_percentual": 21.24,
      "taxas_totais": 0.0,
      "valor_final_bruto": 1249.9,
      "valor_final_liquido": 1212.42
    },
    "taxa_administracao": 0.0,
    "taxa_anual": 10.5,
    "taxa_custodia": 0.0,
    "total_impostos": 37.49,
    "total_taxas": 0.0,
    "valor_final_bruto": 1249.9,
    "valor_final_liquido": 1212.41,
    "valor_investido": 1000.0,
    "valor_taxa_administracao": 0.0,
    "valor_taxa_custodia": 0.0
  }
}
```

## Tratamento de Erros

O endpoint retorna erros HTTP 400 em caso de parâmetros inválidos:

| Código | Tipo de Erro | Descrição |
|--------|-------------|-----------|
| 400 | Parâmetros obrigatórios ausentes | Quando `data`, `valor` ou `taxa_anual` não são fornecidos |
| 400 | Formato de data inválido | Quando a data não está no formato YYYY-MM-DD |
| 400 | Valor numérico inválido | Quando um valor numérico não pode ser convertido |
| 400 | Período inválido | Quando a data inicial é posterior à data final |
| 400 | Regime inválido | Quando o regime não é 'diario' ou 'anual' |
| 500 | Erro interno | Quando ocorre um erro não esperado no servidor |

Exemplo de resposta de erro:

```json
{
  "error": "O parâmetro 'data' é obrigatório."
}
```
