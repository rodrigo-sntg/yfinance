# Calculadora de Investimentos em Tesouro IPCA+

Este módulo fornece uma calculadora completa para investimentos em títulos do Tesouro IPCA+, considerando a variação do IPCA (Índice Nacional de Preços ao Consumidor Amplo) acumulada no período e a taxa fixa acordada no momento da compra do título.

## Sobre o Tesouro IPCA+

O Tesouro IPCA+ é um título público do Tesouro Direto que paga:
- A variação do IPCA (inflação oficial do Brasil) acumulada durante o período de investimento
- Uma taxa fixa anual definida no momento da compra (por exemplo, IPCA + 5% ao ano)

Este título é uma proteção contra a inflação, garantindo rendimento real acima do IPCA.

## Funcionalidades

A calculadora oferece as seguintes funcionalidades:

1. **Cálculo de Rendimento Real**: Utiliza dados históricos do IPCA para calcular o rendimento exato de um investimento em Tesouro IPCA+ no passado.
2. **Projeção de Investimentos**: Estima o valor futuro de um investimento com base em uma projeção do IPCA.
3. **Cálculo de Impostos e Taxas**: Considera impostos (IR e IOF) e taxas (administração e custódia) para calcular o rendimento líquido.

## Como usar a biblioteca

### Exemplo básico de cálculo de rendimento:

```python
from datetime import datetime
from app.ipca import calcular_rendimento_ipca

resultado = calcular_rendimento_ipca(
    data_inicial=datetime(2023, 1, 1).date(),  # Data de início do investimento
    valor_investido=10000.0,                   # R$ 10.000,00 de investimento inicial
    taxa_fixa_anual=5.0,                       # IPCA + 5% ao ano
    data_final=datetime(2023, 12, 31).date(),  # Data final do investimento
    taxa_admin=0.0,                            # Sem taxa de administração
    taxa_custodia=0.25,                        # Taxa de custódia de 0,25% ao ano
    incluir_impostos=True                      # Incluir cálculo de impostos (IR e IOF)
)

# Resultados
print(f"Valor Inicial: R$ {resultado['valor_investido']:.2f}")
print(f"Valor Final Bruto: R$ {resultado['valor_final_bruto']:.2f}")
print(f"Valor Final Líquido: R$ {resultado['valor_final_liquido']:.2f}")
print(f"Rendimento Percentual: {resultado['rendimento_percentual_bruto']:.2f}%")
```

### Exemplo de projeção futura:

```python
from datetime import datetime
from app.ipca import estimar_valor_futuro_ipca

projecao = estimar_valor_futuro_ipca(
    data_inicial=datetime(2023, 1, 1).date(),  # Data de início do investimento
    valor_investido=10000.0,                   # R$ 10.000,00 de investimento inicial
    taxa_fixa_anual=5.0,                       # IPCA + 5% ao ano
    data_final=datetime(2028, 1, 1).date(),    # Data para projeção (5 anos à frente)
    ipca_estimado_anual=4.5,                   # Estimativa do IPCA: 4,5% ao ano
    taxa_admin=0.0,                            # Sem taxa de administração
    taxa_custodia=0.25,                        # Taxa de custódia de 0,25% ao ano
    incluir_impostos=True                      # Incluir cálculo de impostos
)

# Resultados
print(f"Valor Inicial: R$ {projecao['valor_investido']:.2f}")
print(f"Valor Final Estimado: R$ {projecao['valor_final_liquido']:.2f}")
print(f"Rendimento Estimado: {projecao['rendimento_percentual_liquido']:.2f}%")
```

## Script de Linha de Comando

O módulo inclui um script de linha de comando para simulações rápidas:

```bash
python simular_tesouro_ipca.py --valor_inicial 10000 --taxa_fixa 5.0 --data_inicial 01/01/2023
```

### Opções do script:

```
--valor_inicial VALOR     Valor inicial investido (em reais)
--taxa_fixa TAXA          Taxa fixa anual do título (em %, ex: 5.0 para IPCA+5%)
--data_inicial DATA       Data inicial do investimento (formato DD/MM/AAAA)
--data_final DATA         Data final do investimento (formato DD/MM/AAAA)
--projecao                Usar modo de projeção futura
--ipca_estimado VALOR     IPCA anual estimado para projeção (em %)
--taxa_admin VALOR        Taxa de administração anual (em %)
--taxa_custodia VALOR     Taxa de custódia anual (em %)
--sem_impostos            Não incluir impostos no cálculo (IR e IOF)
```

## Detalhes do Cálculo

### Fórmula do Rendimento

O cálculo do valor final do Tesouro IPCA+ é baseado na seguinte fórmula:

\[ VF = VP \times \left(1 + \text{Taxa Combinada}\right)^{\frac{\text{Dias Úteis}}{252}} \]

Onde:
- \( VF \): Valor futuro (valor final do investimento)
- \( VP \): Valor presente (valor investido)
- \( \text{Taxa Combinada} \): IPCA acumulado mais taxa fixa anual
- \( \text{Dias Úteis} \): Número de dias úteis no período

A taxa combinada é calculada como:

\[ \text{Taxa Combinada} = (1 + \text{IPCA}) \times (1 + \text{Taxa Fixa}) - 1 \]

### Impostos e Taxas

O cálculo considera:

1. **Imposto de Renda (IR)**:
   - 22,5% para aplicações até 180 dias
   - 20,0% para aplicações de 181 a 360 dias
   - 17,5% para aplicações de 361 a 720 dias
   - 15,0% para aplicações acima de 720 dias

2. **IOF** (para resgates antes de 30 dias): 
   - Taxa regressiva conforme tabela estabelecida

3. **Taxa de Custódia**: 0,25% ao ano sobre o valor investido (padrão do Tesouro Direto)

4. **Taxa de Administração**: Conforme definida pela corretora

## Fonte de Dados do IPCA

A calculadora utiliza a API do Banco Central do Brasil para obter:
- IPCA acumulado 12 meses (série 433)
- IPCA mensal (série 188)

Os dados são automaticamente cacheados para otimizar o desempenho e reduzir requisições à API.

## Dependências

- Python 3.6 ou superior
- Biblioteca `requests` para comunicação com a API do IBGE
- Módulo interno `app.investimento` para cálculo de impostos e taxas
- Módulo interno `app.holidays` para identificação de dias úteis

## Observações Importantes

1. O cálculo considera apenas dias úteis para a rentabilidade, seguindo a convenção do mercado brasileiro de 252 dias úteis por ano.

2. Em caso de falha na obtenção dos dados do IPCA, a calculadora usará uma estimativa baseada na meta de inflação (4,5% ao ano).

3. Para simulações de longo prazo, é recomendável utilizar a função de projeção (`estimar_valor_futuro_ipca`) com uma estimativa conservadora do IPCA.

4. Os valores calculados são aproximações e podem diferir ligeiramente dos valores reais devido a arredondamentos e à metodologia de cálculo do Tesouro Nacional. 