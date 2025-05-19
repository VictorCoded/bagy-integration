"""
Flask app para fornecer endpoints de API REST para o serviço de sincronização Bagy-GestãoClick.
Inclui verificação de status, estatísticas e gerenciamento de produtos incompletos.
"""
from flask import Flask, jsonify, request
import os
import sys
import logging
import json
from datetime import datetime

# Importar a classe BidirectionalSynchronizer para acessar os dados de sincronização
# Vamos usar a implementação atualizada da sincronização
# from sync import BidirectionalSynchronizer
from storage import IncompleteProductsStorage

# Não vamos usar um sincronizador global, pois agora usamos a implementação atualizada
# O app.py será apenas para gerenciar endpoints REST
incomplete_products = IncompleteProductsStorage('data/incomplete_products.json')

# Create the Flask app
app = Flask(__name__)

def get_sync_info():
    """Get synchronization info from log files and storage."""
    try:
        # Check if logs directory exists
        if not os.path.exists('logs/sync.log'):
            return {
                'status': 'Not Started',
                'last_run': None,
                'errors': None
            }
        
        # Read the last 20 lines of the log file
        with open('logs/sync.log', 'r') as f:
            # Get the last 20 lines
            lines = f.readlines()[-20:]
            
            # Parse log for status info
            status = 'Unknown'
            errors = []
            last_run = None
            
            for line in lines:
                if 'Starting full synchronization at' in line:
                    timestamp = line.split('at ')[1].strip()
                    last_run = timestamp
                    status = 'Running'
                elif 'Full synchronization completed in' in line:
                    status = 'Completed'
                elif 'ERROR' in line:
                    errors.append(line.strip())
            
            return {
                'status': status,
                'last_run': last_run,
                'errors': errors if errors else None
            }
    except Exception as e:
        return {
            'status': 'Error',
            'error': str(e)
        }

@app.route('/')
def index():
    """Health check endpoint."""
    return jsonify({
        'status': 'OK',
        'message': 'Bidirectional Synchronization Tool for Bagy and GestãoClick',
        'time': datetime.now().isoformat(),
        'sync_info': get_sync_info()
    })

@app.route('/api/incomplete-products/statistics', methods=['GET'])
def get_incomplete_products_statistics():
    """
    Retorna estatísticas de produtos incompletos.
    """
    try:
        stats = synchronizer.get_incomplete_products_statistics()
        return jsonify({
            'status': 'success',
            'data': stats
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/incomplete-products', methods=['GET'])
def get_incomplete_products():
    """
    Retorna lista de todos os produtos incompletos.
    """
    try:
        products = synchronizer.get_all_incomplete_products()
        return jsonify({
            'status': 'success',
            'data': products
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/incomplete-products/<product_id>', methods=['DELETE'])
def clear_incomplete_product(product_id):
    """
    Remove um produto da lista de produtos incompletos.
    Útil quando o produto foi corrigido manualmente no GestãoClick.
    """
    try:
        result = synchronizer.clear_incomplete_product(product_id)
        if result:
            return jsonify({
                'status': 'success',
                'message': f'Produto {product_id} removido da lista de incompletos'
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': f'Não foi possível remover o produto {product_id}'
            }), 400
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/sync/run', methods=['POST'])
def run_sync():
    """
    Executa uma sincronização única (não agendada).
    """
    try:
        results = synchronizer.sync_all()
        return jsonify({
            'status': 'success',
            'message': 'Sincronização concluída com sucesso',
            'data': results
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))