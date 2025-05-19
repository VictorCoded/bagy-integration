const cron = require('node-cron');
const { buscarProdutos } = require('./produtoService');

module.exports = function () {
    console.log('Iniciando serviço de polling...');
    cron.schedule('*/5 * * * *', async () => {
        console.log('[Polling] Verificando novos produtos...');
        await buscarProdutos();
    });
    buscarProdutos();
};
