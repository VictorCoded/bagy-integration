"""
Implementação final e otimizada do método create_product para o BagyClient,
que resolve definitivamente os problemas com variações e SKUs.
"""

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
                    variation_payload['external_id'] = variation['external_id']
                else:
                    variation_payload['external_id'] = f"{product_id}-var-{i+1}"
                
                # GARANTIR CAMPOS DE CÓDIGO
                for codigo_field in ['sku', 'reference', 'code']:
                    if codigo_field in variation and variation[codigo_field]:
                        variation_payload[codigo_field] = str(variation[codigo_field])
                    else:
                        # Se não existe no original, copiar do produto base com sufixo
                        variation_payload[codigo_field] = f"{product_data[codigo_field]}-{i+1}"
                
                # PREÇOS
                variation_payload['price'] = variation.get('price', product_data.get('price', 0))
                variation_payload['price_compare'] = variation.get('price_compare', product_data.get('price_compare', 0))
                
                # ESTOQUE
                variation_payload['balance'] = variation.get('balance', 0)
                variation_payload['active'] = True
                
                # GERAR NOME PARA COR
                color_name = None
                
                # Opção 1: Extrair de atributos existentes na variação
                if 'attributes' in variation:
                    for attr in variation.get('attributes', []):
                        if attr.get('name', '').lower() in ['cor', 'color', 'colour']:
                            color_name = attr.get('value')
                            break
                
                # Opção 2: Usar o primeiro atributo disponível como nome da cor
                if not color_name and 'attributes' in variation and variation['attributes']:
                    color_name = variation['attributes'][0].get('value')
                
                # Opção 3: Nome genérico único baseado no SKU
                if not color_name:
                    color_name = f"Cor-{variation_payload.get('sku', f'var-{i+1}')}"
                
                # CRIAR/BUSCAR COR E OBTER SEU ID
                color_id = None
                
                # Verificar no cache primeiro
                if color_name.lower() in colors_cache:
                    color_id = colors_cache[color_name.lower()]
                    self.logger.info(f"🎨 Cor '{color_name}' encontrada no cache (ID: {color_id})")
                else:
                    # Criar nova cor
                    try:
                        color_data = {
                            "name": color_name,
                            "hexadecimal": "#000000",  # Preto por padrão
                            "active": True
                        }
                        
                        color_response = self._make_request(
                            method="POST",
                            endpoint="/colors",
                            data=color_data,
                            headers=self._get_headers()
                        )
                        
                        if color_response and 'id' in color_response:
                            color_id = color_response['id']
                            colors_cache[color_name.lower()] = color_id
                            self.logger.info(f"🎨 Cor '{color_name}' criada com sucesso (ID: {color_id})")
                        else:
                            self.logger.error(f"❌ Falha ao criar cor '{color_name}': {color_response}")
                    except Exception as e:
                        self.logger.error(f"❌ Erro ao criar cor '{color_name}': {str(e)}")
                
                # ADICIONAR COLOR_ID AO PAYLOAD (OBRIGATÓRIO)
                if color_id:
                    variation_payload['color_id'] = color_id
                else:
                    self.logger.error(f"❌ Não foi possível obter ID da cor '{color_name}', variação não será criada")
                    continue
                
                # CRIAR VARIAÇÃO COM PAYLOAD COMPLETO E SIMPLIFICADO
                try:
                    self.logger.info(f"📤 Enviando payload da variação: {json.dumps(variation_payload)}")
                    
                    variation_response = self._make_request(
                        method="POST",
                        endpoint="/variations",
                        data=variation_payload,
                        headers=self._get_headers()
                    )
                    
                    if variation_response and 'id' in variation_response:
                        self.logger.info(f"✅ Variação {i+1} criada com sucesso (ID: {variation_response['id']})")
                        successful_variations += 1
                    else:
                        self.logger.warning(f"⚠️ Falha ao criar variação {i+1}. Resposta: {variation_response}")
                
                except Exception as e:
                    self.logger.error(f"❌ Erro ao criar variação {i+1}: {str(e)}")
                    import traceback
                    self.logger.error(f"❌ Detalhes do erro: {traceback.format_exc()}")
            
            self.logger.info(f"✨ Total: {successful_variations} de {len(original_variations)} variações criadas para o produto {product_id}")
            
            # Obter produto atualizado com todas as variações
            updated_product = self.get_product_by_id(product_id)
            if updated_product:
                return updated_product
        
        return response
    else:
        self.logger.error(f"❌ Falha ao criar produto: {product_data.get('name')}. Resposta: {response}")
        return response