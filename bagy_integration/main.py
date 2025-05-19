"""
Main entry point for the Bagy to GestãoClick synchronization tool.
Versão final com suporte completo para variações como produtos independentes.
"""
import os
import sys
import argparse
import logging
import config
from variacao_bidirectional_synchronizer import VariacaoBidirectionalSynchronizer
from new_product_converter import ProductConverter
from storage import IncompleteProductsStorage
from app import app  # Import the Flask app for Gunicorn

def main():
    """Main function to run the synchronization tool."""
    # Set up logging
    logger = config.setup_logging()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Bagy to GestãoClick Synchronization Tool')
    parser.add_argument('--run-once', action='store_true', help='Run synchronization once and exit')
    parser.add_argument('--interval', type=int, help='Sync interval in minutes')
    parser.add_argument('--entity', choices=['products_to_bagy', 'customers', 'orders', 'all'], 
                       default='all', help='Entity to synchronize')
    args = parser.parse_args()
    
    # Verify API keys and credentials
    if not config.BAGY_API_KEY:
        logger.error("Bagy API key not provided. Set BAGY_API_KEY environment variable.")
        sys.exit(1)
    
    if not config.GESTAOCLICK_API_KEY or not config.GESTAOCLICK_EMAIL:
        logger.error("GestãoClick credentials not provided. Set GESTAOCLICK_API_KEY and GESTAOCLICK_EMAIL environment variables.")
        sys.exit(1)
    
    # Criar armazenamentos
    storage_dir = config.STORAGE_DIR
    os.makedirs(storage_dir, exist_ok=True)
    
    # Criar o armazenamento de produtos incompletos
    incomplete_products = IncompleteProductsStorage(f"{storage_dir}/incomplete_products.json")
    
    # Criar o conversor de produtos com suporte a variações
    product_converter = ProductConverter(incomplete_products_storage=incomplete_products)
    
    # Initialize synchronizer with variation support
    logger.info("Initializing bidirectional synchronizer with variation support")
    synchronizer = VariacaoBidirectionalSynchronizer(
        product_converter=product_converter,
        incomplete_products_storage=incomplete_products
    )
    
    if args.run_once:
        # Run synchronization once
        logger.info("Running one-time synchronization")
        
        if args.entity == 'products_to_bagy':
            logger.info("Synchronizing products from GestãoClick to Bagy only")
            product_success, product_errors = synchronizer.sync_products_from_gestaoclick()
            logger.info(f"Product synchronization to Bagy completed: {product_success} successful, {product_errors} errors")
        elif args.entity == 'customers':
            logger.info("Synchronizing customers from Bagy to GestãoClick only")
            customer_success, customer_errors = synchronizer.sync_customers()
            logger.info(f"Customer synchronization to GestãoClick completed: {customer_success} successful, {customer_errors} errors")
        elif args.entity == 'orders':
            logger.info("Synchronizing orders from Bagy to GestãoClick only")
            order_success, order_errors = synchronizer.sync_orders()
            logger.info(f"Order synchronization to GestãoClick completed: {order_success} successful, {order_errors} errors")
        else:
            logger.info("Synchronizing all entities bidirectionally")
            results = synchronizer.sync_all()
            logger.info(f"Full bidirectional synchronization completed in {results['duration_seconds']} seconds")
            logger.info(f"Products (GestãoClick → Bagy): {results['products_to_bagy']['success']} successful, {results['products_to_bagy']['errors']} errors")
            logger.info(f"Customers (Bagy → GestãoClick): {results['customers_to_gestaoclick']['success']} successful, {results['customers_to_gestaoclick']['errors']} errors")
            logger.info(f"Orders (Bagy → GestãoClick): {results['orders_to_gestaoclick']['success']} successful, {results['orders_to_gestaoclick']['errors']} errors")
    else:
        # Run scheduled synchronization
        interval = args.interval or config.SYNC_INTERVAL_MINUTES
        logger.info(f"Starting scheduled synchronization every {interval} minutes")
        synchronizer.start_scheduled_sync(interval)

if __name__ == "__main__":
    main()
