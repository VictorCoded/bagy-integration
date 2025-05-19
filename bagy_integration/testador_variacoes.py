"""
Script simplificado para testar a conversão de variações em produtos independentes na Bagy.
"""
import os
import logging
import json
import time
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='✅ %(asctime)s | %(name)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestadorVariacoes")

# Carregar variáveis de ambiente
load_dotenv()

from api_clients import BagyClient, GestaoClickClient
from new_product_converter import ProductConverter


def main():
    """Função principal para testar conversão de variações"""
    logger.info("Iniciando teste de conversão de variações para produtos independentes")
    
    # Usar as chaves de API diretamente do sistema
    bagy_api_key = os.environ.get("BAGY_API_KEY")
    
    # Usar os valores corretos do arquivo .env
    gestaoclick_api_key = "194c67425b6083fddab6afa899d09f9845d68589"
    gestaoclick_secret_key = "1a8cd45d5b2527b88de64f47c2ca4bfe7b76ed07"
    
    # Verificar se pelo menos temos a chave da Bagy
    if not bagy_api_key:
        logger.error("❌ Chave de API da Bagy não encontrada na variável de ambiente.")
        return
        
    logger.info(f"✅ Chaves de API encontradas e configuradas")
    
    # Criar clientes de API
    logger.info("Criando clientes de API")
    bagy_client = BagyClient(bagy_api_key)
    gc_client = GestaoClickClient(gestaoclick_api_key, gestaoclick_secret_key)
    
    # Criar converter de produtos
    logger.info("Criando converter de produtos")
    product_converter = ProductConverter()
    
    # Buscar um produto específico com variações
    logger.info("Buscando produtos da GestãoClick...")
    
    # Lista para armazenar produtos com variações
    produtos_com_variacoes = []
    
    # Buscar produtos da primeira página
    produtos_page1 = gc_client.get_products(page=1, limit=100)
    
    if not produtos_page1 or 'data' not in produtos_page1:
        logger.error("❌ Erro ao buscar produtos da GestãoClick")
        return
    
    # Processar produtos da primeira página
    for produto in produtos_page1['data']:
        if 'variacoes' in produto and produto['variacoes']:
            logger.info(f"✨ Produto com variações encontrado: {produto['nome']} (ID: {produto['id']})")
            logger.info(f"   Número de variações: {len(produto['variacoes'])}")
            produtos_com_variacoes.append(produto)
            
            # Limitar a 5 produtos para o teste
            if len(produtos_com_variacoes) >= 5:
                break
    
    if not produtos_com_variacoes:
        logger.info("Nenhum produto com variações encontrado na primeira página. Buscando mais...")
        produtos_page2 = gc_client.get_products(page=2, limit=100)
        
        if produtos_page2 and 'data' in produtos_page2:
            for produto in produtos_page2['data']:
                if 'variacoes' in produto and produto['variacoes']:
                    logger.info(f"✨ Produto com variações encontrado: {produto['nome']} (ID: {produto['id']})")
                    logger.info(f"   Número de variações: {len(produto['variacoes'])}")
                    produtos_com_variacoes.append(produto)
                    
                    # Limitar a 5 produtos para o teste
                    if len(produtos_com_variacoes) >= 5:
                        break
    
    # Verificar se encontramos produtos com variações
    if not produtos_com_variacoes:
        logger.error("❌ Nenhum produto com variações encontrado!")
        return
    
    logger.info(f"🎯 Encontrados {len(produtos_com_variacoes)} produtos com variações para teste")
    
    # Testar conversão de um produto com variações
    for index, produto in enumerate(produtos_com_variacoes):
        logger.info(f"\n--- TESTE #{index+1}: {produto['nome']} (ID: {produto['id']}) ---")
        logger.info(f"Número de variações: {len(produto['variacoes'])}")
        
        # Exibir informações das variações
        logger.info("Detalhes das variações:")
        for i, var in enumerate(produto['variacoes']):
            logger.info(f"  Variação #{i+1}: Nome={var.get('nome', 'N/A')}, SKU={var.get('codigo_interno', 'N/A')}")
        
        # Converter o produto para o formato da Bagy
        logger.info("Convertendo produto para formato Bagy (variações como produtos independentes)...")
        bagy_products = product_converter.gestaoclick_to_bagy(produto)
        
        if not bagy_products:
            logger.error(f"❌ Não foi possível converter o produto {produto['nome']} (ID: {produto['id']})")
            continue
        
        logger.info(f"✅ Conversão bem-sucedida! Gerados {len(bagy_products)} produtos para a Bagy")
        
        # Exibir informações dos produtos convertidos
        for i, bagy_prod in enumerate(bagy_products):
            logger.info(f"  Produto Bagy #{i+1}: Nome={bagy_prod.get('name')}, external_id={bagy_prod.get('external_id')}, SKU={bagy_prod.get('sku')}")
        
        # Tentar criar produtos na Bagy
        logger.info("Criando produtos na Bagy...")
        
        for i, bagy_prod in enumerate(bagy_products):
            try:
                # Verificar se o produto já existe pelo external_id
                existing = bagy_client.get_product_by_external_id(bagy_prod['external_id'])
                
                if existing:
                    logger.info(f"   Produto #{i+1} já existe na Bagy com ID={existing['id']}, atualizando...")
                    # Atualizar com a nova versão
                    updated = bagy_client.update_product(existing['id'], bagy_prod)
                    logger.info(f"   ✅ Produto #{i+1} atualizado com sucesso: {bagy_prod['name']}")
                else:
                    # Criar novo produto
                    logger.info(f"   Criando produto #{i+1}: {bagy_prod['name']}")
                    created = bagy_client.create_product(bagy_prod)
                    
                    if created and 'id' in created:
                        logger.info(f"   ✅ Produto #{i+1} criado com sucesso! ID Bagy: {created['id']}")
                    else:
                        logger.error(f"   ❌ Falha ao criar produto #{i+1}: {bagy_prod['name']}")
                
            except Exception as e:
                logger.error(f"   ❌ Erro ao processar produto #{i+1}: {str(e)}")
        
        # Pausa entre produtos
        if index < len(produtos_com_variacoes) - 1:
            logger.info("Pausando 2 segundos antes do próximo produto...")
            time.sleep(2)
    
    logger.info("\n✨ Teste de conversão de variações concluído!")


if __name__ == "__main__":
    main()