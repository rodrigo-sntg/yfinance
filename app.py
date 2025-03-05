from flask import Flask, request, jsonify
import yfinance as yf
from flask_cors import CORS
import logging
import os
from datetime import datetime

# Inicializa a aplicação Flask
app = Flask(__name__)
CORS(app, resources={r"/stock/*": {"origins": "http://localhost:4200"}})

# Configuração do logging
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)  # Cria a pasta logs se não existir
log_file = os.path.join(log_dir, f'stock_service_{datetime.now().strftime("%Y%m%d")}.log')

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define o endpoint para obter o preço da ação
@app.route('/stock/<symbol>', methods=['GET'])
def get_stock_price(symbol):
    try:
        logger.info(f"Recebida requisição para o símbolo: {symbol}")
        # Cria um objeto Ticker com o símbolo fornecido
        stock = yf.Ticker(symbol)
        # Obtém o histórico do último dia
        data = stock.history(period="1d")
        # Verifica se os dados estão vazios (ação não encontrada)
        if data.empty:
            logger.warning(f"Símbolo {symbol} não encontrado")
            return jsonify({"error": "Stock not found"}), 404
        # Pega o preço de fechamento mais recente
        price = data['Close'].iloc[-1]
        logger.info(f"Preço obtido para {symbol}: {price}")
        # Retorna os dados em formato JSON
        return jsonify({"symbol": symbol, "price": price})
    except Exception as e:
        logger.error(f"Erro ao processar requisição para {symbol}: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Executa o servidor
if __name__ == '__main__':
    logger.info("Iniciando o servidor Flask na porta 5000")
    app.run(host='0.0.0.0', port=5000)