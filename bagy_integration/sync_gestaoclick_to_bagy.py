
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
        self.base_url = "https://api.dooca.store/"
        self.api_key = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzaG9wX2lkIjoxNjY2OTMsInR5cGUiOiJhcGkiLCJlbWFpbCI6IjUwMTEwOTYzODY4OTMwNzgwMDAwLmJhZ3lAYXBpLmNvbS5iciIsImZpcnN0X25hbWUiOiJBUEkgQmFneSBTZXggRmlyZSIsImFjdGl2ZSI6dHJ1ZSwiaWF0IjoxNzQxODAxNjU5fQ.FnoqxouQZ9iq3S05tx_wGWURZ916xDxFMDjKGEJLV48"

    def _make_request(self, method, endpoint, json_data=None, retries=3):
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        for attempt in range(retries):
            try:
                response = requests.request(method, url, headers=headers, json=json_data, timeout=10)
                if not response.ok:
                    raise Exception(f"Erro {response.status_code}: {response.text}")
                return response.json()
            except requests.exceptions.RequestException as e:
                print(f"⚠️ Tentativa {attempt + 1} falhou: {e}")
                time.sleep(2)
        raise Exception(f"Erro após {retries} tentativas: não foi possível acessar {url}")

    def list_all_products(self):
        return self._make_request("GET", "products")

    def delete_product(self, product_id):
        endpoint = f"products/{product_id}"
        try:
            response = requests.request("DELETE", f"{self.base_url}{endpoint}", headers={
                "Authorization": f"Bearer {self.api_key}"
            }, timeout=30)
            if response.ok:
                print(f"🗑️ Produto {product_id} deletado com sucesso.")
            else:
                print(f"Erro ao deletar produto {product_id}: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Erro ao deletar produto {product_id}: {e}")

    def create_product(self, product_data):
        self.logger.info(f"Creating new product in Bagy: {product_data['name']}")
        return self._make_request("POST", "products", json_data=product_data)

def carregar_produtos_do_gestaoclick():
    with open('data/produtos.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def converter_para_bagy(produto):
    def safe_float(value, default=0.1):
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    imagens = []
    for url in produto.get("fotos", []):
        if isinstance(url, str) and url.strip().startswith("http"):
            imagens.append({"src": url.strip()})

    if not imagens:
        imagens = [{"src": "https://upload-arquivos.s3.sa-east-1.amazonaws.com/img/produtos_fotos/imagem-padrao.png"}]

    if produto.get("possui_variacao") == "1":
        tipo_variacao = produto.get("variacoes", [{}])[0].get("nome") or "Tamanho"
        nomes_ja_adicionados = set()
        variacoes = []

        for valor in produto.get("valores", []):
            nome_var = valor.get("variacao")
            if nome_var in nomes_ja_adicionados:
                continue
            nomes_ja_adicionados.add(nome_var)

            variacoes.append({
                "name": nome_var,
                "price": safe_float(valor.get("preco_venda")),
                "stock": int(produto.get("estoque", 0)),
                "attributes": {tipo_variacao: nome_var},
                "reference": str(produto.get("codigo_interno") or ""),
                "sku": str(valor.get("codigo_barra") or f"SKU{produto.get('id')}-{nome_var}"),
                "images": imagens if imagens else [{"src": "https://upload-arquivos.s3-sa-east-1.amazonaws.com/img/produtos_fotos/imagem-padrao.png"}]
            })

        return {
            "name": produto.get("nome"),
            "description": produto.get("descricao", ""),
            "code": str(produto.get("id")),
            "external_id": f"{produto.get('id')}-{int(time.time())}",
            "reference": str(produto.get("codigo_interno") or ""),
            "sku": str(produto.get("codigo_barra") or f"SKU{produto.get('id')}"),
            "active": produto.get("ativo") == "1",
            "variations": variacoes,
            "images": imagens if imagens else [{"src": "https://upload-arquivos.s3-sa-east-1.amazonaws.com/img/produtos_fotos/imagem-padrao.png"}]
        }

    return {
        "name": produto.get("nome"),
        "description": produto.get("descricao", ""),
        "price": safe_float(produto.get("valor_venda")),
        "cost_price": safe_float(produto.get("valor_custo")),
        "stock": int(produto.get("estoque", 0)),
        "reference": str(produto.get("codigo_interno") or ""),
        "sku": str(produto.get("codigo_barra") or f"SKU{produto.get('id')}"),
        "code": str(produto.get("id")),
        "external_id": f"{produto.get('id')}-{int(time.time())}",
        "weight": safe_float(produto.get("peso")),
        "width": safe_float(produto.get("largura")),
        "height": safe_float(produto.get("altura")),
        "depth": safe_float(produto.get("comprimento")),
        "active": produto.get("ativo") == "1",
        "images": imagens if imagens else [{"src": "https://upload-arquivos.s3-sa-east-1.amazonaws.com/img/produtos_fotos/imagem-padrao.png"}]

        if not imagens:
    print(f"[AVISO] Produto '{produto.get('nome')}' está sem imagens válidas.")

    }

def excluir_todos_os_produtos(cliente_bagy):
    try:
        produtos_existentes = cliente_bagy.list_all_products()
        data = produtos_existentes.get("data") if isinstance(produtos_existentes, dict) and "data" in produtos_existentes else produtos_existentes
        for produto in data:
            cliente_bagy.delete_product(produto['id'])
    except Exception as e:
        print("Erro ao excluir produtos:", e)

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
