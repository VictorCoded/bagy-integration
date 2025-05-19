"""
Integrador de sincronização com suporte a variações como produtos independentes.
Este arquivo implementa a versão final do sincronizador que trata cada variação como um produto independente na Bagy.
"""
import logging
import time
from datetime import datetime
import os

from storage import EntityMapping
from solucao_final import VariationHandler
from utils import Pagination, get_current_datetime

class SyncIntegrator:
    """
    Integrador de sincronização que utiliza o VariationHandler para tratar
    variações como produtos independentes na Bagy.
    """
    def __init__(self, gestaoclick_client, bagy_client, product_converter, entity_mapping, incomplete_products_storage=None):
        """
        Inicializa o integrador de sincronização.
        
        Args:
            gestaoclick_client: Cliente da API do GestãoClick
            bagy_client: Cliente da API do Bagy
            product_converter: Conversor de produtos
            entity_mapping: Mapeamento de entidades
            incomplete_products_storage: Armazenamento de produtos incompletos
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.gc_client = gestaoclick_client
        self.bagy_client = bagy_client
        self.product_converter = product_converter
        self.entity_mapping = entity_mapping
        self.incomplete_products_storage = incomplete_products_storage
        
        # Criar o manipulador de variações
        self.variation_handler = VariationHandler(bagy_client, product_converter)
    
    def sync_products_to_bagy(self):
        """
        Sincroniza produtos do GestãoClick para a Bagy, tratando variações como produtos independentes.
        
        Returns:
            dict: Estatísticas de sincronização
        """
        stats = {
            'success': 0,
            'errors': 0,
            'incomplete': 0
        }
        
        self.logger.info("🔄 Iniciando sincronização de produtos do GestãoClick para Bagy")
        
        # Obter todos os produtos da GestãoClick
        self.logger.info("📋 Buscando catálogo de produtos do GestãoClick...")
        all_gestaoclick_products = []
        
        try:
            # Usar paginação para obter todos os produtos
            pagination = Pagination()
            all_gestaoclick_products = pagination.get_all_pages(
                fetcher=self.gc_client.get_products,
                data_key='data'
            )
            
            self.logger.info(f"📦 Encontrados {len(all_gestaoclick_products)} produtos no GestãoClick")
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter produtos do GestãoClick: {str(e)}")
            stats['errors'] += 1
            return stats
        
        # Processar cada produto
        for gc_product in all_gestaoclick_products:
            try:
                product_id = gc_product.get('id')
                product_name = gc_product.get('nome', 'Desconhecido')
                
                # Verificar se o produto tem variações
                has_variations = 'variacoes' in gc_product and gc_product['variacoes']
                
                if has_variations:
                    self.logger.info(f"🔀 Produto {product_name} (ID: {product_id}) tem variações. Processando cada variação como produto independente...")
                    variation_stats = self.variation_handler.process_gestaoclick_product(gc_product, self.entity_mapping)
                    
                    # Atualizar estatísticas
                    stats['success'] += variation_stats['success']
                    stats['errors'] += variation_stats['errors']
                    
                    # Se nenhuma variação foi processada com sucesso, incrementar contador de produtos incompletos
                    if variation_stats['success'] == 0 and variation_stats['errors'] > 0:
                        stats['incomplete'] += 1
                        
                        # Registrar produto como incompleto, se o armazenamento foi fornecido
                        if self.incomplete_products_storage:
                            self.incomplete_products_storage.add_product(
                                product_id=product_id,
                                product_name=product_name,
                                missing_fields=['Erro ao processar variações']
                            )
                else:
                    # Produto sem variações, processar normalmente
                    self.logger.info(f"📦 Processando produto simples: {product_name} (ID: {product_id})")
                    product_stats = self.variation_handler.process_gestaoclick_product(gc_product, self.entity_mapping)
                    
                    # Atualizar estatísticas
                    stats['success'] += product_stats['success']
                    stats['errors'] += product_stats['errors']
                    
                    # Se o produto não foi processado com sucesso, incrementar contador de produtos incompletos
                    if product_stats['success'] == 0 and product_stats['errors'] > 0:
                        stats['incomplete'] += 1
            
            except Exception as e:
                self.logger.error(f"❌ Erro ao processar produto {gc_product.get('nome', 'Desconhecido')} (ID: {gc_product.get('id', 'Desconhecido')}): {str(e)}")
                stats['errors'] += 1
        
        self.logger.info(f"✨ Sincronização de produtos para Bagy concluída: {stats['success']} com sucesso, {stats['errors']} erros, {stats['incomplete']} incompletos")
        return stats