# Scripts para Gerenciamento da SELIC Apurada

Esta pasta contém scripts para manter a taxa SELIC apurada atualizada e consistente em seu ambiente local. A SELIC apurada é obtida do Banco Central do Brasil e armazenada em cache para uso eficiente.

## Problema identificado e solução

Foi identificado um problema no sistema onde datas iguais eram consultadas repetidamente no Banco Central, mesmo após terem sido obtidas anteriormente. Isso ocorria porque:

1. O cache não era devidamente verificado para ver se a data já estava presente
2. As chaves eram armazenadas em formatos inconsistentes (tanto objeto datetime quanto string)
3. O cache não estava sendo ordenado por data
4. Haviam duplicatas com a mesma data no cache

Para resolver esses problemas, foram implementados vários scripts e melhorias, incluindo:

- Uso consistente de datas no formato ISO (YYYY-MM-DD) como chaves para comparações
- Ordenação dos registros por data antes de salvar no cache
- Verificação e eliminação de entradas duplicadas
- Melhorias na detecção de feriados e dias não úteis

## Scripts Disponíveis

### Atualizar SELIC Completa

O script `atualizar_selic_completa.py` atualiza a cache da SELIC para o período especificado.

```bash
python atualizar_selic_completa.py --data-inicial 01/01/2023 --data-final 31/12/2023
```

Opções:
- `--data-inicial`: Data inicial para atualização (formato DD/MM/YYYY)
- `--data-final`: Data final para atualização (opcional, padrão: dia anterior)
- `--incluir-nao-uteis`: Se deve incluir dias não úteis (opcional, padrão: True)
- `--mostrar-resumo`: Mostra um resumo da atualização (opcional)
- `--mostrar-detalhes`: Mostra detalhes de cada dia processado (opcional)

### Verificar SELIC Completa

O script `verificar_selic_completa.py` verifica a consistência do cache da SELIC.

```bash
python verificar_selic_completa.py --data-inicial 01/01/2023 --mostrar-problemas
```

Opções:
- `--data-inicial`: Data inicial para verificação (formato DD/MM/YYYY)
- `--data-final`: Data final para verificação (opcional, padrão: dia anterior)
- `--mostrar-problemas`: Mostra detalhes dos problemas encontrados (opcional)
- `--corrigir`: Corrige os problemas encontrados (opcional)
- `--verbose`: Mostra informações detalhadas durante a execução (opcional)

### Ordenar e Remover Duplicatas da SELIC

O script `ordenar_e_deduplicar_selic.py` remove duplicatas e ordena os registros da SELIC por data.

```bash
python ordenar_e_deduplicar_selic.py
```

Opções:
- `--dry-run`: Executa em modo de simulação, sem alterar o cache
- `--estrategia`: Estratégia para selecionar qual registro manter em caso de duplicatas: recente (padrão), maior ou menor
- `--backup`: Cria um backup do cache antes de modificá-lo
- `--mostrar-duplicatas`: Mostra detalhes das duplicatas encontradas

Exemplos de uso:
```bash
# Simulação para verificar duplicatas sem alterar o cache
python ordenar_e_deduplicar_selic.py --dry-run --mostrar-duplicatas

# Ordenar e remover duplicatas, mantendo o maior valor em caso de conflito
python ordenar_e_deduplicar_selic.py --estrategia maior --backup
```

### Visualizar SELIC Cache

O script `visualizar_selic_cache.py` exibe o conteúdo do cache da SELIC de diferentes formas.

```bash
python visualizar_selic_cache.py --formato lista
```

Opções:
- `--formato`: Formato de visualização (lista, tabela, calendario, estatisticas)
- `--data-inicial`: Data inicial para filtrar (formato DD/MM/YYYY)
- `--data-final`: Data final para filtrar (opcional)
- `--tipo`: Filtrar por tipo de dia (util, nao_util, todos)
- `--mostrar-taxas`: Mostra as taxas diárias (opcional, apenas para formato lista)
- `--mes`: Mês para exibir no formato calendário (1-12)
- `--ano`: Ano para exibir no formato calendário (ex: 2023)

## Fluxo de Trabalho Recomendado

1. **Atualizar o cache**:
   ```bash
   python atualizar_selic_completa.py --data-inicial 01/01/2023 --mostrar-resumo
   ```

2. **Ordenar e remover duplicatas**:
   ```bash
   python ordenar_e_deduplicar_selic.py --backup
   ```

3. **Verificar consistência**:
   ```bash
   python verificar_selic_completa.py --data-inicial 01/01/2023 --mostrar-problemas
   ```

4. **Corrigir problemas** (se necessário):
   ```bash
   python verificar_selic_completa.py --data-inicial 01/01/2023 --corrigir
   ```

5. **Visualizar os dados**:
   ```bash
   python visualizar_selic_cache.py --formato estatisticas
   ```

## Observações Importantes

- Os dias não úteis (finais de semana e feriados) são armazenados com taxa zero (0.0)
- Os feriados são identificados a partir de uma API externa ou de um cache local
- O script de ordenação e deduplicação pode ser executado periodicamente para manter o cache organizado
- Python 3.6+ é necessário para executar esses scripts
- Os scripts dependem do módulo `app` da aplicação principal 