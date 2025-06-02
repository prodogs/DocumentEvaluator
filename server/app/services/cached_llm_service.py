"""
Cached LLM Service

Demonstrates how to use caching and async functionality for LLM calls.
"""

import hashlib
import json
from typing import Dict, Any, Optional, List

from app.core.cache import cache, cached, cache_result
from app.core.logger import get_logger, get_performance_logger
from app.utils.async_utils import AsyncLLMProcessor, process_documents_sync

logger = get_logger(__name__)
perf_logger = get_performance_logger('llm_service')


class CachedLLMService:
    """LLM service with caching and performance optimization"""
    
    def __init__(self):
        self.cache_ttl = 3600  # 1 hour default
    
    def _generate_cache_key(self, provider_id: int, prompt_id: int, 
                          document_content: str) -> str:
        """Generate cache key for LLM response"""
        # Create hash of content to handle long documents
        content_hash = hashlib.md5(document_content.encode()).hexdigest()
        return f"llm_response:{provider_id}:{prompt_id}:{content_hash}"
    
    @cache_result(timeout=3600)
    def get_provider_config(self, provider_id: int) -> Optional[Dict[str, Any]]:
        """Get provider configuration with caching"""
        from database import Session
        from models import Connection, Model, LlmProvider
        
        session = Session()
        try:
            connection = session.query(Connection).filter_by(id=provider_id).first()
            if not connection:
                return None
            
            model = session.query(Model).filter_by(id=connection.model_id).first()
            provider = session.query(LlmProvider).filter_by(id=connection.provider_id).first()
            
            return {
                'id': connection.id,
                'name': connection.name,
                'type': provider.provider_type if provider else 'unknown',
                'api_key': connection.api_key,
                'base_url': connection.base_url,
                'model': model.model_name if model else connection.model_name,
                'temperature': connection.temperature,
                'max_tokens': connection.max_tokens
            }
        finally:
            session.close()
    
    def process_document_cached(self, provider_id: int, prompt_id: int,
                              document: Dict[str, Any]) -> Dict[str, Any]:
        """Process single document with caching"""
        import time
        start_time = time.time()
        
        # Generate cache key
        cache_key = self._generate_cache_key(
            provider_id, prompt_id, document.get('content', '')
        )
        
        # Check cache first
        if cache:
            cached_response = cache.get(cache_key)
            if cached_response:
                logger.info(f"Cache hit for document {document.get('id')}")
                perf_logger.log_operation(
                    'llm_cache_hit',
                    time.time() - start_time,
                    metadata={'document_id': document.get('id')}
                )
                return cached_response
        
        # Get provider config
        provider_config = self.get_provider_config(provider_id)
        if not provider_config:
            return {
                'success': False,
                'error': f'Provider {provider_id} not found',
                'document_id': document.get('id')
            }
        
        # Get prompt
        prompt_text = self._get_prompt_text(prompt_id)
        if not prompt_text:
            return {
                'success': False,
                'error': f'Prompt {prompt_id} not found',
                'document_id': document.get('id')
            }
        
        # Process with LLM (using async under the hood)
        result = process_documents_sync(
            [document], [provider_config], [{'text': prompt_text}]
        )[0]
        
        # Cache successful responses
        if result.get('success') and cache:
            cache.set(cache_key, result, timeout=self.cache_ttl)
            logger.info(f"Cached response for document {document.get('id')}")
        
        perf_logger.log_operation(
            'llm_process',
            time.time() - start_time,
            success=result.get('success', False),
            metadata={
                'document_id': document.get('id'),
                'cached': False,
                'provider': provider_config['name']
            }
        )
        
        return result
    
    def process_batch_cached(self, batch_id: int) -> Dict[str, Any]:
        """Process entire batch with caching and parallel execution"""
        import time
        from database import Session
        from models import Batch, Document
        
        start_time = time.time()
        results = {
            'batch_id': batch_id,
            'total': 0,
            'cached': 0,
            'processed': 0,
            'failed': 0,
            'responses': []
        }
        
        session = Session()
        try:
            # Get batch configuration
            batch = session.query(Batch).filter_by(id=batch_id).first()
            if not batch or not batch.config_snapshot:
                return {'success': False, 'error': 'Batch not found or missing config'}
            
            config = batch.config_snapshot
            connection_ids = [c['id'] for c in config.get('connections', [])]
            prompt_ids = [p['id'] for p in config.get('prompts', [])]
            
            # Get documents
            documents = session.query(Document).filter_by(batch_id=batch_id).all()
            
            # Process each combination
            for doc in documents:
                doc_dict = {
                    'id': doc.id,
                    'content': doc.content,
                    'filename': doc.filename
                }
                
                for conn_id in connection_ids:
                    for prompt_id in prompt_ids:
                        results['total'] += 1
                        
                        # Check if we have cached response
                        cache_key = self._generate_cache_key(
                            conn_id, prompt_id, doc.content
                        )
                        
                        if cache:
                            cached_response = cache.get(cache_key)
                            if cached_response:
                                results['cached'] += 1
                                results['responses'].append(cached_response)
                                continue
                        
                        # Process document
                        response = self.process_document_cached(
                            conn_id, prompt_id, doc_dict
                        )
                        
                        if response.get('success'):
                            results['processed'] += 1
                        else:
                            results['failed'] += 1
                        
                        results['responses'].append(response)
            
            # Log performance
            duration = time.time() - start_time
            perf_logger.log_operation(
                'batch_process',
                duration,
                success=True,
                metadata={
                    'batch_id': batch_id,
                    'total': results['total'],
                    'cached': results['cached'],
                    'cache_hit_rate': round(results['cached'] / max(results['total'], 1) * 100, 2)
                }
            )
            
            logger.info(
                f"Batch {batch_id} processed: {results['total']} total, "
                f"{results['cached']} cached ({results['cached']/max(results['total'], 1)*100:.1f}% hit rate)"
            )
            
            return {
                'success': True,
                'results': results,
                'duration': duration
            }
            
        except Exception as e:
            logger.error(f"Error processing batch {batch_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'results': results
            }
        finally:
            session.close()
    
    def _get_prompt_text(self, prompt_id: int) -> Optional[str]:
        """Get prompt text with caching"""
        @cache_result(timeout=3600)
        def _fetch_prompt(pid):
            from database import Session
            from models import Prompt
            
            session = Session()
            try:
                prompt = session.query(Prompt).filter_by(id=pid).first()
                return prompt.prompt_text if prompt else None
            finally:
                session.close()
        
        return _fetch_prompt(prompt_id)
    
    def invalidate_provider_cache(self, provider_id: int):
        """Invalidate cache for a specific provider"""
        if cache:
            pattern = f"llm_response:{provider_id}:*"
            count = cache.clear(pattern)
            logger.info(f"Invalidated {count} cache entries for provider {provider_id}")
    
    def get_cache_stats_for_batch(self, batch_id: int) -> Dict[str, Any]:
        """Get cache statistics for a batch"""
        from database import Session
        from models import Batch, Document
        
        session = Session()
        try:
            batch = session.query(Batch).filter_by(id=batch_id).first()
            if not batch or not batch.config_snapshot:
                return {'error': 'Batch not found'}
            
            config = batch.config_snapshot
            connection_ids = [c['id'] for c in config.get('connections', [])]
            prompt_ids = [p['id'] for p in config.get('prompts', [])]
            
            documents = session.query(Document).filter_by(batch_id=batch_id).all()
            
            total_combinations = len(documents) * len(connection_ids) * len(prompt_ids)
            cached_count = 0
            
            if cache:
                for doc in documents:
                    for conn_id in connection_ids:
                        for prompt_id in prompt_ids:
                            cache_key = self._generate_cache_key(
                                conn_id, prompt_id, doc.content
                            )
                            if cache.get(cache_key):
                                cached_count += 1
            
            return {
                'batch_id': batch_id,
                'total_combinations': total_combinations,
                'cached': cached_count,
                'cache_hit_rate': round(cached_count / max(total_combinations, 1) * 100, 2),
                'potential_time_saved': cached_count * 2  # Assume 2 seconds per LLM call
            }
            
        finally:
            session.close()


# Example usage in routes
def create_cached_llm_routes(app):
    """Create routes that demonstrate cached LLM usage"""
    
    service = CachedLLMService()
    
    @app.route('/api/llm/process-cached', methods=['POST'])
    def process_with_cache():
        """Process document with caching"""
        from flask import request, jsonify
        
        data = request.get_json()
        result = service.process_document_cached(
            data['provider_id'],
            data['prompt_id'],
            data['document']
        )
        return jsonify(result)
    
    @app.route('/api/llm/cache-stats/<int:batch_id>')
    def get_batch_cache_stats(batch_id):
        """Get cache statistics for batch"""
        from flask import jsonify
        
        stats = service.get_cache_stats_for_batch(batch_id)
        return jsonify(stats)
    
    @app.route('/api/llm/invalidate-cache/<int:provider_id>', methods=['POST'])
    def invalidate_cache(provider_id):
        """Invalidate cache for provider"""
        from flask import jsonify
        
        service.invalidate_provider_cache(provider_id)
        return jsonify({'success': True, 'message': f'Cache invalidated for provider {provider_id}'})