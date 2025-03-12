# API de Taxa SELIC Diária

Este módulo implementa uma API e sistema de cache para consulta da taxa SELIC diária, utilizando dados oficiais do Banco Central do Brasil.

## Endpoints Disponíveis

### GET /selic/diaria

Retorna a taxa SELIC para uma data específica.

**Parâmetros:**
- `data` (obrigatório): Data no formato `YYYY-MM-DD`

**Exemplo de Requisição:**
```shell
curl "http://localhost:5001/selic/diaria?data=2022-05-10"
```

**Exemplo de Resposta:**
```json
{
  "data": "2022-05-10",
  "data_formatada": "10/05/2022",
  "valor": "12.75",
  "valor_decimal": 12.75,
  "sucesso": true
}
```

**Códigos de Retorno:**
- `200 OK`: Taxa encontrada com sucesso
- `400 Bad Request`: Formato de data inválido ou parâmetro data não fornecido
- `404 Not Found`: Taxa não encontrada para a data solicitada
- `500 Internal Server Error`: Erro interno no servidor

## Sistema de Cache

A API utiliza um sistema de cache local para minimizar as consultas à API do Banco Central. Os dados são armazenados no arquivo `selic_diaria_cache.json` no diretório raiz da aplicação.

O cache é atualizado automaticamente quando uma data é solicitada e não está presente no cache local.

## Scripts Utilitários

### popular_selic_diaria.py

Este script permite a pré-população do cache com dados históricos desde 2000, otimizando o desempenho da API em requisições futuras.

**Uso:**
```
python scripts/popular_selic_diaria.py [--ano_inicio YYYY] [--ano_fim YYYY] [--verbose]
```

**Opções:**
- `--ano_inicio YYYY`: Ano inicial para buscar dados (padrão: 2000)
- `--ano_fim YYYY`: Ano final para buscar dados (padrão: ano atual)
- `--verbose`: Exibe logs mais detalhados durante a execução

**Exemplos:**
```shell
# Popula todo o período desde 2000 até o ano atual
python scripts/popular_selic_diaria.py

# Popula apenas dados de 2010 a 2015
python scripts/popular_selic_diaria.py --ano_inicio 2010 --ano_fim 2015

# Popula desde 2018 até o ano atual com logs detalhados
python scripts/popular_selic_diaria.py --ano_inicio 2018 --verbose
```

## Detalhes da Implementação

### API do Banco Central

A API utiliza o seguinte endpoint do Banco Central do Brasil:
```
https://www.bcb.gov.br/api/servico/sitebcb/bcdatasgs?tronco=estatisticas&guidLista=323626f4-c92f-46d6-bac7-55bf88f6430b&dataInicial=01/03/2025&dataFinal=12/03/2025&serie=432
```

Parâmetros:
- `tronco`: estatisticas (fixo)
- `guidLista`: 323626f4-c92f-46d6-bac7-55bf88f6430b (identificador da série de taxas SELIC)
- `dataInicial`: Data inicial no formato DD/MM/YYYY
- `dataFinal`: Data final no formato DD/MM/YYYY
- `serie`: 432 (código da série de taxas SELIC)

### Formato do Cache

O cache é armazenado no seguinte formato:
```json
{
  "conteudo": [
    {
      "data": "01/03/2022",
      "valor": "11.65"
    },
    {
      "data": "02/03/2022",
      "valor": "11.65"
    },
    ...
  ]
}
```

## Estrutura de Arquivos

- `app/selic_diaria.py`: Implementação principal do módulo
- `app/routes.py`: Contém o endpoint da API
- `scripts/popular_selic_diaria.py`: Script para popular o cache

## Diferenças para a API de SELIC Apurada

Essa API é complementar à API de SELIC Apurada existente. Diferenças principais:

1. **Formato de Dados**: A API de SELIC Diária retorna a taxa nominal anual em vez do fator diário
2. **Fonte de Dados**: Utiliza um endpoint diferente do BCB, com séries temporais oficiais
3. **Formato de Cache**: Estrutura mais simples, focada apenas na taxa do dia
4. **Disponibilidade**: Pode fornecer dados para um período mais longo (desde 2000)

## Recomendações de Uso

1. Execute o script `popular_selic_diaria.py` para pré-carregar o cache com dados históricos
2. Para consultas rotineiras, utilize o endpoint `/selic/diaria`
3. O cache será atualizado automaticamente para novas datas quando forem solicitadas 