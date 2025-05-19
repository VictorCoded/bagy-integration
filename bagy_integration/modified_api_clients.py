# Início da nova implementação
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
        
        # NOVA ABORDAGEM SEGUNDO SUPORTE BAGY:
        # 1. Para produtos com variações, criar o produto principal PRIMEIRO
        # 2. Depois criar cada variação SEPARADAMENTE
        # 3. Verificar cores existentes para evitar o erro "color_attribute_already_exists"
        
        # Verificar se é um produto com variações
        original_variations = []
        is_variant_product = False
        
        if product_data.get('type') == "variant" and 'variations' in product_data and product_data['variations']:
            is_variant_product = True
            original_variations = product_data['variations'].copy()
            self.logger.info(f"🔍 NOVA ABORDAGEM BAGY: Primeiro criar produto base, depois cada variação separadamente")
            self.logger.info(f"🔍 Produto contém {len(original_variations)} variações que serão criadas separadamente")
            
            # Remover as variações do payload principal (seguindo orientação do suporte Bagy)
            del product_data['variations']
        elif 'variations' in product_data:
            # Para produtos simples, remover as variações
            self.logger.info(f"🔍 Produto simples: removendo {len(product_data.get('variations', []))} variações")
            if 'variations' in product_data:
                del product_data['variations']
        
        # Garantir que campos críticos estejam como strings
        for codigo_field in ['sku', 'reference', 'code']:
            if codigo_field in product_data and product_data[codigo_field] is not None:
                product_data[codigo_field] = str(product_data[codigo_field])
                self.logger.info(f"🔧 Garantindo que {codigo_field} seja string: '{product_data[codigo_field]}'")
        
        # Criar produto principal
        self.logger.info(f"📦 Criando produto principal: {product_data.get('name')}")
        response = self._make_request(
            method="POST", 
            endpoint="/products",
            data=product_data,
            headers=self._get_headers()
        )
        
        # Verificar se o produto foi criado com sucesso
        if response and 'id' in response:
            product_id = response['id']
            self.logger.info(f"✅ Produto principal criado com sucesso (ID: {product_id})")
            
            # Criar variações separadamente, conforme orientação do suporte Bagy
            if is_variant_product and original_variations:
                successful_variations = 0
                
                for i, variation in enumerate(original_variations):
                    # Adicionar o product_id à variação
                    variation['product_id'] = product_id
                    
                    self.logger.info(f"🔄 Criando variação {i+1}/{len(original_variations)} para o produto {product_id}")
                    
                    # IMPORTANTE: Remover atributos da variação para evitar erro de cor já existente
                    variation_data = variation.copy()
                    if 'attributes' in variation_data:
                        self.logger.info(f"🔧 Removendo atributos (attributes) da variação para evitar erro color_attribute_already_exists")
                        del variation_data['attributes']
                    
                    # Garantir campos críticos nas variações como strings
                    for codigo_field in ['sku', 'reference', 'code']:
                        if codigo_field in variation_data and variation_data[codigo_field] is not None:
                            variation_data[codigo_field] = str(variation_data[codigo_field])
                            self.logger.info(f"🔧 Garantindo que {codigo_field} da variação seja string: '{variation_data[codigo_field]}'")
                    
                    # Garantir que a variação tenha um SKU válido
                    if not variation_data.get('sku'):
                        if variation_data.get('reference'):
                            variation_data['sku'] = str(variation_data['reference'])
                        else:
                            variation_data['sku'] = f"var-{product_id}-{i+1}"
                        self.logger.info(f"🔧 Definindo SKU da variação: '{variation_data['sku']}'")
                    
                    # Garantir que a variação tenha uma referência
                    if not variation_data.get('reference'):
                        variation_data['reference'] = variation_data['sku']
                        self.logger.info(f"🔧 Definindo reference da variação: '{variation_data['reference']}'")
                    
                    # Garantir que a variação tenha um código
                    if not variation_data.get('code'):
                        variation_data['code'] = variation_data['sku']
                        self.logger.info(f"🔧 Definindo code da variação: '{variation_data['code']}'")
                    
                    # Garantir que a variação tenha um estoque
                    if 'balance' not in variation_data:
                        variation_data['balance'] = 0
                        self.logger.info(f"🔧 Definindo estoque da variação como 0")
                    
                    try:
                        # Criar variação (sem atributos para evitar erro color_attribute_already_exists)
                        variation_response = self._make_request(
                            method="POST",
                            endpoint="/variations",
                            data=variation_data,
                            headers=self._get_headers()
                        )
                        
                        if variation_response and 'id' in variation_response:
                            self.logger.info(f"✅ Variação {i+1} criada com sucesso (ID: {variation_response['id']})")
                            successful_variations += 1
                        else:
                            self.logger.warning(f"⚠️ Falha ao criar variação {i+1}. Resposta: {variation_response}")
                    
                    except Exception as e:
                        error_msg = str(e)
                        self.logger.error(f"❌ Erro ao criar variação {i+1}: {error_msg}")
                
                self.logger.info(f"✨ Total: {successful_variations} de {len(original_variations)} variações criadas para o produto {product_id}")
                
                # Obter o produto atualizado com todas as variações
                updated_product = self.get_product_by_id(product_id)
                if updated_product:
                    response = updated_product
            
            return response
        else:
            self.logger.error(f"❌ Falha ao criar produto: {product_data.get('name')}. Resposta: {response}")
            return response
# Fim da nova implementação