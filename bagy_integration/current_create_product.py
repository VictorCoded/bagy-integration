    def create_product(self, product_data):
        """
        Create a new product in Bagy.
        
        Args:
            product_data (dict): Product data
            
        Returns:
            dict: Created product data
        """
        self.logger.info(f"Creating new product in Bagy: {product_data.get('name', 'Unknown')}")
        
        # Verificar se o produto já existe pelo external_id
        external_id = product_data.get('external_id')
        if external_id:
            existing_product = self.get_product_by_external_id(external_id)
            if existing_product:
                self.logger.info(f"Produto com external_id {external_id} já existe no Bagy (ID: {existing_product.get('id')})")
                return existing_product
        
        # Verificar dimensões
        # Se faltar alguma dimensão, adicionamos valores padrão mínimos aceitos pela API
        if 'depth' not in product_data or 'width' not in product_data or 'height' not in product_data or 'weight' not in product_data:
            self.logger.warning(f"⚠️ Produto com dimensões incompletas será criado com valores mínimos: {product_data.get('name', 'Unknown')}")
            
            # Adicionar valores padrão mínimos para dimensões faltantes
            if 'depth' not in product_data:
                product_data['depth'] = "0.1"
            if 'width' not in product_data:
                product_data['width'] = "0.1"
            if 'height' not in product_data:
                product_data['height'] = "0.1"
            if 'weight' not in product_data:
                product_data['weight'] = "0.1"
        
        # Nova estratégia: criar o produto COM as variações em um único request
        # Não vamos extrair as variações, vamos deixá-las no payload e criar tudo de uma vez
        if 'variations' in product_data:
            variation_count = len(product_data['variations'])
            self.logger.info(f"🧪 [TESTE-VAR] Produto contém {variation_count} variações")
            
            # Log detalhado da primeira variação para diagnóstico
            if variation_count > 0:
                first_variation = product_data['variations'][0]
                self.logger.info(f"🧪 [TESTE-VAR] Primeira variação: {first_variation}")
                
            # Validar variações para garantir que estão corretas
            for i, variation in enumerate(product_data['variations']):
                # Log das variações para diagnóstico
                self.logger.info(f"🧪 [TESTE-VAR] Variação {i+1}: ID={variation.get('external_id')}, SKU={variation.get('sku')}")
                
                # Remover qualquer atributo attributes que possa estar nas variações
                if 'attributes' in variation:
                    self.logger.info(f"🧪 [TESTE-VAR] Removendo campo 'attributes' da variação {i+1}")
                    del variation['attributes']
                
                # Remover campos problemáticos relacionados a cores se estiverem vazios
                if 'attribute_value_id' in variation and not variation['attribute_value_id']:
                    self.logger.info(f"🧪 [TESTE-VAR] Removendo campo 'attribute_value_id' vazio da variação {i+1}")
                    del variation['attribute_value_id']
                    
                # Garantir que campos críticos estejam presentes
                if 'external_id' not in variation or not variation['external_id']:
                    self.logger.warning(f"⚠️ Campo 'external_id' ausente na variação {i+1}, adicionando um ID padrão")
                    variation['external_id'] = f"{product_data.get('external_id')}-var-{i+1}"
                    
                if 'sku' not in variation or not variation['sku']:
                    self.logger.warning(f"⚠️ Campo 'sku' ausente na variação {i+1}, adicionando um SKU padrão")
                    variation['sku'] = f"{product_data.get('sku')}-var-{i+1}" if product_data.get('sku') else f"var-{i+1}"
                    
                # Garantir que campos booleanos estejam como true/false e não 1/0
                if 'active' in variation:
                    variation['active'] = True if variation['active'] else False
        
        # ABORDAGEM REVISADA: Para produtos com variações, criar PRIMEIRO o produto BASE, depois as variações
        # A API exige que variações tenham um product_id, não podemos criar variações independentes
        
        # Verificar se é um produto com variações
        original_variations = []
        
        if product_data.get('type') == "variant" and 'variations' in product_data and product_data['variations']:
            original_variations = product_data['variations']
            self.logger.info(f"🔄 ABORDAGEM REVISADA: Primeiro criar o produto base, depois as variações")
            self.logger.info(f"🧪 [TESTE-VAR] Produto contém {len(original_variations)} variações")
            
            # Salvar as variações originais e removê-las temporariamente
            self.logger.info(f"🧪 [TESTE-VAR] Removendo variações temporariamente do payload para criar primeiro o produto base")
            product_data['variations'] = []
        
        elif 'variations' in product_data:
            # Para produtos do tipo "simple", simplesmente removemos as variações
            self.logger.info(f"🔍 Produto simples: removendo {len(product_data['variations'])} variações sem processar")
            product_data['variations'] = []
        
        # Log para depuração dos campos SKU e Reference
        if 'sku' in product_data:
            self.logger.info(f"🔍 Enviando produto com SKU: '{product_data.get('sku')}'")
        if 'reference' in product_data:
            self.logger.info(f"🔍 Enviando produto com Reference: '{product_data.get('reference')}'")
            
        # CORREÇÃO: Garantir que os campos de código estejam como strings
        for codigo_field in ['sku', 'reference', 'code']:
            if codigo_field in product_data and product_data[codigo_field] is not None:
                # Garantir que seja uma string, mesmo que venha como número
                product_data[codigo_field] = str(product_data[codigo_field])
                self.logger.info(f"🔧 Garantindo que {codigo_field} seja string: '{product_data[codigo_field]}'")
            
        # Agora criamos o produto base
        response = self._make_request(
            method="POST", 
            endpoint="/products",
            data=product_data,
            headers=self._get_headers()
        )
        
        # Verificar se o produto foi criado com sucesso
        if response and 'id' in response:
            product_id = response['id']
            self.logger.info(f"Produto criado com sucesso (ID: {product_id})")
            
            # Se temos variações, adicioná-las uma a uma
            if original_variations:
                successful_variations = 0
                
                for i, variation in enumerate(original_variations):
                    # Adicionar o product_id à variação
                    variation['product_id'] = product_id
                    
                    self.logger.info(f"🧪 [TESTE-VAR] Adicionando variação {i+1}/{len(original_variations)} ao produto {product_id}")
                    
                    # Garantir campos booleanos corretos
                    if 'active' in variation:
                        variation['active'] = True if variation['active'] else False
                    
                    # Verificar se devemos remover os atributos para evitar o erro color_attribute_already_exists
                    has_color_attribute = False
                    if 'attributes' in variation:
                        for attr in variation['attributes']:
                            if attr.get('name', '').lower() in ['cor', 'color', 'opcao', 'opção', 'option']:
                                has_color_attribute = True
                                break
                    
                    # Se for um atributo de cor, remover para evitar conflitos
                    if has_color_attribute:
                        variation_copy = variation.copy()
                        if 'attributes' in variation_copy:
                            self.logger.info(f"🔧 Removendo atributos de cor para evitar conflitos")
                            del variation_copy['attributes']
                        try_data = variation_copy
                    else:
                        try_data = variation.copy()  # Usar cópia para evitar alterações no objeto original
                    
                    # Garantir que a variação tenha todos os campos críticos
                    # 1. SKU (código do produto)
                    if not try_data.get('sku'):
                        if try_data.get('reference'):
                            self.logger.info(f"🔧 Usando reference como sku para a variação")
                            try_data['sku'] = try_data['reference']
                        else:
                            self.logger.warning(f"⚠️ SKU e reference ausentes, usando ID como fallback")
                            try_data['sku'] = try_data.get('external_id') or f"var-{i+1}"
                    
                    # 2. Reference (código interno/referência)
                    if not try_data.get('reference'):
                        self.logger.info(f"🔧 Usando sku como reference para a variação")
                        try_data['reference'] = try_data['sku']
                    
                    # 3. Code (código adicional para compatibilidade com API mais recente)
                    if not try_data.get('code'):
                        self.logger.info(f"🔧 Campo 'code' ausente, usando sku")
                        try_data['code'] = try_data['sku']
                    
                    # 4. Balance (estoque)
                    if 'balance' not in try_data:
                        self.logger.warning(f"⚠️ Campo 'balance' (estoque) ausente, definindo como 0")
                        try_data['balance'] = 0
                    
                    # Log detalhado da variação com todos os campos críticos
                    self.logger.info(f"🔍 CAMPOS CRÍTICOS PARA VARIAÇÃO: SKU='{try_data['sku']}', REF='{try_data['reference']}', CODE='{try_data['code']}', ESTOQUE={try_data['balance']}")
                    
                    try:
                        # Verificar de forma completa se todos os campos críticos existem
                        critical_fields = ['sku', 'reference', 'code', 'balance']
                        
                        for field in critical_fields:
                            if field not in try_data or try_data[field] is None:
                                if field in ['sku', 'reference', 'code']:
                                    # Usar um valor padrão para campos de texto baseado no ID da variação
                                    default_value = f"var-{i+1}"
                                    try_data[field] = default_value
                                    self.logger.warning(f"⚠️ Campo '{field}' ausente ou nulo. Definindo como '{default_value}'")
                                elif field == 'balance':
                                    # Para o estoque, usar 0 como padrão
                                    try_data[field] = 0
                                    self.logger.warning(f"⚠️ Campo 'balance' ausente ou nulo. Definindo como 0")
                        
                        # CORREÇÃO: Garantir que os campos de código estejam como strings para variações também
                        for codigo_field in ['sku', 'reference', 'code']:
                            if codigo_field in try_data and try_data[codigo_field] is not None:
                                # Garantir que seja uma string, mesmo que venha como número
                                try_data[codigo_field] = str(try_data[codigo_field])
                                self.logger.info(f"🔧 Garantindo que {codigo_field} da variação seja string: '{try_data[codigo_field]}'")
                        
                        # Verificação final dos campos críticos para o log
                        self.logger.info(f"🔍 VERIFICAÇÃO FINAL PRÉ-ENVIO: SKU='{try_data['sku']}', REF='{try_data['reference']}', CODE='{try_data['code']}', ESTOQUE={try_data['balance']}")
                        
                        # Criar variação com product_id
                        variation_response = self._make_request(
                            method="POST",
                            endpoint="/variations",
                            data=try_data,
                            headers=self._get_headers()
                        )
                        
                        if variation_response and 'id' in variation_response:
                            self.logger.info(f"✅ Variação {i+1} criada com sucesso (ID: {variation_response['id']})")
                            successful_variations += 1
                        else:
                            self.logger.warning(f"⚠️ Falha ao criar variação {i+1}. Resposta: {variation_response}")
                    
                    except Exception as e:
                        # Se falhar por conta do erro de atributo de cor, tentar novamente sem esses atributos
                        if "color_attribute_already_exists" in str(e) and 'attributes' in variation:
                            self.logger.warning(f"⚠️ Erro color_attribute_already_exists - tentando novamente sem atributos")
                            # Tentar criar novamente sem os atributos
                            try:
                                variation_without_attrs = variation.copy()
                                del variation_without_attrs['attributes']
                                
                                # Verificar e garantir que os campos críticos estejam presentes
                                self.logger.info(f"🔍 Verificando campos críticos para segunda tentativa de criação")
                                
                                # Garantir que o SKU esteja presente e não seja vazio
                                if not variation_without_attrs.get('sku'):
                                    variation_without_attrs['sku'] = variation_without_attrs.get('reference') or f"var-{i+1}"
                                    self.logger.warning(f"⚠️ Campo 'sku' ausente na variação, definindo como '{variation_without_attrs['sku']}'")
                                
                                # Garantir que a referência (código interno) esteja presente
                                if not variation_without_attrs.get('reference'):
                                    variation_without_attrs['reference'] = variation_without_attrs.get('sku')
                                    self.logger.warning(f"⚠️ Campo 'reference' ausente na variação, definindo como '{variation_without_attrs['reference']}'")
                                
                                # Garantir que o code (código do produto) esteja presente
                                if not variation_without_attrs.get('code'):
                                    variation_without_attrs['code'] = variation_without_attrs.get('sku')
                                    self.logger.warning(f"⚠️ Campo 'code' ausente na variação, definindo como '{variation_without_attrs['code']}'")
                                
                                # Garantir que o estoque esteja presente
                                if 'balance' not in variation_without_attrs:
                                    variation_without_attrs['balance'] = 0
                                    self.logger.warning(f"⚠️ Campo 'balance' (estoque) ausente na variação, definindo como 0")
                                
                                # CORREÇÃO: Garantir que os campos de código estejam como strings para variações também
                                for codigo_field in ['sku', 'reference', 'code']:
                                    if codigo_field in variation_without_attrs and variation_without_attrs[codigo_field] is not None:
                                        # Garantir que seja uma string, mesmo que venha como número
                                        variation_without_attrs[codigo_field] = str(variation_without_attrs[codigo_field])
                                        self.logger.info(f"🔧 Garantindo que {codigo_field} da variação (segunda tentativa) seja string: '{variation_without_attrs[codigo_field]}'")
                                
                                # Log detalhado dos campos críticos
                                self.logger.info(f"🔍 CAMPOS CRÍTICOS: SKU='{variation_without_attrs['sku']}', REF='{variation_without_attrs['reference']}', CODE='{variation_without_attrs['code']}', ESTOQUE={variation_without_attrs['balance']}")
                                
                                variation_response = self._make_request(
                                    method="POST",
                                    endpoint="/variations",
                                    data=variation_without_attrs,
                                    headers=self._get_headers()
                                )
                                
                                if variation_response and 'id' in variation_response:
                                    self.logger.info(f"✅ Variação {i+1} criada com sucesso na segunda tentativa (ID: {variation_response['id']})")
                                    successful_variations += 1
                            except Exception as e2:
                                self.logger.error(f"❌ Erro na segunda tentativa de criar variação {i+1}: {str(e2)}")
                        else:
                            self.logger.error(f"❌ Erro ao criar variação {i+1}: {str(e)}")
                
                # Atualizar o response com o número de variações criadas
                self.logger.info(f"📊 Resumo: {successful_variations}/{len(original_variations)} variações criadas com sucesso")
                response['variations_count'] = successful_variations
        
        return response
    
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
    
