const axios = require('axios');
const fs = require('fs');
const path = require('path');

const accessToken = '194c67425b6083fddab6afa899d09f9845d68589';
const secretToken = '1a8cd45d5b2527b88de64f47c2ca4bfe7b76ed07';

async function buscarProdutos() {
    try {
        const res = await axios.get('https://api.gestaoclick.com/api/produtos', {
            headers: {
                'access-token': accessToken,
                'secret-access-token': secretToken,
            },
        });

        console.log("[DEBUG] Resposta da API GestãoClick:", res.data);

        const produtos = res.data?.data || res.data;

        fs.writeFileSync(
            path.join(__dirname, '../../data/produtos.json'),
            JSON.stringify(produtos, null, 2)
        );

        console.log(`[OK] ${produtos.length} produtos salvos.`);
    } catch (error) {
        console.error("[ERRO] Falha ao buscar produtos:", error.response?.data || error.message);
    }
}


module.exports = { buscarProdutos };