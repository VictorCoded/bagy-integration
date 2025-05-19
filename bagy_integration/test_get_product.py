"""
Script para testar a obtenção de um produto específico da API do GestãoClick
"""
import json
import logging
import os
from api_clients import GestaoClickClient

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ProductTester")

def main():
    """Função principal para testar a obtenção de um produto específico"""
    # Usar as credenciais definidas no arquivo .env
    api_key = "194c67425b6083fddab6afa899d09f9845d68589"  # GESTAOCLICK_API_KEY
    secret_key = "1a8cd45d5b2527b88de64f47c2ca4bfe7b76ed07"  # GESTAOCLICK_EMAIL
    
    logger.info(f"Usando API Key: {api_key}")
    logger.info(f"Usando Secret Key: {secret_key}")
    
    # Criar cliente da API
    client = GestaoClickClient(api_key=api_key, secret_key=secret_key)
    
    # ID do produto EGG Masturbador Masculino
    product_id = "47433753"
    
    logger.info("Testando produtos com variações")
    
    try:
        # Buscar produtos com código EGG
        logger.info("Buscando produtos com código 'EGG'")
        endpoint_by_code = "produtos?codigo_interno=EGG"
        produtos_por_codigo = client._make_request("GET", endpoint_by_code)
        
        if produtos_por_codigo and 'data' in produtos_por_codigo and produtos_por_codigo['data']:
            for produto in produtos_por_codigo['data']:
                logger.info(f"Produto por código: {produto.get('nome', 'Nome não encontrado')} (ID: {produto.get('id')})")
                logger.info(f"Possui variação: {produto.get('possui_variacao')}")
                product_id = produto.get('id')
        else:
            logger.warning("Nenhum produto encontrado com código 'EGG'")
        
        # Buscar produto pelo ID
        logger.info(f"Buscando produto pelo ID: {product_id}")
        endpoint = f"produtos/{product_id}"
        produto = client._make_request("GET", endpoint)
        
        if produto:
            # Exibir informações do produto
            logger.info(f"Produto encontrado: {produto.get('nome', 'Nome não encontrado')}")
            logger.info(f"Possui variação: {produto.get('possui_variacao')}")
            logger.info(f"Código interno: {produto.get('codigo_interno')}")
            logger.info(f"Dimensões: peso={produto.get('peso')}, altura={produto.get('altura')}, largura={produto.get('largura')}, profundidade={produto.get('profundidade')}")
            
            # Exibir detalhes das variações, se houver
            if 'variacoes' in produto and produto['variacoes']:
                logger.info(f"Número de variações: {len(produto['variacoes'])}")
                for i, var in enumerate(produto['variacoes']):
                    if isinstance(var, dict):
                        variacao = var.get('variacao', {})
                        logger.info(f"Variação {i+1}: ID={variacao.get('id')}, Nome={variacao.get('nome')}")
                    else:
                        logger.info(f"Variação {i+1}: {var}")
            else:
                logger.info("Produto não possui variações ou campo 'variacoes' não encontrado")
            
            # Salvar resposta completa em arquivo JSON para análise detalhada
            with open('produto_egg.json', 'w', encoding='utf-8') as f:
                json.dump(produto, f, ensure_ascii=False, indent=2)
                logger.info("Dados do produto salvos em 'produto_egg.json'")
        else:
            logger.error(f"Produto com ID {product_id} não encontrado")
            
        # Tentar buscar com parâmetro "completo"
        logger.info(f"Buscando produto com parâmetro 'completo=true'")
        endpoint_complete = f"produtos/{product_id}?completo=true"
        produto_completo = client._make_request("GET", endpoint_complete)
        
        if produto_completo:
            logger.info(f"Dados completos do produto incluem variações? {'variacoes' in produto_completo}")
            # Salvar resposta completa em arquivo JSON para análise detalhada
            with open('produto_egg_completo.json', 'w', encoding='utf-8') as f:
                json.dump(produto_completo, f, ensure_ascii=False, indent=2)
                logger.info("Dados completos do produto salvos em 'produto_egg_completo.json'")
    
    except Exception as e:
        logger.error(f"Erro ao buscar produto: {str(e)}")

if __name__ == "__main__":
    main()