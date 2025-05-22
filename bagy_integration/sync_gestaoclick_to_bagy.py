import json
import requests
import time

class DummyLogger:
    def info(self, msg):
        print("[INFO]", msg)
    def error(self, msg):
        print("[ERROR]", msg)

class BagyClient:
    def __init__(self):
        self.logger = DummyLogger()
        self.created_products = []
        self.base_url = "https://api.bagy.com.br"
        self.api_key = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzaG9wX2lkIjoxNjY2OTMsInR5cGUiOiJhcGkiLCJlbWFpbCI6IjUwMTEwOTYzODY4OTMwNzgwMDAwLmJhZ3lAYXBpLmNvbS5iciIsImZpcnN0X25hbWUiOiJBUEkgQmFneSBTZXggRmlyZSIsImFjdGl2ZSI6dHJ1ZSwiaWF0IjoxNzQxODAxNjU5fQ.FnoqxouQZ9iq3S05tx_wGWURZ916xDxFMDjKGEJLV48"

    def _make_request(self, method, endpoint, json=None):
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        response = requests.request(method, url, headers=headers, json=json, timeout=30)

        if not response.ok:
            raise Exception(f"Erro {response.status_code}: {response.text}")

        return response.json()

    def create_product(self, product_data):
        self.logger.info(f"Creating new product in Bagy: {product_data['name']}")
        response = self._make_request("POST", "/v2/products", json=product_data)
        return response

    def get_product_by_external_id(self, external_id):
        return None  # pode ser implementado depois

def carregar_produtos_do_gestaoclick():
    with open('data/produtos.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def converter_para_bagy(produto):
    return {
        'name': produto.get('nome'),
        'description': produto.get('descricao', ''),
        'price': float(produto.get('valor_venda', 0)),
        'cost_price': float(produto.get('valor_custo', 0)),
        'stock': int(produto.get('estoque', 0)),
        'sku': str(produto.get('codigo_interno') or f"SKU{produto.get('id')}"),
        'reference': str(produto.get('codigo_barra') or ''),
        'code': str(produto.get('id')),
        'external_id': str(produto.get('id')),
        'weight': float(produto.get('peso', 0.1)),
        'width': float(produto.get('largura', 0.1)),
        'height': float(produto.get('altura', 0.1)),
        'depth': float(produto.get('comprimento', 0.1)),
        'active': produto.get('ativo') == '1'
    }

def main():
    cliente_bagy = BagyClient()
    excluir_todos_os_produtos(cliente_bagy)
    produtos = carregar_produtos_do_gestaoclick()
    for produto in produtos:
        if produto.get('ativo') != '1':
            continue
        try:
            produto_formatado = converter_para_bagy(produto)
            resposta = cliente_bagy.create_product(produto_formatado)
            print("✅ Produto enviado:", resposta.get('name'))
        except Exception as e:
            print("❌ Erro ao enviar produto:", produto.get("nome"), e)

if __name__ == '__main__':
    main()
