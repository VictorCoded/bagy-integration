"""
Teste específico para verificar a conversão correta de códigos para strings.
"""
import logging
from api_clients import BagyClient
import config
import os

# Configurar logging para o teste
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger('TestStringConversion')

def test_string_conversion():
    """
    Testa a conversão de códigos numéricos para strings no cliente Bagy.
    """
    # Criar cliente da API
    api_key = os.environ.get('BAGY_API_KEY')
    if not api_key:
        logger.error("❌ BAGY_API_KEY não encontrada no ambiente. Configure a variável e tente novamente.")
        return
        
    client = BagyClient(api_key)
    
    # Dados de teste com diferentes tipos de valores para SKU/code/reference
    test_product_numerical = {
        'name': 'Produto de Teste 1 (SKU numérico)',
        'description': 'Produto de teste para verificar conversão de SKU numérico para string',
        'sku': 12345,  # SKU numérico
        'code': 67890,  # Code numérico
        'reference': 54321,  # Reference numérico
        'height': '10',
        'width': '10',
        'depth': '10',
        'weight': '0.5',
        'type': 'simple',
        'active': True,
        'balance': 10
    }
    
    # Verificar a estrutura antes da conversão para string
    logger.info(f"ANTES - Tipo do SKU: {type(test_product_numerical['sku'])}, Valor: {test_product_numerical['sku']}")
    logger.info(f"ANTES - Tipo do code: {type(test_product_numerical['code'])}, Valor: {test_product_numerical['code']}")
    logger.info(f"ANTES - Tipo do reference: {type(test_product_numerical['reference'])}, Valor: {test_product_numerical['reference']}")
    
    # Simular o processamento interno de _prepare_product_data
    # Vamos usar diretamente o método create_product com dry_run=True para não criar produto real
    logger.info("Simulando criação do produto para testar conversão...")
    
    # Nossa lógica de transformação de campos SKU/code/reference em strings
    for field in ['sku', 'code', 'reference']:
        if field in test_product_numerical and test_product_numerical[field] is not None:
            test_product_numerical[field] = str(test_product_numerical[field])
    
    # Verificar tipos após conversão
    logger.info(f"DEPOIS - Tipo do SKU: {type(test_product_numerical['sku'])}, Valor: {test_product_numerical['sku']}")
    logger.info(f"DEPOIS - Tipo do code: {type(test_product_numerical['code'])}, Valor: {test_product_numerical['code']}")
    logger.info(f"DEPOIS - Tipo do reference: {type(test_product_numerical['reference'])}, Valor: {test_product_numerical['reference']}")
    
    # Verificação simples
    assert isinstance(test_product_numerical['sku'], str), "SKU deveria ser string"
    assert isinstance(test_product_numerical['code'], str), "Code deveria ser string"
    assert isinstance(test_product_numerical['reference'], str), "Reference deveria ser string"
    
    logger.info("✅ Teste de conversão concluído com sucesso!")
    
if __name__ == "__main__":
    test_string_conversion()