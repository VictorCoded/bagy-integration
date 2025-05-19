"""
Solução final para o problema de variações de produtos.
Esta implementação garante que cada variação seja tratada como um produto independente na Bagy.
"""
import logging
import hashlib
import time

class VariationHandler:
    """
    Gerenciador de variações que trata cada variação como um produto independente na Bagy.
    """
    def __init__(self, bagy_client, product_converter):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.bagy_client = bagy_client
        self.product_converter = product_converter
    
    def process_gestaoclick_product(self, gc_product, entity_mapping):
        """
        Processa um produto do GestãoClick, convertendo suas variações em produtos independentes na Bagy.
        
        Args:
            gc_product (dict): Produto do GestãoClick
            entity_mapping: Objeto de mapeamento de entidades para registro
            
        Returns:
            dict: Estatísticas de processamento (sucesso, erros)
        """
        stats = {
            'success': 0,
            'errors': 0
        }
        
        # Converter o produto em uma lista de produtos (um para cada variação)
        bagy_products = self.product_converter.gestaoclick_to_bagy(gc_product)
        
        # Se não conseguimos converter o produto, retorna estatísticas vazias
        if not bagy_products:
            self.logger.warning(f"❌ Não foi possível converter o produto {gc_product.get('nome', 'Desconhecido')} (ID: {gc_product.get('id', 'Desconhecido')})")
            return stats
        
        # Processa cada produto convertido (cada variação como produto independente)
        for bagy_product in bagy_products:
            try:
                external_id = bagy_product.get('external_id')
                product_name = bagy_product.get('name')
                
                # Verificar se o produto já existe na Bagy
                existing_product = self.bagy_client.get_product_by_external_id(external_id)
                
                if not existing_product:
                    # Produto ainda não existe, criar novo
                    self.logger.info(f"📦 Criando novo produto na Bagy: {product_name} (external_id: {external_id})")
                    new_product = self.bagy_client.create_product(bagy_product)
                    
                    if new_product and 'id' in new_product:
                        # Registrar no mapeamento
                        entity_mapping.add_mapping(
                            entity_type='product',
                            external_id=external_id,
                            bagy_id=new_product['id'],
                            name=product_name
                        )
                        stats['success'] += 1
                        self.logger.info(f"✅ Produto criado com sucesso na Bagy: {product_name} (Bagy ID: {new_product['id']})")
                    else:
                        self.logger.error(f"❌ Falha ao criar produto na Bagy: {product_name}")
                        stats['errors'] += 1
                else:
                    # Produto já existe, atualizar
                    bagy_id = existing_product.get('id')
                    self.logger.info(f"🔄 Atualizando produto existente na Bagy: {product_name} (Bagy ID: {bagy_id})")
                    
                    # Preparar dados para atualização
                    update_data = {
                        'name': bagy_product.get('name'),
                        'description': bagy_product.get('description'),
                        'price': bagy_product.get('price'),
                        'price_compare': bagy_product.get('price_compare'),
                        'balance': bagy_product.get('balance'),
                        'height': bagy_product.get('height'),
                        'width': bagy_product.get('width'),
                        'depth': bagy_product.get('depth'),
                        'weight': bagy_product.get('weight')
                    }
                    
                    # Verificar se SKU precisa ser atualizado
                    current_sku = existing_product.get('sku')
                    new_sku = bagy_product.get('sku')
                    
                    if current_sku != new_sku:
                        if new_sku:
                            update_data['sku'] = new_sku
                            update_data['reference'] = new_sku
                            update_data['code'] = new_sku
                    
                    # Atualizar produto
                    updated_product = self.bagy_client.update_product(bagy_id, update_data)
                    
                    if updated_product:
                        stats['success'] += 1
                        self.logger.info(f"✅ Produto atualizado com sucesso na Bagy: {product_name} (Bagy ID: {bagy_id})")
                    else:
                        stats['errors'] += 1
                        self.logger.error(f"❌ Falha ao atualizar produto na Bagy: {product_name} (Bagy ID: {bagy_id})")
            
            except Exception as e:
                self.logger.error(f"❌ Erro ao processar produto {bagy_product.get('name', 'Desconhecido')}: {str(e)}")
                stats['errors'] += 1
        
        return stats