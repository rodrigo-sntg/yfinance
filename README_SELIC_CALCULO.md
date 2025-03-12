# Cálculo de Rendimentos SELIC com Impostos e Taxas

Este módulo permite o cálculo preciso de rendimentos em aplicações baseadas na taxa SELIC, considerando impostos (IR e IOF) e taxas administrativas cobradas por instituições financeiras.

## Características Principais

- **Cálculo completo de rendimentos** brutos e líquidos
- **Aplicação automática de alíquotas de IR** conforme o prazo da aplicação
- **Cálculo de IOF regressivo** para resgates em menos de 30 dias
- **Consideração de taxas administrativas** cobradas por instituições financeiras
- **Suporte a diferentes prazos de aplicação**
- **Identificação adequada de dias úteis e não úteis** (finais de semana e feriados)

## Como Usar

### Funções Disponíveis

#### 1. `calcular_rendimento_selic` - Função Principal

```python
resultado = calcular_rendimento_selic(
    valor_inicial=10000.00,        # Valor inicial investido
    start_date=date(2023, 1, 1),   # Data inicial da aplicação
    end_date=date(2023, 12, 31),   # Data final da aplicação
    taxa_admin=0.5,                # Taxa de administração (% ao ano)
    taxa_custodia=0,               # Taxa de custódia (% ao ano)
    taxas_diarias=None             # Opcional: dicionário com taxas diárias pré-carregadas
)
```

#### 2. `calcular_rendimento_bruto` - Apenas Rendimento Bruto

```python
valor_final, fator_composto, dias_totais, dias_uteis = calcular_rendimento_bruto(
    valor_inicial=10000.00,        # Valor inicial investido
    start_date=date(2023, 1, 1),   # Data inicial da aplicação
    end_date=date(2023, 12, 31),   # Data final da aplicação
    taxas_diarias=None             # Opcional: dicionário com taxas diárias pré-carregadas
)
```

#### 3. `calcular_impostos_taxas` - Apenas Impostos e Taxas

```python
resultado = calcular_impostos_taxas(
    valor_investido=10000.00,      # Valor inicial investido
    fator_composto=1.1065,         # Fator de rentabilidade do período
    dias_totais=365,               # Número total de dias da aplicação
    taxa_admin=0.5,                # Taxa de administração (% ao ano)
    taxa_custodia=0,               # Taxa de custódia (% ao ano)
    ioftable=None                  # Opcional: tabela personalizada de IOF
)
```

### Exemplo de Uso

```python
from datetime import date
from app.selic import calcular_rendimento_selic

# Configura os parâmetros
valor_inicial = 10000.00
data_inicial = date(2023, 1, 1)
data_final = date(2023, 12, 31)
taxa_admin = 0.5  # 0.5% ao ano

# Calcula o rendimento
resultado = calcular_rendimento_selic(
    valor_inicial=valor_inicial,
    start_date=data_inicial,
    end_date=data_final,
    taxa_admin=taxa_admin
)

# Exibe os resultados
print(f"Valor inicial: R$ {resultado['valor_investido']:.2f}")
print(f"Valor final bruto: R$ {resultado['valor_final_bruto']:.2f}")
print(f"Valor final líquido: R$ {resultado['valor_final_liquido']:.2f}")
print(f"Rendimento líquido: R$ {resultado['lucro_liquido']:.2f}")
print(f"Imposto de Renda: R$ {resultado['imposto_renda']:.2f}")
print(f"Taxa de administração: R$ {resultado['taxa_admin_valor']:.2f}")
```

## Impostos e Taxas Aplicáveis

### Imposto de Renda (IR)

- **Até 180 dias:** 22,5% sobre o lucro
- **De 181 a 360 dias:** 20% sobre o lucro
- **De 361 a 720 dias:** 17,5% sobre o lucro
- **Acima de 720 dias:** 15% sobre o lucro

### IOF (Imposto sobre Operações Financeiras)

- Aplicável apenas nos primeiros 30 dias
- Redução regressiva de 96% no primeiro dia até 0% no 30º dia
- Incide apenas sobre o rendimento

### Taxas Administrativas

- **Taxa de administração:** Configurável em % ao ano
- **Taxa de custódia:** Configurável em % ao ano

## Estrutura do Resultado

O resultado do cálculo é um dicionário com as seguintes chaves:

```python
{
    "valor_investido": 10000.0,        # Valor inicial investido
    "valor_final_bruto": 11065.4,      # Valor bruto antes de impostos e taxas
    "valor_final_liquido": 10929.15,   # Valor líquido final após todos os descontos
    "lucro_bruto": 1065.4,             # Rendimento bruto
    "lucro_liquido": 929.15,           # Rendimento líquido após descontos
    "imposto_renda": 159.81,           # Valor do IR retido (15% do lucro)
    "taxa_admin_valor": 50.0,          # Valor da taxa de administração
    "taxa_custodia_valor": 0.0,        # Valor da taxa de custódia
    "iof": 0.0,                        # Valor do IOF (se aplicável)
    "aliquota_ir": 15.0,               # Alíquota de IR aplicada (%)
    "dias_totais": 365,                # Total de dias do período
    "dias_uteis": 251,                 # Total de dias úteis do período
    "fator_composto": 1.10654,         # Fator de rentabilidade do período
    "data_inicial": "01/01/2023",      # Data inicial formatada
    "data_final": "31/12/2023",        # Data final formatada
    "taxa_admin_percentual": 0.5,      # Taxa de administração aplicada
    "taxa_custodia_percentual": 0.0    # Taxa de custódia aplicada
}
```

## Exemplo Prático

Para um exemplo detalhado de uso, veja o script `exemplo_calculo_com_taxas.py` que demonstra o cálculo com diferentes taxas de administração e mostra resultados comparativos.

## Observações Importantes

1. O cálculo de rendimento considera apenas dias úteis para a aplicação da taxa SELIC.
2. Finais de semana e feriados são automaticamente identificados e recebem taxa zero.
3. O sistema utiliza o cache de taxas SELIC para evitar consultas desnecessárias à API do Banco Central.
4. Para períodos onde a taxa SELIC não está disponível, o sistema tentará identificar se é um feriado ou considerará como problema de API.

---

Data de atualização: Novembro de 2023 