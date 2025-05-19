"""
Script para testar a sincronização de um único produto com variações.
Este script cria manualmente um produto completo e o envia para a Bagy.
"""
import os
import json
import logging
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Importar as classes necessárias
from api_clients import BagyClient
from models import ProductConverter

# Configurar logging
logging.basicConfig(level=logging.INFO, 
                    format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Função principal para testar a criação de produto com variações."""
    logger.info("🧪 Iniciando teste de produto com variações")
    
    # Criar cliente da API Bagy
    bagy_api_key = os.getenv("BAGY_API_KEY")
    if not bagy_api_key:
        logger.error("❌ BAGY_API_KEY não encontrada nas variáveis de ambiente")
        return
    
    bagy_client = BagyClient(bagy_api_key)
    product_converter = ProductConverter()
    
    # Criar um produto de teste completo manualmente
    test_product = {
        "id": "123456789",
        "nome": "Produto de Teste com Variações",
        "codigo_interno": "TESTE-VAR-001",
        "codigo_barra": "7899999999999",
        "descricao": "Este é um produto de teste com múltiplas variações para validar a sincronização com a Bagy.",
        "ativo": "1",
        "altura": "10",
        "largura": "10",
        "profundidade": "10",
        "peso": "0.5",
        "valor_custo": "50",
        "valor_venda": "100",
        "estoque": "50",
        "possui_variacao": "1",
        "variacoes": [
            {
                "variacao": {
                    "id": "1001",
                    "nome": "Opção Azul",
                    "codigo": "TESTE-VAR-001-AZUL",
                    "estoque": "10",
                    "valores": [
                        {
                            "valor_venda": "100.00"
                        }
                    ]
                }
            },
            {
                "variacao": {
                    "id": "1002",
                    "nome": "Opção Verde",
                    "codigo": "TESTE-VAR-001-VERDE",
                    "estoque": "15",
                    "valores": [
                        {
                            "valor_venda": "100.00"
                        }
                    ]
                }
            },
            {
                "variacao": {
                    "id": "1003",
                    "nome": "Opção Vermelho",
                    "codigo": "TESTE-VAR-001-VERMELHO",
                    "estoque": "20",
                    "valores": [
                        {
                            "valor_venda": "120.00"
                        }
                    ]
                }
            }
        ]
    }
    
    # Converter o produto para o formato da Bagy
    logger.info(f"🔄 Convertendo produto: {test_product['nome']}")
    bagy_product = product_converter.gestaoclick_to_bagy(test_product)
    
    # Log detalhado do produto convertido
    logger.info(f"📋 Produto convertido:")
    logger.info(f"  - Nome: {bagy_product['name']}")
    logger.info(f"  - Tipo: {bagy_product['type']}")
    logger.info(f"  - SKU: {bagy_product['sku']}")
    logger.info(f"  - Variações: {len(bagy_product['variations'])}")
    logger.info(f"  - Atributos: {json.dumps(bagy_product.get('attributes', []), indent=2)}")
    
    # Log das variações
    for i, variation in enumerate(bagy_product['variations']):
        logger.info(f"  - Variação {i+1}:")
        logger.info(f"    - SKU: {variation['sku']}")
        logger.info(f"    - Preço: {variation['price']}")
        if 'attributes' in variation:
            logger.info(f"    - Atributos: {json.dumps(variation['attributes'], indent=2)}")
    
    # Verificar se o produto já existe pelo external_id
    existing_product = bagy_client.get_product_by_external_id(bagy_product['external_id'])
    if existing_product:
        logger.info(f"🔍 Produto com external_id {bagy_product['external_id']} já existe na Bagy (ID: {existing_product.get('id')})")
        logger.info(f"⚠️ Vamos atualizar o produto existente")
        result = bagy_client.update_product(existing_product['id'], bagy_product)
        logger.info(f"✅ Produto atualizado com sucesso (ID: {result.get('id')})")
    else:
        # Criar o produto na Bagy
        logger.info(f"🔍 Produto com external_id {bagy_product['external_id']} não existe na Bagy")
        logger.info(f"🔄 Criando novo produto na Bagy")
        result = bagy_client.create_product(bagy_product)
        if result and 'id' in result:
            logger.info(f"✅ Produto criado com sucesso (ID: {result['id']})")
            logger.info(f"📊 Variações criadas: {result.get('variations_count', 0)}")
        else:
            logger.error(f"❌ Erro ao criar produto: {result}")
    
    logger.info("✨ Teste concluído")

if __name__ == "__main__":
    main()