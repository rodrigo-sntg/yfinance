# Atualização da Selic Apurada

Documentação dos scripts para atualização automática do cache de dados da Selic Apurada do Banco Central do Brasil.

## Visão Geral

Este conjunto de scripts foi desenvolvido para manter um cache local dos dados da Selic Apurada, obtidos diretamente da API do Banco Central do Brasil. O sistema garante que não haja duplicidade de dados e inclui informações sobre dias não úteis (finais de semana e feriados).

## Arquivos incluídos

- `atualizar_selic_apurada.py`: Script principal com a lógica de atualização do cache
- `atualizar_selic_cron.py`: Script para execução automatizada via crontab, com suporte a logs
- `testar_atualizacao.py`: Script para testar a consulta à API do BCB
- `testar_ultima_data_valida.py`: Script para testar a identificação da última data válida
- `selic_apurada_cache.json`: Arquivo de cache com os dados da Selic Apurada

## Requisitos

- Python 3.6 ou superior
- Biblioteca requests (`pip install requests`)

## Como funciona

### Arquivo de Cache (`selic_apurada_cache.json`)

O arquivo de cache contém registros de dados da Selic Apurada em formato JSON. Cada registro possui:

- `dataCotacao`: Data no formato DD/MM/YYYY
- `fatorDiario`: Fator diário da Selic
- `taxaAnual`: Taxa anual da Selic
- `isBusinessDay`: Indica se é um dia útil (true) ou não (false)
- Outros campos com informações adicionais (média, mediana, desvio padrão, etc.)

Para dias não úteis (finais de semana e feriados), o campo `fatorDiario` é "0" e há um campo `reason` explicando o motivo.

### Script Principal (`atualizar_selic_apurada.py`)

Este script verifica qual a última data válida no cache (com dados reais) e busca dados novos a partir do dia seguinte até a data de ontem (data de corte). Principais características:

1. Identificação inteligente da última data com dados válidos
2. Consulta otimizada à API do BCB, com divisão em períodos de até 365 dias
3. Tratamento automático de dias não úteis (finais de semana)
4. Identificação de possíveis feriados (dias úteis sem dados)
5. Ordenação dos registros por data
6. Tratamento de erros e reconexão em caso de falhas

### Script para Crontab (`atualizar_selic_cron.py`)

Este script é ideal para ser configurado em um agendador como o crontab, pois:

1. Registra logs detalhados em arquivo e console
2. Captura e registra exceções
3. Mede o tempo de execução
4. Retorna código de saída apropriado (0 para sucesso, 1 para falha)

### Script de Teste de Última Data Válida (`testar_ultima_data_valida.py`)

Este script ajuda a verificar a lógica de identificação da última data válida:

1. Exibe a última data válida identificada no cache
2. Analisa os últimos 20 registros do cache
3. Mostra detalhes sobre cada registro, incluindo sua validade
4. Indica a data a partir da qual a próxima atualização buscará dados

## Como usar

### Atualização manual

Para atualizar manualmente o cache:

```bash
python atualizar_selic_apurada.py
```

### Configuração do crontab

Para configurar a atualização automática diária, adicione a seguinte linha ao seu crontab:

```bash
# Atualiza a Selic Apurada todos os dias às 22h
0 22 * * * /caminho/para/python /caminho/para/atualizar_selic_cron.py >> /caminho/para/selic_atualizacao.log 2>&1
```

Para editar seu crontab:

```bash
crontab -e
```

### Testes

Para testar a consulta à API:

```bash
python testar_atualizacao.py
```

Para testar a identificação da última data válida:

```bash
python testar_ultima_data_valida.py
```

## Detalhes técnicos

### API do BCB

O script utiliza o endpoint REST do Banco Central do Brasil:

```
https://www3.bcb.gov.br/novoselic/rest/taxaSelicApurada/pub/search
```

A consulta é feita via POST com parâmetros para o período desejado.

### Identificação de Dados Válidos

O script considera um registro válido quando:

1. Para dias úteis: tem `fatorDiario` e `taxaAnual` válidos e maiores que zero
2. Dias não úteis (fins de semana e feriados) são ignorados na busca por dados válidos

Isso permite que o script identifique corretamente o ponto a partir do qual deve buscar novos dados, mesmo quando o cache contém registros parciais ou com problemas.

### Tratamento de erros

O script principal inclui:

1. Tentativas múltiplas em caso de falha na API
2. Tempos de espera entre tentativas (backoff)
3. Divisão de períodos longos em chunks menores
4. Verificação de conteúdo válido nas respostas

## Recomendações

1. Configure o crontab para executar diariamente, preferencialmente fora do horário comercial
2. Monitore o arquivo de log periodicamente
3. Faça backup do arquivo de cache regularmente
4. Execute o script `testar_ultima_data_valida.py` periodicamente para verificar a integridade dos dados

## Limitações conhecidas

1. A API do BCB pode ter limitações de taxa de requisições (rate limiting)
2. Períodos muito extensos podem sobrecarregar a API
3. O script não identifica automaticamente feriados específicos (apenas marca dias úteis sem dados) 