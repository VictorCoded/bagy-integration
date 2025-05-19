#!/usr/bin/env python
"""
Script para testar a nova lógica de criação de variações.
"""
import os
import json
import logging
from dotenv import load_dotenv
from api_clients import BagyClient
from config import setup_logging

# Carregar variáveis de ambiente e configurar logging
load_dotenv()
setup_logging()
logger = logging.getLogger("TestVariationLogic")

# Obter API key do ambiente
BAGY_API_KEY = os.getenv("BAGY_API_KEY")

def test_create_product_with_variations():
    """
    Testa a criação de um produto com variações utilizando a nova abordagem.
    """
    logger.info("🧪 Iniciando teste de criação de produto com variações")
    
    # Inicializar o cliente da API
    client = BagyClient(BAGY_API_KEY)
    
    # Criar payload de teste para um produto com variações (tipo 'variant')
    product_data = {
        "name": "Produto de Teste com Variações",
        "description": "<p>Este é um produto de teste com variações para validar nossa nova abordagem.</p>",
        "short_description": "Produto de teste",
        "sku": "TEST-VAR-001",
        "external_id": "test-var-001",
        "price": 99.99,
        "weight": "0.5",
        "height": "10",
        "width": "10",
        "depth": "10",
        "active": True,
        "type": "variant",  # Importante: marcar como produto com variações
        "attributes": [
            {
                "name": "Cor",
                "type": "options",
                "options": [],
                "default": None
            }
        ],
        "variations": [
            {
                "sku": "TEST-VAR-AZUL",
                "external_id": "test-var-azul",
                "price": 99.99,
                "active": True,
                "balance": 10,
                "attributes": [
                    {
                        "name": "Cor",
                        "value": "Azul"
                    }
                ]
            },
            {
                "sku": "TEST-VAR-VERDE",
                "external_id": "test-var-verde",
                "price": 99.99,
                "active": True,
                "balance": 5,
                "attributes": [
                    {
                        "name": "Cor",
                        "value": "Verde"
                    }
                ]
            }
        ]
    }
    
    # Tentar criar o produto
    logger.info("🧪 Criando produto de teste com variações")
    response = client.create_product(product_data)
    
    # Verificar resultado
    if response and "id" in response:
        logger.info(f"✅ Produto criado com sucesso! ID: {response['id']}")
        logger.info(f"Detalhes da resposta: {json.dumps(response, indent=2)}")
    else:
        logger.error(f"❌ Falha ao criar o produto: {response}")

if __name__ == "__main__":
    test_create_product_with_variations()