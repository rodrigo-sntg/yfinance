# Exemplos de Comandos curl para Testar o Endpoint de Investimento

## Comando Básico (Sem Taxas e Impostos)

```bash
curl "http://localhost:5001/investimento?data=2023-01-01&valor=1000"
```

## Com Taxa de Administração

```bash
curl "http://localhost:5001/investimento?data=2023-01-01&valor=1000&taxa_admin=0.5"
```

## Sem Cálculo de Impostos

```bash
curl "http://localhost:5001/investimento?data=2023-01-01&valor=1000&incluir_impostos=false"
```

## Com Data Final Específica

```bash
curl "http://localhost:5001/investimento?data=2023-01-01&valor=1000&data_final=2023-12-31&taxa_admin=0.5"
```

## Teste Completo com Todos os Parâmetros

```bash
curl "http://localhost:5001/investimento?data=2023-01-01&valor=1000&data_final=2023-12-31&taxa_admin=0.5&taxa_custodia=0.1&incluir_impostos=true"
```

## Testes para Diferentes Alíquotas de IR

### IR de 22,5% (até 180 dias)

```bash
curl "http://localhost:5001/investimento?data=2023-01-01&valor=1000&data_final=2023-06-30&taxa_admin=0.5"
```

### IR de 20% (181 a 360 dias)

```bash
curl "http://localhost:5001/investimento?data=2023-01-01&valor=1000&data_final=2023-12-31&taxa_admin=0.5"
```

### IR de 17,5% (361 a 720 dias)

```bash
curl "http://localhost:5001/investimento?data=2022-01-01&valor=1000&data_final=2023-06-30&taxa_admin=0.5"
```

### IR de 15% (acima de 720 dias)

```bash
curl "http://localhost:5001/investimento?data=2021-01-01&valor=1000&data_final=2023-01-01&taxa_admin=0.5"
```

## Teste com IOF (menos de 30 dias)

```bash
curl "http://localhost:5001/investimento?data=2023-01-01&valor=1000&data_final=2023-01-25&taxa_admin=0.5"
```

## Endpoint da API

```bash
curl "http://localhost:5001/api/investimento?data=2023-01-01&valor=1000&data_final=2023-12-31&taxa_admin=0.5&taxa_custodia=0.1&incluir_impostos=true"
```

**Observação**: Ajuste o host (localhost:5001) conforme necessário para o seu ambiente. 