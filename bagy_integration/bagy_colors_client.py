"""
Implementação de métodos para gerenciar cores na API da Bagy.

Conforme documentação da API, as cores devem ser criadas via endpoint /colors
antes de serem utilizadas nas variações de produtos.
"""

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
    self.logger.info(f"Verificando se cor {color_name} existe na Bagy")
    
    # Verificar se cor já existe
    existing_colors = self.get_colors()
    if existing_colors and 'data' in existing_colors:
        for color in existing_colors['data']:
            if color.get('name').lower() == color_name.lower():
                self.logger.info(f"Cor {color_name} já existe (ID: {color.get('id')})")
                return color.get('id')
    
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
        return response['id']
    else:
        self.logger.error(f"Não foi possível garantir que a cor {color_name} exista")
        return None