"""
Bidirectional synchronization module for transferring data between Bagy and GestãoClick.

From Bagy to GestãoClick:
- Customer information
- Orders (purchases)

From GestãoClick to Bagy:
- Products
"""
import logging
import time
from datetime import datetime
import traceback
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

import config
from api_clients import BagyClient, GestaoClickClient
from models import ProductConverter, CustomerConverter, OrderConverter
from storage import EntityMapping, SyncHistory, IncompleteProductsStorage
from utils import generate_entity_version, paginate_all_results, extract_business_entity_id

class BidirectionalSynchronizer:
    """
    Main synchronizer class for bidirectional data flow between Bagy and GestãoClick.
    
    From Bagy to GestãoClick:
    - Customer information 
    - Orders (purchases)
    
    From GestãoClick to Bagy:
    - Products
    """
    
    def __init__(self):
        """Initialize the synchronizer with API clients and converters."""
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize API clients
        self.bagy_client = BagyClient(config.BAGY_API_KEY)
        self.gestaoclick_client = GestaoClickClient(
            config.GESTAOCLICK_API_KEY,
            config.GESTAOCLICK_EMAIL
        )
        
        # Initialize data converters
        self.product_converter = ProductConverter()
        self.customer_converter = CustomerConverter()
        self.order_converter = OrderConverter()
        
        # Initialize storage components
        self.entity_mapping = EntityMapping()
        self.sync_history = SyncHistory()
        self.incomplete_products_storage = IncompleteProductsStorage()
    
    # Os métodos antigos para gerenciamento de produtos incompletos foram substituídos pela classe IncompleteProductsStorage
            
    def _ensure_category_exists(self, category_name):
        """
        Verifica se uma categoria existe na Bagy e a cria se não existir.
        
        Args:
            category_name (str): Nome da categoria
            
        Returns:
            int or None: ID da categoria se existir ou for criada com sucesso, None caso contrário
        """
        try:
            if not category_name:
                return None
                
            # Verifica se a categoria já existe
            category = self.bagy_client.get_category_by_name(category_name)
            
            if category:
                self.logger.debug(f"Categoria '{category_name}' já existe (ID: {category.get('id')})")
                return category.get('id')
                
            # Se não existir, cria a categoria
            self.logger.info(f"🔄 Criando categoria '{category_name}' na Bagy")
            
            category_data = {
                "name": category_name,
                "description": f"Categoria {category_name} importada automaticamente do GestãoClick",
                "active": True,
                "meta_title": category_name,
                "meta_description": f"Produtos da categoria {category_name}"
            }
            
            result = self.bagy_client.create_category(category_data)
            
            if result and 'id' in result:
                self.logger.info(f"✅ Categoria '{category_name}' criada com sucesso (ID: {result['id']})")
                return result['id']
            else:
                self.logger.error(f"❌ Erro ao criar categoria '{category_name}': {result}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Erro ao verificar/criar categoria '{category_name}': {str(e)}")
            return None
    
    def sync_products_from_gestaoclick(self):
        """
        Synchronize products from GestãoClick to Bagy.
        
        Returns:
            tuple: (success_count, error_count)
        """
        self.logger.info("🔄 Iniciando sincronização de produtos do GestãoClick para Bagy")
        success_count = 0
        error_count = 0
        
        try:
            # Fetch all products from GestãoClick
            self.logger.info("📋 Buscando catálogo de produtos do GestãoClick...")
            gestao_products = paginate_all_results(
                fetch_page_func=lambda page: self.gestaoclick_client.get_products(page=page, limit=100),
                extract_items_func=lambda data: data.get('data', [])
            )
            
            self.logger.info(f"📦 Found {len(gestao_products)} products in GestãoClick")
            
            # Process each product
            for gestao_product in gestao_products:
                try:
                    product_id = gestao_product.get('id')
                    if not product_id:
                        self.logger.warning("Skipping product without ID")
                        continue
                    
                    # Generate a version hash for the product
                    product_version = generate_entity_version(gestao_product)
                    
                    # Check if product should be synchronized
                    if not self.sync_history.should_sync('products_to_bagy', product_id, product_version):
                        self.logger.debug(f"Product {product_id} hasn't changed, skipping")
                        continue
                    
                    # Verificar se o produto estava previamente na lista de incompletos
                    # Se estiver com todos os campos agora, remover da lista
                    product_name = gestao_product.get('nome', 'Produto sem nome')
                    
                    # Log adicional para variações
                    if gestao_product.get('possui_variacao') in ["1", 1, True]:
                        self.logger.info(f"🛒 Produto com variações: {gestao_product.get('nome', '')} (ID: {product_id})")
                        
                        # Verificar se temos o campo variacoes e se não está vazio
                        if 'variacoes' in gestao_product and gestao_product['variacoes']:
                            self.logger.info(f"🛒 Número de variações: {len(gestao_product['variacoes'])}")
                        else:
                            self.logger.warning(f"⚠️ Produto marcado com variações, mas lista de variações vazia ou ausente: {gestao_product.get('nome', '')}")
                    
                    # Log específico para o produto EGG que sabemos ter variações
                    if gestao_product.get('codigo_interno') == 'EGG' or 'egg' in gestao_product.get('nome', '').lower():
                        self.logger.info(f"🥚 Produto EGG encontrado: {gestao_product.get('nome', '')} (ID: {product_id})")
                        self.logger.info(f"🥚 Possui variação marcada: {gestao_product.get('possui_variacao')}")
                    
                    # Convert product to Bagy format
                    result = self.product_converter.gestaoclick_to_bagy(gestao_product)
                    
                    # Verificar se o produto tem todos os campos obrigatórios
                    if isinstance(result, tuple):
                        bagy_product, missing_fields = result
                        
                        # Registramos o produto como incompleto para referência futura
                        # Usar log menos verboso (debug) para não poluir a saída principal
                        self.logger.debug(f"⚠️ Produto {product_name} (ID: {product_id}) tem campos faltando: {', '.join(missing_fields)}")
                        
                        # Armazenar informações sobre produtos incompletos usando a nova classe
                        self.incomplete_products_storage.add_product(product_id, product_name, missing_fields)
                        
                        # Verificar se são apenas dimensões ou SKU faltando
                        campos_criticos = ['descrição']
                        
                        if any(campo in campos_criticos for campo in missing_fields):
                            # Se faltar algum campo crítico, não processar o produto
                            self.logger.warning(f"❌ Produto {product_name} (ID: {product_id}) não pode ser sincronizado. Campo crítico faltando: descrição")
                            error_count += 1
                            continue
                        
                        # Neste ponto, temos um produto com campos não críticos faltando (altura, largura, etc)
                        # Vamos continuar com a criação do produto, pois os campos faltantes serão preenchidos pelo API client
                    
                    # Verificar se o resultado da conversão é uma tupla (None, missing_fields)
                    # Isso significa que o produto não tem todos os campos necessários
                    if isinstance(result, tuple) and result[0] is None:
                        missing_fields = result[1]
                        self.logger.warning(f"❌ Produto {product_id} não pode ser sincronizado. Campos críticos faltando: {', '.join(missing_fields)}")
                        # Adicionar à lista de produtos incompletos usando a nova classe
                        product_name = gestao_product.get('nome', '')
                        self.incomplete_products_storage.add_product(product_id, product_name, missing_fields)
                        error_count += 1
                        continue
                        
                    # Se chegou aqui, o produto está completo
                    # Remover da lista de incompletos, se existir
                    self.incomplete_products_storage.clear_product(product_id)
                    
                    bagy_product = result
                    
                    # Verificar e criar categoria, se necessário
                    category_name = gestao_product.get('nome_grupo')
                    category_id = None
                    if category_name:
                        category_id = self._ensure_category_exists(category_name)
                        if category_id:
                            # Atualizar o objeto do produto com o ID da categoria
                            bagy_product["category_default_id"] = str(category_id)
                            bagy_product["category_ids"] = [int(category_id)]  # array de integers
                        else:
                            # Remover os campos de categoria se não conseguimos criar/encontrar a categoria
                            if "category_default_id" in bagy_product:
                                del bagy_product["category_default_id"]
                            if "category_ids" in bagy_product:
                                del bagy_product["category_ids"]
                    
                    # Check if product already exists in Bagy
                    bagy_id = None
                    for mapping_id, gestao_id in self.entity_mapping.mapping.get('products', {}).items():
                        if gestao_id == product_id:
                            bagy_id = mapping_id
                            break
                    
                    # Verificação inicial - todos os produtos precisam estar sincronizados corretamente
                    # Inicialmente não forçamos sincronização, a menos que haja uma razão específica
                    force_sync = False
                    
                    # Verificar se o campo SKU precisa ser atualizado (para corrigir produtos criados antes da correção)
                    should_update_sku = False
                    if bagy_id:
                        # Buscar produto atual na Bagy para verificar se o SKU está correto
                        try:
                            current_bagy_product = self.bagy_client.get_product_by_id(bagy_id)
                            
                            # Se o SKU atual é diferente do código interno do GestãoClick, precisamos atualizar
                            if current_bagy_product and (
                                current_bagy_product.get('sku') != gestao_product.get('codigo_interno') or 
                                not current_bagy_product.get('sku')
                            ):
                                self.logger.info(f"🔄 SKU desatualizado detectado: atual={current_bagy_product.get('sku')}, novo={gestao_product.get('codigo_interno')}")
                                should_update_sku = True
                                force_sync = True
                        except Exception as e:
                            self.logger.warning(f"Erro ao buscar produto na Bagy para verificar SKU: {str(e)}")
                    
                    if bagy_id and not force_sync:
                        # Update existing product
                        self.logger.info(f"🔄 Atualizando produto {product_id} (Bagy ID: {bagy_id})")
                        result = self.bagy_client.update_product(bagy_id, bagy_product)
                    elif bagy_id and force_sync:
                        # Forçar atualização do produto existente
                        self.logger.info(f"🔄 Atualizando produto {product_id} (Bagy ID: {bagy_id}) - FORÇADO")
                        if should_update_sku:
                            self.logger.info(f"🔄 Atualizando SKU para {gestao_product.get('codigo_interno')}")
                        
                        # Log especial para variações
                        possui_variacao = gestao_product.get('possui_variacao') in ["1", 1, True]
                        if possui_variacao and 'variacoes' in gestao_product and gestao_product['variacoes']:
                            self.logger.info(f"🔄 Sincronizando {len(gestao_product['variacoes'])} variações para o produto {product_id}")
                            for var_item in gestao_product['variacoes']:
                                var = var_item.get('variacao', {})
                                if var:
                                    self.logger.info(f"  - Variação: {var.get('nome', 'Sem nome')} (ID: {var.get('id')}, Código: {var.get('codigo', '')})")
                        
                        result = self.bagy_client.update_product(bagy_id, bagy_product)
                    else:
                        # Create new product
                        self.logger.info(f"📦 Criando novo produto {product_id} no Bagy")
                        result = self.bagy_client.create_product(bagy_product)
                        
                        # Store the mapping (reverse direction)
                        new_id = result.get('id')
                        if new_id:
                            self.entity_mapping.add_mapping('products', new_id, product_id)
                    
                    # Update sync history
                    self.sync_history.update_sync('products_to_bagy', product_id, product_version)
                    success_count += 1
                    
                except Exception as e:
                    self.logger.error(f"Error synchronizing product {gestao_product.get('id')} to Bagy: {str(e)}")
                    self.logger.debug(traceback.format_exc())
                    error_count += 1
            
            self.logger.info(f"✨ Sincronização de produtos para Bagy concluída: {success_count} com sucesso, {error_count} erros")
            
        except Exception as e:
            self.logger.error(f"Error during product synchronization to Bagy: {str(e)}")
            self.logger.debug(traceback.format_exc())
        
        return success_count, error_count
    
    def sync_products_from_bagy(self):
        """
        Synchronize products from Bagy to GestãoClick (legacy method kept for reference).
        This method is no longer used in the bidirectional flow.
        
        Returns:
            tuple: (success_count, error_count)
        """
        self.logger.info("🔄 Iniciando sincronização de produtos")
        success_count = 0
        error_count = 0
        
        try:
            # Fetch all products from Bagy
            bagy_products = paginate_all_results(
                fetch_page_func=lambda page: self.bagy_client.get_products(page=page, limit=100),
                extract_items_func=lambda data: data.get('data', [])
            )
            
            self.logger.info(f"📦 Encontrados {len(bagy_products)} produtos no Bagy")
            
            # Process each product
            for bagy_product in bagy_products:
                try:
                    product_id = bagy_product.get('id')
                    if not product_id:
                        self.logger.warning("Skipping product without ID")
                        continue
                    
                    # Generate a version hash for the product
                    product_version = generate_entity_version(bagy_product)
                    
                    # Check if product should be synchronized
                    if not self.sync_history.should_sync('products', product_id, product_version):
                        self.logger.debug(f"Product {product_id} hasn't changed, skipping")
                        continue
                    
                    # Convert product to GestãoClick format
                    gestao_product = self.product_converter.bagy_to_gestaoclick(bagy_product)
                    
                    # Check if product already exists in GestãoClick
                    existing_id = self.entity_mapping.get_gestaoclick_id('products', product_id)
                    
                    if existing_id:
                        # Update existing product
                        self.logger.info(f"Updating product {product_id} (GestãoClick ID: {existing_id})")
                        result = self.gestaoclick_client.update_product(existing_id, gestao_product)
                    else:
                        # Check for duplicate using SKU
                        sku_search_result = self.gestaoclick_client.get_product_by_sku(gestao_product.get('sku', ''))
                        
                        if sku_search_result and 'data' in sku_search_result and sku_search_result['data']:
                            # Product exists with the same SKU
                            existing_product = sku_search_result['data'][0]
                            existing_id = existing_product.get('id')
                            
                            self.logger.info(f"Found existing product with SKU {gestao_product.get('sku')} (GestãoClick ID: {existing_id})")
                            
                            # Update the existing product
                            result = self.gestaoclick_client.update_product(existing_id, gestao_product)
                            
                            # Store the mapping
                            self.entity_mapping.add_mapping('products', product_id, existing_id)
                        else:
                            # Create new product
                            self.logger.info(f"Creating new product {product_id}")
                            result = self.gestaoclick_client.create_product(gestao_product)
                            
                            # Store the mapping
                            new_id = result.get('id')
                            if new_id:
                                self.entity_mapping.add_mapping('products', product_id, new_id)
                    
                    # Update sync history
                    self.sync_history.update_sync('products', product_id, product_version)
                    success_count += 1
                    
                except Exception as e:
                    self.logger.error(f"Error synchronizing product {bagy_product.get('id')}: {str(e)}")
                    self.logger.debug(traceback.format_exc())
                    error_count += 1
            
            self.logger.info(f"Product synchronization completed: {success_count} successful, {error_count} errors")
            
        except Exception as e:
            self.logger.error(f"Error during product synchronization: {str(e)}")
            self.logger.debug(traceback.format_exc())
        
        return success_count, error_count
    
    def sync_customers(self):
        """
        Synchronize customers from Bagy to GestãoClick.
        
        Returns:
            tuple: (success_count, error_count)
        """
        self.logger.info("🔄 Iniciando sincronização de clientes do Bagy para GestãoClick")
        success_count = 0
        error_count = 0
        
        try:
            # Fetch all customers from Bagy
            bagy_customers = paginate_all_results(
                fetch_page_func=lambda page: self.bagy_client.get_customers(page=page, limit=100),
                extract_items_func=lambda data: data.get('data', [])
            )
            
            self.logger.info(f"👥 Encontrados {len(bagy_customers)} clientes no Bagy")
            
            # Process each customer
            for bagy_customer in bagy_customers:
                try:
                    customer_id = bagy_customer.get('id')
                    if not customer_id:
                        self.logger.warning("Skipping customer without ID")
                        continue
                    
                    # Generate a version hash for the customer
                    customer_version = generate_entity_version(bagy_customer)
                    
                    # Check if customer should be synchronized
                    if not self.sync_history.should_sync('customers', customer_id, customer_version):
                        self.logger.debug(f"Customer {customer_id} hasn't changed, skipping")
                        continue
                    
                    # Convert customer to GestãoClick format
                    gestao_customer = self.customer_converter.bagy_to_gestaoclick(bagy_customer)
                    
                    # Check if customer already exists in GestãoClick
                    existing_id = self.entity_mapping.get_gestaoclick_id('customers', customer_id)
                    
                    if existing_id:
                        # Update existing customer
                        self.logger.info(f"👤 Atualizando cliente {customer_id} (GestãoClick ID: {existing_id})")
                        result = self.gestaoclick_client.update_customer(existing_id, gestao_customer)
                    else:
                        # Check for duplicate using document
                        if gestao_customer.get('documento'):
                            doc_search_result = self.gestaoclick_client.get_customer_by_document(gestao_customer['documento'])
                            
                            if doc_search_result and 'data' in doc_search_result and doc_search_result['data']:
                                # Customer exists with the same document
                                existing_customer = doc_search_result['data'][0]
                                existing_id = existing_customer.get('id')
                                
                                self.logger.info(f"Found existing customer with document {gestao_customer['documento']} (GestãoClick ID: {existing_id})")
                                
                                # Update the existing customer
                                result = self.gestaoclick_client.update_customer(existing_id, gestao_customer)
                                
                                # Store the mapping
                                self.entity_mapping.add_mapping('customers', customer_id, existing_id)
                                self.sync_history.update_sync('customers', customer_id, customer_version)
                                success_count += 1
                                continue
                        
                        # Check for duplicate using email
                        if gestao_customer.get('email'):
                            email_search_result = self.gestaoclick_client.get_customer_by_email(gestao_customer['email'])
                            
                            if email_search_result and 'data' in email_search_result and email_search_result['data']:
                                # Customer exists with the same email
                                existing_customer = email_search_result['data'][0]
                                existing_id = existing_customer.get('id')
                                
                                self.logger.info(f"Found existing customer with email {gestao_customer['email']} (GestãoClick ID: {existing_id})")
                                
                                # Update the existing customer
                                result = self.gestaoclick_client.update_customer(existing_id, gestao_customer)
                                
                                # Store the mapping
                                self.entity_mapping.add_mapping('customers', customer_id, existing_id)
                                self.sync_history.update_sync('customers', customer_id, customer_version)
                                success_count += 1
                                continue
                        
                        # Create new customer
                        self.logger.info(f"👤 Criando novo cliente {customer_id}")
                        result = self.gestaoclick_client.create_customer(gestao_customer)
                        
                        # Store the mapping
                        new_id = result.get('id')
                        if new_id:
                            self.entity_mapping.add_mapping('customers', customer_id, new_id)
                    
                    # Update sync history
                    self.sync_history.update_sync('customers', customer_id, customer_version)
                    success_count += 1
                    
                except Exception as e:
                    self.logger.error(f"Error synchronizing customer {bagy_customer.get('id')}: {str(e)}")
                    self.logger.debug(traceback.format_exc())
                    error_count += 1
            
            self.logger.info(f"✨ Sincronização de clientes concluída: {success_count} com sucesso, {error_count} erros")
            
        except Exception as e:
            self.logger.error(f"Error during customer synchronization: {str(e)}")
            self.logger.debug(traceback.format_exc())
        
        return success_count, error_count
    
    def sync_orders(self):
        """
        Synchronize orders from Bagy to GestãoClick.
        
        Returns:
            tuple: (success_count, error_count)
        """
        self.logger.info("🔄 Iniciando sincronização de pedidos do Bagy para GestãoClick")
        success_count = 0
        error_count = 0
        
        try:
            # Fetch all orders from Bagy
            bagy_orders = paginate_all_results(
                fetch_page_func=lambda page: self.bagy_client.get_orders(page=page, limit=100),
                extract_items_func=lambda data: data.get('data', [])
            )
            
            self.logger.info(f"🛒 Encontrados {len(bagy_orders)} pedidos no Bagy")
            
            # Process each order
            for bagy_order in bagy_orders:
                try:
                    order_id = bagy_order.get('id')
                    if not order_id:
                        self.logger.warning("Skipping order without ID")
                        continue
                    
                    # Generate a version hash for the order
                    order_version = generate_entity_version(bagy_order)
                    
                    # Check if order should be synchronized
                    if not self.sync_history.should_sync('orders', order_id, order_version):
                        self.logger.debug(f"Order {order_id} hasn't changed, skipping")
                        continue
                    
                    # Get the customer ID from the mapping
                    customer_bagy_id = bagy_order.get('cliente_id')
                    customer_gestao_id = None
                    
                    if customer_bagy_id:
                        customer_gestao_id = self.entity_mapping.get_gestaoclick_id('customers', customer_bagy_id)
                        if not customer_gestao_id:
                            self.logger.warning(f"⚠️ Cliente {customer_bagy_id} não encontrado no GestãoClick, sincronizando cliente primeiro")
                            
                            # Try to get customer details from Bagy
                            try:
                                bagy_customer = self.bagy_client.get_customer_by_id(customer_bagy_id)
                                if bagy_customer:
                                    # Convert and create/update customer
                                    gestao_customer = self.customer_converter.bagy_to_gestaoclick(bagy_customer)
                                    
                                    # Check if customer already exists by document or email
                                    if gestao_customer.get('documento'):
                                        doc_search_result = self.gestaoclick_client.get_customer_by_document(gestao_customer['documento'])
                                        if doc_search_result and 'data' in doc_search_result and doc_search_result['data']:
                                            existing_customer = doc_search_result['data'][0]
                                            customer_gestao_id = existing_customer.get('id')
                                            self.entity_mapping.add_mapping('customers', customer_bagy_id, customer_gestao_id)
                                    
                                    if not customer_gestao_id and gestao_customer.get('email'):
                                        email_search_result = self.gestaoclick_client.get_customer_by_email(gestao_customer['email'])
                                        if email_search_result and 'data' in email_search_result and email_search_result['data']:
                                            existing_customer = email_search_result['data'][0]
                                            customer_gestao_id = existing_customer.get('id')
                                            self.entity_mapping.add_mapping('customers', customer_bagy_id, customer_gestao_id)
                                    
                                    if not customer_gestao_id:
                                        # Create new customer
                                        result = self.gestaoclick_client.create_customer(gestao_customer)
                                        customer_gestao_id = result.get('id')
                                        if customer_gestao_id:
                                            self.entity_mapping.add_mapping('customers', customer_bagy_id, customer_gestao_id)
                            except Exception as e:
                                self.logger.error(f"❌ Erro ao sincronizar cliente para pedido: {str(e)}")
                    
                    # Convert order to GestãoClick format
                    gestao_order = self.order_converter.bagy_to_gestaoclick(bagy_order, customer_gestao_id)
                    
                    # Check if order already exists in GestãoClick
                    existing_id = self.entity_mapping.get_gestaoclick_id('orders', order_id)
                    
                    if existing_id:
                        # Update existing order
                        self.logger.info(f"🛒 Atualizando pedido {order_id} (GestãoClick ID: {existing_id})")
                        result = self.gestaoclick_client.update_order(existing_id, gestao_order)
                    else:
                        # Check for duplicate using external ID
                        external_id_search_result = self.gestaoclick_client.get_order_by_external_id(str(order_id))
                        
                        if external_id_search_result and 'data' in external_id_search_result and external_id_search_result['data']:
                            # Order exists with the same external ID
                            existing_order = external_id_search_result['data'][0]
                            existing_id = existing_order.get('id')
                            
                            self.logger.info(f"🔍 Encontrado pedido existente com ID externo {order_id} (GestãoClick ID: {existing_id})")
                            
                            # Update the existing order
                            result = self.gestaoclick_client.update_order(existing_id, gestao_order)
                            
                            # Store the mapping
                            self.entity_mapping.add_mapping('orders', order_id, existing_id)
                        else:
                            # Create new order
                            self.logger.info(f"🛒 Criando novo pedido {order_id}")
                            result = self.gestaoclick_client.create_order(gestao_order)
                            
                            # Store the mapping
                            new_id = result.get('id')
                            if new_id:
                                self.entity_mapping.add_mapping('orders', order_id, new_id)
                    
                    # Update sync history
                    self.sync_history.update_sync('orders', order_id, order_version)
                    success_count += 1
                    
                except Exception as e:
                    self.logger.error(f"❌ Erro ao sincronizar pedido {bagy_order.get('id')}: {str(e)}")
                    self.logger.debug(traceback.format_exc())
                    error_count += 1
            
            self.logger.info(f"✨ Sincronização de pedidos concluída: {success_count} com sucesso, {error_count} erros")
            
        except Exception as e:
            self.logger.error(f"❌ Erro durante a sincronização de pedidos: {str(e)}")
            self.logger.debug(traceback.format_exc())
        
        return success_count, error_count
    
    def sync_all(self):
        """
        Run a full bidirectional synchronization of all entities.
        
        From GestãoClick to Bagy:
        - Products
        
        From Bagy to GestãoClick:
        - Customers
        - Orders
        
        Returns:
            dict: Synchronization results
        """
        start_time = datetime.now()
        self.logger.info(f"🔄 Iniciando sincronização bidirecional completa em {start_time.isoformat()}")
        
        results = {
            'start_time': start_time.isoformat(),
            'end_time': None,
            'duration_seconds': None,
            'products_to_bagy': {
                'success': 0,
                'errors': 0,
                'incomplete': 0
            },
            'customers_to_gestaoclick': {
                'success': 0,
                'errors': 0
            },
            'orders_to_gestaoclick': {
                'success': 0,
                'errors': 0
            }
        }
        
        try:
            # Sync products from GestãoClick to Bagy
            self.logger.info("📦 Iniciando sincronização de produtos do GestãoClick para Bagy...")
            product_success, product_errors = self.sync_products_from_gestaoclick()
            results['products_to_bagy']['success'] = product_success
            results['products_to_bagy']['errors'] = product_errors
            
            # Sync customers from Bagy to GestãoClick
            self.logger.info("👥 Iniciando sincronização de clientes do Bagy para GestãoClick...")
            customer_success, customer_errors = self.sync_customers()
            results['customers_to_gestaoclick']['success'] = customer_success
            results['customers_to_gestaoclick']['errors'] = customer_errors
            
            # Sync orders from Bagy to GestãoClick
            self.logger.info("🛒 Iniciando sincronização de pedidos do Bagy para GestãoClick...")
            order_success, order_errors = self.sync_orders()
            results['orders_to_gestaoclick']['success'] = order_success
            results['orders_to_gestaoclick']['errors'] = order_errors
            
        except Exception as e:
            self.logger.error(f"❌ Erro inesperado durante a sincronização completa: {str(e)}")
            self.logger.debug(traceback.format_exc())
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        results['end_time'] = end_time.isoformat()
        results['duration_seconds'] = duration
        
        self.logger.info(f"✨ Sincronização concluída em {duration:.2f} segundos")
        # Obter estatísticas atualizadas sobre produtos incompletos usando nossa classe especializada
        try:
            # Obter estatísticas de produtos incompletos da classe
            incomplete_stats = self.incomplete_products_storage.get_statistics()
            results['products_to_bagy']['incomplete'] = incomplete_stats.get('total', 0)
            
            # Adicionar detalhes adicionais de campos faltantes mais comuns
            if 'campos_frequentes' in incomplete_stats and incomplete_stats['campos_frequentes']:
                results['products_to_bagy']['missing_fields'] = incomplete_stats['campos_frequentes']
        except Exception as e:
            self.logger.warning(f"⚠️ Erro ao obter estatísticas de produtos incompletos: {str(e)}")
            results['products_to_bagy']['incomplete'] = 0
            
        # Preparar string de campos faltantes frequentes
        missing_fields_str = ""
        if 'missing_fields' in results['products_to_bagy'] and results['products_to_bagy']['missing_fields']:
            missing_fields_str = "\n   📋 Campos mais frequentes:\n"
            for field, count in results['products_to_bagy']['missing_fields'].items():
                missing_fields_str += f"      - {field}: {count} produtos\n"
                
        summary = f"""
📊 Resumo da sincronização:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🕒 Início: {results['start_time']}
🕕 Fim: {results['end_time']}
⏱️ Duração: {results['duration_seconds']:.2f} segundos

📦 Produtos (GestãoClick → Bagy):
   ✅ Sucesso: {results['products_to_bagy']['success']}
   ❌ Erros: {results['products_to_bagy']['errors']}
   ⚠️ Incompletos: {results['products_to_bagy']['incomplete']}{missing_fields_str}

👥 Clientes (Bagy → GestãoClick):
   ✅ Sucesso: {results['customers_to_gestaoclick']['success']}
   ❌ Erros: {results['customers_to_gestaoclick']['errors']}

🛒 Pedidos (Bagy → GestãoClick):
   ✅ Sucesso: {results['orders_to_gestaoclick']['success']}
   ❌ Erros: {results['orders_to_gestaoclick']['errors']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        self.logger.info(summary)
        
        return results
    
    def get_incomplete_products_statistics(self):
        """
        Retorna estatísticas detalhadas sobre produtos incompletos.
        
        Returns:
            dict: Estatísticas de produtos incompletos, incluindo totais, campos mais frequentes, etc.
        """
        try:
            return self.incomplete_products_storage.get_statistics()
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter estatísticas de produtos incompletos: {str(e)}")
            return {
                'total': 0,
                'campos_frequentes': {},
                'ultima_atualizacao': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': str(e)
            }
            
    def get_all_incomplete_products(self):
        """
        Retorna uma lista completa de todos os produtos incompletos.
        
        Returns:
            dict: Dados de todos os produtos incompletos
        """
        try:
            return self.incomplete_products_storage.get_all_products()
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter lista de produtos incompletos: {str(e)}")
            return {
                'produtos': [],
                'total': 0,
                'ultima_atualizacao': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': str(e)
            }
            
    def clear_incomplete_product(self, product_id):
        """
        Remove um produto específico da lista de produtos incompletos.
        Útil quando um produto foi corrigido manualmente.
        
        Args:
            product_id (str): ID do produto a remover
            
        Returns:
            bool: True se o produto foi removido com sucesso, False caso contrário
        """
        try:
            self.incomplete_products_storage.clear_product(product_id)
            self.logger.info(f"✅ Produto {product_id} removido da lista de incompletos manualmente")
            return True
        except Exception as e:
            self.logger.error(f"❌ Erro ao remover produto {product_id} da lista de incompletos: {str(e)}")
            return False
            
    def start_scheduled_sync(self, interval_minutes=None):
        """
        Start scheduled synchronization.
        
        Args:
            interval_minutes (int, optional): Sync interval in minutes
        """
        if interval_minutes is None:
            interval_minutes = config.SYNC_INTERVAL_MINUTES
        
        self.logger.info(f"⏱️ Iniciando sincronização agendada a cada {interval_minutes} minutos")
        
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            self.sync_all,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id='bagy_gestaoclick_sync',
            replace_existing=True
        )
        
        # Run an initial sync
        self.logger.info("🔄 Executando sincronização inicial...")
        self.sync_all()
        
        scheduler.start()
        
        try:
            # Keep the main thread alive
            while True:
                time.sleep(60)
        except (KeyboardInterrupt, SystemExit):
            self.logger.info("🛑 Interrompendo sincronização agendada")
            scheduler.shutdown()
