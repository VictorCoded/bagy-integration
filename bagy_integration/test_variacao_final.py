"""
Teste da solução final para variações como produtos independentes.
Este script testa a implementação final com um produto específico que possui variações.
"""
import os
import logging
import sys

from api_clients import BagyClient, GestaoClickClient
from new_product_converter import ProductConverter
from solucao_final import VariationHandler
from storage import EntityMapping, IncompleteProductsStorage

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='✅ %(asctime)s | %(name)s | %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger('VariationFinalTester')

def test_variation_handler():
    """
    Teste do VariationHandler com um produto específico que contém variações.
    """
    logger.info("Iniciando teste da solução final para variações")
    
    # Usar as chaves de API corretas do arquivo .env
    bagy_api_key = os.environ.get("BAGY_API_KEY")
    gestaoclick_api_key = "194c67425b6083fddab6afa899d09f9845d68589"
    gestaoclick_secret_key = "1a8cd45d5b2527b88de64f47c2ca4bfe7b76ed07"
    
    # Verificar se pelo menos temos a chave da Bagy
    if not bagy_api_key:
        logger.error("❌ Chave de API da Bagy não encontrada na variável de ambiente.")
        return
    
    logger.info("✅ Chaves de API encontradas e configuradas")
    
    # Criar clientes de API
    logger.info("Criando clientes de API")
    bagy_client = BagyClient(bagy_api_key)
    gc_client = GestaoClickClient(gestaoclick_api_key, gestaoclick_secret_key)
    
    # Criar converter de produtos
    logger.info("Criando converter de produtos")
    incomplete_products = IncompleteProductsStorage('./data/incomplete_products.json')
    product_converter = ProductConverter(incomplete_products_storage=incomplete_products)
    
    # Criar manipulador de variações
    logger.info("Criando manipulador de variações")
    variation_handler = VariationHandler(bagy_client, product_converter)
    
    # Criar mapeamento de entidades
    entity_mapping = EntityMapping('./data/entity_mapping.json')
    
    # ID do produto a testar - Plug Anal Pom Pom (ID: 77298129) - tem 20 variações
    product_id = "77298129"
    logger.info(f"Buscando produto específico com ID: {product_id}")
    
    try:
        # Obter produto da GestãoClick por SKU (que é o ID)
        gc_product = gc_client.get_product_by_sku(product_id)
        
        if not gc_product:
            logger.error(f"❌ Produto com ID {product_id} não encontrado na GestãoClick")
            return
        
        product_name = gc_product.get('nome', 'Desconhecido')
        logger.info(f"✅ Produto encontrado: {product_name}")
        
        # Verificar variações
        variations = gc_product.get('variacoes', [])
        variation_count = len(variations)
        
        if variation_count == 0:
            logger.warning(f"⚠️ Produto {product_name} não possui variações. Testando mesmo assim.")
        else:
            logger.info(f"🔀 Produto {product_name} possui {variation_count} variação(ões)")
        
        # Processar o produto com o VariationHandler
        logger.info(f"💫 Processando produto {product_name} com variações utilizando a solução final")
        stats = variation_handler.process_gestaoclick_product(gc_product, entity_mapping)
        
        # Exibir resultados
        logger.info(f"✨ Processamento concluído. Estatísticas:")
        logger.info(f"   ✅ Sucessos: {stats['success']}")
        logger.info(f"   ❌ Erros: {stats['errors']}")
        
        if stats['success'] > 0:
            logger.info("🎉 TESTE BEM-SUCEDIDO! As variações foram enviadas para a Bagy como produtos independentes.")
        else:
            logger.warning("⚠️ Nenhuma variação foi enviada com sucesso. Verifique os logs para detalhes.")
    
    except Exception as e:
        logger.error(f"❌ Erro durante o teste: {str(e)}")

if __name__ == "__main__":
    test_variation_handler()