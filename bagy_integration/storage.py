"""
Storage utilities for tracking synchronized entities and preventing duplicates.
Also provides storage for incomplete products that couldn't be synchronized.
"""
import os
import json
import logging
from datetime import datetime
import config

class EntityMapping:
    """
    Manages the mapping between Bagy IDs and GestãoClick IDs to prevent duplicates.
    """
    
    def __init__(self, storage_file=config.ENTITY_MAPPING_FILE):
        self.storage_file = storage_file
        self.logger = logging.getLogger(self.__class__.__name__)
        self.mapping = self._load_mapping()
    
    def _load_mapping(self):
        """
        Load entity mappings from storage file.
        
        Returns:
            dict: Mapping data structure
        """
        default_mapping = {
            'products': {},
            'customers': {},
            'orders': {}
        }
        
        try:
            if os.path.exists(self.storage_file):
                try:
                    with open(self.storage_file, 'r') as f:
                        return json.load(f)
                except json.JSONDecodeError as e:
                    self.logger.error(f"❌ Erro ao ler arquivo de mapeamento (JSON corrompido): {str(e)}")
                    
                    # Arquivo JSON corrompido - criar backup e iniciar novo
                    if os.path.exists(self.storage_file):
                        backup_file = f"{self.storage_file}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
                        try:
                            # Criar backup do arquivo corrompido
                            os.rename(self.storage_file, backup_file)
                            self.logger.info(f"✅ Backup do arquivo de mapeamento corrompido criado: {backup_file}")
                        except Exception as rename_error:
                            self.logger.error(f"❌ Não foi possível criar backup do mapeamento: {str(rename_error)}")
                    
                    # Retornar estrutura padrão
                    return default_mapping
            else:
                return default_mapping
        except Exception as e:
            self.logger.error(f"Error loading entity mapping: {str(e)}")
            return default_mapping
    
    def _save_mapping(self):
        """Save entity mappings to storage file."""
        try:
            # Crie um arquivo temporário para garantir que não corrompemos o arquivo atual
            temp_file = f"{self.storage_file}.tmp"
            os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)
            
            # Escrever primeiro no arquivo temporário
            with open(temp_file, 'w') as f:
                json.dump(self.mapping, f, indent=2)
            
            # Se a escrita for bem-sucedida, renomeie o arquivo temporário para o nome final
            if os.path.exists(self.storage_file):
                # Em sistemas Windows, pode ser necessário remover o arquivo existente antes
                os.replace(temp_file, self.storage_file)
            else:
                os.rename(temp_file, self.storage_file)
                
            self.logger.debug("Arquivo de mapeamento de entidades salvo com sucesso")
        except Exception as e:
            self.logger.error(f"❌ Erro ao salvar mapeamento de entidades: {str(e)}")
    
    def get_gestaoclick_id(self, entity_type, bagy_id):
        """
        Get GestãoClick ID for a given Bagy entity ID.
        
        Args:
            entity_type (str): Type of entity ('products', 'customers', 'orders')
            bagy_id (str): Bagy entity ID
            
        Returns:
            str or None: GestãoClick entity ID if found, None otherwise
        """
        bagy_id = str(bagy_id)
        return self.mapping.get(entity_type, {}).get(bagy_id)
    
    def add_mapping(self, entity_type, bagy_id, gestaoclick_id):
        """
        Add a new mapping between Bagy and GestãoClick IDs.
        
        Args:
            entity_type (str): Type of entity ('products', 'customers', 'orders')
            bagy_id (str): Bagy entity ID
            gestaoclick_id (str): GestãoClick entity ID
        """
        bagy_id = str(bagy_id)
        gestaoclick_id = str(gestaoclick_id)
        
        if entity_type not in self.mapping:
            self.mapping[entity_type] = {}
        
        self.mapping[entity_type][bagy_id] = gestaoclick_id
        self._save_mapping()
        self.logger.debug(f"Added mapping: {entity_type} - Bagy ID {bagy_id} -> GestãoClick ID {gestaoclick_id}")


class IncompleteProductsStorage:
    """
    Manages storage of products that couldn't be synchronized due to missing fields.
    Provides methods to add, retrieve and analyze incomplete products.
    """
    
    def __init__(self, storage_file=config.INCOMPLETE_PRODUCTS_FILE):
        self.storage_file = storage_file
        self.logger = logging.getLogger(self.__class__.__name__)
        self.incomplete_products = self._load_products()
    
    def _load_products(self):
        """
        Load incomplete products from storage file.
        
        Returns:
            dict: Incomplete products data structure
        """
        default_data = {
            'products': {},
            'last_update': datetime.now().isoformat(),
            'statistics': {
                'total': 0,
                'missing_description': 0,
                'missing_dimensions': 0,
                'missing_weight': 0,
                'missing_other': 0
            }
        }
        
        try:
            if os.path.exists(self.storage_file):
                try:
                    with open(self.storage_file, 'r') as f:
                        data = json.load(f)
                        return data
                except json.JSONDecodeError as e:
                    self.logger.error(f"❌ Erro ao ler arquivo de produtos incompletos (JSON corrompido): {str(e)}")
                    
                    # Arquivo JSON corrompido - criar backup e iniciar novo
                    if os.path.exists(self.storage_file):
                        backup_file = f"{self.storage_file}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
                        try:
                            # Criar backup do arquivo corrompido
                            os.rename(self.storage_file, backup_file)
                            self.logger.info(f"✅ Backup do arquivo corrompido criado: {backup_file}")
                        except Exception as rename_error:
                            self.logger.error(f"❌ Não foi possível criar backup: {str(rename_error)}")
                    
                    # Retornar estrutura padrão
                    return default_data
            else:
                return default_data
        except Exception as e:
            self.logger.error(f"❌ Erro ao processar arquivo de produtos incompletos: {str(e)}")
            return default_data
    
    def _save_products(self):
        """Save incomplete products to storage file."""
        try:
            # Atualiza estatísticas antes de salvar
            self._update_statistics()
            
            # Crie um arquivo temporário para garantir que não corrompemos o arquivo atual
            temp_file = f"{self.storage_file}.tmp"
            os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)
            
            # Escrever primeiro no arquivo temporário
            with open(temp_file, 'w') as f:
                json.dump(self.incomplete_products, f, indent=2)
            
            # Se a escrita for bem-sucedida, renomeie o arquivo temporário para o nome final
            if os.path.exists(self.storage_file):
                # Em sistemas Windows, pode ser necessário remover o arquivo existente antes
                os.replace(temp_file, self.storage_file)
            else:
                os.rename(temp_file, self.storage_file)
                
            self.logger.debug("Arquivo de produtos incompletos salvo com sucesso")
        except Exception as e:
            self.logger.error(f"❌ Erro ao salvar produtos incompletos: {str(e)}")
    
    def _update_statistics(self):
        """Update statistics about incomplete products."""
        products = self.incomplete_products['products']
        stats = {
            'total': len(products),
            'missing_description': 0,
            'missing_dimensions': 0,
            'missing_weight': 0,
            'missing_other': 0
        }
        
        for product_id, product_data in products.items():
            missing_fields = product_data.get('missing_fields', [])
            if 'descrição' in missing_fields:
                stats['missing_description'] += 1
            if any(field in missing_fields for field in ['altura', 'largura', 'comprimento']):
                stats['missing_dimensions'] += 1
            if 'peso' in missing_fields:
                stats['missing_weight'] += 1
            if any(field not in ['descrição', 'altura', 'largura', 'comprimento', 'peso'] for field in missing_fields):
                stats['missing_other'] += 1
        
        self.incomplete_products['statistics'] = stats
        self.incomplete_products['last_update'] = datetime.now().isoformat()
    
    def add_product(self, product_id, product_name, missing_fields):
        """
        Add a product to the incomplete products storage.
        
        Args:
            product_id (str): GestãoClick product ID
            product_name (str): Product name
            missing_fields (list): List of missing fields
        """
        product_id = str(product_id)
        
        self.incomplete_products['products'][product_id] = {
            'name': product_name,
            'missing_fields': missing_fields,
            'added_at': datetime.now().isoformat()
        }
        
        self._save_products()
        self.logger.info(f"📋 Produto incompleto registrado: {product_name} - Campos faltantes: {', '.join(missing_fields)}")
    
    def get_all_products(self):
        """
        Get all incomplete products.
        
        Returns:
            dict: Incomplete products data
        """
        return self.incomplete_products['products']
    
    def get_statistics(self):
        """
        Get statistics about incomplete products.
        
        Returns:
            dict: Statistics data
        """
        self._update_statistics()
        return self.incomplete_products['statistics']
    
    def clear_product(self, product_id):
        """
        Remove a product from the incomplete products storage.
        
        Args:
            product_id (str): GestãoClick product ID
        """
        product_id = str(product_id)
        
        if product_id in self.incomplete_products['products']:
            del self.incomplete_products['products'][product_id]
            self._save_products()
            self.logger.info(f"Produto removido da lista de incompletos: ID {product_id}")


class SyncHistory:
    """
    Tracks synchronization history to avoid redundant operations.
    """
    
    def __init__(self, storage_file=config.SYNC_HISTORY_FILE):
        self.storage_file = storage_file
        self.logger = logging.getLogger(self.__class__.__name__)
        self.history = self._load_history()
    
    def _load_history(self):
        """
        Load sync history from storage file.
        
        Returns:
            dict: Sync history data structure
        """
        default_history = {
            'products': {},
            'customers': {},
            'orders': {}
        }
        
        try:
            if os.path.exists(self.storage_file):
                try:
                    with open(self.storage_file, 'r') as f:
                        return json.load(f)
                except json.JSONDecodeError as e:
                    self.logger.error(f"❌ Erro ao ler arquivo de histórico de sincronização (JSON corrompido): {str(e)}")
                    
                    # Arquivo JSON corrompido - criar backup e iniciar novo
                    if os.path.exists(self.storage_file):
                        backup_file = f"{self.storage_file}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
                        try:
                            # Criar backup do arquivo corrompido
                            os.rename(self.storage_file, backup_file)
                            self.logger.info(f"✅ Backup do arquivo de histórico corrompido criado: {backup_file}")
                        except Exception as rename_error:
                            self.logger.error(f"❌ Não foi possível criar backup do histórico: {str(rename_error)}")
                    
                    # Retornar estrutura padrão
                    return default_history
            else:
                return default_history
        except Exception as e:
            self.logger.error(f"Error loading sync history: {str(e)}")
            return default_history
    
    def _save_history(self):
        """Save sync history to storage file."""
        try:
            # Crie um arquivo temporário para garantir que não corrompemos o arquivo atual
            temp_file = f"{self.storage_file}.tmp"
            os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)
            
            # Escrever primeiro no arquivo temporário
            with open(temp_file, 'w') as f:
                json.dump(self.history, f, indent=2)
            
            # Se a escrita for bem-sucedida, renomeie o arquivo temporário para o nome final
            if os.path.exists(self.storage_file):
                # Em sistemas Windows, pode ser necessário remover o arquivo existente antes
                os.replace(temp_file, self.storage_file)
            else:
                os.rename(temp_file, self.storage_file)
                
            self.logger.debug("Arquivo de histórico de sincronização salvo com sucesso")
        except Exception as e:
            self.logger.error(f"❌ Erro ao salvar histórico de sincronização: {str(e)}")
    
    def get_last_sync(self, entity_type, entity_id):
        """
        Get last sync timestamp for an entity.
        
        Args:
            entity_type (str): Type of entity ('products', 'customers', 'orders')
            entity_id (str): Entity ID
            
        Returns:
            str or None: Last sync timestamp if found, None otherwise
        """
        entity_id = str(entity_id)
        return self.history.get(entity_type, {}).get(entity_id, {}).get('last_sync')
    
    def get_version(self, entity_type, entity_id):
        """
        Get last synced entity version.
        
        Args:
            entity_type (str): Type of entity ('products', 'customers', 'orders')
            entity_id (str): Entity ID
            
        Returns:
            str or None: Entity version if found, None otherwise
        """
        entity_id = str(entity_id)
        return self.history.get(entity_type, {}).get(entity_id, {}).get('version')
    
    def update_sync(self, entity_type, entity_id, version=None):
        """
        Update sync history for an entity.
        
        Args:
            entity_type (str): Type of entity ('products', 'customers', 'orders')
            entity_id (str): Entity ID
            version (str, optional): Entity version
        """
        entity_id = str(entity_id)
        
        if entity_type not in self.history:
            self.history[entity_type] = {}
        
        if entity_id not in self.history[entity_type]:
            self.history[entity_type][entity_id] = {}
        
        self.history[entity_type][entity_id]['last_sync'] = datetime.now().isoformat()
        
        if version is not None:
            self.history[entity_type][entity_id]['version'] = str(version)
        
        self._save_history()
        self.logger.debug(f"Updated sync history: {entity_type} - ID {entity_id}")
    
    def should_sync(self, entity_type, entity_id, current_version=None):
        """
        Determine if an entity should be synchronized.
        
        Args:
            entity_type (str): Type of entity ('products', 'customers', 'orders')
            entity_id (str): Entity ID
            current_version (str, optional): Current entity version
            
        Returns:
            bool: True if the entity should be synchronized, False otherwise
        """
        entity_id = str(entity_id)
        
        # If entity has never been synced, sync it
        if not self.get_last_sync(entity_type, entity_id):
            return True
        
        # If version is provided, compare with stored version
        if current_version is not None:
            stored_version = self.get_version(entity_type, entity_id)
            return stored_version != current_version
        
        return False
