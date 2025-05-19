"""
Método definitivo para criação de produtos na Bagy, com suporte completo a variações.
Este arquivo contém a implementação final para substituir o método atual.
"""

import re
import time
import json
from copy import deepcopy

def criar_produto_com_variacoes(self, produto_data):
    """
    Método otimizado para criar produto na Bagy com suporte completo a variações.
    
    Args:
        produto_data (dict): Dados do produto a ser criado
        
    Returns:
        dict: Dados do produto criado
    """
    self.logger.info(f"👉 NOVA IMPLEMENTAÇÃO - Criando produto: {produto_data.get('name')}")
    
    # Fazer cópia dos dados para não modificar o original
    produto = deepcopy(produto_data)
    
    # 1. VALIDAÇÃO E PREPARAÇÃO DOS DADOS BÁSICOS
    # Verificar se produto já existe
    external_id = produto.get('external_id')
    if external_id:
        produto_existente = self.get_product_by_external_id(external_id)
        if produto_existente:
            self.logger.info(f"✅ Produto já existe com external_id={external_id} (ID: {produto_existente.get('id')})")
            return produto_existente
    
    # 2. GARANTIR DIMENSÕES DO PRODUTO (obrigatórias)
    for dim in ['height', 'width', 'depth', 'weight']:
        if dim not in produto or not produto[dim]:
            produto[dim] = 0.1
            self.logger.info(f"📏 Garantindo dimensão: {dim}=0.1")
    
    # 3. GARANTIR CÓDIGOS DO PRODUTO (SKU, reference, code)
    for codigo_field in ['sku', 'reference', 'code']:
        # Se campo não existe ou está vazio
        if codigo_field not in produto or not produto[codigo_field]:
            # Gerar um código baseado no nome ou timestamp
            timestamp = str(int(time.time()))[-4:]
            if 'name' in produto and produto['name']:
                # Gerar baseado no nome
                slug = re.sub(r'[^a-zA-Z0-9]', '', produto['name'])[:8]
                produto[codigo_field] = f"{slug}-{timestamp}"
            else:
                # Fallback para timestamp
                produto[codigo_field] = f"PROD-{timestamp}"
            
            self.logger.info(f"🔑 Código {codigo_field} gerado: '{produto[codigo_field]}'")
        else:
            # Garantir que seja string
            produto[codigo_field] = str(produto[codigo_field])
            self.logger.info(f"🔑 Código {codigo_field} convertido para string: '{produto[codigo_field]}'")
    
    # 4. PROCESSAR VARIAÇÕES
    tem_variacoes = False
    variacoes_originais = []
    
    if 'variations' in produto:
        tem_variacoes = True
        variacoes_originais = produto.pop('variations', [])
        self.logger.info(f"🔀 Produto tem {len(variacoes_originais)} variações que serão criadas separadamente")
    
    # Definir tipo do produto corretamente
    produto['type'] = 'variant' if tem_variacoes else 'simple'
    self.logger.info(f"📋 Tipo do produto definido como: {produto['type']}")
    
    # 5. CRIAR PRODUTO BASE
    self.logger.info(f"🔷 Criando produto base: {produto.get('name')}")
    resposta = self._make_request(
        method="POST", 
        endpoint="/products",
        data=produto,
        headers=self._get_headers()
    )
    
    # 6. VERIFICAR SE PRODUTO BASE FOI CRIADO COM SUCESSO
    if not resposta or 'id' not in resposta:
        self.logger.error(f"❌ Falha ao criar produto base: {resposta}")
        return resposta
    
    produto_id = resposta['id']
    self.logger.info(f"✅ Produto base criado com sucesso (ID: {produto_id})")
    
    # 7. PULAR CRIAÇÃO DE VARIAÇÕES SE NÃO HOUVER VARIAÇÕES
    if not tem_variacoes or len(variacoes_originais) == 0:
        self.logger.info(f"ℹ️ Produto sem variações, retornando produto base")
        return resposta
    
    # 8. OBTER TODAS AS CORES EXISTENTES (para evitar criar duplicadas)
    cores_cache = {}
    try:
        cores_resposta = self._make_request(
            method="GET",
            endpoint="/colors",
            headers=self._get_headers()
        )
        
        if cores_resposta and 'data' in cores_resposta:
            for cor in cores_resposta['data']:
                cores_cache[cor['name'].lower()] = cor['id']
            self.logger.info(f"🎨 Cache de cores carregado com {len(cores_cache)} cores")
    except Exception as e:
        self.logger.error(f"❌ Erro ao carregar cache de cores: {str(e)}")
    
    # 9. PROCESSAR CADA VARIAÇÃO INDIVIDUALMENTE
    variacoes_criadas = 0
    
    for i, variacao in enumerate(variacoes_originais):
        self.logger.info(f"🔄 Processando variação {i+1}/{len(variacoes_originais)}")
        
        # 9.1 CRIAR PAYLOAD SIMPLIFICADO DE VARIAÇÃO
        payload_variacao = {
            "product_id": produto_id,
            "active": True
        }
        
        # 9.2 CONFIGURAR IDENTIFICADORES
        if 'external_id' in variacao and variacao['external_id']:
            payload_variacao['external_id'] = str(variacao['external_id'])
        else:
            payload_variacao['external_id'] = f"{produto['external_id']}-var-{i+1}" if 'external_id' in produto else f"{produto_id}-var-{i+1}"
            
        # 9.3 GARANTIR CAMPOS DE CÓDIGO
        for codigo_field in ['sku', 'reference', 'code']:
            # Prioridade 1: Valor da variação
            if codigo_field in variacao and variacao[codigo_field]:
                payload_variacao[codigo_field] = str(variacao[codigo_field])
            # Prioridade 2: Valor do produto base com sufixo
            elif codigo_field in produto:
                payload_variacao[codigo_field] = f"{produto[codigo_field]}-{i+1}"
            # Prioridade 3: Gerar um novo
            else:
                payload_variacao[codigo_field] = f"VAR-{produto_id}-{i+1}"
            
            self.logger.info(f"🔑 Variação {i+1}: Campo {codigo_field} = '{payload_variacao[codigo_field]}'")
        
        # 9.4 DEFINIR PREÇOS E ESTOQUE
        payload_variacao['price'] = variacao.get('price', produto.get('price', 0))
        payload_variacao['price_compare'] = variacao.get('price_compare', produto.get('price_compare', 0))
        payload_variacao['balance'] = variacao.get('balance', 0)
        
        # 9.5 DETERMINAR E CRIAR COR (CRÍTICO PARA A API DA BAGY)
        nome_cor = None
        
        # Estratégia 1: Procurar atributo "Cor" explícito
        if 'attributes' in variacao:
            for attr in variacao['attributes']:
                if attr.get('name', '').lower() in ['cor', 'color', 'colour']:
                    nome_cor = attr.get('value')
                    self.logger.info(f"🎨 Usando atributo 'Cor' explícito: '{nome_cor}'")
                    break
        
        # Estratégia 2: Usar qualquer atributo como nome de cor
        if not nome_cor and 'attributes' in variacao and variacao['attributes']:
            nome_cor = variacao['attributes'][0].get('value')
            self.logger.info(f"🎨 Usando primeiro atributo como cor: '{nome_cor}'")
        
        # Estratégia 3: Gerar nome único baseado no SKU
        if not nome_cor:
            nome_cor = f"Cor-{payload_variacao.get('sku', f'var-{i}')}"
            self.logger.info(f"🎨 Gerando nome de cor baseado no SKU: '{nome_cor}'")
        
        # 9.6 BUSCAR OU CRIAR A COR NA API
        cor_id = None
        nome_cor_lower = nome_cor.lower()
        
        # Verificar no cache primeiro (mais rápido)
        if nome_cor_lower in cores_cache:
            cor_id = cores_cache[nome_cor_lower]
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
                    cores_cache[nome_cor_lower] = cor_id
                    self.logger.info(f"🎨 Nova cor criada: '{nome_cor}' (ID: {cor_id})")
                else:
                    self.logger.error(f"❌ Falha ao criar cor '{nome_cor}': {cor_resposta}")
            except Exception as e:
                self.logger.error(f"❌ Erro ao criar cor '{nome_cor}': {str(e)}")
        
        # 9.7 ADICIONAR COLOR_ID (OBRIGATÓRIO PARA A API)
        if not cor_id:
            self.logger.error(f"❌ Impossível criar variação sem color_id. Pulando variação {i+1}.")
            continue
        
        payload_variacao['color_id'] = cor_id
        
        # 9.8 CRIAR A VARIAÇÃO NA API
        try:
            self.logger.info(f"📤 Enviando variação para API: {json.dumps(payload_variacao)}")
            
            variacao_resposta = self._make_request(
                method="POST",
                endpoint="/variations",
                data=payload_variacao,
                headers=self._get_headers()
            )
            
            if variacao_resposta and 'id' in variacao_resposta:
                variacao_id = variacao_resposta['id']
                self.logger.info(f"✅ Variação {i+1} criada com sucesso (ID: {variacao_id})")
                variacoes_criadas += 1
            else:
                self.logger.error(f"❌ Falha ao criar variação {i+1}: {variacao_resposta}")
                
        except Exception as e:
            self.logger.error(f"❌ Erro ao criar variação {i+1}: {str(e)}")
            import traceback
            self.logger.error(f"❌ Detalhes: {traceback.format_exc()}")
    
    # 10. RESUMO FINAL
    self.logger.info(f"✨ Total: {variacoes_criadas} de {len(variacoes_originais)} variações criadas com sucesso")
    
    # 11. OBTER PRODUTO COMPLETO ATUALIZADO
    produto_atualizado = self.get_product_by_id(produto_id)
    if produto_atualizado:
        self.logger.info(f"✅ Produto final obtido com todas as variações")
        return produto_atualizado
    
    return resposta