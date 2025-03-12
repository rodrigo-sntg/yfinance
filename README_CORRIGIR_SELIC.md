# Script para Correção do Cache de Selic Apurada

Este script foi desenvolvido para corrigir problemas no arquivo de cache da Selic apurada, garantindo duas propriedades importantes:

1. **Unicidade**: Cada data terá apenas uma cotação (eliminando duplicatas)
2. **Ordenação**: Os registros ficarão ordenados em ordem crescente de data

## Funcionalidades

O script realiza as seguintes operações:

- Carrega o cache atual de `selic_apurada_cache.json`
- Identifica e remove duplicatas (múltiplas cotações para a mesma data)
- Ordena todos os registros em ordem crescente de data
- Cria um backup diário do cache antes de aplicar as correções
- Salva o cache corrigido no mesmo arquivo

## Como Usar

### Execução Básica

Para executar o script com as configurações padrão:

```bash
python corrigir_selic_apurada.py
```

### Modo Simulação (Dry Run)

Para verificar as alterações que seriam feitas sem realmente modificar o arquivo:

```bash
python corrigir_selic_apurada.py --dry-run
```

### Escolher Estratégia para Duplicatas

Quando existem múltiplas cotações para a mesma data, o script precisa decidir qual manter. Você pode escolher entre diferentes estratégias:

```bash
# Manter o registro mais recente (padrão)
python corrigir_selic_apurada.py --estrategia recente

# Manter o registro com maior fator diário
python corrigir_selic_apurada.py --estrategia maior_fator

# Manter o registro com menor fator diário (não-zero)
python corrigir_selic_apurada.py --estrategia menor_fator
```

## Saída do Script

Durante a execução, o script mostrará:

- Número total de registros no cache original
- Duplicatas encontradas (com detalhes das primeiras ocorrências)
- Amostra dos registros antes e depois da correção
- Estatísticas da correção (registros originais, inválidos, duplicatas removidas, finais)
- Verificações finais de ordenação e unicidade

## Backup Automático

Antes de modificar o arquivo de cache, o script cria automaticamente um backup diário na pasta `backups/`. Apenas um backup por dia é mantido, e backups com mais de 30 dias são removidos automaticamente.

## Exemplos de Saída

```
Iniciando correção do cache da Selic apurada...
Estratégia para resolver duplicatas: recente
Cache carregado com 1254 registros

Encontradas 12 datas com múltiplas cotações:
- 05/06/2023: 2 ocorrências
- 06/06/2023: 2 ocorrências
...

Estatísticas da correção:
- Registros originais: 1254
- Registros inválidos (sem dataCotacao): 0
- Duplicatas removidas: 12
- Registros finais: 1242

Salvando cache corrigido...
Cache da Selic apurada corrigido e salvo com sucesso!

Verificação de ordenação:
- Registros estão corretamente ordenados por data crescente ✓

Verificação de unicidade:
- Cada data possui exatamente uma cotação ✓

Processo de correção concluído!
```

## Resolução de Problemas

Se o script encontrar erros durante a execução:

1. Verifique se o arquivo de cache existe e é um JSON válido
2. Execute no modo `--dry-run` para verificar as alterações propostas
3. Consulte os backups na pasta `backups/` caso precise restaurar uma versão anterior

Em caso de dúvidas ou problemas persistentes, entre em contato com a equipe de desenvolvimento. 