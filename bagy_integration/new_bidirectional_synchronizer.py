"""
Nova implementação do sincronizador bidirecional com suporte a conversão
de variações como produtos independentes.
Otimizado para execução contínua 24/7 em serviço de hospedagem.
"""
import logging
import time
import json
from datetime import datetime, timedelta
from threading import Thread, Event
import traceback

from new_product_converter import ProductConverter
from storage import IncompleteProductsStorage, EntityMapping, SyncHistory
from datetime import datetime

class BidirectionalSynchronizer:
    """
    Sincronizador bidirecional entre GestãoClick e Bagy,
    com suporte para converter variações em produtos independentes.
    """

    def __init__(self, gestaoclick_client, bagy_client, storage_dir='./data'):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.gc_client = gestaoclick_client
        self.bagy_client = bagy_client

        # Armazenamento persistente
        self.incomplete_products = IncompleteProductsStorage(f"{storage_dir}/incomplete_products.json")
        self.entity_mapping = EntityMappingStorage(f"{storage_dir}/entity_mapping.json")
        self.sync_history = SyncHistoryStorage(f"{storage_dir}/sync_history.json")

        # Converter de produtos
        self.product_converter = ProductConverter(incomplete_products_storage=self.incomplete_products)
        
        # Controle de threads para execução contínua
        self._stop_event = Event()
        self._sync_thread = None
        self._sync_interval = 300  # 5 minutos como padrão
        
    def set_sync_interval(self, seconds):
        """
        Definir intervalo de sincronização
        """
        self._sync_interval = max(60, seconds)  # Mínimo de 60 segundos
        self.logger.info(f"⏱️ Intervalo de sincronização definido para {self._sync_interval} segundos")
    
    def start_continuous_sync(self):
        """
        Iniciar thread de sincronização contínua
        """
        if self._sync_thread and self._sync_thread.is_alive():
            self.logger.warning("⚠️ Thread de sincronização já está em execução")
            return
            
        self._stop_event.clear()
        self._sync_thread = Thread(target=self._continuous_sync_worker)
        self._sync_thread.daemon = True
        self._sync_thread.start()
        self.logger.info("🔄 Sincronização contínua iniciada")
    
    def stop_continuous_sync(self):
        """
        Interromper thread de sincronização contínua
        """
        if not self._sync_thread or not self._sync_thread.is_alive():
            self.logger.warning("⚠️ Thread de sincronização não está em execução")
            return
            
        self._stop_event.set()
        self._sync_thread.join(timeout=10)
        self.logger.info("🛑 Sincronização contínua interrompida")
    
    def _continuous_sync_worker(self):
        """
        Worker que executa a sincronização em intervalos regulares
        """
        self.logger.info(f"🔄 Iniciando worker de sincronização contínua (intervalo: {self._sync_interval}s)")
        
        while not self._stop_event.is_set():
            try:
                # Executar sincronização completa
                self.logger.info("🔄 Executando sincronização agendada")
                self.sync_all()
                self.logger.info(f"✅ Sincronização agendada concluída. Próxima em {self._sync_interval} segundos")
            except Exception as e:
                self.logger.error(f"❌ Erro durante sincronização agendada: {str(e)}")
                self.logger.error(traceback.format_exc())
            
            # Aguardar pelo próximo ciclo ou até ser interrompido
            self._stop_event.wait(self._sync_interval)
    
    def run_once(self):
        """
        Executa uma sincronização única e completa
        """
        self.logger.info("🔄 Executando sincronização única completa")
        self.sync_all()
        
    def sync_all(self):
        """
        Executa a sincronização bidirecional completa.
        """
        start_time = get_current_datetime()
        self.logger.info(f"🔄 Iniciando sincronização bidirecional completa em {start_time}")
        
        # Tracking de estatísticas
        stats = {
            'products': {'success': 0, 'errors': 0, 'incomplete': 0},
            'customers': {'success': 0, 'errors': 0},
            'orders': {'success': 0, 'errors': 0},
        }
        
        # Sincronizar produtos da GestãoClick para Bagy
        self.logger.info("📦 Iniciando sincronização de produtos do GestãoClick para Bagy...")
        stats['products'] = self.sync_products_to_bagy()
        
        # Sincronizar clientes da Bagy para GestãoClick
        self.logger.info("👥 Iniciando sincronização de clientes do Bagy para GestãoClick...")
        stats['customers'] = self.sync_customers_to_gestaoclick()
        
        # Sincronizar pedidos da Bagy para GestãoClick
        self.logger.info("🛒 Iniciando sincronização de pedidos do Bagy para GestãoClick...")
        stats['orders'] = self.sync_orders_to_gestaoclick()
        
        # Registrar estatísticas
        end_time = get_current_datetime()
        duration = (end_time - start_time).total_seconds()
        
        self.logger.info(f"✨ Sincronização concluída em {duration:.2f} segundos")
        self.logger.info(f"""
📊 Resumo da sincronização:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🕒 Início: {start_time}
🕕 Fim: {end_time}
⏱️ Duração: {duration:.2f} segundos
📦 Produtos (GestãoClick → Bagy):
   ✅ Sucesso: {stats['products']['success']}
   ❌ Erros: {stats['products']['errors']}
   ⚠️ Incompletos: {stats['products']['incomplete']}
👥 Clientes (Bagy → GestãoClick):
   ✅ Sucesso: {stats['customers']['success']}
   ❌ Erros: {stats['customers']['errors']}
🛒 Pedidos (Bagy → GestãoClick):
   ✅ Sucesso: {stats['orders']['success']}
   ❌ Erros: {stats['orders']['errors']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━""")
        
        # Salvar histórico
        self.sync_history.add_sync_record(
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            duration_seconds=duration,
            success_products=stats['products']['success'],
            error_products=stats['products']['errors'],
            incomplete_products=stats['products']['incomplete'],
            success_customers=stats['customers']['success'],
            error_customers=stats['customers']['errors'],
            success_orders=stats['orders']['success'],
            error_orders=stats['orders']['errors']
        )
        
        return stats

    def sync_products_to_bagy(self):
        """
        Sincroniza produtos da GestãoClick para a Bagy.
        NOVA ESTRATÉGIA: Variações de produtos na GestãoClick se tornam produtos independentes na Bagy.
        
        Returns:
            dict: Estatísticas da sincronização
        """
        stats = {'success': 0, 'errors': 0, 'incomplete': 0}
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
        
        # Inicializar contador de produtos incompletos
        incomplete_count = 0
        
        # Processar cada produto
        for gc_product in all_gestaoclick_products:
            try:
                product_id = gc_product.get('id')
                product_name = gc_product.get('nome', 'Desconhecido')
                
                # NOVA ESTRATÉGIA: Converter cada produto da GestãoClick em um ou mais produtos Bagy
                # (um para cada variação, ou um único se não houver variações)
                bagy_products = self.product_converter.gestaoclick_to_bagy(gc_product)
                
                # Se a conversão falhou (produto incompleto)
                if not bagy_products:
                    self.logger.warning(f"❌ Produto {product_id} não pode ser sincronizado. Campos críticos faltando.")
                    stats['incomplete'] += 1
                    incomplete_count += 1
                    continue
                
                # Processar cada produto convertido (pode ser um único ou múltiplos para variações)
                for bagy_product in bagy_products:
                    try:
                        external_id = bagy_product.get('external_id')
                        
                        # Verificar se é uma variação (external_id contém '-')
                        is_variation = '-' in external_id
                        
                        # Se for uma variação, precisamos verificar se já existe como produto independente
                        if is_variation:
                            # Extrair o ID do produto principal e da variação
                            parts = external_id.split('-')
                            product_id = parts[0]
                            variation_id = parts[1] if len(parts) > 1 else ''
                            
                            # Verificar se esta variação já existe como produto independente
                            existing_product = self.bagy_client.get_product_by_external_id(external_id)
                            
                            if not existing_product:
                                # Variação ainda não existe como produto independente, criar novo
                                self.logger.info(f"📦 Criando variação como produto independente: {bagy_product.get('name')} (external_id: {external_id})")
                                new_product = self.bagy_client.create_product(bagy_product)
                                
                                if new_product and 'id' in new_product:
                                    # Registrar mapeamento
                                    self.entity_mapping.add_mapping(
                                        entity_type='product',
                                        external_id=external_id,
                                        internal_id=new_product['id'],
                                        name=bagy_product.get('name', '')
                                    )
                                    stats['success'] += 1
                                else:
                                    self.logger.error(f"❌ Falha ao criar variação como produto independente: {external_id}")
                                    stats['errors'] += 1
                            else:
                                # Variação já existe como produto independente, atualizar
                                bagy_id = existing_product.get('id')
                                self.logger.info(f"🔄 Atualizando variação como produto independente: {external_id} (Bagy ID: {bagy_id})")
                                
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
                                    'weight': bagy_product.get('weight'),
                                }
                                
                                # Verificar se o SKU precisa ser atualizado
                                current_sku = existing_product.get('sku')
                                new_sku = bagy_product.get('sku')
                                
                                if current_sku != new_sku:
                                    self.logger.info(f"🔄 SKU desatualizado detectado: atual={current_sku}, novo={new_sku}")
                                    if new_sku:
                                        self.logger.info(f"🔄 Atualizando SKU para {new_sku}")
                                        update_data['sku'] = new_sku
                                        update_data['reference'] = new_sku
                                        update_data['code'] = new_sku
                                
                                # Atualizar na Bagy
                                self.bagy_client.update_product(bagy_id, update_data)
                                stats['success'] += 1
                        else:
                            # Produto normal (não é variação)
                            existing_product = self.bagy_client.get_product_by_external_id(external_id)
                            
                            if existing_product:
                                # Produto existe, atualizar
                                bagy_id = existing_product.get('id')
                                self.logger.info(f"🔄 Atualizando produto {external_id} (Bagy ID: {bagy_id})")
                                
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
                                    'weight': bagy_product.get('weight'),
                                }
                                
                                # Verificar se o SKU precisa ser atualizado
                                current_sku = existing_product.get('sku')
                                new_sku = bagy_product.get('sku')
                                
                                if current_sku != new_sku:
                                    self.logger.info(f"🔄 SKU desatualizado detectado: atual={current_sku}, novo={new_sku}")
                                    if new_sku:
                                        self.logger.info(f"🔄 Atualizando SKU para {new_sku}")
                                        update_data['sku'] = new_sku
                                        update_data['reference'] = new_sku
                                        update_data['code'] = new_sku
                                
                                # Atualizar na Bagy
                                self.bagy_client.update_product(bagy_id, update_data)
                                stats['success'] += 1
                                
                            else:
                                # Produto não existe, criar novo
                                self.logger.info(f"📦 Criando novo produto {external_id} no Bagy")
                                new_product = self.bagy_client.create_product(bagy_product)
                                
                                if new_product and 'id' in new_product:
                                    # Registrar mapeamento
                                    self.entity_mapping.add_mapping(
                                        entity_type='product',
                                        external_id=external_id,
                                        internal_id=new_product['id'],
                                        name=bagy_product.get('name', '')
                                    )
                                    stats['success'] += 1
                                else:
                                    self.logger.error(f"❌ Falha ao criar produto {external_id} na Bagy")
                                    stats['errors'] += 1
                            
                    except Exception as e:
                        self.logger.error(f"❌ Erro ao processar produto {external_id}: {str(e)}")
                        stats['errors'] += 1
                
            except Exception as e:
                self.logger.error(f"❌ Erro ao processar produto {gc_product.get('id', 'Desconhecido')}: {str(e)}")
                stats['errors'] += 1
        
        # Atualizar contagem de produtos incompletos nas estatísticas
        stats['incomplete'] = incomplete_count
        
        self.logger.info(f"✨ Sincronização de produtos para Bagy concluída: {stats['success']} com sucesso, {stats['errors']} erros")
        return stats

    def sync_customers_to_gestaoclick(self):
        """
        Sincroniza clientes da Bagy para o GestãoClick.
        
        Returns:
            dict: Estatísticas da sincronização
        """
        stats = {'success': 0, 'errors': 0}
        self.logger.info("🔄 Iniciando sincronização de clientes do Bagy para GestãoClick")
        
        # Obter todos os clientes da Bagy
        all_bagy_customers = []
        
        try:
            # Usar paginação para obter todos os clientes
            pagination = Pagination()
            all_bagy_customers = pagination.get_all_pages(
                fetcher=self.bagy_client.get_customers,
                data_key='data'
            )
            
            self.logger.info(f"👥 Encontrados {len(all_bagy_customers)} clientes no Bagy")
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter clientes do Bagy: {str(e)}")
            stats['errors'] += 1
            return stats
        
        # Processar cada cliente
        for bagy_customer in all_bagy_customers:
            try:
                customer_id = bagy_customer.get('id')
                customer_name = bagy_customer.get('name', 'Desconhecido')
                
                # Verificar se o cliente já existe no GestãoClick pelo documento
                document = bagy_customer.get('document', '')
                if not document:
                    self.logger.warning(f"⚠️ Cliente {customer_name} (ID: {customer_id}) não tem documento, pulando...")
                    continue
                
                existing_customer = self.gc_client.get_customer_by_document(document)
                
                if existing_customer and 'data' in existing_customer and existing_customer['data']:
                    # Cliente existe, atualizar
                    gc_customer_id = existing_customer['data'][0].get('id')
                    self.logger.info(f"🔄 Atualizando cliente {customer_name} (ID GestãoClick: {gc_customer_id})")
                    
                    # Preparar dados para atualização
                    update_data = {
                        'nome': customer_name,
                        'email': bagy_customer.get('email', ''),
                        'cpf_cnpj': document,
                        'telefone': bagy_customer.get('phone', ''),
                        'celular': bagy_customer.get('mobile', ''),
                        'tipo_pessoa': 'PF' if len(document) <= 11 else 'PJ',
                    }
                    
                    # Adicionar endereço, se disponível
                    if 'address' in bagy_customer and bagy_customer['address']:
                        address = bagy_customer['address']
                        update_data.update({
                            'logradouro': address.get('street', ''),
                            'numero': address.get('number', ''),
                            'complemento': address.get('complement', ''),
                            'bairro': address.get('neighborhood', ''),
                            'cidade': address.get('city', ''),
                            'uf': address.get('state', ''),
                            'cep': address.get('zipcode', ''),
                        })
                    
                    # Atualizar no GestãoClick
                    self.gc_client.update_customer(gc_customer_id, update_data)
                    stats['success'] += 1
                    
                else:
                    # Cliente não existe, criar novo
                    self.logger.info(f"👤 Criando novo cliente {customer_name} no GestãoClick")
                    
                    # Preparar dados para criação
                    create_data = {
                        'nome': customer_name,
                        'email': bagy_customer.get('email', ''),
                        'cpf_cnpj': document,
                        'telefone': bagy_customer.get('phone', ''),
                        'celular': bagy_customer.get('mobile', ''),
                        'tipo_pessoa': 'PF' if len(document) <= 11 else 'PJ',
                    }
                    
                    # Adicionar endereço, se disponível
                    if 'address' in bagy_customer and bagy_customer['address']:
                        address = bagy_customer['address']
                        create_data.update({
                            'logradouro': address.get('street', ''),
                            'numero': address.get('number', ''),
                            'complemento': address.get('complement', ''),
                            'bairro': address.get('neighborhood', ''),
                            'cidade': address.get('city', ''),
                            'uf': address.get('state', ''),
                            'cep': address.get('zipcode', ''),
                        })
                    
                    # Criar no GestãoClick
                    new_customer = self.gc_client.create_customer(create_data)
                    
                    if new_customer and 'id' in new_customer:
                        # Registrar mapeamento
                        self.entity_mapping.add_mapping(
                            entity_type='customer',
                            external_id=customer_id,
                            internal_id=new_customer['id'],
                            name=customer_name
                        )
                        stats['success'] += 1
                    else:
                        self.logger.error(f"❌ Falha ao criar cliente {customer_name} no GestãoClick")
                        stats['errors'] += 1
                
            except Exception as e:
                self.logger.error(f"❌ Erro ao processar cliente {bagy_customer.get('id', 'Desconhecido')}: {str(e)}")
                stats['errors'] += 1
        
        self.logger.info(f"✨ Sincronização de clientes concluída: {stats['success']} com sucesso, {stats['errors']} erros")
        return stats

    def sync_orders_to_gestaoclick(self):
        """
        Sincroniza pedidos da Bagy para o GestãoClick.
        
        Returns:
            dict: Estatísticas da sincronização
        """
        stats = {'success': 0, 'errors': 0}
        self.logger.info("🔄 Iniciando sincronização de pedidos do Bagy para GestãoClick")
        
        # Obter todos os pedidos da Bagy
        all_bagy_orders = []
        
        try:
            # Usar paginação para obter todos os pedidos
            pagination = Pagination()
            all_bagy_orders = pagination.get_all_pages(
                fetcher=self.bagy_client.get_orders,
                data_key='data'
            )
            
            self.logger.info(f"🛒 Encontrados {len(all_bagy_orders)} pedidos no Bagy")
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter pedidos do Bagy: {str(e)}")
            stats['errors'] += 1
            return stats
        
        # Processar cada pedido
        for bagy_order in all_bagy_orders:
            try:
                order_id = bagy_order.get('id')
                order_number = bagy_order.get('number', 'Desconhecido')
                
                # Verificar se o pedido já existe no GestãoClick
                external_id = str(order_id)
                existing_order = self.gc_client.get_order_by_external_id(external_id)
                
                if existing_order and 'data' in existing_order and existing_order['data']:
                    # Pedido já existe, pular
                    self.logger.info(f"⏩ Pedido {order_number} (ID: {order_id}) já existe no GestãoClick, pulando...")
                    continue
                
                # Obter detalhes do pedido (completo)
                order_details = self.bagy_client.get_order_by_id(order_id)
                
                if not order_details:
                    self.logger.warning(f"⚠️ Não foi possível obter detalhes do pedido {order_number} (ID: {order_id})")
                    stats['errors'] += 1
                    continue
                
                # Obter cliente do pedido
                customer_id = order_details.get('customer', {}).get('id')
                if not customer_id:
                    self.logger.warning(f"⚠️ Pedido {order_number} (ID: {order_id}) não tem cliente associado")
                    stats['errors'] += 1
                    continue
                
                customer_details = self.bagy_client.get_customer_by_id(customer_id)
                
                if not customer_details:
                    self.logger.warning(f"⚠️ Não foi possível obter detalhes do cliente {customer_id} para o pedido {order_number}")
                    stats['errors'] += 1
                    continue
                
                # Verificar se o cliente existe no GestãoClick
                document = customer_details.get('document', '')
                if not document:
                    self.logger.warning(f"⚠️ Cliente do pedido {order_number} não tem documento, pulando...")
                    stats['errors'] += 1
                    continue
                
                gc_customer = self.gc_client.get_customer_by_document(document)
                
                if not gc_customer or 'data' not in gc_customer or not gc_customer['data']:
                    self.logger.warning(f"⚠️ Cliente do pedido {order_number} não existe no GestãoClick, sincronizando cliente primeiro...")
                    
                    # Criar cliente no GestãoClick
                    customer_data = {
                        'nome': customer_details.get('name', ''),
                        'email': customer_details.get('email', ''),
                        'cpf_cnpj': document,
                        'telefone': customer_details.get('phone', ''),
                        'celular': customer_details.get('mobile', ''),
                        'tipo_pessoa': 'PF' if len(document) <= 11 else 'PJ',
                    }
                    
                    # Adicionar endereço, se disponível
                    if 'address' in customer_details and customer_details['address']:
                        address = customer_details['address']
                        customer_data.update({
                            'logradouro': address.get('street', ''),
                            'numero': address.get('number', ''),
                            'complemento': address.get('complement', ''),
                            'bairro': address.get('neighborhood', ''),
                            'cidade': address.get('city', ''),
                            'uf': address.get('state', ''),
                            'cep': address.get('zipcode', ''),
                        })
                    
                    # Criar no GestãoClick
                    gc_customer = self.gc_client.create_customer(customer_data)
                    
                    if not gc_customer or 'id' not in gc_customer:
                        self.logger.error(f"❌ Falha ao criar cliente para o pedido {order_number} no GestãoClick")
                        stats['errors'] += 1
                        continue
                
                # Obter ID do cliente no GestãoClick
                gc_customer_id = gc_customer['data'][0]['id'] if 'data' in gc_customer else gc_customer['id']
                
                # Preparar itens do pedido
                order_items = []
                for item in order_details.get('items', []):
                    # Obter produto pelo SKU
                    product_sku = item.get('product', {}).get('sku', '')
                    
                    if not product_sku:
                        self.logger.warning(f"⚠️ Item do pedido {order_number} não tem SKU, pulando...")
                        continue
                    
                    # Buscar produto no GestãoClick pelo SKU
                    gc_product = self.gc_client.get_product_by_sku(product_sku)
                    
                    if not gc_product or 'data' not in gc_product or not gc_product['data']:
                        self.logger.warning(f"⚠️ Produto SKU={product_sku} não encontrado no GestãoClick, pulando...")
                        continue
                    
                    gc_product_id = gc_product['data'][0]['id']
                    
                    # Adicionar item ao pedido
                    order_items.append({
                        'codigo_interno': product_sku,
                        'produto_id': gc_product_id,
                        'quantidade': item.get('quantity', 1),
                        'preco_unitario': item.get('price', 0),
                        'preco_total': item.get('total', 0),
                        'desconto': item.get('discount', 0),
                    })
                
                if not order_items:
                    self.logger.warning(f"⚠️ Pedido {order_number} não tem itens válidos, pulando...")
                    stats['errors'] += 1
                    continue
                
                # Preparar dados do pedido para o GestãoClick
                order_data = {
                    'cliente_id': gc_customer_id,
                    'codigo': str(order_id),  # Usar ID do Bagy como referência externa
                    'data': order_details.get('created_at', datetime.now().isoformat()),
                    'forma_pagamento': order_details.get('payment', {}).get('method', 'Cartão'),
                    'status': order_details.get('status', ''),
                    'valor_total': order_details.get('total', 0),
                    'valor_frete': order_details.get('shipping', {}).get('price', 0),
                    'itens': order_items,
                }
                
                # Adicionar endereço de entrega, se disponível
                if 'shipping_address' in order_details and order_details['shipping_address']:
                    address = order_details['shipping_address']
                    order_data.update({
                        'entrega_logradouro': address.get('street', ''),
                        'entrega_numero': address.get('number', ''),
                        'entrega_complemento': address.get('complement', ''),
                        'entrega_bairro': address.get('neighborhood', ''),
                        'entrega_cidade': address.get('city', ''),
                        'entrega_uf': address.get('state', ''),
                        'entrega_cep': address.get('zipcode', ''),
                    })
                
                # Criar pedido no GestãoClick
                self.logger.info(f"🛒 Criando pedido {order_number} (ID: {order_id}) no GestãoClick")
                new_order = self.gc_client.create_order(order_data)
                
                if new_order and 'id' in new_order:
                    # Registrar mapeamento
                    self.entity_mapping.add_mapping(
                        entity_type='order',
                        external_id=str(order_id),
                        internal_id=new_order['id'],
                        name=f"Pedido #{order_number}"
                    )
                    stats['success'] += 1
                else:
                    self.logger.error(f"❌ Falha ao criar pedido {order_number} no GestãoClick")
                    stats['errors'] += 1
                
            except Exception as e:
                self.logger.error(f"❌ Erro ao processar pedido {bagy_order.get('id', 'Desconhecido')}: {str(e)}")
                self.logger.error(traceback.format_exc())
                stats['errors'] += 1
        
        self.logger.info(f"✨ Sincronização de pedidos concluída: {stats['success']} com sucesso, {stats['errors']} erros")
        return stats