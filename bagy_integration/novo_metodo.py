    def create_product(self, product_data):
        """
        Create a new product in Bagy.
        
        Args:
            product_data (dict): Product data
            
        Returns:
            dict: Created product data
        """
        # VERIFICAR DIMENSÕES - Essa parte é crítica para garantir que nenhum produto seja rejeitado por falta de dimensões
        for dim in ['height', 'width', 'depth', 'weight']:
            if dim not in product_data or not product_data[dim]:
                product_data[dim] = 0.1
                self.logger.info(f"🔍 Adicionando dimensão mínima padrão: {dim}=0.1")
        
        # GARANTIR SKU E CÓDIGOS - Certeza absoluta de que SKU, reference e code são strings e nunca vazios
        for codigo_field in ['sku', 'reference', 'code']:
            if codigo_field not in product_data or not product_data[codigo_field]:
                # Se não existe, criar um com base no nome do produto ou timestamp
                if 'name' in product_data and product_data['name']:
                    # Gerar SKU baseado no nome do produto (primeiros 8 caracteres alfanuméricos + timestamp)
                    import re
                    slug = re.sub(r'[^a-zA-Z0-9]', '', product_data['name'])[:8]
                    timestamp = str(int(time.time()))[-4:]
                    product_data[codigo_field] = f"{slug}-{timestamp}"
                else:
                    # Fallback para timestamp se não tiver nome
                    product_data[codigo_field] = f"PROD-{int(time.time())}"
                
                self.logger.info(f"🔧 Adicionando {codigo_field} gerado automaticamente: '{product_data[codigo_field]}'")
            else:
                # Garantir que seja string
                product_data[codigo_field] = str(product_data[codigo_field])
                self.logger.info(f"🔧 Garantindo que {codigo_field} seja string: '{product_data[codigo_field]}'")
        
        # CRIAR PRODUTO BASE (SIMPLES, SEM VARIAÇÕES)
        self.logger.info(f"Creating new product in Bagy: {product_data.get('name')}")
        
        # Verificar se produto já existe
        external_id = product_data.get('external_id')
        if external_id:
            existing_product = self.get_product_by_external_id(external_id)
            if existing_product:
                self.logger.info(f"✅ Produto já existe com external_id={external_id} (ID: {existing_product.get('id')})")
                return existing_product
        
        # Limpar campos de variações para criar produto base
        has_variations = False
        original_variations = []
        
        if 'variations' in product_data:
            has_variations = True
            original_variations = product_data.pop('variations', [])
            self.logger.info(f"🔍 Produto contém {len(original_variations)} variações que serão criadas separadamente")
        
        # Se produto tem variações, marcar como 'variant', caso contrário 'simple'
        product_data['type'] = 'variant' if has_variations else 'simple'
        
        # CRIAR PRODUTO BASE
        response = self._make_request(
            method="POST",
            endpoint="/products",
            data=product_data,
            headers=self._get_headers()
        )
        
        # SE PRODUTO BASE FOI CRIADO COM SUCESSO
        if response and 'id' in response:
            product_id = response['id']
            self.logger.info(f"✅ Produto principal criado com sucesso (ID: {product_id})")
            
            # SE TEM VARIAÇÕES, CRIA-LAS UMA POR UMA
            if has_variations and len(original_variations) > 0:
                self.logger.info(f"🔄 Criando {len(original_variations)} variações para o produto {product_id}")
                successful_variations = 0
                
                # OBTER LISTA DE CORES EXISTENTES PARA CACHE
                colors_cache = {}
                try:
                    colors_response = self.get_colors()
                    if colors_response and 'data' in colors_response:
                        for color in colors_response['data']:
                            colors_cache[color['name'].lower()] = color['id']
                        self.logger.info(f"🎨 Cache de cores carregado com {len(colors_cache)} cores")
                except Exception as e:
                    self.logger.error(f"❌ Erro ao carregar cache de cores: {str(e)}")
                
                # CRIAR CADA VARIAÇÃO INDIVIDUALMENTE
                for i, variation in enumerate(original_variations):
                    self.logger.info(f"🔄 Criando variação {i+1}/{len(original_variations)}")
                    
                    # PREPARAR PAYLOAD DA VARIAÇÃO SIMPLIFICADO
                    variation_payload = {
                        "product_id": product_id,  # ID do produto base
                    }
                    
                    # GARANTIR QUE EXTERNAL_ID SEJA DEFINIDO
                    if 'external_id' in variation and variation['external_id']:
                        variation_payload['external_id'] = str(variation['external_id'])
                    else:
                        variation_payload['external_id'] = f"{product_data.get('external_id', '')}-var-{i+1}" if 'external_id' in product_data else f"{product_id}-var-{i+1}"
                            
                    # GARANTIR CAMPOS DE CÓDIGO
                    for codigo_field in ['sku', 'reference', 'code']:
                        # Prioridade 1: Valor da variação
                        if codigo_field in variation and variation[codigo_field]:
                            variation_payload[codigo_field] = str(variation[codigo_field])
                        # Prioridade 2: Valor do produto base com sufixo
                        elif codigo_field in product_data:
                            variation_payload[codigo_field] = f"{product_data[codigo_field]}-{i+1}"
                        # Prioridade 3: Gerar um novo
                        else:
                            variation_payload[codigo_field] = f"VAR-{product_id}-{i+1}"
                        
                        self.logger.info(f"🔑 Variação {i+1}: Campo {codigo_field} = '{variation_payload[codigo_field]}'")
                    
                    # PREÇOS E ESTOQUE
                    variation_payload['price'] = variation.get('price', product_data.get('price', 0))
                    variation_payload['price_compare'] = variation.get('price_compare', product_data.get('price_compare', 0))
                    variation_payload['balance'] = variation.get('balance', 0)
                    variation_payload['active'] = True
                    
                    # DETERMINAR E CRIAR COR (CRÍTICO PARA A API DA BAGY)
                    nome_cor = None
                    
                    # Estratégia 1: Procurar atributo "Cor" explícito
                    if 'attributes' in variation:
                        for attr in variation['attributes']:
                            if attr.get('name', '').lower() in ['cor', 'color', 'colour']:
                                nome_cor = attr.get('value')
                                self.logger.info(f"🎨 Usando atributo 'Cor' explícito: '{nome_cor}'")
                                break
                    
                    # Estratégia 2: Usar qualquer atributo como nome de cor
                    if not nome_cor and 'attributes' in variation and variation['attributes']:
                        nome_cor = variation['attributes'][0].get('value')
                        self.logger.info(f"🎨 Usando primeiro atributo como cor: '{nome_cor}'")
                    
                    # Estratégia 3: Gerar nome único baseado no SKU
                    if not nome_cor:
                        nome_cor = f"Cor-{variation_payload.get('sku', f'var-{i}')}"
                        self.logger.info(f"🎨 Gerando nome de cor baseado no SKU: '{nome_cor}'")
                    
                    # BUSCAR OU CRIAR A COR NA API
                    cor_id = None
                    nome_cor_lower = nome_cor.lower() if nome_cor else "default"
                    
                    # Verificar no cache primeiro (mais rápido)
                    if nome_cor_lower in colors_cache:
                        cor_id = colors_cache[nome_cor_lower]
                        self.logger.info(f"🎨 Cor encontrada no cache: '{nome_cor}' (ID: {cor_id})")
                    else:
                        # Criar nova cor
                        try:
                            cor_payload = {
                                "name": nome_cor,
                                "hexadecimal": "#000000",  # Default para preto
                                "active": True
                            }
                            
                            cor_resposta = self._make_request(
                                method="POST",
                                endpoint="/colors",
                                data=cor_payload,
                                headers=self._get_headers()
                            )
                            
                            if cor_resposta and 'id' in cor_resposta:
                                cor_id = cor_resposta['id']
                                colors_cache[nome_cor_lower] = cor_id
                                self.logger.info(f"🎨 Nova cor criada: '{nome_cor}' (ID: {cor_id})")
                            else:
                                self.logger.error(f"❌ Falha ao criar cor '{nome_cor}': {cor_resposta}")
                        except Exception as e:
                            self.logger.error(f"❌ Erro ao criar cor '{nome_cor}': {str(e)}")
                    
                    # ADICIONAR COLOR_ID (OBRIGATÓRIO PARA A API)
                    if not cor_id:
                        self.logger.error(f"❌ Impossível criar variação sem color_id. Pulando variação {i+1}.")
                        continue
                    
                    variation_payload['color_id'] = cor_id
                    
                    # CRIAR A VARIAÇÃO NA API
                    try:
                        self.logger.info(f"📤 Enviando variação para API: {json.dumps(variation_payload)}")
                        
                        variacao_resposta = self._make_request(
                            method="POST",
                            endpoint="/variations",
                            data=variation_payload,
                            headers=self._get_headers()
                        )
                        
                        if variacao_resposta and 'id' in variacao_resposta:
                            variacao_id = variacao_resposta['id']
                            self.logger.info(f"✅ Variação {i+1} criada com sucesso (ID: {variacao_id})")
                            successful_variations += 1
                        else:
                            self.logger.error(f"❌ Falha ao criar variação {i+1}: {variacao_resposta}")
                            
                    except Exception as e:
                        self.logger.error(f"❌ Erro ao criar variação {i+1}: {str(e)}")
                        import traceback
                        self.logger.error(f"❌ Detalhes: {traceback.format_exc()}")
                
                # RESUMO FINAL
                self.logger.info(f"✨ Total: {successful_variations} de {len(original_variations)} variações criadas com sucesso")
                
                # OBTER PRODUTO COMPLETO ATUALIZADO
                produto_atualizado = self.get_product_by_id(product_id)
                if produto_atualizado:
                    self.logger.info(f"✅ Produto final obtido com todas as variações")
                    return produto_atualizado
            
            return response
        else:
            self.logger.error(f"❌ Falha ao criar produto: {product_data.get('name')}. Resposta: {response}")
            return response