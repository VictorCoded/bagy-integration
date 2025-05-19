"""
Versão atualizada do ponto de entrada principal da aplicação, 
integrando o novo tratamento de variações como produtos independentes.
"""
import os
import logging
import time
import argparse
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

import config
from storage import IncompleteProductsStorage, EntityMapping, SyncHistory
from new_product_converter import ProductConverter
from solucao_final import VariationHandler
from sync_integrator import SyncIntegrator
from api_clients import BagyClient, GestaoClickClient

# Configurar logging
config.setup_logging()
logger = logging.getLogger(__name__)

def verify_env_vars():
    """
    Verificar se as variáveis de ambiente necessárias estão presentes.
    
    Returns:
        tuple: (True, None) se OK, (False, mensagem) se faltar alguma variável
    """
    required_vars = [
        'BAGY_API_KEY',
        'GESTAOCLICK_API_KEY', 
        'GESTAOCLICK_EMAIL',
        'BAGY_BASE_URL',
        'GESTAOCLICK_BASE_URL'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        return False, f"Variáveis de ambiente requeridas não encontradas: {', '.join(missing_vars)}"
    
    return True, None

def run_sync():
    """
    Executa uma sincronização única (não agendada).
    """
    logger.info("Executando sincronização única")
    
    # Verificar variáveis de ambiente
    env_ok, message = verify_env_vars()
    if not env_ok:
        logger.error(f"❌ {message}")
        return
    
    # Criar clientes de API
    bagy_client = BagyClient(
        api_key=os.environ.get('BAGY_API_KEY'),
        base_url=os.environ.get('BAGY_BASE_URL')
    )
    
    gestaoclick_client = GestaoClickClient(
        api_key=os.environ.get('GESTAOCLICK_API_KEY'),
        secret_key=os.environ.get('GESTAOCLICK_EMAIL'),
        base_url=os.environ.get('GESTAOCLICK_BASE_URL')
    )
    
    # Criar armazenamentos
    storage_dir = os.environ.get('STORAGE_DIR', './data')
    os.makedirs(storage_dir, exist_ok=True)
    
    incomplete_products = IncompleteProductsStorage(f"{storage_dir}/incomplete_products.json")
    entity_mapping = EntityMapping(f"{storage_dir}/entity_mapping.json")
    sync_history = SyncHistory(f"{storage_dir}/sync_history.json")
    
    # Criar o conversor de produtos
    product_converter = ProductConverter(incomplete_products_storage=incomplete_products)
    
    # Criar integrador de sincronização com o novo gerenciador de variações
    sync_integrator = SyncIntegrator(
        gestaoclick_client=gestaoclick_client,
        bagy_client=bagy_client,
        product_converter=product_converter,
        entity_mapping=entity_mapping,
        incomplete_products_storage=incomplete_products
    )
    
    # Registrar início da sincronização
    start_time = datetime.now()
    logger.info(f"Iniciando sincronização completa em {start_time}")
    
    # Sincronizar produtos (GestãoClick -> Bagy)
    stats = sync_integrator.sync_products_to_bagy()
    
    # Registrar fim da sincronização
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Registrar estatísticas da sincronização
    logger.info(f"Sincronização completa em {duration:.2f} segundos")
    logger.info(f"Produtos (GestãoClick → Bagy): {stats['success']} com sucesso, {stats['errors']} erros, {stats['incomplete']} incompletos")
    
    # Registrar histórico da sincronização
    sync_history.add_sync_record(
        start_time=start_time.isoformat(),
        end_time=end_time.isoformat(),
        duration=duration,
        products_success=stats['success'],
        products_errors=stats['errors'],
        products_incomplete=stats['incomplete'],
        customers_success=0,
        customers_errors=0,
        orders_success=0,
        orders_errors=0
    )
    
    logger.info("Sincronização concluída!")

def scheduled_sync_job():
    """
    Função de sincronização agendada pelo scheduler.
    """
    logger.info("Executando sincronização agendada")
    try:
        run_sync()
        logger.info("Sincronização agendada concluída com sucesso")
    except Exception as e:
        logger.error(f"Erro durante sincronização agendada: {str(e)}")

def start_scheduler():
    """
    Iniciar o scheduler para execução periódica da sincronização.
    """
    # Obter intervalo de sincronização (em minutos) do ambiente
    sync_interval = int(os.environ.get('SYNC_INTERVAL_MINUTES', 60))
    logger.info(f"Configurando sincronização automática a cada {sync_interval} minutos")
    
    # Criar e configurar o scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_sync_job, 'interval', minutes=sync_interval)
    scheduler.start()
    
    logger.info("Scheduler iniciado com sucesso!")
    
    return scheduler

def main():
    """Função principal para execução do sincronizador."""
    logger.info("Inicializando sincronizador bidirecional")
    
    parser = argparse.ArgumentParser(description='Sincronizador Bidirecional Bagy <-> GestãoClick')
    parser.add_argument('--run-once', action='store_true', help='Executar sincronização uma única vez e sair')
    args = parser.parse_args()
    
    if args.run_once:
        logger.info("Executando sincronização única")
        run_sync()
        return
    
    # Executar uma sincronização inicial
    logger.info("Executando sincronização inicial")
    try:
        run_sync()
    except Exception as e:
        logger.error(f"Erro durante sincronização inicial: {str(e)}")
    
    # Iniciar o scheduler para sincronizações periódicas
    scheduler = start_scheduler()
    
    # Manter a aplicação em execução
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Encerrando aplicação")
        scheduler.shutdown()

if __name__ == "__main__":
    main()