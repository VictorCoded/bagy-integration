from flask import Flask, request, jsonify

app = Flask(__name__)
produtos = []

@app.route("/v2/products", methods=["GET"])
def listar_produtos():
    return jsonify(produtos), 200

@app.route("/v2/products", methods=["POST"])
def criar_produto():
    produto = request.json  # aqui é onde o produto chega da requisição
    produto_id = len(produtos) + 1
    produto["id"] = produto_id
    produtos.append(produto)

    print(f"✅ Produto recebido: {produto.get('name')}")

    if "variations" in produto:
        print("📦 Variações recebidas:")
        for v in produto["variations"]:
            print(f" - {v.get('name')} | Preço: R${v.get('price')} | Estoque: {v.get('stock')}")

    return jsonify(produto), 201

@app.route("/v2/products/<int:produto_id>", methods=["DELETE"])
def deletar_produto(produto_id):
    global produtos
    produtos = [p for p in produtos if p.get("id") != produto_id]
    print(f"🗑️ Produto {produto_id} deletado (mock)")
    return "", 204

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
