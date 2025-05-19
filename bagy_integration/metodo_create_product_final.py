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
            
            # Tentar localizar atributo de cor na variação
            if 'attributes' in variation:
                for attr in variation['attributes']:
                    if attr.get('name', '').lower() in ['cor', 'color', 'colour']:
                        color_name = attr.get('value')
                        break
            
            # Se não encontrou atributo de cor, tentar extrair de qualquer atributo
            if not color_name and 'attributes' in variation and variation['attributes']:
                # Usar o primeiro atributo disponível
                color_name = variation['attributes'][0].get('value')
            
            # Se mesmo assim não tiver cor, gerar um nome único
            if not color_name:
                color_name = f"Color-{variation_data.get('sku', f'var-{variation_number}')}"
            
            # Normalizar e validar nome da cor
            if not color_name or len(color_name.strip()) == 0:
                color_name = f"Color-{product_id}-{variation_number}"
            
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