import pandas as pd
from flask import request, jsonify
from app.logger import logger

def simular_aposentadoria(
    idade_atual,
    idade_aposentadoria,
    patrimonio_inicial,
    aportes_mensais,
    retirada_mensal,
    retorno_anual,
    inflacao_anual
):
    """
    Simula a evolução patrimonial até e após a aposentadoria utilizando resolução mensal.
    Todos os cálculos são feitos em termos reais, convertendo o retorno nominal anual e a inflação
    para uma taxa real anual e, em seguida, para taxa real mensal.
    
    Para cada mês são registrados os seguintes dados:
      - Anos: idade do investidor (em anos, com casas decimais)
      - Anos (int): idade inteira
      - PL Inicial: patrimônio líquido no início do mês
      - Aportes: valor aportado no mês (apenas na fase de acumulação)
      - Saques: valor retirado no mês (apenas na fase de aposentadoria)
      - Rendimento: rendimento do mês, calculado sobre o valor após aporte (ou após saque)
      - PL Final: patrimônio no final do mês
      - Zeragem: flag (1 se os recursos se esgotam neste mês, 0 caso contrário)
      - Flx. Caixa: fluxo de caixa do período (Aportes + Rendimento na acumulação ou -Saques + Rendimento na aposentadoria)
      
    Args:
        idade_atual (int): idade atual do investidor (anos)
        idade_aposentadoria (int): idade desejada para aposentadoria (anos)
        patrimonio_inicial (float): patrimônio inicial (em termos reais)
        aportes_mensais (float): valor aportado mensalmente até a aposentadoria (em termos reais)
        retirada_mensal (float): valor desejado de retirada mensal após a aposentadoria (em termos reais)
        retorno_anual (float): retorno nominal anual esperado (ex: 0.14 para 14%)
        inflacao_anual (float): inflação nominal anual esperada (ex: 0.06 para 6%)
        
    Returns:
        dict: contendo:
          - patrimonio_final: patrimônio final após a simulação
          - patrimonio_aposentadoria: patrimônio na entrada da aposentadoria
          - idade_quando_acaba: idade em que os recursos se esgotam (None se não esgotarem)
          - anos_aposentadoria: duração da aposentadoria (em anos) ou None se os recursos não zerarem
          - saque_sustentavel_mensal: valor do saque sustentável mensal calculado com base na taxa real mensal
          - dinheiro_pra_vida_toda: flag indicando se os recursos duram para a vida toda
          - evolucao_patrimonial: lista de dicionários com a evolução mensal detalhada
          - parametros: dicionário com os parâmetros utilizados (convertendo taxas para percentual)
    """
    # Cálculo do retorno real anual e conversão para taxa real mensal
    retorno_real_anual = (1 + retorno_anual) / (1 + inflacao_anual) - 1
    retorno_real_mensal = (1 + retorno_real_anual) ** (1/12) - 1

    historico = []
    pl = patrimonio_inicial

    # Fase de acumulação (antes da aposentadoria)
    meses_acumulacao = int((idade_aposentadoria - idade_atual) * 12)
    for mes in range(meses_acumulacao):
        periodo = {}
        idade_frac = idade_atual + mes / 12.0
        idade_int = int(idade_frac)
        periodo["anos"] = round(idade_frac, 2)
        periodo["anos_int"] = idade_int
        periodo["pl_inicial"] = round(pl, 2)
        periodo["aportes"] = round(aportes_mensais, 2)
        periodo["saques"] = 0.0

        # Após o aporte, calcula o rendimento
        interim = pl + aportes_mensais
        rendimento = interim * retorno_real_mensal
        periodo["rendimento"] = round(rendimento, 2)
        pl_final = interim + rendimento
        periodo["pl_final"] = round(pl_final, 2)
        periodo["zeragem"] = 0
        # Fluxo de caixa: Aportes + Rendimento
        periodo["flx_caixa"] = round(aportes_mensais + rendimento, 2)

        historico.append(periodo)
        pl = pl_final

    patrimonio_aposentadoria = pl  # Valor na entrada da aposentadoria

    # Fase de aposentadoria (retirada mensal)
    mesapos = 0
    idade_quando_acaba = None
    while pl > 0:
        periodo = {}
        idade_frac = idade_aposentadoria + mesapos / 12.0
        idade_int = int(idade_frac)
        periodo["anos"] = round(idade_frac, 2)
        periodo["anos_int"] = idade_int
        periodo["pl_inicial"] = round(pl, 2)
        periodo["aportes"] = 0.0  # Não há aportes na aposentadoria

        if pl >= retirada_mensal:
            saque = retirada_mensal
            periodo["saques"] = round(saque, 2)
            interim = pl - saque
            rendimento = interim * retorno_real_mensal
            periodo["rendimento"] = round(rendimento, 2)
            pl_final = interim + rendimento
            periodo["pl_final"] = round(pl_final, 2)
            periodo["zeragem"] = 0
            # Fluxo de caixa: -Saques + Rendimento
            periodo["flx_caixa"] = round(-saque + rendimento, 2)
            pl = pl_final
        else:
            # Último período: saque parcial, patrimonio se esgota
            saque = pl
            periodo["saques"] = round(saque, 2)
            periodo["rendimento"] = 0.0
            periodo["pl_final"] = 0.0
            periodo["zeragem"] = 1
            periodo["flx_caixa"] = round(-saque, 2)
            pl = 0.0
            idade_quando_acaba = idade_frac

        historico.append(periodo)
        mesapos += 1

        if idade_frac > 120:  # Limite de segurança
            break

    patrimonio_final = pl
    if patrimonio_final == 0 and idade_quando_acaba is not None:
        anos_aposentadoria = idade_quando_acaba - idade_aposentadoria
    else:
        anos_aposentadoria = None

    # Cálculo do saque sustentável mensal
    saque_sustentavel = patrimonio_aposentadoria * retorno_real_mensal if retorno_real_mensal > 0 else 0

    resultado = {
        "patrimonio_final": round(patrimonio_final, 2),
        "patrimonio_aposentadoria": round(patrimonio_aposentadoria, 2),
        "idade_quando_acaba": round(idade_quando_acaba, 2) if idade_quando_acaba is not None else None,
        "anos_aposentadoria": round(anos_aposentadoria, 2) if anos_aposentadoria is not None else None,
        "saque_sustentavel_mensal": round(saque_sustentavel, 2),
        "dinheiro_pra_vida_toda": idade_quando_acaba is None,
        "evolucao_patrimonial": historico,
        "parametros": {
            "idade_atual": idade_atual,
            "idade_aposentadoria": idade_aposentadoria,
            "patrimonio_inicial": patrimonio_inicial,
            "aportes_mensais": aportes_mensais,
            "retirada_mensal": retirada_mensal,
            "retorno_anual": retorno_anual * 100,
            "inflacao_anual": inflacao_anual * 100,
            "retorno_real_anual": retorno_real_anual * 100,
            "retorno_real_mensal": retorno_real_mensal * 100
        }
    }

    return resultado


def register_aposentadoria_routes(app):
    """
    Registra as rotas relacionadas à simulação de aposentadoria.
    
    Args:
        app: Instância do Flask.
    """
    @app.route('/simular/aposentadoria', methods=['POST'])
    def simular_aposentadoria_endpoint():
        """
        Endpoint que recebe os parâmetros da simulação e retorna a evolução patrimonial mensal
        com os dados detalhados conforme a planilha:
          - anos (fração de ano)
          - anos (idade inteira)
          - pl_inicial
          - rendimento
          - aportes
          - saques
          - pl_final
          - zeragem
          - flx_caixa
          
        Parâmetros (JSON):
          - idade_atual: Idade atual do investidor (anos)
          - idade_aposentadoria: Idade desejada para aposentadoria (anos)
          - patrimonio_inicial: Patrimônio inicial (em termos reais)
          - aportes_mensais: Valor dos aportes mensais (em termos reais)
          - retirada_mensal: Valor de retirada mensal após a aposentadoria (em termos reais)
          - retorno_anual: Retorno nominal anual esperado (decimal, ex: 0.08 para 8%)
          - inflacao_anual: Inflação nominal anual esperada (decimal, ex: 0.04 para 4%)
        
        Retorna um JSON com:
          - patrimonio_final
          - patrimonio_aposentadoria
          - idade_quando_acaba
          - anos_aposentadoria
          - saque_sustentavel_mensal
          - dinheiro_pra_vida_toda
          - evolucao_patrimonial (lista detalhada)
          - parametros (usados na simulação)
        """
        try:
            logger.info(f"Recebida requisição para simulação de aposentadoria. "
                        f"IP: {request.remote_addr}, "
                        f"User-Agent: {request.headers.get('User-Agent')}")
            
            dados = request.json

            # Validação dos parâmetros obrigatórios
            parametros_obrigatorios = [
                "idade_atual", "idade_aposentadoria", "patrimonio_inicial",
                "aportes_mensais", "retirada_mensal", "retorno_anual", "inflacao_anual"
            ]
            for param in parametros_obrigatorios:
                if param not in dados:
                    return jsonify({"error": f"Parâmetro '{param}' é obrigatório"}), 400

            # Conversão dos parâmetros para os tipos adequados
            try:
                idade_atual = int(dados["idade_atual"])
                idade_aposentadoria = int(dados["idade_aposentadoria"])
                patrimonio_inicial = float(dados["patrimonio_inicial"])
                aportes_mensais = float(dados["aportes_mensais"])
                retirada_mensal = float(dados["retirada_mensal"])
                retorno_anual = float(dados["retorno_anual"])
                inflacao_anual = float(dados["inflacao_anual"])
            except (ValueError, TypeError):
                return jsonify({"error": "Parâmetros numéricos inválidos"}), 400

            # Validações adicionais
            if idade_atual < 0 or idade_atual > 100:
                return jsonify({"error": "Idade atual deve estar entre 0 e 100 anos"}), 400
            if idade_aposentadoria <= idade_atual:
                return jsonify({"error": "Idade de aposentadoria deve ser maior que a idade atual"}), 400
            if patrimonio_inicial < 0:
                return jsonify({"error": "Patrimônio inicial não pode ser negativo"}), 400
            if aportes_mensais < 0:
                return jsonify({"error": "Aportes mensais não podem ser negativos"}), 400
            if retirada_mensal < 0:
                return jsonify({"error": "Retirada mensal não pode ser negativa"}), 400
            if retorno_anual < -0.5 or retorno_anual > 1:
                return jsonify({"error": "Retorno anual deve estar entre -50% e 100%"}), 400
            if inflacao_anual < 0 or inflacao_anual > 0.5:
                return jsonify({"error": "Inflação anual deve estar entre 0% e 50%"}), 400

            resultado = simular_aposentadoria(
                idade_atual=idade_atual,
                idade_aposentadoria=idade_aposentadoria,
                patrimonio_inicial=patrimonio_inicial,
                aportes_mensais=aportes_mensais,
                retirada_mensal=retirada_mensal,
                retorno_anual=retorno_anual,
                inflacao_anual=inflacao_anual
            )

            logger.info(f"Simulação de aposentadoria concluída com sucesso para usuário {request.remote_addr}")
            return jsonify(resultado)
        except Exception as e:
            logger.error(f"Erro ao processar simulação de aposentadoria: {str(e)}", exc_info=True)
            return jsonify({"error": "Erro ao processar a simulação"}), 500
