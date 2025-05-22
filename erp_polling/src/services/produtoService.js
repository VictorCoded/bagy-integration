const axios = require("axios");
const fs = require("fs");
const path = require("path");

const accessToken = "194c67425b6083fddab6afa899d09f9845d68589";
const secretToken = "1a8cd45d5b2527b88de64f47c2ca4bfe7b76ed07";

async function buscarProdutos() {
  try {
    const produtosBase = await axios.get("https://api.gestaoclick.com/api/produtos", {
      headers: {
        "access-token": accessToken,
        "secret-access-token": secretToken,
      },
    });

    const produtos = produtosBase.data?.data || produtosBase.data;
    const produtosCompletos = [];

    for (const produto of produtos) {
      const id = produto.id;
      let variacoes = [];

      try {
        const resVar = await axios.get(`https://api.gestaoclick.com/api/produtos/${id}/variacoes`, {
          headers: {
            "access-token": accessToken,
            "secret-access-token": secretToken,
          },
        });

        variacoes = resVar.data?.data || resVar.data;
      } catch (e) {
        console.warn(`[WARN] Sem variações para produto ID ${id}`);
      }

      produtosCompletos.push({
        ...produto,
        possui_variacao: variacoes.length > 0 ? "1" : "0",
        variacoes: variacoes.map((v) => ({
          nome: v.nome,
          preco_venda: v.preco_venda,
          estoque: v.estoque,
          sku: v.codigo_barra,
        })),
        valores: variacoes.map((v) => ({
          variacao: v.nome,
          preco_venda: v.preco_venda,
        })),
      });
    }

    const outputPath = path.join(__dirname, "../../data/produtos.json");
    fs.writeFileSync(outputPath, JSON.stringify(produtosCompletos, null, 2));
    console.log(`[OK] ${produtosCompletos.length} produtos com variações salvos.`);
  } catch (error) {
    console.error("[ERRO] Falha ao buscar produtos:", error.response?.data || error.message);
  }
}

module.exports = { buscarProdutos };
