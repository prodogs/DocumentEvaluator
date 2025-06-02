"""
Async Utilities Module

Provides async/await support for LLM calls and other I/O operations.
"""

import asyncio
import aiohttp
import time
from typing import List, Dict, Any, Optional, Callable, Tuple
from concurrent.futures import ThreadPoolExecutor
from functools import wraps

from app.core.logger import get_logger, get_performance_logger

logger = get_logger(__name__)
perf_logger = get_performance_logger('async')


class AsyncClient:
    """Async HTTP client with connection pooling and retry logic"""
    
    def __init__(self, 
                 connector_limit: int = 100,
                 connector_limit_per_host: int = 30,
                 timeout: int = 30,
                 max_retries: int = 3):
        self.connector_limit = connector_limit
        self.connector_limit_per_host = connector_limit_per_host
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.session = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        connector = aiohttp.TCPConnector(
            limit=self.connector_limit,
            limit_per_host=self.connector_limit_per_host
        )
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=self.timeout
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def request(self, method: str, url: str, **kwargs) -> Tuple[int, Any]:
        """Make async HTTP request with retry logic"""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                
                async with self.session.request(method, url, **kwargs) as response:
                    data = await response.json() if response.content_type == 'application/json' else await response.text()
                    
                    duration = time.time() - start_time
                    perf_logger.log_api_call(
                        service=url.split('/')[2],  # Extract domain
                        endpoint=url,
                        method=method,
                        duration=duration,
                        status_code=response.status,
                        metadata={'attempt': attempt + 1}
                    )
                    
                    if response.status >= 500:  # Server error, retry
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status
                        )
                    
                    return response.status, data
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Request failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Request failed after {self.max_retries} attempts: {e}")
        
        raise last_error
    
    async def post(self, url: str, **kwargs) -> Tuple[int, Any]:
        """Make async POST request"""
        return await self.request('POST', url, **kwargs)
    
    async def get(self, url: str, **kwargs) -> Tuple[int, Any]:
        """Make async GET request"""
        return await self.request('GET', url, **kwargs)


class AsyncBatcher:
    """Batch async operations for efficiency"""
    
    def __init__(self, batch_size: int = 10, max_wait: float = 1.0):
        self.batch_size = batch_size
        self.max_wait = max_wait
        self.pending = []
        self.results = {}
        self.lock = asyncio.Lock()
        
    async def add(self, key: str, coro: Callable) -> Any:
        """Add operation to batch"""
        async with self.lock:
            future = asyncio.Future()
            self.pending.append((key, coro, future))
            
            # Process batch if full or after timeout
            if len(self.pending) >= self.batch_size:
                await self._process_batch()
            else:
                asyncio.create_task(self._process_after_delay())
        
        return await future
    
    async def _process_after_delay(self):
        """Process batch after delay"""
        await asyncio.sleep(self.max_wait)
        async with self.lock:
            if self.pending:
                await self._process_batch()
    
    async def _process_batch(self):
        """Process current batch"""
        if not self.pending:
            return
        
        batch = self.pending[:]
        self.pending.clear()
        
        # Execute all operations concurrently
        coros = [item[1]() for item in batch]
        results = await asyncio.gather(*coros, return_exceptions=True)
        
        # Set results
        for (key, _, future), result in zip(batch, results):
            if isinstance(result, Exception):
                future.set_exception(result)
            else:
                future.set_result(result)


class AsyncLLMProcessor:
    """Process LLM calls asynchronously"""
    
    def __init__(self, max_concurrent: int = 10):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.client = None
        
    async def __aenter__(self):
        """Context manager entry"""
        self.client = AsyncClient()
        await self.client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.client:
            await self.client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def process_single(self, provider_config: Dict[str, Any], 
                           prompt: str, document: Dict[str, Any]) -> Dict[str, Any]:
        """Process single LLM call"""
        async with self.semaphore:
            start_time = time.time()
            
            try:
                # Build request based on provider type
                if provider_config['type'] == 'openai':
                    url = provider_config.get('base_url', 'https://api.openai.com') + '/v1/chat/completions'
                    headers = {
                        'Authorization': f"Bearer {provider_config['api_key']}",
                        'Content-Type': 'application/json'
                    }
                    data = {
                        'model': provider_config['model'],
                        'messages': [
                            {'role': 'system', 'content': prompt},
                            {'role': 'user', 'content': document['content']}
                        ],
                        'temperature': provider_config.get('temperature', 0.7),
                        'max_tokens': provider_config.get('max_tokens', 1000)
                    }
                    
                    status, response = await self.client.post(url, headers=headers, json=data)
                    
                    if status == 200:
                        return {
                            'success': True,
                            'response': response['choices'][0]['message']['content'],
                            'usage': response.get('usage', {}),
                            'duration': time.time() - start_time
                        }
                    else:
                        return {
                            'success': False,
                            'error': f"API returned status {status}: {response}",
                            'duration': time.time() - start_time
                        }
                
                else:
                    # Add other provider types as needed
                    raise NotImplementedError(f"Provider type {provider_config['type']} not implemented")
                    
            except Exception as e:
                logger.error(f"LLM processing error: {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'duration': time.time() - start_time
                }
    
    async def process_batch(self, provider_config: Dict[str, Any],
                          prompt: str, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process multiple documents concurrently"""
        tasks = [
            self.process_single(provider_config, prompt, doc)
            for doc in documents
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    'success': False,
                    'error': str(result),
                    'document_id': documents[i].get('id')
                })
            else:
                result['document_id'] = documents[i].get('id')
                processed_results.append(result)
        
        return processed_results


# Async task runner for Flask
class AsyncTaskRunner:
    """Run async tasks from sync Flask context"""
    
    def __init__(self):
        self.loop = None
        self.thread = None
        self.executor = ThreadPoolExecutor(max_workers=1)
        
    def start(self):
        """Start async event loop in separate thread"""
        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()
        
        self.thread = self.executor.submit(run_loop)
        
        # Wait for loop to start
        while self.loop is None:
            time.sleep(0.01)
    
    def stop(self):
        """Stop async event loop"""
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
        if self.thread:
            self.thread.result()
        self.executor.shutdown()
    
    def run_async(self, coro):
        """Run async coroutine from sync context"""
        if not self.loop:
            self.start()
        
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result()


# Global async runner
async_runner = AsyncTaskRunner()


# Decorator for async endpoints
def async_route(func):
    """Decorator to run async route handlers"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        return async_runner.run_async(func(*args, **kwargs))
    return wrapper


# Utility functions
async def gather_with_concurrency(n: int, *coros):
    """Gather results with limited concurrency"""
    semaphore = asyncio.Semaphore(n)
    
    async def sem_coro(coro):
        async with semaphore:
            return await coro
    
    return await asyncio.gather(*(sem_coro(c) for c in coros))


async def run_with_timeout(coro, timeout: float):
    """Run coroutine with timeout"""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        logger.error(f"Coroutine timed out after {timeout}s")
        raise


# Example usage for batch processing
async def process_documents_async(documents: List[Dict], 
                                provider_configs: List[Dict],
                                prompts: List[Dict]) -> List[Dict]:
    """Process documents with multiple providers and prompts asynchronously"""
    
    async with AsyncLLMProcessor(max_concurrent=10) as processor:
        tasks = []
        
        for doc in documents:
            for provider in provider_configs:
                for prompt in prompts:
                    task = processor.process_single(provider, prompt['text'], doc)
                    tasks.append(task)
        
        # Process all tasks with concurrency limit
        results = await gather_with_concurrency(20, *tasks)
        
        return results


def process_documents_sync(documents: List[Dict], 
                         provider_configs: List[Dict],
                         prompts: List[Dict]) -> List[Dict]:
    """Sync wrapper for async document processing"""
    return async_runner.run_async(
        process_documents_async(documents, provider_configs, prompts)
    )