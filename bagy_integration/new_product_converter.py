"""
Nova abordagem de conversão de produtos: cada variação será um produto independente na Bagy
"""
import logging
import re
import time
import hashlib
from datetime import datetime

class ProductConverter:
    """
    Classe para converter produtos entre os sistemas GestãoClick e Bagy.
    Nova abordagem: cada variação será um produto independente.
    """
    
    def __init__(self, incomplete_products_storage=None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.incomplete_products_storage = incomplete_products_storage
        
    def _validate_required_fields(self, product_data, required_fields):
        """
        Verificar se todos os campos obrigatórios estão presentes no produto.
        
        Args:
            product_data (dict): Dados do produto
            required_fields (list): Lista de campos obrigatórios
            
        Returns:
            tuple: (True, []) se válido, (False, [campos_faltantes]) caso contrário
        """
        missing_fields = []
        
        for field in required_fields:
            if field not in product_data or product_data[field] is None or product_data[field] == "":
                missing_fields.append(field)
                
        return (len(missing_fields) == 0, missing_fields)
    
    def _convert_dimensions(self, gc_product):
        """
        Converte as dimensões do GestãoClick para o formato da Bagy.
        As dimensões no GestãoClick estão em metros, na Bagy estão em centímetros.
        
        Args:
            gc_product (dict): Produto do GestãoClick
            
        Returns:
            dict: Dimensões convertidas para Bagy
        """
        dimensions = {}
        
        # Tentar converter altura
        try:
            if 'altura' in gc_product and gc_product['altura']:
                height_m = float(gc_product['altura'])
                height_cm = height_m * 10  # Converter de metros para centímetros
                self.logger.info(f"Convertendo altura: {height_m} m -> {height_cm} cm")
                dimensions['height'] = height_cm
            else:
                self.logger.warning(f"⚠️ Produto {gc_product.get('nome')} (ID: {gc_product.get('id')}) - Erro ao converter altura.")
        except (ValueError, TypeError) as e:
            self.logger.warning(f"⚠️ Produto {gc_product.get('nome')} (ID: {gc_product.get('id')}) - Erro ao converter altura.")
        
        # Tentar converter largura
        try:
            if 'largura' in gc_product and gc_product['largura']:
                width_m = float(gc_product['largura'])
                width_cm = width_m * 10  # Converter de metros para centímetros
                self.logger.info(f"Convertendo largura: {width_m} m -> {width_cm} cm")
                dimensions['width'] = width_cm
            else:
                self.logger.warning(f"⚠️ Produto {gc_product.get('nome')} (ID: {gc_product.get('id')}) - Erro ao converter largura.")
        except (ValueError, TypeError) as e:
            self.logger.warning(f"⚠️ Produto {gc_product.get('nome')} (ID: {gc_product.get('id')}) - Erro ao converter largura.")
        
        # Tentar converter profundidade (comprimento)
        try:
            if 'comprimento' in gc_product and gc_product['comprimento']:
                depth_m = float(gc_product['comprimento'])
                depth_cm = depth_m * 10  # Converter de metros para centímetros
                self.logger.info(f"Convertendo profundidade: {depth_m} m -> {depth_cm} cm")
                dimensions['depth'] = depth_cm
            else:
                self.logger.warning(f"⚠️ Produto {gc_product.get('nome')} (ID: {gc_product.get('id')}) - Erro ao converter profundidade.")
        except (ValueError, TypeError) as e:
            self.logger.warning(f"⚠️ Produto {gc_product.get('nome')} (ID: {gc_product.get('id')}) - Erro ao converter profundidade.")
        
        # Tentar obter peso (já em kg)
        try:
            if 'peso' in gc_product and gc_product['peso']:
                weight_kg = float(gc_product['peso'])
                dimensions['weight'] = weight_kg
            else:
                self.logger.warning(f"⚠️ Produto {gc_product.get('nome')} (ID: {gc_product.get('id')}) - Erro ao converter peso.")
        except (ValueError, TypeError) as e:
            self.logger.warning(f"⚠️ Produto {gc_product.get('nome')} (ID: {gc_product.get('id')}) - Erro ao converter peso.")
        
        # Verificar se temos todas as dimensões
        required_dimensions = ['height', 'width', 'depth', 'weight']
        missing_dimensions = [dim for dim in required_dimensions if dim not in dimensions]
        
        if missing_dimensions:
            self.logger.warning(f"⚠️ Produto {gc_product.get('nome')} (ID: {gc_product.get('id')}) com dimensões incompletas: {', '.join(missing_dimensions)}")
            self.logger.info(f"📏 Diagnóstico de dimensões para produto rejeitado {gc_product.get('nome')} (ID: {gc_product.get('id')}): altura={gc_product.get('altura', '')}, largura={gc_product.get('largura', '')}, comprimento={gc_product.get('comprimento', '')}, peso={gc_product.get('peso', '')}")
            
            # Registrar produto incompleto, se um armazenamento foi fornecido
            if self.incomplete_products_storage:
                self.incomplete_products_storage.add_product(
                    product_id=gc_product.get('id'),
                    product_name=gc_product.get('nome', ''),
                    missing_fields=missing_dimensions
                )
        else:
            self.logger.info(f"Dimensões convertidas - altura: {dimensions['height']:.2f}cm (original {gc_product.get('altura')}m), largura: {dimensions['width']:.2f}cm (original {gc_product.get('largura')}m), profundidade: {dimensions['depth']:.2f}cm (original {gc_product.get('comprimento')}m), peso: {dimensions['weight']:.3f}kg")
        
        return dimensions, missing_dimensions
        
    def gestaoclick_to_bagy(self, gestaoclick_product):
        """
        Converte um produto da GestãoClick para o formato da Bagy.
        NOVA ESTRATÉGIA: Cada variação será tratada como um produto independente.
        
        Args:
            gestaoclick_product (dict): Produto da GestãoClick
            
        Returns:
            list: Lista de produtos Bagy (um para cada variação, ou um único se não houver variações)
        """
        # Verificar campos obrigatórios
        required_fields = ['id', 'nome', 'descricao']
        is_valid, missing_fields = self._validate_required_fields(gestaoclick_product, required_fields)
        
        if not is_valid:
            self.logger.warning(f"❌ Produto {gestaoclick_product.get('nome', 'Desconhecido')} (ID: {gestaoclick_product.get('id', 'Desconhecido')}) não pode ser convertido. Campos faltantes: {', '.join(missing_fields)}")
            
            # Registrar produto incompleto
            if self.incomplete_products_storage:
                self.incomplete_products_storage.add_product(
                    product_id=gestaoclick_product.get('id'),
                    product_name=gestaoclick_product.get('nome', 'Desconhecido'),
                    missing_fields=missing_fields
                )
            
            return []
        
        # Converter dimensões
        dimensions, missing_dimensions = self._convert_dimensions(gestaoclick_product)
        
        # Se faltar alguma dimensão, não podemos prosseguir
        if missing_dimensions:
            return []
        
        # Lista de produtos convertidos (um para cada variação)
        converted_products = []
        
        # Verificar se o produto tem variações
        if 'variacoes' in gestaoclick_product and gestaoclick_product['variacoes']:
            # Processar cada variação como um produto independente
            for variation in gestaoclick_product['variacoes']:
                # Gerar nome completo (produto + variação)
                variation_name = variation.get('nome', '')
                product_name = gestaoclick_product['nome']
                
                # Combinar nome do produto com a variação
                if variation_name and variation_name.strip() and variation_name.strip().lower() != 'padrão':
                    full_name = f"{product_name} - {variation_name}"
                else:
                    full_name = product_name
                
                # Gerar um external_id único para a variação
                variation_id = variation.get('id', '')
                
                # Se não tiver ID na variação, criar um ID baseado nos dados disponíveis
                if not variation_id or variation_id == '':
                    # Primeiro tenta usar o código interno
                    if 'codigo_interno' in variation and variation['codigo_interno']:
                        variation_id = f"codigo-{variation['codigo_interno']}"
                    # Se não tiver código interno, usar o nome e outras propriedades para criar um hash único
                    else:
                        # Criar uma string com todas as propriedades disponíveis da variação
                        var_props = []
                        for k, v in variation.items():
                            if v is not None:
                                var_props.append(f"{k}:{v}")
                        
                        # Criar um hash a partir dessas propriedades
                        if var_props:
                            props_str = "-".join(var_props)
                            hash_obj = hashlib.md5(props_str.encode())
                            variation_id = f"var-{hash_obj.hexdigest()[:8]}"
                        else:
                            # Último recurso: timestamp + nome da variação
                            variation_id = f"var-{int(time.time())}-{variation.get('nome', 'padrao')}"
                
                self.logger.info(f"🔑 ID gerado para variação: {variation_id}")
                external_id = f"{gestaoclick_product['id']}-{variation_id}"
                
                # Obter SKU da variação ou do produto principal
                sku = variation.get('codigo_interno', gestaoclick_product.get('codigo_interno', ''))
                
                # Construir produto para a Bagy a partir da variação
                bagy_product = {
                    'external_id': external_id,
                    'name': full_name,
                    'description': gestaoclick_product['descricao'],
                    'sku': str(sku) if sku else None,
                    'reference': str(sku) if sku else None,
                    'code': str(sku) if sku else None,
                    'price': variation.get('preco_venda', gestaoclick_product.get('preco_venda', 0)),
                    'price_compare': variation.get('preco_venda', gestaoclick_product.get('preco_venda', 0)),
                    'balance': variation.get('estoque', 0),
                    'active': True,
                    'type': 'simple',  # Sempre será um produto simples na Bagy
                    # Adicionar dimensões
                    'height': dimensions['height'],
                    'width': dimensions['width'],
                    'depth': dimensions['depth'],
                    'weight': dimensions['weight']
                }
                
                self.logger.info(f"🔍 Convertendo variação para produto independente: {full_name} (SKU: {sku})")
                converted_products.append(bagy_product)
                
        else:
            # Produto sem variações, converter diretamente
            sku = gestaoclick_product.get('codigo_interno', '')
            
            bagy_product = {
                'external_id': str(gestaoclick_product['id']),
                'name': gestaoclick_product['nome'],
                'description': gestaoclick_product['descricao'],
                'sku': str(sku) if sku else None,
                'reference': str(sku) if sku else None,
                'code': str(sku) if sku else None,
                'price': gestaoclick_product.get('preco_venda', 0),
                'price_compare': gestaoclick_product.get('preco_venda', 0),
                'balance': gestaoclick_product.get('estoque', 0),
                'active': True,
                'type': 'simple',  # Sempre será um produto simples na Bagy
                # Adicionar dimensões
                'height': dimensions['height'],
                'width': dimensions['width'],
                'depth': dimensions['depth'],
                'weight': dimensions['weight']
            }
            
            self.logger.info(f"🔍 Convertendo produto simples: {gestaoclick_product['nome']} (SKU: {sku})")
            converted_products.append(bagy_product)
        
        return converted_products
    
    def bagy_to_gestaoclick(self, bagy_product):
        """
        Converte um produto do Bagy para o formato da GestãoClick.
        
        Args:
            bagy_product (dict): Produto do Bagy
            
        Returns:
            dict: Produto convertido para GestãoClick ou None se não puder ser convertido
        """
        # Verificar campos obrigatórios
        required_fields = ['id', 'name', 'description']
        is_valid, missing_fields = self._validate_required_fields(bagy_product, required_fields)
        
        if not is_valid:
            self.logger.warning(f"❌ Produto {bagy_product.get('name', 'Desconhecido')} (ID: {bagy_product.get('id', 'Desconhecido')}) não pode ser convertido. Campos faltantes: {', '.join(missing_fields)}")
            return None
        
        # Extrair external_id se existir para identificar se é uma variação
        external_id = bagy_product.get('external_id', '')
        is_variation = '-' in external_id if external_id else False
        
        if is_variation:
            # Extrair IDs do produto principal e da variação
            parts = external_id.split('-')
            product_id = parts[0]
            variation_id = parts[1] if len(parts) > 1 else ''
            
            # Este é um produto que foi uma variação na GestãoClick
            # Como não estamos fazendo sincronização nesta direção para variações,
            # apenas registramos info e retornamos None
            self.logger.info(f"⚠️ Produto {bagy_product.get('name')} é uma variação. Não será sincronizado de volta.")
            return None
        
        # Conversão direta para um produto GestãoClick
        product_data = {
            'nome': bagy_product['name'],
            'descricao': bagy_product['description'],
            'codigo_interno': bagy_product.get('sku', ''),
            'preco_venda': bagy_product.get('price', 0),
            'estoque': bagy_product.get('balance', 0),
            'ativo': bagy_product.get('active', True)
        }
        
        return product_data