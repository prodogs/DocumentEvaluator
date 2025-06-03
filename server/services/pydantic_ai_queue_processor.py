"""
PydanticAI-powered Queue Processor

This service uses PydanticAI agents to process documents with type-safe, structured outputs.
It coordinates with BatchService for document retrieval and status updates.
"""

import asyncio
import json
import logging
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.ollama import OllamaModel
from services.batch_service import batch_service

logger = logging.getLogger(__name__)


# Pydantic Models for Structured Outputs
class TokenMetrics(BaseModel):
    """Token usage and cost metrics"""
    input_tokens: int = Field(description="Number of input tokens used")
    output_tokens: int = Field(description="Number of output tokens generated")
    total_cost: float = Field(description="Total cost in USD", default=0.0)


class DocumentAnalysis(BaseModel):
    """Structured document analysis result"""
    overall_score: float = Field(ge=0, le=100, description="Overall document quality score")
    insights: List[str] = Field(description="Key insights extracted from document")
    categories: List[str] = Field(description="Document categories/tags")
    summary: str = Field(description="Brief document summary")
    sentiment: str = Field(description="Document sentiment: positive/negative/neutral")
    tokens: TokenMetrics
    processing_time_ms: int = Field(description="Processing time in milliseconds")
    confidence: float = Field(ge=0, le=1, description="Analysis confidence score")


class ProcessingDependencies(BaseModel):
    """Dependencies injected into PydanticAI agents"""
    document_id: str
    document_content: str
    batch_id: int
    connection_config: Dict[str, Any]


class PydanticAIBatchProcessor:
    """Process batches using PydanticAI agents with BatchService coordination"""
    
    def __init__(self, check_interval=5, max_concurrent=3):
        self.check_interval = check_interval
        self.max_concurrent = max_concurrent
        self.is_running = False
        self.processing_thread = None
        self.active_tasks = {}  # task_id -> task info
        self.agents = {}  # provider_type -> Agent
        self.stats = {
            'processed': 0,
            'failed': 0,
            'started_at': None,
            'last_activity': None
        }
        
        # Initialize agents for different providers
        self._initialize_agents()
        
    def _initialize_agents(self):
        """Initialize PydanticAI agents for different LLM providers"""
        
        # Document analysis system prompt
        system_prompt = """You are an expert document analyst. 
        
        Analyze the provided document and extract:
        1. Key insights and findings
        2. Document categories and themes
        3. Overall quality and relevance score (0-100)
        4. Brief summary of main points
        5. Sentiment analysis
        
        Be thorough but concise. Focus on actionable insights."""
        
        try:
            # OpenAI Agent
            self.agents['openai'] = Agent(
                model=None,  # Will be set per connection
                result_type=DocumentAnalysis,
                system_prompt=system_prompt,
                deps_type=ProcessingDependencies
            )
            
            # Anthropic Agent
            self.agents['anthropic'] = Agent(
                model=None,  # Will be set per connection
                result_type=DocumentAnalysis,
                system_prompt=system_prompt,
                deps_type=ProcessingDependencies
            )
            
            # Ollama Agent
            self.agents['ollama'] = Agent(
                model=None,  # Will be set per connection
                result_type=DocumentAnalysis,
                system_prompt=system_prompt,
                deps_type=ProcessingDependencies
            )
            
            # Register tools for all agents
            self._register_agent_tools()
            
            logger.info("PydanticAI agents initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing PydanticAI agents: {e}")
            
    def _register_agent_tools(self):
        """Register tools for PydanticAI agents"""
        
        @self.agents['openai'].tool
        @self.agents['anthropic'].tool
        @self.agents['ollama'].tool
        async def calculate_quality_score(
            ctx: RunContext[ProcessingDependencies],
            content_length: int,
            readability: str,
            relevance: str
        ) -> float:
            """Calculate document quality score based on various factors"""
            base_score = 50.0
            
            # Length factor
            if content_length > 1000:
                base_score += 10
            elif content_length < 100:
                base_score -= 15
                
            # Readability factor
            if readability.lower() == 'high':
                base_score += 20
            elif readability.lower() == 'low':
                base_score -= 10
                
            # Relevance factor
            if relevance.lower() == 'high':
                base_score += 20
            elif relevance.lower() == 'low':
                base_score -= 15
                
            return max(0, min(100, base_score))
            
        @self.agents['openai'].tool
        @self.agents['anthropic'].tool
        @self.agents['ollama'].tool
        async def extract_key_phrases(
            ctx: RunContext[ProcessingDependencies],
            text: str,
            max_phrases: int = 10
        ) -> List[str]:
            """Extract key phrases from text"""
            # Simple keyword extraction (in real implementation, use NLP)
            words = text.lower().split()
            common_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
            key_words = [w for w in words if len(w) > 4 and w not in common_words]
            return list(set(key_words))[:max_phrases]
    
    def start(self):
        """Start the PydanticAI queue processor"""
        if self.is_running:
            logger.warning("PydanticAI queue processor is already running")
            return
            
        self.is_running = True
        self.stats['started_at'] = datetime.now()
        self.processing_thread = threading.Thread(target=self._async_wrapper)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        logger.info("PydanticAI queue processor started")
        
    def stop(self):
        """Stop the queue processor"""
        self.is_running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=10)
        logger.info("PydanticAI queue processor stopped")
        
    def _async_wrapper(self):
        """Wrapper to run async event loop in thread"""
        asyncio.run(self._process_loop())
        
    async def _process_loop(self):
        """Main async processing loop"""
        logger.info("PydanticAI processing loop started")
        
        while self.is_running:
            try:
                # Monitor batches ready for processing
                await self._monitor_batches()
                
                # Check status of active tasks
                await self._check_active_tasks()
                
                # Wait before next check
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in PydanticAI processing loop: {e}", exc_info=True)
                await asyncio.sleep(self.check_interval)
                
        logger.info("PydanticAI processing loop stopped")
        
    async def _monitor_batches(self):
        """Monitor for batches ready for processing"""
        try:
            # Get batches ready for processing from BatchService
            ready_batches = batch_service.get_batches_ready_for_processing()
            
            if not ready_batches:
                return
                
            logger.info(f"Found {len(ready_batches)} batches ready for PydanticAI processing")
            
            # Process each batch if we have capacity
            for batch in ready_batches:
                if len(self.active_tasks) >= self.max_concurrent:
                    logger.debug(f"At max concurrent limit ({self.max_concurrent}), skipping batch {batch['batch_id']}")
                    break
                    
                await self._process_batch_documents(batch['batch_id'])
                
        except Exception as e:
            logger.error(f"Error monitoring batches: {e}")
            
    async def _process_batch_documents(self, batch_id: int):
        """Process documents from a specific batch using PydanticAI"""
        try:
            # Keep processing documents while we have capacity
            while len(self.active_tasks) < self.max_concurrent:
                # Get next document from BatchService
                doc_info = batch_service.get_next_document_for_processing(batch_id)
                
                if not doc_info:
                    logger.debug(f"No more documents to process in batch {batch_id}")
                    break
                    
                # Process document with PydanticAI
                task_id = f"pydantic_ai_{doc_info['response_id']}_{datetime.now().timestamp()}"
                
                # Update BatchService with task_id
                success = batch_service.update_document_task(
                    doc_info['response_id'], 
                    task_id, 
                    'PROCESSING'
                )
                
                if success:
                    # Start async processing
                    asyncio.create_task(self._process_document_async(task_id, doc_info))
                    
                    # Track active task
                    self.active_tasks[task_id] = {
                        'doc_id': doc_info['response_id'],
                        'batch_id': batch_id,
                        'submitted_at': datetime.now(),
                        'document_id': doc_info['document_id'],
                        'status': 'processing'
                    }
                    logger.info(f"✓ Started PydanticAI processing for document {doc_info['response_id']} as task {task_id}")
                else:
                    logger.error(f"Failed to update task_id for document {doc_info['response_id']}")
                    
        except Exception as e:
            logger.error(f"Error processing batch {batch_id} documents: {e}")
            
    async def _process_document_async(self, task_id: str, doc_info: Dict[str, Any]):
        """Process a single document asynchronously using PydanticAI"""
        start_time = datetime.now()
        
        try:
            # Determine provider and get appropriate agent
            provider_type = doc_info['llm_config'].get('provider_type', 'openai')
            agent = self.agents.get(provider_type)
            
            if not agent:
                raise Exception(f"No agent available for provider: {provider_type}")
                
            # Set up the model for this specific connection
            model = self._create_model_for_connection(doc_info['llm_config'])
            agent.model = model
            
            # Prepare dependencies
            deps = ProcessingDependencies(
                document_id=doc_info['document_id'],
                document_content=doc_info['encoded_content'],  # Base64 content
                batch_id=doc_info['batch_id'],
                connection_config=doc_info['connection_details']
            )
            
            # Create the analysis prompt
            prompt = f"""
            Analyze this document using the following prompt:
            
            {doc_info['prompt']['text']}
            
            Document content is provided in base64 encoding. Please decode and analyze it thoroughly.
            """
            
            # Run the PydanticAI agent
            result = await agent.run(prompt, deps=deps)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Update the result with actual processing time
            analysis = result.data
            analysis.processing_time_ms = int(processing_time)
            
            # Prepare response data for BatchService
            response_data = {
                'response_text': f"Analysis: {analysis.summary}",
                'input_tokens': analysis.tokens.input_tokens,
                'output_tokens': analysis.tokens.output_tokens,
                'response_time_ms': analysis.processing_time_ms,
                'overall_score': analysis.overall_score,
                'structured_analysis': analysis.model_dump(),
                'insights': analysis.insights,
                'categories': analysis.categories,
                'sentiment': analysis.sentiment,
                'confidence': analysis.confidence
            }
            
            # Update BatchService with success
            batch_service.update_document_status(
                self.active_tasks[task_id]['doc_id'],
                'COMPLETED',
                response_data
            )
            
            # Update task status
            self.active_tasks[task_id]['status'] = 'completed'
            self.stats['processed'] += 1
            self.stats['last_activity'] = datetime.now()
            
            logger.info(f"✓ PydanticAI task {task_id} completed successfully (score: {analysis.overall_score})")
            
        except Exception as e:
            # Handle failure
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            batch_service.update_document_status(
                self.active_tasks[task_id]['doc_id'],
                'FAILED',
                {
                    'error': str(e),
                    'processing_time_ms': int(processing_time),
                    'provider_type': provider_type
                }
            )
            
            # Update task status
            self.active_tasks[task_id]['status'] = 'failed'
            self.stats['failed'] += 1
            self.stats['last_activity'] = datetime.now()
            
            logger.error(f"✗ PydanticAI task {task_id} failed: {e}")
            
    def _create_model_for_connection(self, llm_config: Dict[str, Any]):
        """Create appropriate PydanticAI model based on connection config"""
        provider_type = llm_config.get('provider_type', 'openai')
        
        if provider_type == 'openai':
            return OpenAIModel(
                model=llm_config.get('model_name', 'gpt-4'),
                api_key=llm_config.get('api_key'),
                base_url=llm_config.get('base_url')
            )
        elif provider_type == 'anthropic':
            return AnthropicModel(
                model=llm_config.get('model_name', 'claude-3-sonnet-20240229'),
                api_key=llm_config.get('api_key')
            )
        elif provider_type == 'ollama':
            return OllamaModel(
                model=llm_config.get('model_name', 'llama2'),
                base_url=llm_config.get('base_url', 'http://localhost:11434')
            )
        else:
            raise Exception(f"Unsupported provider type: {provider_type}")
            
    async def _check_active_tasks(self):
        """Check and clean up completed tasks"""
        completed_tasks = []
        
        for task_id, task_info in self.active_tasks.items():
            if task_info['status'] in ['completed', 'failed']:
                completed_tasks.append(task_id)
            elif self._is_task_timeout(task_info):
                # Handle timeout
                batch_service.update_document_status(
                    task_info['doc_id'],
                    'TIMEOUT',
                    {'error': 'PydanticAI task processing timeout'}
                )
                completed_tasks.append(task_id)
                self.stats['failed'] += 1
                logger.error(f"⏱ PydanticAI task {task_id} timed out")
                
        # Remove completed tasks
        for task_id in completed_tasks:
            del self.active_tasks[task_id]
            
    def _is_task_timeout(self, task_info: Dict[str, Any], timeout_minutes: int = 30) -> bool:
        """Check if a task has timed out"""
        elapsed = datetime.now() - task_info['submitted_at']
        return elapsed.total_seconds() > (timeout_minutes * 60)
        
    def get_status(self) -> Dict[str, Any]:
        """Get processor status"""
        return {
            'is_running': self.is_running,
            'check_interval': self.check_interval,
            'max_concurrent': self.max_concurrent,
            'active_tasks': len(self.active_tasks),
            'available_agents': list(self.agents.keys()),
            'stats': self.stats.copy()
        }


# Global instance
pydantic_ai_batch_processor = PydanticAIBatchProcessor()


def start_pydantic_ai_processor():
    """Start the PydanticAI batch processor"""
    pydantic_ai_batch_processor.start()
    

def stop_pydantic_ai_processor():
    """Stop the PydanticAI batch processor"""
    pydantic_ai_batch_processor.stop()
    

def get_pydantic_ai_processor_status():
    """Get status of the PydanticAI batch processor"""
    return pydantic_ai_batch_processor.get_status()