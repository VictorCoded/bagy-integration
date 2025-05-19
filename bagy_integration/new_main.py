"""
Aplicativo principal para sincronização de dados entre Bagy e GestãoClick.
Nova versão com suporte para execução contínua 24/7 e conversão de variações em produtos independentes.
Para implantação em Railway ou serviços semelhantes.
"""
import os
import sys
import logging
import argparse
from datetime import datetime
import time
import signal
import traceback
from dotenv import load_dotenv

# Importar clientes de API
from api_clients import BagyClient, GestaoClickClient

# Importar sincronizador bidirecional - VERSÃO NOVA - Cada variação é um produto independente
from new_bidirectional_synchronizer import BidirectionalSynchronizer

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='✅ %(asctime)s | %(name)s | %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"logs/sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log", mode='w')
    ]
)

# Desativar logs de bibliotecas externas
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)

# Obter logger principal
logger = logging.getLogger("root")

def get_api_client_instances():
    """
    Cria instâncias dos clientes de API usando chaves de ambiente.
    
    Returns:
        tuple: (BagyClient, GestaoClickClient)
    """
    # Verificar se as chaves de API estão definidas
    bagy_api_key = os.environ.get("BAGY_API_KEY")
    gestaoclick_api_key = os.environ.get("GESTAOCLICK_API_KEY")
    gestaoclick_secret_key = os.environ.get("GESTAOCLICK_SECRET_KEY")
    
    if not bagy_api_key:
        raise ValueError("Chave de API da Bagy não encontrada. Defina a variável de ambiente BAGY_API_KEY.")
    
    if not gestaoclick_api_key or not gestaoclick_secret_key:
        raise ValueError("Chaves de API do GestãoClick não encontradas. Defina as variáveis de ambiente GESTAOCLICK_API_KEY e GESTAOCLICK_SECRET_KEY.")
    
    # Criar instâncias
    bagy_client = BagyClient(bagy_api_key)
    gestaoclick_client = GestaoClickClient(gestaoclick_api_key, gestaoclick_secret_key)
    
    return bagy_client, gestaoclick_client

def handle_signal(signum, frame):
    """
    Lidar com sinais de interrupção (SIGINT, SIGTERM)
    """
    logger.info(f"Sinal recebido: {signum}. Encerrando sincronizador...")
    global should_stop
    should_stop = True

def main():
    """Função principal"""
    global should_stop
    should_stop = False
    
    # Parse de argumentos da linha de comando
    parser = argparse.ArgumentParser(description='Sincronizador Bagy-GestãoClick')
    parser.add_argument('--run-once', action='store_true', help='Executar uma única sincronização e sair')
    parser.add_argument('--interval', type=int, default=300, help='Intervalo de sincronização em segundos (padrão: 300)')
    args = parser.parse_args()
    
    # Registrar manipuladores de sinal
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    # Inicializar sincronizador
    try:
        logger.info("Initializing bidirectional synchronizer")
        bagy_client, gestaoclick_client = get_api_client_instances()
        synchronizer = BidirectionalSynchronizer(gestaoclick_client, bagy_client)
        
        # Configurar intervalo de sincronização
        synchronizer.set_sync_interval(args.interval)
        
        if args.run_once:
            # Modo de execução única
            logger.info("Running one-time synchronization")
            start_time = time.time()
            
            # Executar sincronização de todas as entidades
            logger.info("Synchronizing all entities bidirectionally")
            stats = synchronizer.sync_all()
            
            # Registrar tempo de execução
            duration = time.time() - start_time
            logger.info(f"Full bidirectional synchronization completed in {duration:.6f} seconds")
            logger.info(f"Products (GestãoClick → Bagy): {stats['products']['success']} successful, {stats['products']['errors']} errors")
            logger.info(f"Customers (Bagy → GestãoClick): {stats['customers']['success']} successful, {stats['customers']['errors']} errors")
            logger.info(f"Orders (Bagy → GestãoClick): {stats['orders']['success']} successful, {stats['orders']['errors']} errors")
            
        else:
            # Modo de execução contínua
            logger.info(f"Starting continuous synchronization with interval of {args.interval} seconds")
            synchronizer.start_continuous_sync()
            
            # Manter o processo em execução até receber sinal de parada
            while not should_stop:
                time.sleep(1)
            
            # Parar sincronização quando solicitado
            synchronizer.stop_continuous_sync()
            logger.info("Synchronization stopped gracefully")
        
    except Exception as e:
        logger.error(f"Critical error in synchronizer: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
    
    return 0

if __name__ == "__main__":
    # Criar diretório de logs se não existir
    os.makedirs("logs", exist_ok=True)
    
    # Criar diretório de dados se não existir
    os.makedirs("data", exist_ok=True)
    
    # Executar aplicativo principal
    sys.exit(main())