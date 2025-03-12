# Documentação de Testes

Este documento descreve os testes implementados para a aplicação de cálculo de investimentos baseados na taxa Selic.

## Estrutura de Testes

Os testes foram organizados em duas categorias principais:

```
tests/
├── unit/             # Testes unitários
│   ├── test_cache.py            # Testes para funções de cache
│   ├── test_holidays.py         # Testes para funções de feriados
│   ├── test_investimento.py     # Testes para funções de cálculo de investimento
│   ├── test_selic.py            # Testes para funções de taxas Selic
│   └── test_utils.py            # Testes para funções utilitárias
└── integration/      # Testes de integração
    └── test_routes.py           # Testes para endpoints da API
```

## Testes Unitários

Os testes unitários verificam o funcionamento isolado de funções e métodos específicos:

### 1. Funções de Cache (`test_cache.py`)
- Testes para `load_cache()` e `save_cache()`: verifica a leitura e escrita correta dos arquivos de cache para taxas Selic.
- Testes para `load_holidays_cache()` e `save_holidays_cache()`: verifica a leitura e escrita dos arquivos de cache de feriados.
- Teste para `get_cached_rates()`: verifica a correta extração de taxas diárias do cache.

### 2. Funções de Feriados (`test_holidays.py`)
- Testes para `fetch_holidays_for_year()`: verifica a obtenção de feriados da API Brasil.
- Testes para `get_holidays_for_year()`: verifica a obtenção de feriados do cache ou API.
- Testes para `is_business_day()`: verifica a correta identificação de dias úteis e não úteis.
- Teste para `preload_holidays_for_period()`: verifica o pré-carregamento de feriados para um período.

### 3. Funções de Taxas Selic (`test_selic.py`)
- Testes para `fetch_selic_for_date()`: verifica a obtenção de taxas Selic da API do Banco Central.
- Testes para `ensure_non_business_day_in_cache()`: verifica a correta adição de dias não úteis ao cache.
- Testes para `ensure_rates_in_cache()`: verifica que todas as taxas necessárias para um período estão no cache.

### 4. Funções de Investimento (`test_investimento.py`)
- Testes para `calcular_rendimento()`: verifica o cálculo de rendimento para períodos com diferentes características.
- Testes para `analisar_investimento()`: verifica a análise detalhada de investimentos com estatísticas.

### 5. Funções Utilitárias (`test_utils.py`)
- Testes para `parse_date()`: verifica a conversão de strings para objetos de data.
- Testes para `safe_float()`: verifica a conversão segura de strings para números de ponto flutuante.

## Testes de Integração

Os testes de integração (`test_routes.py`) verificam o funcionamento dos endpoints da API:

1. **Endpoint `/ping`**: Verifica se o serviço está em execução.
2. **Endpoint `/selic/apurada`**: Verifica consulta de taxas Selic para dias úteis, finais de semana e feriados.
3. **Endpoint `/investimento`**: Verifica cálculo de rendimentos de investimentos.
4. **Endpoint `/investimento/analise`**: Verifica análise detalhada de investimentos.
5. **Endpoint `/dia-util`**: Verifica identificação de dias úteis e não úteis.

## Uso de Mocks

Os testes utilizam mocks extensivamente para simular:

- Respostas da API do Banco Central
- Respostas da Brasil API para feriados
- Operações de E/S (leitura/escrita de arquivos)
- Comportamento de funções dependentes

Este uso de mocks permite testar componentes isoladamente, sem depender de serviços externos ou estado do sistema.

## Como Executar os Testes

Para sua conveniência, disponibilizamos um script `run_tests.py` que facilita a execução dos testes:

### Executar Apenas Testes Unitários
```
python run_tests.py unit
```

### Executar Apenas Testes de Integração
```
python run_tests.py integration
```

### Executar Todos os Testes com Relatório de Cobertura
```
python run_tests.py all
```
ou simplesmente:
```
python run_tests.py
```

Ao executar os testes com cobertura, será gerado um relatório HTML na pasta `coverage_html/`.

## Considerações Importantes

1. **Independência de Testes**: Cada teste é independente e não depende do estado deixado por outros testes.
2. **Testes de Borda**: Cobrimos casos limites como entradas inválidas, erros de API e cache corrompido.
3. **Cobertura de Código**: Buscamos alta cobertura para garantir que todos os caminhos do código sejam testados.

## Melhorias Futuras

- Implementar testes de desempenho para verificar o comportamento com grandes volumes de dados.
- Adicionar testes para casos de uso completos (end-to-end).
- Automatizar os testes através de integração contínua (CI). 