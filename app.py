from flask import Flask, request, jsonify
import yfinance as yf
from flask_cors import CORS

# Inicializa a aplicação Flask
app = Flask(__name__)
CORS(app, resources={r"/stock/*": {"origins": "http://localhost:4200"}})

# Define o endpoint para obter o preço da ação
@app.route('/stock/<symbol>', methods=['GET'])
def get_stock_price(symbol):
    try:
        # Cria um objeto Ticker com o símbolo fornecido
        stock = yf.Ticker(symbol)
        # Obtém o histórico do último dia
        data = stock.history(period="1d")
        # Verifica se os dados estão vazios (ação não encontrada)
        if data.empty:
            return jsonify({"error": "Stock not found"}), 404
        # Pega o preço de fechamento mais recente
        price = data['Close'].iloc[-1]
        # Retorna os dados em formato JSON
        return jsonify({"symbol": symbol, "price": price})
    except Exception as e:
        # Retorna erro em caso de falha
        return jsonify({"error": str(e)}), 500

# Executa o servidor
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)