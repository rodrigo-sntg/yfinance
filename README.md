# Calculadora de Investimento Selic

Aplicação Flask para cálculo de rendimentos de investimentos baseados na taxa Selic.

## Estrutura do Projeto

O projeto foi organizado de forma modular para facilitar a manutenção e expansão:

```
/
|── app/                    # Pacote principal
|   ├── __init__.py         # Inicialização do Flask
|   ├── config.py           # Configurações globais
|   ├── logger.py           # Configuração de logging
|   ├── cache.py            # Gerenciamento de cache
|   ├── selic.py            # Funcionalidades para taxas Selic
|   ├── holidays.py         # Gerenciamento de feriados
|   ├── utils.py            # Funções utilitárias
|   ├── routes.py           # Rotas da API
|   └── investimento.py     # Cálculos de investimento
|── run.py                  # Script para iniciar a aplicação
|── requirements.txt        # Dependências do projeto
|── README.md               # Documentação
|── README_TESTS.md         # Documentação dos testes
```

## Funcionalidades

- Cálculo de rentabilidade de investimentos baseados na taxa Selic
- Verificação de dias úteis (considerando feriados nacionais)
- Consulta de taxas Selic para datas específicas
- Análise detalhada de investimentos
- Cache eficiente para reduzir chamadas à API do Banco Central

## API Endpoints

- `/selic/apurada` - Retorna a taxa Selic para uma data específica
- `/investimento` - Calcula o rendimento de um investimento
- `/investimento/analise` - Análise detalhada de um investimento
- `/dia-util` - Verifica se uma data é um dia útil
- `/ping` - Endpoint para verificação de saúde da API

## Como Executar

1. Instale as dependências:
```
pip install -r requirements.txt
```

2. Execute a aplicação:
```
python run.py
```

A aplicação estará disponível em http://localhost:5001

## Características Técnicas

- **Cache Inteligente**: Armazena automaticamente informações sobre dias úteis e não úteis
- **Minimização de Requisições**: Identifica proativamente dias não úteis para evitar chamadas desnecessárias à API do BC
- **Detecção de Feriados**: Integração com a Brasil API para obtenção de feriados nacionais
- **Modularização**: Código organizado em módulos de responsabilidade única
- **Logging Detalhado**: Registro de operações para diagnóstico e monitoramento

## Execução de Testes

Para executar os testes:

```
python -m unittest discover -s . -p "test_selic_calculator.py"
```

Para executar com cobertura:

```
python -m coverage run -m unittest discover -s . -p "test_selic_calculator.py"
python -m coverage report -m
```

Consulte o arquivo README_TESTS.md para informações detalhadas sobre os testes. 