"""
Data models for entity conversion between Bagy and GestãoClick.
"""
import logging
import re
from datetime import datetime

class BaseConverter:
    """Base converter with common functionality."""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)


class ProductConverter(BaseConverter):
    """Convert product data between Bagy and GestãoClick formats."""
    
    def _generate_slug(self, text):
        """
        Generate a URL-friendly slug from a text string.
        
        Args:
            text (str): Text to convert to slug
            
        Returns:
            str: URL-friendly slug
        """
        if not text:
            return ""
            
        # Replace spaces with hyphens
        slug = text.lower().strip().replace(' ', '-')
        
        # Remove special characters
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        
        # Remove multiple hyphens
        slug = re.sub(r'-+', '-', slug)
        
        # Ensure the slug is not empty
        if not slug:
            return "produto"
            
        return slug
        
    def _format_description(self, description):
        """
        Formata a descrição do produto para exibição adequada na Bagy.
        
        Args:
            description (str): Texto da descrição original
            
        Returns:
            str: Descrição formatada com HTML adequado
        """
        if not description:
            return ""
            
        # Normalizar quebras de linha
        description = description.replace('\r\n', '\n')
        
        # Identificar seções pela formatação (linhas que terminam com :)
        lines = description.split('\n')
        formatted_lines = []
        
        in_list = False
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                # Linha vazia, adicionar quebra de parágrafo se não for a primeira ou última linha
                if i > 0 and i < len(lines) - 1:
                    formatted_lines.append("<br><br>")
                continue
                
            # Verificar se é título de seção (termina com : ou tem menos de 50 caracteres e está em maiúsculas)
            if line.endswith(':') or (len(line) < 50 and line.upper() == line and not line.startswith('0') and not line.startswith('-')):
                # Fechar lista anterior se estiver em uma
                if in_list:
                    formatted_lines.append("</ul>")
                    in_list = False
                
                # Adicionar título como parágrafo em negrito
                formatted_lines.append(f"<p><strong>{line}</strong></p>")
                
                # Se a próxima linha parece ser um item de lista, iniciar uma lista
                if i + 1 < len(lines) and (lines[i+1].strip().startswith('0') or lines[i+1].strip().startswith('-')):
                    formatted_lines.append("<ul>")
                    in_list = True
            
            # Verificar se parece item de lista
            elif line.startswith('0') or line.startswith('-') or line.startswith('•'):
                # Se ainda não iniciou a lista, iniciar
                if not in_list:
                    formatted_lines.append("<ul>")
                    in_list = True
                
                # Remover o marcador e adicionar como item de lista
                item_content = line[1:].strip() if line.startswith('-') or line.startswith('0') else line[1:].strip()
                formatted_lines.append(f"<li>{item_content}</li>")
            
            else:
                # Fechar lista anterior se estiver em uma
                if in_list:
                    formatted_lines.append("</ul>")
                    in_list = False
                
                # Adicionar como parágrafo normal
                formatted_lines.append(f"<p>{line}</p>")
        
        # Fechar qualquer lista aberta
        if in_list:
            formatted_lines.append("</ul>")
        
        # Juntar tudo
        formatted_description = "\n".join(formatted_lines)
        
        # Verificar se há formatação HTML, se não tiver, adicionar parágrafos simples
        if "<p>" not in formatted_description and "<ul>" not in formatted_description:
            # Usar o formato correto sem caracteres de escape em f-strings
            newline = "\n"
            double_newline = "\n\n"
            formatted_description = f"<p>{description.replace(double_newline, '</p><p>').replace(newline, '<br>')}</p>"
            
        return formatted_description
    
    def gestaoclick_to_bagy(self, gestao_product):
        """
        Convert a GestãoClick product to Bagy format.
        
        Args:
            gestao_product (dict): Product data from GestãoClick (Betel API)
            
        Returns:
            dict or tuple: Product data in Bagy format (Dooca API) or tuple (None, missing_fields) if required fields are missing
        """
        self.logger.debug(f"Converting product from GestãoClick to Bagy: {gestao_product.get('nome', 'Unknown')}")
        
        # Lista de campos obrigatórios para sincronização
        # Verificar se o produto tem todos os campos obrigatórios
        missing_fields = []
        invalid_fields = []  # Para valores inválidos mas presentes
        product_id = gestao_product.get('id')
        
        # Verificar nome
        name = gestao_product.get('nome', '')
        if not name:
            missing_fields.append("nome")
            
        # Verificar SKU (código interno) - não é mais obrigatório
        sku = gestao_product.get('codigo_interno', '')
        
        # Verificar descrição
        description = gestao_product.get('descricao', '')
        if not description or description.strip() == '':
            missing_fields.append("descrição")
        
        # Verificar dimensões e peso - não são mais obrigatórios
        peso_original = gestao_product.get('peso')
        altura_original = gestao_product.get('altura')
        largura_original = gestao_product.get('largura')
        comprimento_original = gestao_product.get('comprimento')
        
        # Se faltar algum campo obrigatório, retornar None para que o produto seja ignorado
        if missing_fields:
            # Usar log em nível de debug para não poluir a saída principal
            self.logger.debug(f"❌ Produto ID: {product_id} ({name}) não pode ser sincronizado. Campos faltando: {', '.join(missing_fields)}")
            return None, missing_fields
            
        # Tratar preço para formatos corretos
        price = gestao_product.get('valor_venda', 0)
        if isinstance(price, str):
            price = price.replace(',', '.')
            try:
                price = float(price)
            except (ValueError, TypeError):
                price = 0
        
        # Definir o código SKU do produto (código interno)
        sku = gestao_product.get('codigo_interno', '')
        # Se o código interno estiver vazio, mantemos vazio (não usamos alternativas)
        if not sku:
            sku = ''
            self.logger.warning(f"⚠️ Produto {name} (ID: {product_id}) - Código interno (SKU) não encontrado.")
            
        # Código de barras / GTIN  
        barcode = gestao_product.get('codigo_barra', '')
        
        # Status do produto
        active = True if gestao_product.get('ativo') in ["1", 1, True] else False
        
        # Tratamento para estoque com possíveis formatos diferentes
        stock_value = gestao_product.get('estoque', 0)
        if isinstance(stock_value, str):
            # Remove caracteres não numéricos como ponto decimal ou vírgula
            stock_value = stock_value.replace(',', '.')
            try:
                stock = int(float(stock_value))
            except (ValueError, TypeError):
                stock = 0
        else:
            try:
                stock = int(float(stock_value))
            except (ValueError, TypeError):
                stock = 0
        
        # Extract dimensions and weight (usar os valores originais verificados)
        height = altura_original
        width = largura_original
        depth = comprimento_original
        weight = peso_original
        
        # Convert weight from comma to dot format if necessary
        if isinstance(height, str):
            height = height.replace(',', '.')
        if isinstance(width, str):
            width = width.replace(',', '.')
        if isinstance(depth, str):
            depth = depth.replace(',', '.')
        if isinstance(weight, str):
            weight = weight.replace(',', '.')
            
        # Converter dimensões de metros para centímetros (GestãoClick -> Bagy)
        try:
            height_float = float(height)
            # Converter de metros para centímetros (multiplicar por 10)
            height_cm = height_float * 10.0
            height = height_cm
            self.logger.info(f"Convertendo altura: {height_float} m -> {height_cm} cm")
        except (ValueError, TypeError):
            pass
            
        try:
            width_float = float(width)
            # Converter de metros para centímetros (multiplicar por 10)
            width_cm = width_float * 10.0
            width = width_cm
            self.logger.info(f"Convertendo largura: {width_float} m -> {width_cm} cm")
        except (ValueError, TypeError):
            pass
            
        try:
            depth_float = float(depth)
            # Converter de metros para centímetros (multiplicar por 10)
            depth_cm = depth_float * 10.0
            depth = depth_cm
            self.logger.info(f"Convertendo profundidade: {depth_float} m -> {depth_cm} cm")
        except (ValueError, TypeError):
            pass
            
        if isinstance(weight, str):
            weight = weight.replace(',', '.')
        
        # Verificação de valores - TODOS os campos de dimensão são OBRIGATÓRIOS
        # Se não houver valores ou forem inválidos, o produto NÃO será sincronizado
        
        dimensions_missing = []
        
        # Verificar altura
        try:
            height = float(height) if not isinstance(height, float) else height
            if height <= 0:
                dimensions_missing.append("altura")
        except (ValueError, TypeError):
            self.logger.warning(f"⚠️ Produto {name} (ID: {product_id}) - Erro ao converter altura.")
            dimensions_missing.append("altura")
            
        # Verificar largura
        try:
            width = float(width) if not isinstance(width, float) else width
            if width <= 0:
                dimensions_missing.append("largura")
        except (ValueError, TypeError):
            self.logger.warning(f"⚠️ Produto {name} (ID: {product_id}) - Erro ao converter largura.")
            dimensions_missing.append("largura")
            
        # Verificar profundidade
        try:
            depth = float(depth) if not isinstance(depth, float) else depth
            if depth <= 0:
                dimensions_missing.append("profundidade")
        except (ValueError, TypeError):
            self.logger.warning(f"⚠️ Produto {name} (ID: {product_id}) - Erro ao converter profundidade.")
            dimensions_missing.append("profundidade")
            
        # Verificar peso
        try:
            weight = float(weight) if not isinstance(weight, float) else weight
            if weight <= 0:
                dimensions_missing.append("peso")
        except (ValueError, TypeError):
            self.logger.warning(f"⚠️ Produto {name} (ID: {product_id}) - Erro ao converter peso.")
            dimensions_missing.append("peso")
            
        # Se faltar alguma dimensão, adicionar aos campos faltantes
        if dimensions_missing:
            missing_fields.extend(dimensions_missing)
            self.logger.warning(f"⚠️ Produto {name} (ID: {product_id}) com dimensões incompletas: {', '.join(dimensions_missing)}")
        
        # Verificar novamente se há campos faltantes
        if missing_fields:
            # Adicionar log de diagnóstico para mostrar as dimensões antes da rejeição
            self.logger.info(f"📏 Diagnóstico de dimensões para produto rejeitado {name} (ID: {product_id}): altura={altura_original}, largura={largura_original}, comprimento={comprimento_original}, peso={peso_original}")
            self.logger.debug(f"❌ Produto ID: {product_id} ({name}) não pode ser sincronizado. Campos faltando: {', '.join(missing_fields)}")
            return None, missing_fields
        
        # Valores passaram pela validação, agora precisamos converter as unidades:
        # GestãoClick: dimensões em metros, peso em kg
        # Bagy: dimensões em centímetros, peso em kg
        
        # Os valores de dimensão já devem ser números (float ou int) neste ponto
        # Vamos garantir isso e então formatar para strings
        try:
            # Formatamos as dimensões para exibição nas casas decimais apropriadas
            height_float = float(height)
            width_float = float(width)
            depth_float = float(depth)
            weight_float = float(weight)
            
            height_str = f"{height_float:.2f}"
            width_str = f"{width_float:.2f}"
            depth_str = f"{depth_float:.2f}"
            weight_str = f"{weight_float:.3f}"
            
            # Calcular os valores originais em metros (dividindo por 10)
            height_m = height_float / 10.0
            width_m = width_float / 10.0
            depth_m = depth_float / 10.0
            
            self.logger.info(f"Dimensões convertidas - altura: {height_str}cm (original {height_m:.3f}m), largura: {width_str}cm (original {width_m:.3f}m), profundidade: {depth_str}cm (original {depth_m:.3f}m), peso: {weight_str}kg")
        except (ValueError, TypeError):
            # Se algum valor não puder ser convertido para float, usamos os valores como estão
            # Isso é uma fallback para o caso em que os valores não são numéricos
            self.logger.warning(f"⚠️ Não foi possível converter dimensões para float. Usando valores como estão.")
            height_str = str(height)
            width_str = str(width)
            depth_str = str(depth)
            weight_str = str(weight)
            self.logger.info(f"Dimensões (como texto) - altura: {height_str}cm, largura: {width_str}cm, profundidade: {depth_str}cm, peso: {weight_str}kg")
            
        # Extract category info
        category_id = gestao_product.get('grupo_id')
        category_name = gestao_product.get('nome_grupo')
        
        # Build Bagy product object (Dooca API format)
        # Seguindo exatamente o formato mostrado na documentação
        # Usar os valores formatados na validação anterior
        weight_formatted = weight_str
        depth_formatted = depth_str
        width_formatted = width_str
        height_formatted = height_str
        price_formatted = f"{price:.2f}"
        
        # Formatar a descrição do produto com HTML adequado
        formatted_description = self._format_description(description)
        self.logger.debug(f"Descrição formatada para o produto {name} (ID: {product_id})")
        
        # IMPORTANTE: Na Bagy, o campo "sku" deve receber o código interno do GestãoClick
        # O campo "reference" também deve receber o código interno
        # O campo "external_id" na Bagy deve receber o ID do produto no GestãoClick para rastreabilidade
        
        # Verificar se o produto possui variações (movido para cima)
        possui_variacao = gestao_product.get('possui_variacao') in ["1", 1, True]
        
        # CORREÇÃO CRÍTICA: Definir o tipo do produto como 'variant' para produtos com variações
        # Este campo é essencial para que a Bagy entenda que o produto tem variações
        product_type = "variant" if possui_variacao and 'variacoes' in gestao_product and gestao_product.get('variacoes') else "simple"
        self.logger.info(f"🧪 [TESTE-VAR] Definindo tipo do produto {name} como '{product_type}'")
        
        # Log explícito dos códigos para depuração
        self.logger.info(f"🔍 SKU/código interno: '{sku}', ID externo: '{product_id}'")
        
        # Criar a estrutura básica do produto
        bagy_product = {
            "name": name,  # obrigatório (string)
            "description": formatted_description,  # obrigatório (string)
            "short_description": name[:4000] if len(name) > 4000 else name,  # descrição curta (string max 4096)
            "relevance": 1,  # relevância do produto (integer 1 a 5)
            "min_quantity": 1,  # quantidade mínima de compra (integer)
            "sell_in_kit_only": False,  # vender apenas em kit (boolean)
            "kit": False,  # não é um kit (boolean)
            "kit_markup": 1,  # markup para kits (integer)
            "weight": weight_formatted,  # peso (string decimal)
            "depth": depth_formatted,  # profundidade (string decimal)
            "width": width_formatted,  # largura (string decimal)
            "height": height_formatted,  # altura (string decimal)
            "sell_out_of_stock": False,  # não vender quando fora de estoque (boolean)
            "price": float(price_formatted),  # preço (float)
            "active": active,  # ativo (boolean)
            "sku": sku,  # CORREÇÃO: O código interno do GestãoClick vai para o SKU na Bagy
            "reference": sku,  # NOVO: Duplicar o código interno no campo reference
            "code": sku,  # ADICIONAL: Incluir também no campo code para APIs mais recentes
            "external_id": product_id,  # ID do produto no GestãoClick como referência externa
            "type": product_type,  # IMPORTANTE: Tipo de produto (simple ou variant)
            "images": []  # array de imagens (sempre presente, mesmo vazio)
        }
        
        # Log para depuração dos campos de código/SKU
        self.logger.info(f"🔍 Gerando produto para Bagy. SKU='{sku}', ID='{product_id}'")
        
        # CORREÇÃO CRÍTICA: Para produtos com variações, adicionar configuração de atributos
        # Este campo informa à API quais atributos diferenciam as variações
        if product_type == "variant":
            # Adicionar atributos de variação (essencial para produtos com variações)
            # O tipo "options" é usado para variações com opções de seleção (como cores, tamanhos, etc.)
            # A opção "default" é necessária para a Bagy entender que essas variações devem ser criadas
            bagy_product["attributes"] = [
                {
                    "name": "Opção",  # Nome do atributo
                    "type": "options",  # Tipo do atributo (options = seleção de opções)
                    "options": [],  # Lista vazia, será preenchida ao criar as variações
                    "default": None
                }
            ]
            self.logger.info(f"🧪 [TESTE-VAR] Adicionando configuração de atributos para produto com variações")
        
        
        # Adicionar código de barras se disponível
        if barcode:
            bagy_product["gtin"] = barcode
            
        # Adicionar NCM se disponível    
        if gestao_product.get('ncm'):
            bagy_product["ncm"] = gestao_product.get('ncm')
        
        # Adicionar imagens se disponíveis
        image_url = gestao_product.get('imagem_url')
        if image_url:
            bagy_product["images"] = [{"src": image_url}]
            
        # Inicializar o array de variações
        variations = []
        
        # Log adicional para depuração de produtos com variações
        if possui_variacao:
            # Configuramos para um log INFO para todos os produtos com variações,
            # garantindo maior visibilidade no tratamento geral
            self.logger.info(f"🔍 Produto {name} (ID: {product_id}) tem variações: possui_variacao={possui_variacao}")
            
            if 'variacoes' in gestao_product:
                # Para produtos com muitas variações (>5), usar log mais detalhado
                if gestao_product['variacoes'] and len(gestao_product['variacoes']) > 5:
                    self.logger.info(f"🔍 Produto complexo: {name} (ID: {product_id}) com {len(gestao_product['variacoes'])} variações")
                    # Amostragem das primeiras variações para entender a estrutura
                    for i, var_item in enumerate(gestao_product['variacoes'][:3]):  # Mostrar apenas as 3 primeiras
                        var = var_item.get('variacao', {})
                        if var:
                            self.logger.info(f"  - Amostra variação {i+1}: {var.get('nome', 'Sem nome')} (ID: {var.get('id')}, Código: {var.get('codigo', '')})")
                    
                    if len(gestao_product['variacoes']) > 3:
                        self.logger.info(f"  - ... e mais {len(gestao_product['variacoes'])-3} variações")
            else:
                self.logger.warning(f"⚠️ Produto {name} tem possui_variacao=1 mas não tem o campo 'variacoes'")
        
        # IMPORTANTE: Nova estratégia para lidar com produtos com variações
        # Detectar se é um produto com múltiplas variações (que pode causar o erro "color_attribute_already_exists")
        has_too_many_variations = False
        has_color_variations = False

        # Log inicial
        if possui_variacao:
            self.logger.info(f"🧪 [TESTE-VAR] Analisando produto {name} (ID: {product_id}) com possui_variacao={possui_variacao}")
        
        # Verificar se o produto tem variações
        if possui_variacao and 'variacoes' in gestao_product and gestao_product['variacoes']:
            self.logger.info(f"🧪 [TESTE-VAR] Produto {name} tem {len(gestao_product['variacoes'])} variações no objeto gestao_product")
            
            # REGRA 1: Verificar se simplesmente tem muitas variações (mais de 3 já é considerado "muitas")
            if len(gestao_product['variacoes']) > 3:
                has_too_many_variations = True
                self.logger.warning(f"⚠️ Produto {name} tem muitas variações ({len(gestao_product['variacoes'])}), usando estratégia alternativa")
                
            # REGRA 2: Verificar se as variações têm nomes que parecem ser cores
            color_keywords = ['azul', 'rosa', 'água', 'vermelho', 'preto', 'branco', 'verde', 'amarelo', 
                            'laranja', 'roxo', 'violeta', 'marrom', 'cinza', 'dourado', 'prata', 'bege',
                            'lilás', 'turquesa', 'vinho', 'fúcsia', 'salmão', 'magenta', 'creme', 'nude']
            
            # Se for um produto com mais de uma variação, verificar se tem cores
            if len(gestao_product['variacoes']) > 1:
                for var_item in gestao_product['variacoes']:
                    var = var_item.get('variacao', {})
                    if var and var.get('nome'):
                        var_nome = var.get('nome', '').lower()
                        # Verificar se o nome da variação contém alguma palavra que parece ser cor
                        for color in color_keywords:
                            if color in var_nome:
                                has_color_variations = True
                                self.logger.warning(f"⚠️ Produto {name} tem variações de cores! Detectado: '{var_nome}' contém '{color}'")
                                break
                        if has_color_variations:
                            break
                            
            # REGRA 3: Verificar palavras-chave específicas nos nomes das variações
            # Para produtos como o "Egg Masturbador" que tem variações como "SPIDER", "SILKY", etc.
            # ou nomes de sabores, texturas, etc. que não são cores mas que a Bagy trata como atributos
            special_variation_keywords = ["egg", "masturbador", "vibrador", "lubrificante", "óleo", "gel"]
            if any(keyword in name.lower() for keyword in special_variation_keywords):
                # Verificar se tem pelo menos 2 variações (caracterizando um produto complexo)
                if len(gestao_product['variacoes']) > 1:
                    has_too_many_variations = True
                    self.logger.warning(f"⚠️ Produto {name} tem palavra-chave especial e múltiplas variações, usando estratégia alternativa")
        else:
            if possui_variacao:
                self.logger.warning(f"🧪 [TESTE-VAR] Produto {name} tem possui_variacao={possui_variacao} mas NÃO tem o campo 'variacoes' ou está vazio")
        
        # ESTRATÉGIA PARA PRODUTOS COM MÚLTIPLAS VARIAÇÕES (CORES OU MUITAS VARIAÇÕES EM GERAL)
        # Produtos com variações de cores ou muitas variações causam o erro color_attribute_already_exists
        # Para esses produtos, vamos mudar para tipo 'simple' e não adicionar variações
        if has_color_variations or has_too_many_variations:
            reason = "variações de cores" if has_color_variations else f"muitas variações ({len(gestao_product['variacoes'])})"
            self.logger.info(f"🔍 Produto com {reason}: {name} (ID: {product_id})")
            self.logger.info(f"⚠️ NOVA ESTRATÉGIA: marcando produto como 'simple' em vez de 'variant' para evitar erro color_attribute_already_exists")
            
            # Alterar o tipo do produto para 'simple' para evitar processamento de variações
            product_type = "simple"
            bagy_product["type"] = "simple"
            
            # Remover atributos se já foram adicionados
            if "attributes" in bagy_product:
                self.logger.info(f"🔄 Removendo atributos do produto para evitar conflito")
                del bagy_product["attributes"]
                
            # Não adicionar variações
            self.logger.info(f"🔄 Produto será criado sem variações")
            variations = []
            
        # ESTRATÉGIA NORMAL PARA PRODUTOS SEM VARIAÇÕES DE CORES
        elif possui_variacao and 'variacoes' in gestao_product and gestao_product['variacoes']:
            # Aumentar o nível de log para INFO para melhor visibilidade das variações
            self.logger.info(f"📋 Processando {len(gestao_product['variacoes'])} variações para o produto {name}")
            
            # Processar cada variação do produto (comportamento normal)
            for var_item in gestao_product['variacoes']:
                var = var_item.get('variacao', {})
                if not var:
                    continue
                    
                var_id = var.get('id')
                var_nome = var.get('nome', '')
                var_estoque = var.get('estoque', '0')
                
                # Verificar se o nome da variação está vazio
                if not var_nome or var_nome.strip() == '':
                    # Usar nome padrão baseado no produto principal e ID da variação
                    var_nome = f"{name} - Variação {var_id}"
                    self.logger.info(f"🔄 Nome da variação vazio. Usando nome padrão: {var_nome}")
                
                # Converter estoque para número
                try:
                    var_estoque = int(float(str(var_estoque).replace(',', '.')))
                except (ValueError, TypeError):
                    var_estoque = 0
                
                # Obter o preço da variação
                var_price = price  # Valor padrão é o do produto
                if 'valores' in var and var['valores']:
                    for valor in var['valores']:
                        if valor.get('valor_venda'):
                            try:
                                var_price = float(str(valor.get('valor_venda', '0')).replace(',', '.'))
                                break
                            except (ValueError, TypeError):
                                pass
                
                # Criar variação para o Bagy
                var_codigo = var.get('codigo', '')
                # Garantir que sempre tenhamos um SKU para a variação
                variation_sku = var_codigo if var_codigo else f"{sku}-{var_id}"
                
                # Garantir que tenhamos um estoque válido
                if var_estoque < 0:
                    var_estoque = 0
                
                # Registrar no log os detalhes da variação para facilitar a depuração
                self.logger.info(f"  - Preparando variação {var_nome}: código original='{var_codigo}' => sku='{variation_sku}', estoque={var_estoque}")
                
                # Construir variação com campos mínimos necessários E campo de atributo
                variation = {
                    "product_id": None,  # Será preenchido no momento da criação
                    "external_id": str(var_id),  # Garantir que seja string
                    "reference": var_codigo if var_codigo else f"{sku}-{var_id}",
                    "sku": variation_sku,
                    "code": variation_sku,  # Adicionar código para compatibilidade com APIs mais recentes
                    "gtin": var.get('codigo_barra', ""),
                    "price": float(f"{var_price:.2f}"),
                    "price_compare": float(f"{var_price:.2f}"),
                    "active": True if active else False,
                    "balance": var_estoque,  # Garantir que o estoque seja enviado
                    # IMPORTANTE: Adicionar atributos para a variação
                    # O valor do atributo deve corresponder ao nome/tipo da variação
                    "attributes": [
                        {
                            "name": "Opção",
                            "value": var_nome,  # Nome da variação como valor do atributo
                        }
                    ]
                }
                
                # Diagnóstico específico dos campos críticos que estavam faltando
                var_index = len(variations)  # Usar o comprimento atual da lista
                self.logger.info(f"🔍 DIAGNÓSTICO VARIAÇÃO #{var_index}: SKU='{variation['sku']}', REF='{variation['reference']}', CODE='{variation.get('code', 'AUSENTE')}', ESTOQUE={variation['balance']}")
                
                # Log específico para os campos críticos que estavam faltando
                self.logger.info(f"🔍 CAMPOS CRÍTICOS: SKU='{variation['sku']}', REFERÊNCIA='{variation['reference']}', ESTOQUE={variation['balance']}")
                
                # Log detalhado da variação para depuração
                self.logger.info(f"🧪 [TESTE-VAR] Variação preparada: SKU={variation_sku}, Nome={var_nome}, Código={var_codigo}, ID={var_id}")
                
                # Adicionar código de barras específico da variação, se disponível
                if var.get('codigo_barra'):
                    variation["gtin"] = var.get('codigo_barra')
                    
                variations.append(variation)
        
        # Se não tiver variações ou se o processamento falhar, criar uma variação padrão
        if not variations:
            # Construir variação padrão EXATAMENTE conforme o formato da documentação
            # Usando formato mínimo necessário conforme exemplos da API
            default_variation = {
                "product_id": None,  # Será preenchido depois no api_clients.py
                "external_id": product_id,  # ID do produto no GestãoClick
                "reference": sku,  # Referência da variação
                "sku": sku,  # SKU (código do produto)
                "code": sku,  # Código do produto para compatibilidade com API mais recente
                "gtin": barcode if barcode else "",  # Código de barras
                "price": float(price_formatted),  # Preço formatado (decimal)
                "price_compare": float(price_formatted),  # Preço de comparação (decimal)
                "active": True if active else False,  # Ativo como boolean (conforme documentação)
                "balance": stock,  # Estoque da variação (integer)
                # IMPORTANTE: Adicionar atributos para a variação padrão
                "attributes": [
                    {
                        "name": "Opção",
                        "value": "Padrão",  # Valor padrão para a variação única
                    }
                ]
            }
            
            # Log para depuração
            self.logger.info(f"🧪 [TESTE-VAR] Criando variação padrão: SKU='{sku}', Code='{sku}', Ref='{sku}'")
            
            # Adicionar código de barras na variação também, se disponível
            if barcode:
                default_variation["gtin"] = barcode
                
            variations = [default_variation]
            
        bagy_product["variations"] = variations
        
        # Adicionar categoria, se disponível
        if category_id:
            bagy_product["category_default_id"] = str(category_id)
            bagy_product["category_ids"] = [int(category_id)]  # array de integers
            
        # Adicionar campos meta se disponíveis
        bagy_product["meta_title"] = name[:250] if len(name) > 250 else name
        bagy_product["meta_description"] = name[:250] if len(name) > 250 else name
        bagy_product["meta_keywords"] = ""
        
        self.logger.debug(f"Converted product to Bagy: {bagy_product['name']}")
        return bagy_product
    
    def bagy_to_gestaoclick(self, bagy_product):
        """
        Convert a Bagy product to GestãoClick format.
        
        Args:
            bagy_product (dict): Product data from Bagy (Dooca API)
            
        Returns:
            dict: Product data in GestãoClick format (Betel API)
        """
        self.logger.debug(f"Converting product: {bagy_product.get('name', 'Unknown')}")
        
        # Extract SKU from variations or use external_id or id
        sku = None
        if 'variations' in bagy_product and bagy_product['variations'] and len(bagy_product['variations']) > 0:
            sku = bagy_product['variations'][0].get('sku') or bagy_product['variations'][0].get('reference') or bagy_product['variations'][0].get('id')
        
        if not sku:
            sku = bagy_product.get('external_id') or str(bagy_product.get('id', ''))
        
        # Determine if product is active
        active = "1" if bagy_product.get('active', True) else "0"
        
        # Extract price from Dooca format
        price = bagy_product.get('price', "0.00")
        cost_price = price  # Default cost price to sale price if not available
        
        # Extract category info
        category_name = ""
        category_id = ""
        if 'category_default' in bagy_product and bagy_product['category_default']:
            category_name = bagy_product['category_default'].get('name', '')
            category_id = str(bagy_product['category_default'].get('id', ''))
        
        # Extract weight and dimensions
        weight = bagy_product.get('weight')
        if weight:
            weight = str(weight).replace('.', ',')
        
        # Build GestãoClick product object (Betel API format)
        gestao_product = {
            'nome': bagy_product.get('name', ''),
            'codigo_interno': str(sku),  # Código interno (SKU)
            'codigo_barra': bagy_product.get('gtin', ''),  # Código de barras (GTIN/EAN)
            'ativo': active,
            'descricao': bagy_product.get('description', ''),
            'valor_custo': cost_price,
            'valor_venda': price,
            'estoque': 0  # Default to 0, we'll update if stock data is available
        }
        
        # Add weight if available
        if weight:
            gestao_product['peso'] = weight  # Atualizado de peso_bruto/peso_liquido para peso
        
        # Adicionar dimensões se disponíveis, convertendo de cm para metros
        # Bagy: dimensões em centímetros
        # GestãoClick: dimensões em metros
        if bagy_product.get('width'):
            try:
                # Converter de cm para m dividindo por 100
                width_cm = float(bagy_product.get('width', 0))
                width_m = width_cm / 100.0
                gestao_product['largura'] = str(round(width_m, 3)).replace('.', ',')
                self.logger.info(f"Convertendo largura: {width_cm} cm -> {width_m} m")
            except (ValueError, TypeError):
                gestao_product['largura'] = str(bagy_product.get('width', '')).replace('.', ',')
                
        if bagy_product.get('height'):
            try:
                # Converter de cm para m dividindo por 100
                height_cm = float(bagy_product.get('height', 0))
                height_m = height_cm / 100.0
                gestao_product['altura'] = str(round(height_m, 3)).replace('.', ',')
                self.logger.info(f"Convertendo altura: {height_cm} cm -> {height_m} m")
            except (ValueError, TypeError):
                gestao_product['altura'] = str(bagy_product.get('height', '')).replace('.', ',')
                
        if bagy_product.get('depth'):
            try:
                # Converter de cm para m dividindo por 100
                depth_cm = float(bagy_product.get('depth', 0))
                depth_m = depth_cm / 100.0
                gestao_product['comprimento'] = str(round(depth_m, 3)).replace('.', ',')
                self.logger.info(f"Convertendo profundidade: {depth_cm} cm -> {depth_m} m")
            except (ValueError, TypeError):
                gestao_product['comprimento'] = str(bagy_product.get('depth', '')).replace('.', ',')
        
        # Add category if available
        if category_id and category_name:
            gestao_product['grupo_id'] = category_id
            gestao_product['nome_grupo'] = category_name
        
        # Add NCM if available
        if bagy_product.get('ncm'):
            gestao_product['ncm'] = bagy_product.get('ncm', '')
        
        # Process variations and stock
        if 'variations' in bagy_product and bagy_product['variations']:
            total_stock = 0
            
            # Sum up stock from all variations
            for variation in bagy_product['variations']:
                total_stock += variation.get('balance', 0)
                
                # If the first variation has a price, use it as the base price
                if variation.get('price') and variation == bagy_product['variations'][0]:
                    gestao_product['valor_venda'] = variation.get('price')
            
            gestao_product['estoque'] = str(total_stock)
        
        self.logger.debug(f"Converted product: {gestao_product['nome']}")
        return gestao_product


class CustomerConverter(BaseConverter):
    """Convert customer data between Bagy and GestãoClick formats."""
    
    def __init__(self):
        super().__init__()
        # Pattern to match only numbers in a document
        self.doc_pattern = re.compile(r'\D')
        
    def clean_document(self, document):
        """
        Clean a document string to contain only numbers.
        
        Args:
            document (str): Document string (CPF/CNPJ)
            
        Returns:
            str: Cleaned document string
        """
        if not document:
            return ""
        
        # Remove non-digits
        return self.doc_pattern.sub('', document)
    
    def bagy_to_gestaoclick(self, bagy_customer):
        """
        Convert a Bagy customer to GestãoClick format.
        
        Args:
            bagy_customer (dict): Customer data from Bagy (Dooca API)
            
        Returns:
            dict: Customer data in GestãoClick format (Betel API)
        """
        self.logger.debug(f"Converting customer: {bagy_customer.get('name', 'Unknown')}")
        
        # Get full name
        first_name = bagy_customer.get('first_name', '')
        last_name = bagy_customer.get('last_name', '')
        name = bagy_customer.get('name', '')
        
        if not name and (first_name or last_name):
            name = f"{first_name} {last_name}".strip()
        
        # Clean and validate document (CGC can be either CPF or CNPJ)
        documento = self.clean_document(bagy_customer.get('cgc', ''))
        
        # Get document type based on length
        tipo_documento = "cpf" if len(documento) <= 11 else "cnpj"
        
        # Extract phone
        telefone = bagy_customer.get('phone', '')
        
        # Get customer address
        address = bagy_customer.get('address', {})
        
        # Build GestãoClick customer object (Betel API format)
        gestao_customer = {
            'nome': name,
            'email': bagy_customer.get('email', ''),
            'tipo_pessoa': 'PF' if len(documento) <= 11 else 'PJ',  # Tipo de pessoa PF (física) ou PJ (jurídica)
            'cpf_cnpj': documento,  # Atualizado de documento para cpf_cnpj
            'telefone': telefone,  # Atualizado de celular para telefone
            'observacao': 'Cliente importado da Bagy/Dooca'  # Atualizado de observacoes para observacao
        }
        
        # Add birthday if available
        if bagy_customer.get('birthday'):
            gestao_customer['data_nascimento'] = bagy_customer.get('birthday', '')
        
        # If it's a company, add company name and additional info
        if bagy_customer.get('entity') == 'company' or len(documento) > 11:
            company_name = bagy_customer.get('company', name)
            if company_name:
                gestao_customer['razao_social'] = company_name  # Atualizado de nome_fantasia para razao_social
                
            # If IE (Inscrição Estadual) is available
            if bagy_customer.get('ie'):
                gestao_customer['inscricao_estadual'] = bagy_customer.get('ie', '')
        
        # Add address if available
        endereco = {}
        if address:
            endereco = {
                'cep': address.get('zipcode', ''),
                'endereco': address.get('street', ''),
                'numero': address.get('number', ''),
                'complemento': address.get('detail', ''),
                'bairro': address.get('district', ''),
                'cidade': address.get('city', ''),
                'estado': address.get('state', ''),
                'pais': 'Brasil'
            }
            
            # Adicionar endereço apenas se tiver informações
            if any(endereco.values()):
                gestao_customer['endereco'] = endereco
        
        self.logger.debug(f"Converted customer: {gestao_customer['nome']}")
        return gestao_customer


class OrderConverter(BaseConverter):
    """Convert order data between Bagy and GestãoClick formats."""
    
    def format_date(self, date_str):
        """
        Format a date string to the required format.
        
        Args:
            date_str (str): Date string
            
        Returns:
            str: Formatted date string
        """
        if not date_str:
            return datetime.now().strftime('%Y-%m-%d')
        
        try:
            # Try different date formats
            for fmt in ['%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime('%Y-%m-%d')
                except ValueError:
                    continue
                
            # If no format works, return the original
            return date_str
        except Exception as e:
            self.logger.error(f"Error formatting date {date_str}: {str(e)}")
            return datetime.now().strftime('%Y-%m-%d')
    
    def bagy_to_gestaoclick(self, bagy_order, customer_id=None):
        """
        Convert a Bagy order to GestãoClick format.
        
        Args:
            bagy_order (dict): Order data from Bagy (Dooca API)
            customer_id (str, optional): GestãoClick customer ID
            
        Returns:
            dict: Order data in GestãoClick format (Betel API)
        """
        self.logger.debug(f"Converting order: {bagy_order.get('id', 'Unknown')}")
        
        # Map status from Dooca to Betel format
        status_mapping = {
            'pending': 'pendente',
            'approved': 'aprovado',
            'attended': 'em_andamento',
            'invoiced': 'faturado',
            'delivered': 'entregue',
            'canceled': 'cancelado',
            'archived': 'arquivado'
        }
        
        # Default to 'em_andamento' if status not found
        status = status_mapping.get(bagy_order.get('status', '').lower(), 'em_andamento')
        
        # Extract payment info
        payment = bagy_order.get('payment', {})
        payment_method = 'credit_card'  # Default
        
        if payment:
            method = payment.get('method', '').lower()
            if 'boleto' in method or 'billet' in method:
                payment_method = 'boleto'
            elif 'pix' in method:
                payment_method = 'pix'
            elif 'deposit' in method or 'transfer' in method:
                payment_method = 'deposito'
        
        # Get customer data
        customer = bagy_order.get('customer', {})
        
        # Create items list
        items = []
        for item in bagy_order.get('items', []):
            item_data = {
                'codigo': item.get('sku') or item.get('reference') or str(item.get('id', '')),  # Priorizar o campo SKU
                'nome': item.get('name', ''),  # Atualizado para 'nome'
                'quantidade': item.get('quantity', 1),
                'valor_unitario': item.get('price', 0),
                'valor_total': float(item.get('total', 0))
            }
            items.append(item_data)
        
        # Create shipping data if available
        endereco_entrega = {}
        address = bagy_order.get('address', {})
        fulfillment = bagy_order.get('fulfillment', {})
        
        if address:
            endereco_entrega = {
                'cep': address.get('zipcode', ''),
                'endereco': address.get('street', ''),
                'numero': address.get('number', ''),
                'complemento': address.get('detail', ''),
                'bairro': address.get('district', ''),
                'cidade': address.get('city', ''),
                'estado': address.get('state', '')
            }
        
        # Informações de envio
        envio = {}
        
        # Add tracking info if available
        if fulfillment:
            if fulfillment.get('shipping_code'):
                envio['codigo_rastreamento'] = fulfillment.get('shipping_code', '')
            if fulfillment.get('shipping_track_url'):
                envio['url_rastreamento'] = fulfillment.get('shipping_track_url', '')
            
            # Add invoice info if available
            if fulfillment.get('nfe_number'):
                envio['nota_fiscal'] = fulfillment.get('nfe_number', '')
        
        # Build order data in GestãoClick format (Betel API)
        order_date = self.format_date(bagy_order.get('created_at'))
        
        gestao_order = {
            'codigo': str(bagy_order.get('code', '')),  # Código do pedido (código externo)
            'data': order_date,  # Atualizado de data_venda para data
            'cliente_id': customer_id,  # ID do cliente no GestãoClick
            'cliente_nome': customer.get('name') if customer else '',  # Nome do cliente
            'cliente_documento': customer.get('cgc') if customer else '',  # Documento do cliente
            'cliente_email': customer.get('email') if customer else '',  # Email do cliente
            'cliente_telefone': customer.get('phone') if customer else '',  # Telefone do cliente
            'produtos': items,  # Atualizado de itens para produtos
            'valor_total': bagy_order.get('total', 0),  # Valor total do pedido
            'situacao': status,  # Atualizado de status para situacao
            'forma_pagamento': payment_method,  # Forma de pagamento
            'origem': 'Bagy/Dooca',  # Origem do pedido
            'codigo_origem': str(bagy_order.get('id', '')),  # ID original do pedido
            'observacao': 'Pedido importado da loja virtual Bagy/Dooca'  # Observações
        }
        
        # Adicionar endereço de entrega se disponível
        if endereco_entrega:
            gestao_order['endereco_entrega'] = endereco_entrega
            
        # Adicionar informações de envio se disponíveis
        if envio:
            gestao_order['envio'] = envio
        
        self.logger.debug(f"Converted order ID: {bagy_order.get('id', '')}")
        return gestao_order
