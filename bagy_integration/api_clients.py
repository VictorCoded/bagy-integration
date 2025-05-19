"""
API Client implementations for Bagy and GestãoClick APIs.
"""
import logging
import time
import json
import re
import requests
from requests.exceptions import RequestException
import config
from copy import deepcopy

class APIClient:
    """Base API client with common functionality."""
    
    def __init__(self, base_url, retry_count=config.MAX_RETRIES, retry_delay=config.RETRY_DELAY_SECONDS):
        self.base_url = base_url
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _make_request(self, method, endpoint, params=None, data=None, headers=None):
        """
        Make an HTTP request with retry logic.
        
        Args:
            method (str): HTTP method (GET, POST, PUT, etc.)
            endpoint (str): API endpoint to call
            params (dict, optional): Query parameters
            data (dict, optional): Request body data
            headers (dict, optional): HTTP headers
            
        Returns:
            dict: API response data
            
        Raises:
            RequestException: If the request fails after all retries
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        method = method.upper()
        
        for attempt in range(self.retry_count + 1):
            try:
                self.logger.debug(f"Making {method} request to {url} (Attempt {attempt + 1}/{self.retry_count + 1})")
                
                # Log de dados para depuração
                if data and method in ['POST', 'PUT']:
                    self.logger.debug(f"Request body: {json.dumps(data, indent=2)}")
                
                response = requests.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data,
                    headers=headers
                )
                
                # Log de resposta para depuração em caso de erro
                if not response.ok:
                    self.logger.error(f"Response error {response.status_code}: {response.text}")
                
                response.raise_for_status()
                return response.json()
                
            except RequestException as e:
                self.logger.warning(f"Request failed: {str(e)}")
                
                if attempt < self.retry_count:
                    sleep_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    self.logger.info(f"Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                else:
                    self.logger.error(f"Request failed after {self.retry_count + 1} attempts")
                    raise


class BagyClient(APIClient):
    """Client for interacting with Bagy API."""
    
    def __init__(self, api_key):
        super().__init__(config.BAGY_BASE_URL)
        self.api_key = api_key
        # Dicionário para cache de cores para evitar requisições repetidas
        self.color_cache = {}
        
    def _get_headers(self):
        """Get default headers for Bagy API."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
    def get_colors(self):
        """
        Lista todas as cores disponíveis na Bagy.
        
        Returns:
            dict: Lista de cores disponíveis
        """
        self.logger.info("Obtendo lista de cores cadastradas na Bagy")
        return self._make_request(
            method="GET",
            endpoint="/colors",
            headers=self._get_headers()
        )

    def create_color(self, color_data):
        """
        Cria uma nova cor na Bagy.
        
        Args:
            color_data (dict): Dados da cor a ser criada
            
        Returns:
            dict: Dados da cor criada
        """
        self.logger.info(f"Criando cor na Bagy: {color_data.get('name', 'Desconhecido')}")
        
        # Verificar se cor já existe com o mesmo nome
        existing_colors = self.get_colors()
        if existing_colors and 'data' in existing_colors:
            for color in existing_colors['data']:
                if color.get('name').lower() == color_data.get('name', '').lower():
                    self.logger.info(f"Cor com nome {color_data.get('name')} já existe (ID: {color.get('id')})")
                    return color
        
        # Cria uma nova cor se não existir
        response = self._make_request(
            method="POST",
            endpoint="/colors",
            data=color_data,
            headers=self._get_headers()
        )
        
        if response:
            self.logger.info(f"Cor criada com sucesso: {response.get('name', 'Desconhecido')} (ID: {response.get('id')})")
        else:
            self.logger.error(f"Falha ao criar cor: {color_data.get('name', 'Desconhecido')}")
        
        return response

    def ensure_color_exists(self, color_name, hex_color="#000000"):
        """
        Garante que uma cor exista no sistema, criando-a se necessário.
        
        Args:
            color_name (str): Nome da cor
            hex_color (str): Código hexadecimal da cor
            
        Returns:
            int: ID da cor na Bagy
        """
        # Verificar cache primeiro
        if color_name.lower() in self.color_cache:
            self.logger.info(f"Cor {color_name} encontrada no cache (ID: {self.color_cache[color_name.lower()]})")
            return self.color_cache[color_name.lower()]
            
        self.logger.info(f"Verificando se cor {color_name} existe na Bagy")
        
        # Verificar se cor já existe
        existing_colors = self.get_colors()
        if existing_colors and 'data' in existing_colors:
            for color in existing_colors['data']:
                if color.get('name').lower() == color_name.lower():
                    color_id = color.get('id')
                    self.logger.info(f"Cor {color_name} já existe (ID: {color_id})")
                    # Adicionar ao cache
                    self.color_cache[color_name.lower()] = color_id
                    return color_id
        
        # Criar cor se não existir
        color_data = {
            "external_id": None,
            "name": color_name,
            "hexadecimal": hex_color,
            "image": None,
            "position": 99,
            "active": True
        }
        
        response = self.create_color(color_data)
        if response and 'id' in response:
            color_id = response['id']
            # Adicionar ao cache
            self.color_cache[color_name.lower()] = color_id
            return color_id
        else:
            self.logger.error(f"Não foi possível garantir que a cor {color_name} exista")
            return None
    
    def get_products(self, page=1, limit=100):
        """
        Get products from Bagy.
        
        Args:
            page (int): Page number for pagination
            limit (int): Number of products per page
            
        Returns:
            dict: Products data
        """
        self.logger.info(f"Fetching products from Bagy (page {page}, limit {limit})")
        return self._make_request(
            method="GET",
            endpoint="/products",
            params={"page": page, "limit": limit},
            headers=self._get_headers()
        )
    
    def get_customers(self, page=1, limit=100):
        """
        Get customers from Bagy.
        
        Args:
            page (int): Page number for pagination
            limit (int): Number of customers per page
            
        Returns:
            dict: Customers data
        """
        self.logger.info(f"Fetching customers from Bagy (page {page}, limit {limit})")
        return self._make_request(
            method="GET",
            endpoint="/customers",
            params={"page": page, "limit": limit},
            headers=self._get_headers()
        )
    
    def get_orders(self, page=1, limit=100):
        """
        Get orders from Bagy.
        
        Args:
            page (int): Page number for pagination
            limit (int): Number of orders per page
            
        Returns:
            dict: Orders data
        """
        self.logger.info(f"Fetching orders from Bagy (page {page}, limit {limit})")
        return self._make_request(
            method="GET",
            endpoint="/orders",
            params={"page": page, "limit": limit},
            headers=self._get_headers()
        )
        
    def get_categories(self, page=1, limit=100):
        """
        Get categories from Bagy.
        
        Args:
            page (int): Page number for pagination
            limit (int): Number of categories per page
            
        Returns:
            dict: Categories data
        """
        self.logger.info(f"Fetching categories from Bagy (page {page}, limit {limit})")
        return self._make_request(
            method="GET",
            endpoint="/categories",
            params={"page": page, "limit": limit},
            headers=self._get_headers()
        )
    
    def create_category(self, category_data):
        """
        Create a new category in Bagy.
        
        Args:
            category_data (dict): Category data
            
        Returns:
            dict: Created category data
        """
        self.logger.info(f"Creating new category in Bagy: {category_data.get('name', 'Unknown')}")
        return self._make_request(
            method="POST",
            endpoint="/categories",
            data=category_data,
            headers=self._get_headers()
        )
        
    def get_category_by_name(self, name):
        """
        Get a category by name from Bagy.
        
        Args:
            name (str): Category name
            
        Returns:
            dict or None: Category data if found, None otherwise
        """
        self.logger.debug(f"Searching for category with name: {name}")
        try:
            response = self._make_request(
                method="GET",
                endpoint="/categories",
                params={"name": name},
                headers=self._get_headers()
            )
            
            # Check if any category matches the exact name
            if response and 'data' in response and response['data']:
                for category in response['data']:
                    if category.get('name', '').lower() == name.lower():
                        return category
            
            return None
        except Exception as e:
            self.logger.error(f"Error fetching category by name: {str(e)}")
            return None
    
    def get_product_by_id(self, product_id):
        """
        Get a specific product by ID.
        
        Args:
            product_id (str): Product ID
            
        Returns:
            dict: Product data
        """
        self.logger.info(f"Fetching product details for ID: {product_id}")
        return self._make_request(
            method="GET",
            endpoint=f"/products/{product_id}",
            headers=self._get_headers()
        )
        
    def get_product_by_external_id(self, external_id):
        """
        Get a product by external ID from Bagy.
        
        Args:
            external_id (str): External product ID
            
        Returns:
            dict or None: Product data if found, None otherwise
        """
        self.logger.info(f"Buscando produto com external_id: {external_id}")
        
        # Primeiro tenta buscar pelo parâmetro external_id
        try:
            response = self._make_request(
                method="GET",
                endpoint="/products",
                params={"external_id": external_id},
                headers=self._get_headers()
            )
            
            if response and isinstance(response, dict) and response.get('data') and len(response['data']) > 0:
                self.logger.info(f"Produto encontrado com external_id={external_id} (ID: {response['data'][0].get('id')})")
                return response['data'][0]  # Return the first matching product
        except Exception as e:
            self.logger.warning(f"Erro na busca por external_id: {str(e)}")
        
        # Se não encontrou, tenta uma abordagem mais exaustiva buscando em todas as páginas
        self.logger.info(f"Fazendo busca exaustiva por produto com external_id: {external_id}")
        try:
            # Busca em todas as páginas até encontrar o produto
            page = 1
            limit = 100
            max_pages = 10  # Limite para não processar infinitamente
            
            while page <= max_pages:
                response = self._make_request(
                    method="GET",
                    endpoint="/products",
                    params={"page": page, "limit": limit},
                    headers=self._get_headers()
                )
                
                if not response or not isinstance(response, dict) or not response.get('data'):
                    break
                    
                # Procura em cada produto na página
                for product in response['data']:
                    if product.get('external_id') == external_id:
                        self.logger.info(f"Produto encontrado na página {page} com external_id={external_id} (ID: {product.get('id')})")
                        return product
                
                # Se não há mais páginas, sair do loop
                if len(response['data']) < limit:
                    break
                    
                page += 1
                
            self.logger.warning(f"Produto não encontrado com external_id: {external_id} após busca exaustiva")
            return None
        except Exception as e:
            self.logger.warning(f"Erro na busca exaustiva por external_id: {str(e)}")
            return None
    

    def create_product(self, product_data):
        """
        Create a new product in Bagy.
        
        Args:
            product_data (dict): Product data
            
        Returns:
            dict: Created product data
        """
        self.logger.info(f"🚀 Iniciando criação do produto: {product_data.get('name', 'Desconhecido')}")
        
        # Criar cópia profunda para não modificar os dados originais
        data = deepcopy(product_data)
        
        # 1. VERIFICAR SE PRODUTO JÁ EXISTE
        external_id = data.get('external_id')
        if external_id:
            existing_product = self.get_product_by_external_id(external_id)
            if existing_product:
                self.logger.info(f"✅ Produto já existe com external_id={external_id} (ID: {existing_product.get('id')})")
                return existing_product
        
        # 2. VERIFICAR E CORRIGIR DIMENSÕES
        for dimension in ['height', 'width', 'depth', 'weight']:
            if dimension not in data or not data[dimension]:
                data[dimension] = 0.1  # Valor mínimo aceito
                self.logger.info(f"📏 Dimensão '{dimension}' definida automaticamente como 0.1")
        
        # 3. VERIFICAR E CORRIGIR CÓDIGOS (SKU, REFERENCE, CODE)
        unique_suffix = str(int(time.time()))[-6:]  # últimos 6 dígitos do timestamp
        
        for code_field in ['sku', 'reference', 'code']:
            # Se campo não existe ou está vazio
            if code_field not in data or not data[code_field]:
                # Usar nome do produto para gerar um código
                if 'name' in data and data['name']:
                    # Gerar código baseado no nome (clean e uniqueified)
                    name_slug = re.sub(r'[^a-zA-Z0-9]', '', data['name'])[:10]
                    data[code_field] = f"{name_slug}-{unique_suffix}"
                else:
                    # Fallback para ID + timestamp
                    fallback_id = data.get('external_id', 'PROD')
                    data[code_field] = f"{fallback_id}-{unique_suffix}"
                
                self.logger.info(f"🔑 Campo '{code_field}' gerado automaticamente: {data[code_field]}")
            else:
                # Garantir que é string
                data[code_field] = str(data[code_field])
                self.logger.info(f"🔑 Campo '{code_field}' garantido como string: {data[code_field]}")
        
        # 4. VERIFICAR VARIAÇÕES
        has_variations = False
        original_variations = []
        
        if 'variations' in data:
            has_variations = True
            original_variations = data.pop('variations')
            self.logger.info(f"🔄 Produto tem {len(original_variations)} variações que serão criadas separadamente")
        
        # 5. DEFINIR TIPO DO PRODUTO
        data['type'] = 'variant' if has_variations else 'simple'
        
        # 6. CRIAR PRODUTO BASE
        product_response = self._make_request(
            method="POST",
            endpoint="/products",
            data=data,
            headers=self._get_headers()
        )
        
        if not product_response or 'id' not in product_response:
            self.logger.error(f"❌ Falha ao criar produto base: {data.get('name')}. Resposta: {product_response}")
            return None
        
        product_id = product_response['id']
        self.logger.info(f"✅ Produto base criado com sucesso: {data.get('name')} (ID: {product_id})")
        
        # Se não tem variações, retornar produto criado
        if not has_variations or not original_variations:
            return product_response
        
        # 7. PROCESSAR VARIAÇÕES
        successful_variations = 0
        
        # Primeiro carregamos todas as cores existentes no sistema (otimização)
        color_response = self.get_colors()
        color_cache = {}
        
        if color_response and 'data' in color_response:
            for color in color_response['data']:
                color_cache[color['name'].lower()] = color['id']
                
            self.logger.info(f"🎨 Carregadas {len(color_cache)} cores do sistema")
            # Atualizar cache da instância
            self.color_cache = color_cache
        
        # Processar cada variação individualmente
        for i, variation in enumerate(original_variations):
            variation_number = i + 1
            self.logger.info(f"🔄 Processando variação {variation_number}/{len(original_variations)}")
            
            # 7.1. Criar estrutura básica da variação
            variation_data = {
                "product_id": product_id,  # Associar ao produto principal
                "active": True,            # Sempre ativar a variação
            }
            
            # 7.2. Copiar external_id da variação ou gerar
            if 'external_id' in variation and variation['external_id']:
                variation_data['external_id'] = str(variation['external_id'])
            else:
                variation_data['external_id'] = f"{external_id}-var-{variation_number}" if external_id else f"var-{product_id}-{variation_number}"
            
            # 7.3. Garantir SKU, REFERENCE e CODE para a variação
            for code_field in ['sku', 'reference', 'code']:
                if code_field in variation and variation[code_field]:
                    # Usar o valor original da variação, convertido para string
                    variation_data[code_field] = str(variation[code_field])
                elif code_field in data:
                    # Usar o valor do produto principal com sufixo
                    variation_data[code_field] = f"{data[code_field]}-{variation_number}"
                else:
                    # Criar um valor completamente novo
                    variation_data[code_field] = f"var-{product_id}-{variation_number}-{unique_suffix}"
            
            # 7.4. Copiar preço e estoque
            variation_data['price'] = variation.get('price', data.get('price', 0))
            variation_data['price_compare'] = variation.get('price_compare', data.get('price_compare', 0))
            variation_data['balance'] = variation.get('balance', 0)
            
            # 7.5. Obter cor para a variação (PARTE CRÍTICA)
            color_name = None
            
            # ESTRATÉGIA 1: Tentar extrair do nome do produto se for um tipo conhecido
            # Caso especial para Masturbador EGG e similares onde as variações são modelos
            product_name = data.get('name', '').upper()
            sku_code = variation_data.get('sku', '').upper()
            
            # Para produtos tipo EGG que usam nomes de variação como SPIDER, SILKY, etc.
            if 'EGG' in product_name or 'MASTURBADOR' in product_name or sku_code.startswith('EGG'):
                # Tentar extrair do nome da variação (caso esteja disponível)
                if 'name' in variation:
                    # Usar nome da variação como cor
                    var_name = variation['name']
                    if var_name and var_name.strip():
                        color_name = var_name.strip()
                        self.logger.info(f"🎨 Usando nome da variação '{color_name}' como cor")
            
            # ESTRATÉGIA 2: Tentar localizar atributo de cor explícito na variação
            if not color_name and 'attributes' in variation:
                for attr in variation['attributes']:
                    if attr.get('name', '').lower() in ['cor', 'color', 'colour', 'variacao', 'variação', 'modelo', 'tipo']:
                        color_name = attr.get('value')
                        self.logger.info(f"🎨 Usando atributo '{attr.get('name')}' como cor: {color_name}")
                        break
            
            # ESTRATÉGIA 3: Extrair modelo/tipo da variação pelo nome da SKU
            # Ex: EGG0001 = SPIDER, EGG0002 = SILKY
            if not color_name and variation.get('sku') and 'description' in variation:
                # Tentar extrair da descrição (algumas APIs fornecem a variação na descrição)
                desc = variation.get('description', '')
                if desc and len(desc) > 3:
                    # Buscar palavras-chave após o código
                    words = desc.split()
                    if len(words) > 1:
                        # Usar a primeira palavra após o sku como "modelo"
                        color_name = words[1].strip()
                        self.logger.info(f"🎨 Extraindo cor da descrição: '{color_name}'")
            
            # ESTRATÉGIA 4: Se tiver um campo 'variant_name' ou similar
            if not color_name:
                for field in ['variant_name', 'variacao', 'variação', 'modelo', 'tipo', 'variant', 'option']:
                    if field in variation and variation[field]:
                        color_name = variation[field]
                        self.logger.info(f"🎨 Usando campo '{field}' como cor: {color_name}")
                        break
            
            # ESTRATÉGIA 5: Usar qualquer atributo disponível
            if not color_name and 'attributes' in variation and variation['attributes']:
                # Usar o primeiro atributo disponível
                color_name = variation['attributes'][0].get('value')
                self.logger.info(f"🎨 Usando primeiro atributo como cor: {color_name}")
            
            # ESTRATÉGIA 6: FALLBACK - Se mesmo assim não tiver cor, usar código SKU
            if not color_name:
                sku = variation_data.get('sku', '')
                if sku:
                    color_name = f"Modelo-{sku}"
                    self.logger.info(f"🎨 Gerando nome de cor baseado no SKU: {color_name}")
                else:
                    # Último recurso - usar número da variação
                    color_name = f"Modelo-{variation_number}"
                    self.logger.info(f"🎨 Gerando nome de cor baseado no número da variação: {color_name}")
            
            # Garantir que o nome da cor é válido
            if not color_name or len(color_name.strip()) == 0:
                color_name = f"Modelo-{product_id}-{variation_number}"
                self.logger.info(f"🎨 Usando nome padrão para cor: {color_name}")
            
            # 7.6. Obter ID da cor (criar se não existir)
            color_id = None
            color_name_lower = color_name.lower()
            
            # Verificar no cache primeiro
            if color_name_lower in color_cache:
                color_id = color_cache[color_name_lower]
                self.logger.info(f"🎨 Cor encontrada no cache: '{color_name}' (ID: {color_id})")
            else:
                # Criar nova cor
                try:
                    color_payload = {
                        "name": color_name,
                        "hexadecimal": "#000000",  # Preto por padrão
                        "active": True
                    }
                    
                    color_create_response = self._make_request(
                        method="POST",
                        endpoint="/colors",
                        data=color_payload,
                        headers=self._get_headers()
                    )
                    
                    if color_create_response and 'id' in color_create_response:
                        color_id = color_create_response['id']
                        color_cache[color_name_lower] = color_id  # Atualiza cache local
                        self.color_cache[color_name_lower] = color_id  # Atualiza cache de instância
                        self.logger.info(f"🎨 Nova cor criada: '{color_name}' (ID: {color_id})")
                    else:
                        self.logger.error(f"❌ Falha ao criar cor: {color_name}. Resposta: {color_create_response}")
                except Exception as e:
                    self.logger.error(f"❌ Erro ao criar cor '{color_name}': {str(e)}")
            
            # 7.7. Adicionar color_id à variação
            if not color_id:
                self.logger.error(f"❌ Variação {variation_number} não pode ser criada sem ID de cor.")
                continue
                
            variation_data['color_id'] = color_id
            
            # 7.8. Criar variação
            try:
                self.logger.info(f"📤 Criando variação {variation_number} com payload: {json.dumps(variation_data)}")
                
                variation_response = self._make_request(
                    method="POST",
                    endpoint="/variations",
                    data=variation_data,
                    headers=self._get_headers()
                )
                
                if variation_response and 'id' in variation_response:
                    variation_id = variation_response['id']
                    self.logger.info(f"✅ Variação {variation_number} criada com sucesso! (ID: {variation_id})")
                    successful_variations += 1
                else:
                    self.logger.error(f"❌ Falha ao criar variação {variation_number}. Resposta: {variation_response}")
            except Exception as e:
                import traceback
                self.logger.error(f"❌ Erro ao criar variação {variation_number}: {str(e)}")
                self.logger.error(f"❌ Detalhes: {traceback.format_exc()}")
        
        # 8. RESUMO DE CRIAÇÃO DAS VARIAÇÕES
        self.logger.info(f"✨ Criadas {successful_variations} de {len(original_variations)} variações.")
        
        # 9. OBTER PRODUTO COMPLETO COM TODAS AS VARIAÇÕES
        complete_product = self.get_product_by_id(product_id)
        if complete_product:
            return complete_product
        
        return product_response
        
    def update_product(self, product_id, product_data):
        """
        Update a product in Bagy.
        
        Args:
            product_id (str): Product ID
            product_data (dict): Updated product data
            
        Returns:
            dict: Updated product data
        """
        self.logger.info(f"Updating product in Bagy with ID: {product_id}")
        
        # Verificar dimensões para atualização
        # Se faltar alguma dimensão, adicionamos valores padrão mínimos aceitos pela API
        if 'depth' not in product_data or 'width' not in product_data or 'height' not in product_data or 'weight' not in product_data:
            self.logger.warning(f"⚠️ Produto com dimensões incompletas será atualizado com valores mínimos: {product_data.get('name', 'Unknown')}")
            
            # Adicionar valores padrão mínimos para dimensões faltantes
            if 'depth' not in product_data:
                product_data['depth'] = "0.1"
            if 'width' not in product_data:
                product_data['width'] = "0.1"
            if 'height' not in product_data:
                product_data['height'] = "0.1"
            if 'weight' not in product_data:
                product_data['weight'] = "0.1"
        
        # CORREÇÃO: Garantir que os campos de código estejam como strings
        for codigo_field in ['sku', 'reference', 'code']:
            if codigo_field in product_data and product_data[codigo_field] is not None:
                # Garantir que seja uma string, mesmo que venha como número
                product_data[codigo_field] = str(product_data[codigo_field])
                self.logger.info(f"🔧 Garantindo que {codigo_field} (update) seja string: '{product_data[codigo_field]}'")
        
        return self._make_request(
            method="PUT",
            endpoint=f"/products/{product_id}",
            data=product_data,
            headers=self._get_headers()
        )
    
    def get_customer_by_id(self, customer_id):
        """
        Get a specific customer by ID.
        
        Args:
            customer_id (str): Customer ID
            
        Returns:
            dict: Customer data
        """
        self.logger.info(f"Fetching customer details for ID: {customer_id}")
        return self._make_request(
            method="GET",
            endpoint=f"/customers/{customer_id}",
            headers=self._get_headers()
        )
    
    def get_order_by_id(self, order_id):
        """
        Get a specific order by ID.
        
        Args:
            order_id (str): Order ID
            
        Returns:
            dict: Order data
        """
        self.logger.info(f"Fetching order details for ID: {order_id}")
        return self._make_request(
            method="GET",
            endpoint=f"/orders/{order_id}",
            headers=self._get_headers()
        )


class GestaoClickClient(APIClient):
    """Client for interacting with GestãoClick API."""
    
    def __init__(self, api_key, secret_key):
        super().__init__(config.GESTAOCLICK_BASE_URL)
        self.api_key = api_key
        self.secret_key = secret_key
    
    def _get_headers(self):
        """Get default headers for GestãoClick API."""
        return {
            "Content-Type": "application/json",
            "access-token": self.api_key,
            "secret-access-token": self.secret_key
        }
    
    def get_products(self, page=1, limit=100):
        """
        Get products from GestãoClick.
        
        Args:
            page (int): Page number for pagination
            limit (int): Number of products per page
            
        Returns:
            dict: Products data
        """
        self.logger.info(f"Fetching products from GestãoClick (page {page}, limit {limit})")
        # De acordo com a documentação, a API usa 'pagina' e 'limite' como parâmetros de paginação
        return self._make_request(
            method="GET",
            endpoint="produtos",
            params={"pagina": page, "limite": limit},
            headers=self._get_headers()
        )
    
    def get_product_by_sku(self, sku):
        """
        Get a product by SKU from GestãoClick.
        
        Args:
            sku (str): Product SKU
            
        Returns:
            dict: Product data or None if not found
        """
        self.logger.info(f"Searching for product with SKU: {sku}")
        try:
            return self._make_request(
                method="GET",
                endpoint="produtos",
                params={"codigo_interno": sku},
                headers=self._get_headers()
            )
        except RequestException:
            return None
    
    def create_product(self, product_data):
        """
        Create a new product in GestãoClick.
        
        Args:
            product_data (dict): Product data
            
        Returns:
            dict: Created product data
        """
        self.logger.info(f"Creating product: {product_data.get('nome', 'Unknown')}")
        return self._make_request(
            method="POST",
            endpoint="produtos",
            data=product_data,
            headers=self._get_headers()
        )
    
    def update_product(self, product_id, product_data):
        """
        Update a product in GestãoClick.
        
        Args:
            product_id (str): Product ID
            product_data (dict): Updated product data
            
        Returns:
            dict: Updated product data
        """
        self.logger.info(f"Updating product with ID: {product_id}")
        return self._make_request(
            method="PUT",
            endpoint=f"produtos/{product_id}",
            data=product_data,
            headers=self._get_headers()
        )
    
    def get_customers(self, page=1, limit=100):
        """
        Get customers from GestãoClick.
        
        Args:
            page (int): Page number for pagination
            limit (int): Number of customers per page
            
        Returns:
            dict: Customers data
        """
        self.logger.info(f"Fetching customers from GestãoClick (page {page}, limit {limit})")
        return self._make_request(
            method="GET",
            endpoint="clientes",
            params={"pagina": page, "limite": limit},
            headers=self._get_headers()
        )
    
    def get_customer_by_document(self, document):
        """
        Get a customer by document (CPF/CNPJ) from GestãoClick.
        
        Args:
            document (str): Customer document number
            
        Returns:
            dict: Customer data or None if not found
        """
        self.logger.info(f"Searching for customer with document: {document}")
        try:
            return self._make_request(
                method="GET",
                endpoint="clientes",
                params={"cpf_cnpj": document},
                headers=self._get_headers()
            )
        except RequestException:
            return None
    
    def get_customer_by_email(self, email):
        """
        Get a customer by email from GestãoClick.
        
        Args:
            email (str): Customer email
            
        Returns:
            dict: Customer data or None if not found
        """
        self.logger.info(f"Searching for customer with email: {email}")
        try:
            return self._make_request(
                method="GET",
                endpoint="clientes",
                params={"email": email},
                headers=self._get_headers()
            )
        except RequestException:
            return None
    
    def create_customer(self, customer_data):
        """
        Create a new customer in GestãoClick.
        
        Args:
            customer_data (dict): Customer data
            
        Returns:
            dict: Created customer data
        """
        self.logger.info(f"Creating customer: {customer_data.get('nome', 'Unknown')}")
        
        # Verificar e garantir que tipo_pessoa seja 'PF' ou 'PJ'
        if 'tipo_pessoa' in customer_data:
            if customer_data['tipo_pessoa'] not in ['PF', 'PJ']:
                documento = customer_data.get('cpf_cnpj', '')
                customer_data['tipo_pessoa'] = 'PF' if len(documento) <= 11 else 'PJ'
        
        return self._make_request(
            method="POST",
            endpoint="clientes",
            data=customer_data,
            headers=self._get_headers()
        )
    
    def update_customer(self, customer_id, customer_data):
        """
        Update a customer in GestãoClick.
        
        Args:
            customer_id (str): Customer ID
            customer_data (dict): Updated customer data
            
        Returns:
            dict: Updated customer data
        """
        self.logger.info(f"Updating customer with ID: {customer_id}")
        # Verificar e garantir que tipo_pessoa seja 'PF' ou 'PJ'
        if 'tipo_pessoa' in customer_data:
            if customer_data['tipo_pessoa'] not in ['PF', 'PJ']:
                documento = customer_data.get('cpf_cnpj', '')
                customer_data['tipo_pessoa'] = 'PF' if len(documento) <= 11 else 'PJ'
        
        return self._make_request(
            method="PUT",
            endpoint=f"clientes/{customer_id}",
            data=customer_data,
            headers=self._get_headers()
        )
    
    def get_orders(self, page=1, limit=100):
        """
        Get orders from GestãoClick.
        
        Args:
            page (int): Page number for pagination
            limit (int): Number of orders per page
            
        Returns:
            dict: Orders data
        """
        self.logger.info(f"Fetching orders from GestãoClick (page {page}, limit {limit})")
        return self._make_request(
            method="GET",
            endpoint="vendas",
            params={"pagina": page, "limite": limit},
            headers=self._get_headers()
        )
    
    def get_order_by_external_id(self, external_id):
        """
        Get an order by external ID from GestãoClick.
        
        Args:
            external_id (str): External order ID
            
        Returns:
            dict: Order data or None if not found
        """
        self.logger.info(f"Searching for order with external ID: {external_id}")
        try:
            return self._make_request(
                method="GET",
                endpoint="vendas",
                params={"codigo": external_id},
                headers=self._get_headers()
            )
        except RequestException:
            return None
    
    def create_order(self, order_data):
        """
        Create a new order in GestãoClick.
        
        Args:
            order_data (dict): Order data
            
        Returns:
            dict: Created order data
        """
        self.logger.info(f"Creating order with external ID: {order_data.get('codigo', 'Unknown')}")
        return self._make_request(
            method="POST",
            endpoint="vendas",
            data=order_data,
            headers=self._get_headers()
        )
    
    def update_order(self, order_id, order_data):
        """
        Update an order in GestãoClick.
        
        Args:
            order_id (str): Order ID
            order_data (dict): Updated order data
            
        Returns:
            dict: Updated order data
        """
        self.logger.info(f"Updating order with ID: {order_id}")
        return self._make_request(
            method="PUT",
            endpoint=f"vendas/{order_id}",
            data=order_data,
            headers=self._get_headers()
        )
