from datetime import datetime
from app.logger import logger

def parse_date(date_str):
    """
    Converte uma string de data para um objeto datetime.date.
    
    Args:
        date_str (str): String de data no formato YYYY-MM-DD
        
    Returns:
        datetime.date: Objeto de data ou None se o formato for inválido
    """
    try:
        # Verifica se o parâmetro é uma string
        if not isinstance(date_str, str):
            logger.warning(f"Erro ao converter data: valor não é uma string - {date_str}")
            return None
            
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError as e:
        logger.warning(f"Erro ao converter data '{date_str}': {e}")
        return None

def safe_float(value_str):
    """
    Converte uma string para float de forma segura.
    
    Args:
        value_str (str): String para converter
        
    Returns:
        float: Valor convertido ou None se inválido
    """
    try:
        return float(value_str)
    except (ValueError, TypeError) as e:
        logger.warning(f"Erro ao converter para float '{value_str}': {e}")
        return None 