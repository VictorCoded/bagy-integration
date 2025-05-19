"""
Script para testar especificamente o produto EGG Masturbador Masculino e suas variações
"""
import json
import logging
import os
import sys
from api_clients import GestaoClickClient
from models import ProductConverter

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("EggProductTester")

def main():
    """Função principal para testar o produto EGG Masturbador Masculino"""
    # Usar credenciais do config em vez de hardcoded
    import config
    api_key = config.GESTAOCLICK_API_KEY
    secret_key = config.GESTAOCLICK_EMAIL
    
    logger.info("Teste de variações para o produto 'Egg Masturbador Masculino'")
    
    # Criar cliente da API e verificar cabeçalhos
    client = GestaoClickClient(api_key=api_key, secret_key=secret_key)
    
    # Verificar cabeçalhos de autenticação
    headers = client._get_headers()
    logger.info(f"Cabeçalhos da API: {headers}")
    
    # Inicializar conversor de produtos
    product_converter = ProductConverter()
    
    try:
        # Primeiro, buscar produtos com código EGG
        logger.info("Buscando produtos com código 'EGG'")
        produtos_por_codigo = client._make_request("GET", "produtos?codigo_interno=EGG")
        
        if produtos_por_codigo and 'data' in produtos_por_codigo and produtos_por_codigo['data']:
            logger.info(f"Encontrados {len(produtos_por_codigo['data'])} produtos com código 'EGG'")
            
            for produto in produtos_por_codigo['data']:
                product_id = produto.get('id')
                logger.info(f"Encontrado produto: {produto.get('nome', 'Nome não encontrado')} (ID: {product_id})")
                logger.info(f"Possui variação: {produto.get('possui_variacao')}")
                
                # Buscar produto completo com possíveis variações
                logger.info(f"Buscando detalhes completos do produto {product_id}")
                try:
                    # Primeiro método - buscar usando ?completo=true
                    produto_completo = client._make_request("GET", f"produtos/{product_id}?completo=true")
                    
                    # Salvar resposta para análise
                    with open(f'produto_egg_{product_id}_completo.json', 'w', encoding='utf-8') as f:
                        json.dump(produto_completo, f, ensure_ascii=False, indent=2)
                        logger.info(f"Dados completos salvos em produto_egg_{product_id}_completo.json")
                    
                    if 'variacoes' in produto_completo and produto_completo['variacoes']:
                        logger.info(f"Produto possui {len(produto_completo['variacoes'])} variações")
                        
                        # Analisar a estrutura das variações
                        logger.info("Estrutura das variações:")
                        for i, var in enumerate(produto_completo['variacoes']):
                            if isinstance(var, dict):
                                logger.info(f"Variação {i+1}: {var.keys()}")
                                if 'variacao' in var:
                                    logger.info(f"  - ID: {var['variacao'].get('id')}")
                                    logger.info(f"  - Nome: {var['variacao'].get('nome')}")
                            else:
                                logger.info(f"Variação {i+1} não é um dicionário: {type(var)}")
                    else:
                        logger.info("O produto não tem variações no retorno da API ou o campo 'variacoes' não existe")
                        
                    # Testar a conversão
                    logger.info("Testando conversão com o ProductConverter")
                    bagy_product = product_converter.gestaoclick_to_bagy(produto_completo)
                    
                    if isinstance(bagy_product, tuple):
                        logger.error(f"Erro na conversão: {bagy_product[1]}")
                    else:
                        logger.info("Produto convertido com sucesso")
                        logger.info(f"Número de variações convertidas: {len(bagy_product.get('variations', []))}")
                        
                        # Salvar produto convertido para análise
                        with open(f'produto_egg_{product_id}_convertido.json', 'w', encoding='utf-8') as f:
                            json.dump(bagy_product, f, ensure_ascii=False, indent=2)
                            logger.info(f"Produto convertido salvo em produto_egg_{product_id}_convertido.json")
                        
                except Exception as e:
                    logger.error(f"Erro ao buscar ou processar produto completo: {str(e)}")
                    
        else:
            logger.warning("Nenhum produto encontrado com código 'EGG'")
            
            # Tentar buscar por nome
            logger.info("Tentando buscar por nome contendo 'egg'")
            produtos_por_nome = client._make_request("GET", "produtos?nome=egg")
            
            if produtos_por_nome and 'data' in produtos_por_nome and produtos_por_nome['data']:
                logger.info(f"Encontrados {len(produtos_por_nome['data'])} produtos com nome contendo 'egg'")
                
                for produto in produtos_por_nome['data']:
                    logger.info(f"Produto: {produto.get('nome')} (ID: {produto.get('id')})")
            else:
                logger.warning("Nenhum produto encontrado com nome contendo 'egg'")
    
    except Exception as e:
        logger.error(f"Erro no teste: {str(e)}")

if __name__ == "__main__":
    main()