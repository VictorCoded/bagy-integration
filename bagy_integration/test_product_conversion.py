"""
Teste para verificar a conversão de dimensões
"""
import logging
from models import ProductConverter

# Configurar logging para visualizar resultados
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def test_dimension_conversion():
    """Testa a conversão de dimensões em ambas as direções"""
    # Criar conversor
    converter = ProductConverter()
    
    # Produto do GestãoClick com dimensões válidas (em metros)
    gestao_product = {
        "nome": "Produto Teste",
        "descricao": "Uma descrição de teste",
        "codigo_interno": "TEST123",
        "codigo_barra": "789123456789",
        "ativo": "1",
        "valor_custo": "100,00",
        "valor_venda": "150,00",
        "estoque": "10",
        "altura": "0,15",  # 15 cm em metros (0,15m)
        "largura": "0,20",  # 20 cm em metros (0,20m)
        "comprimento": "0,25",  # 25 cm em metros (0,25m)
        "peso": "0,5"  # 500g em kg (0,5kg)
    }
    
    # Testar conversão GestãoClick -> Bagy
    print("Teste de conversão GestãoClick -> Bagy:")
    bagy_product = converter.gestaoclick_to_bagy(gestao_product)
    
    # Se for None ou uma tupla, significa que houve erro
    if bagy_product is None:
        print("Erro na conversão: resultado é None")
        return
        
    if not isinstance(bagy_product, dict):
        print(f"Erro na conversão: tipo inesperado {type(bagy_product)}")
        return
    
    # Extrair valores com segurança usando get()
    altura_convertida = bagy_product.get('height', 'N/A')
    largura_convertida = bagy_product.get('width', 'N/A')
    profundidade_convertida = bagy_product.get('depth', 'N/A')
    peso_convertido = bagy_product.get('weight', 'N/A')
    
    # Mostrar resultados
    print(f"Altura original: {gestao_product['altura']}m -> Convertida: {altura_convertida}cm")
    print(f"Largura original: {gestao_product['largura']}m -> Convertida: {largura_convertida}cm")
    print(f"Profundidade original: {gestao_product['comprimento']}m -> Convertida: {profundidade_convertida}cm")
    print(f"Peso original: {gestao_product['peso']}kg -> Mantido: {peso_convertido}kg")
    print("=" * 50)
    
    # Testar conversão Bagy -> GestãoClick
    print("Teste de conversão Bagy -> GestãoClick:")
    bagy_product_reverse = {
        "name": "Produto Teste Reverso",
        "description": "Uma descrição de teste para o reverso",
        "sku": "TEST456",
        "gtin": "789123456789",
        "active": True,
        "price": 200.00,
        "height": "15.0",  # 15 cm
        "width": "20.0",   # 20 cm
        "depth": "25.0",   # 25 cm
        "weight": "0.5"    # 0.5 kg
    }
    
    gestao_product_reverse = converter.bagy_to_gestaoclick(bagy_product_reverse)
    
    # Extrair valores com segurança usando get()
    altura_original = bagy_product_reverse.get('height', 'N/A')
    largura_original = bagy_product_reverse.get('width', 'N/A')
    profundidade_original = bagy_product_reverse.get('depth', 'N/A')
    peso_original = bagy_product_reverse.get('weight', 'N/A')
    
    altura_reconvertida = gestao_product_reverse.get('altura', 'N/A')
    largura_reconvertida = gestao_product_reverse.get('largura', 'N/A')
    comprimento_reconvertido = gestao_product_reverse.get('comprimento', 'N/A')
    peso_reconvertido = gestao_product_reverse.get('peso', 'N/A')
    
    # Mostrar resultados
    print(f"Altura original: {altura_original}cm -> Convertida: {altura_reconvertida}m")
    print(f"Largura original: {largura_original}cm -> Convertida: {largura_reconvertida}m")
    print(f"Profundidade original: {profundidade_original}cm -> Convertida: {comprimento_reconvertido}m")
    print(f"Peso original: {peso_original}kg -> Mantido: {peso_reconvertido}kg")

if __name__ == "__main__":
    test_dimension_conversion()