# Exemplos de Comandos Curl para Testes

Este documento contém exemplos de comandos curl para testar o endpoint de investimento prefixado.

## Endpoint de Investimento Prefixado

A resposta agora contém dois conjuntos de resultados:
1. **situacao_atual**: Cálculos considerando o período da data inicial até a data atual (hoje)
2. **simulacao_completa**: Cálculos considerando o período completo (até a data final)

### Exemplo Básico (apenas parâmetros obrigatórios)

```bash
curl -X GET "http://localhost:5000/investimento/prefixado?data=2023-01-01&valor=1000&taxa_anual=10.5"
```

### Exemplo com Data Final Específica

```bash
curl -X GET "http://localhost:5000/investimento/prefixado?data=2023-01-01&valor=1000&taxa_anual=10.5&data_final=2024-01-01"
```

### Exemplo com Taxas Administrativas

```bash
curl -X GET "http://localhost:5000/investimento/prefixado?data=2023-01-01&valor=1000&taxa_anual=10.5&taxa_admin=0.5&taxa_custodia=0.3"
```

### Exemplo sem Cálculo de Impostos

```bash
curl -X GET "http://localhost:5000/investimento/prefixado?data=2023-01-01&valor=1000&taxa_anual=10.5&incluir_impostos=false"
```

### Exemplo com Regime de Capitalização Anual

```bash
curl -X GET "http://localhost:5000/investimento/prefixado?data=2023-01-01&valor=1000&taxa_anual=10.5&regime=anual"
```

### Exemplo Completo com Todos os Parâmetros

```bash
curl -X GET "http://localhost:5000/investimento/prefixado?data=2023-01-01&valor=10000&taxa_anual=12.5&data_final=2025-01-01&taxa_admin=0.5&taxa_custodia=0.3&incluir_impostos=true&regime=diario"
```

### Exemplo com Data Passada (somente simulação completa)

```bash
curl -X GET "http://localhost:5000/investimento/prefixado?data=2020-01-01&valor=1000&taxa_anual=10.5&data_final=2022-01-01"
```

### Exemplo com Data Futura (somente simulação completa)

```bash
curl -X GET "http://localhost:5000/investimento/prefixado?data=2025-01-01&valor=1000&taxa_anual=10.5&data_final=2026-01-01"
```

## Exemplos de Erros

### Parâmetro Obrigatório Ausente

```bash
curl -X GET "http://localhost:5000/investimento/prefixado?valor=1000&taxa_anual=10.5"
```

### Formato de Data Inválido

```bash
curl -X GET "http://localhost:5000/investimento/prefixado?data=01/01/2023&valor=1000&taxa_anual=10.5"
```

### Valor Numérico Inválido

```bash
curl -X GET "http://localhost:5000/investimento/prefixado?data=2023-01-01&valor=mil&taxa_anual=10.5"
```

### Regime Inválido

```bash
curl -X GET "http://localhost:5000/investimento/prefixado?data=2023-01-01&valor=1000&taxa_anual=10.5&regime=mensal"
``` 