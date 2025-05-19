#!/usr/bin/env python
"""
Script focado em testar a sincronização do produto EGG e suas variações
especificamente verificando se as variações são preservadas corretamente 
e se o SKU está sendo mapeado adequadamente.
"""
import json
import logging
import os
import config
from api_clients import GestaoClickClient, BagyClient
from models import ProductConverter

# Configurar logging mais detalhado para este teste
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger("EggVariationsTester")

def encontrar_egg_por_id():
    """Busca o produto EGG diretamente pelo ID conhecido"""
    # ID conhecido do produto EGG
    egg_id = "47433753"
    
    # Usar credenciais das variáveis de ambiente
    gestao_client = GestaoClickClient(
        api_key=config.GESTAOCLICK_API_KEY,
        secret_key=config.GESTAOCLICK_EMAIL
    )
    
    logger.info(f"Buscando produto EGG pelo ID conhecido: {egg_id}")
    
    try:
        # Fazer requisição direta pelo ID
        produto = gestao_client._make_request("GET", f"produtos/{egg_id}?completo=true")
        
        if produto and not isinstance(produto, dict):
            logger.error(f"Resposta inesperada: {produto}")
            return None
            
        if not produto or 'code' in produto and produto['code'] != 200:
            logger.error(f"Erro ao buscar produto: {json.dumps(produto, indent=2)}")
            return None
            
        # Salvar resultado para referência
        with open('egg_product_completo.json', 'w', encoding='utf-8') as f:
            json.dump(produto, f, ensure_ascii=False, indent=2)
            logger.info("Dados do produto EGG salvos em egg_product_completo.json")
            
        return produto
    except Exception as e:
        logger.error(f"Erro ao buscar produto EGG: {str(e)}")
        return None

def testar_conversao_egg(produto_gestao):
    """Testa a conversão do produto EGG para o formato da Bagy"""
    if not produto_gestao:
        logger.error("Produto não fornecido para teste de conversão")
        return False
        
    converter = ProductConverter()
    
    try:
        logger.info("Iniciando conversão do produto EGG para formato Bagy")
        # Converter produto para formato Bagy
        produto_bagy = converter.gestaoclick_to_bagy(produto_gestao)
        
        # Verificar se o resultado é uma tupla (erro) ou dicionário (sucesso)
        if isinstance(produto_bagy, tuple):
            if produto_bagy[0] is None:
                logger.error(f"Erro na conversão - campos faltantes: {', '.join(produto_bagy[1])}")
                return False
            else:
                logger.warning(f"Conversão parcial: {produto_bagy}")
        
        # Salvar produto convertido
        with open('egg_product_convertido.json', 'w', encoding='utf-8') as f:
            if isinstance(produto_bagy, dict):
                json.dump(produto_bagy, f, ensure_ascii=False, indent=2)
                logger.info("Produto convertido salvo em egg_product_convertido.json")
            else:
                json.dump({"erro": "Conversão falhou", "resultado": str(produto_bagy)}, f, ensure_ascii=False, indent=2)
                
        # Verificações específicas
        if isinstance(produto_bagy, dict):
            # 1. Verificar SKU correto
            codigo_interno = produto_gestao.get('codigo_interno', '')
            sku_bagy = produto_bagy.get('sku', '')
            
            logger.info(f"Verificando código interno: '{codigo_interno}' vs SKU Bagy: '{sku_bagy}'")
            if codigo_interno != sku_bagy:
                logger.error(f"ERRO: SKU não está sendo mapeado corretamente. GestãoClick='{codigo_interno}', Bagy='{sku_bagy}'")
            else:
                logger.info("✅ SKU mapeado corretamente")
                
            # 2. Verificar variações
            possui_variacao_gestao = produto_gestao.get('possui_variacao') in ["1", 1, True]
            variacoes_gestao = []
            
            if 'variacoes' in produto_gestao and produto_gestao['variacoes']:
                variacoes_gestao = produto_gestao['variacoes']
                
            variacoes_bagy = produto_bagy.get('variations', [])
            
            logger.info(f"Variações no GestãoClick: {len(variacoes_gestao)}, Variações na Bagy: {len(variacoes_bagy)}")
            
            # Se tem possui_variacao=true mas não tem variações, deve ter pelo menos uma variação padrão
            if possui_variacao_gestao and not variacoes_gestao:
                if len(variacoes_bagy) >= 1:
                    logger.info("✅ Produto sem variações no GestãoClick recebeu variação padrão na Bagy")
                else:
                    logger.error("ERRO: Produto marcado com variações mas sem variações no GestãoClick não recebeu variação padrão")
                    
            # Se tem variações no GestãoClick, deve ter o mesmo número na Bagy (ou mais se precisar de variação padrão)
            elif variacoes_gestao:
                if len(variacoes_bagy) < len(variacoes_gestao):
                    logger.error(f"ERRO: Algumas variações foram perdidas na conversão. GestãoClick: {len(variacoes_gestao)}, Bagy: {len(variacoes_bagy)}")
                else:
                    logger.info("✅ Todas as variações foram preservadas")
                    
                # Verificar códigos das variações (não devem ter sufixos como "0001")
                for var_gestao in variacoes_gestao:
                    variacao = var_gestao.get('variacao', {})
                    if not variacao:
                        continue
                        
                    var_codigo = variacao.get('codigo', '')
                    if var_codigo:
                        encontrado = False
                        for var_bagy in variacoes_bagy:
                            if var_bagy.get('reference') == var_codigo:
                                encontrado = True
                                logger.info(f"✅ Variação {var_codigo} encontrada com código preservado")
                                break
                                
                        if not encontrado:
                            logger.error(f"ERRO: Variação com código '{var_codigo}' não foi encontrada ou o código foi modificado")
            
            return True
    except Exception as e:
        logger.error(f"Erro durante o teste de conversão: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def carregar_produto_do_arquivo():
    """Carrega o produto EGG a partir do arquivo JSON existente"""
    try:
        egg_id_file = "produto_egg_id.json"
        if os.path.exists(egg_id_file):
            logger.info(f"Carregando produto EGG do arquivo {egg_id_file}")
            with open(egg_id_file, 'r', encoding='utf-8') as f:
                produto = json.load(f)
                
            if produto and 'data' in produto:
                return produto['data']
            else:
                logger.error(f"Formato inesperado no arquivo {egg_id_file}")
                return None
        else:
            logger.error(f"Arquivo {egg_id_file} não encontrado")
            return None
    except Exception as e:
        logger.error(f"Erro ao carregar produto do arquivo: {str(e)}")
        return None

def main():
    """Função principal para o teste focado no produto EGG"""
    logger.info("=" * 50)
    logger.info("Iniciando teste focado no produto EGG e suas variações")
    logger.info("=" * 50)
    
    # Tentar carregar o produto EGG do arquivo local primeiro
    produto_gestao = carregar_produto_do_arquivo()
    
    # Se não conseguir carregar do arquivo, tentar buscar da API
    if not produto_gestao:
        logger.info("Tentando buscar produto EGG da API...")
        produto_gestao = encontrar_egg_por_id()
    
    if not produto_gestao:
        logger.error("Não foi possível encontrar o produto EGG. Teste interrompido.")
        return
        
    logger.info(f"Produto EGG encontrado: {produto_gestao.get('nome', 'Sem nome')}")
    
    # Verificações preliminares
    possui_variacao = produto_gestao.get('possui_variacao') in ["1", 1, True]
    logger.info(f"Possui variação: {possui_variacao}")
    
    if 'variacoes' in produto_gestao and produto_gestao['variacoes']:
        logger.info(f"Número de variações: {len(produto_gestao['variacoes'])}")
        
        # Exibir informações sobre as variações
        logger.info("Detalhes das variações:")
        for i, var_item in enumerate(produto_gestao['variacoes']):
            var = var_item.get('variacao', {})
            if var:
                logger.info(f"  {i+1}. Nome: {var.get('nome', 'Sem nome')}")
                logger.info(f"     ID: {var.get('id', 'Sem ID')}")
                logger.info(f"     Código: {var.get('codigo', 'Sem código')}")
                logger.info(f"     Estoque: {var.get('estoque', '0')}")
    else:
        logger.warning("Produto não possui variações ou o campo 'variacoes' está ausente")
    
    # Etapa 2: Testar conversão para Bagy
    if testar_conversao_egg(produto_gestao):
        logger.info("✅ Teste de conversão concluído com sucesso")
    else:
        logger.error("❌ Teste de conversão falhou")
    
    logger.info("=" * 50)
    logger.info("Teste finalizado")
    logger.info("=" * 50)

if __name__ == "__main__":
    main()