"""
LLM Provider Management Service

This service handles the management of LLM providers, including:
- Provider CRUD operations
- Model discovery from providers
- Connection testing
- Model activation/deactivation
"""

import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session as SQLSession
from sqlalchemy import and_

from database import Session
from models import LlmProvider, LlmModel, LlmConfiguration, Model, ProviderModel
from services.model_service import model_service

logger = logging.getLogger(__name__)

class LlmProviderService:
    """Service for managing LLM providers and their models"""
    
    def __init__(self):
        self.provider_adapters = {}
        self._load_provider_adapters()
    
    def _load_provider_adapters(self):
        """Load provider adapters dynamically"""
        try:
            from services.providers.ollama_provider import OllamaProvider
            from services.providers.openai_provider import OpenAIProvider
            from services.providers.lmstudio_provider import LMStudioProvider
            from services.providers.amazon_provider import AmazonProvider
            from services.providers.grok_provider import GrokProvider
            
            self.provider_adapters = {
                'ollama': OllamaProvider(),
                'openai': OpenAIProvider(),
                'lmstudio': LMStudioProvider(),
                'amazon': AmazonProvider(),
                'grok': GrokProvider()
            }
            logger.info(f"Loaded {len(self.provider_adapters)} provider adapters")
        except ImportError as e:
            logger.warning(f"Some provider adapters not available: {e}")
    
    def get_all_providers(self) -> List[Dict[str, Any]]:
        """Get all LLM providers"""
        session = Session()
        try:
            providers = session.query(LlmProvider).all()
            return [self._provider_to_dict(provider) for provider in providers]
        finally:
            session.close()
    
    def get_provider_by_id(self, provider_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific provider by ID"""
        session = Session()
        try:
            provider = session.query(LlmProvider).filter(LlmProvider.id == provider_id).first()
            return self._provider_to_dict(provider) if provider else None
        finally:
            session.close()
    
    def create_provider(self, provider_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new LLM provider"""
        session = Session()
        try:
            provider = LlmProvider(
                name=provider_data['name'],
                provider_type=provider_data['provider_type'],
                default_base_url=provider_data.get('default_base_url'),
                supports_model_discovery=provider_data.get('supports_model_discovery', True),
                auth_type=provider_data.get('auth_type', 'api_key'),
                notes=provider_data.get('notes')
            )
            
            session.add(provider)
            session.commit()
            
            logger.info(f"Created provider: {provider.name}")
            return self._provider_to_dict(provider)
        finally:
            session.close()
    
    def update_provider(self, provider_id: int, provider_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing provider"""
        session = Session()
        try:
            provider = session.query(LlmProvider).filter(LlmProvider.id == provider_id).first()
            if not provider:
                return None
            
            # Update fields
            for field in ['name', 'provider_type', 'default_base_url', 'supports_model_discovery', 'auth_type', 'notes']:
                if field in provider_data:
                    setattr(provider, field, provider_data[field])
            
            session.commit()
            logger.info(f"Updated provider: {provider.name}")
            return self._provider_to_dict(provider)
        finally:
            session.close()
    
    def delete_provider(self, provider_id: int) -> bool:
        """Delete a provider and all its models"""
        session = Session()
        try:
            provider = session.query(LlmProvider).filter(LlmProvider.id == provider_id).first()
            if not provider:
                return False
            
            # Delete associated models
            session.query(LlmModel).filter(LlmModel.provider_id == provider_id).delete()
            
            # Delete provider
            session.delete(provider)
            session.commit()
            
            logger.info(f"Deleted provider: {provider.name}")
            return True
        finally:
            session.close()
    
    def test_connection(self, provider_config: Dict[str, Any]) -> Tuple[bool, str]:
        """Test connection to a provider"""
        provider_type = provider_config.get('provider_type')
        
        if provider_type not in self.provider_adapters:
            return False, f"Provider type '{provider_type}' not supported"
        
        try:
            adapter = self.provider_adapters[provider_type]
            return adapter.test_connection(provider_config)
        except Exception as e:
            logger.error(f"Connection test failed for {provider_type}: {e}")
            return False, str(e)
    
    def discover_models(self, provider_id: int, provider_config: Dict[str, Any]) -> Tuple[bool, List[Dict[str, Any]], str]:
        """Discover available models from a provider"""
        session = Session()
        try:
            provider = session.query(LlmProvider).filter(LlmProvider.id == provider_id).first()
            if not provider:
                return False, [], "Provider not found"
            
            if not provider.supports_model_discovery:
                return False, [], "Provider does not support model discovery"
            
            provider_type = provider.provider_type
            if provider_type not in self.provider_adapters:
                return False, [], f"Provider type '{provider_type}' not supported"
            
            try:
                adapter = self.provider_adapters[provider_type]
                success, models, error = adapter.discover_models(provider_config)
                
                if success:
                    # Update models using new architecture
                    new_models, linked_models = model_service.discover_and_link_models(provider_id, models)
                    logger.info(f"Discovered {new_models} new models, linked {linked_models} total for provider {provider.name}")

                return success, models, error
            except Exception as e:
                logger.error(f"Model discovery failed for {provider_type}: {e}")
                return False, [], str(e)
        finally:
            session.close()
    
    def get_provider_models(self, provider_id: int) -> List[Dict[str, Any]]:
        """Get all models for a provider using new architecture"""
        return model_service.get_models_by_provider(provider_id)
    
    def toggle_model_status(self, model_id: int, is_active: bool) -> bool:
        """Toggle the active status of a model"""
        session = Session()
        try:
            model = session.query(LlmModel).filter(LlmModel.id == model_id).first()
            if not model:
                return False
            
            model.is_active = is_active
            model.last_updated = datetime.utcnow()
            session.commit()
            
            logger.info(f"Model {model.model_name} {'activated' if is_active else 'deactivated'}")
            return True
        finally:
            session.close()
    
    def sync_models(self, provider_id: int) -> Tuple[bool, str]:
        """Sync models for a provider with its configuration"""
        session = Session()
        try:
            provider = session.query(LlmProvider).filter(LlmProvider.id == provider_id).first()
            if not provider:
                return False, "Provider not found"
            
            # Get provider configuration from associated LlmConfiguration
            config = session.query(LlmConfiguration).filter(
                LlmConfiguration.provider_id == provider_id
            ).first()
            
            if not config:
                return False, "No configuration found for provider"
            
            provider_config = {
                'provider_type': provider.provider_type,
                'base_url': config.base_url,
                'api_key': config.api_key,
                'port_no': config.port_no
            }
            
            success, models, error = self.discover_models(provider_id, provider_config)
            
            if success:
                # Update last sync time
                config.last_model_sync = datetime.utcnow()
                config.available_models = json.dumps([model['model_name'] for model in models])
                session.commit()
                return True, f"Synced {len(models)} models"
            else:
                return False, error
        finally:
            session.close()
    
    def _update_provider_models(self, session: SQLSession, provider_id: int, models: List[Dict[str, Any]]):
        """Update models for a provider in the database"""
        # Get existing models
        existing_models = session.query(LlmModel).filter(LlmModel.provider_id == provider_id).all()
        existing_model_ids = {model.model_id for model in existing_models}
        
        # Add new models
        for model_data in models:
            model_id = model_data.get('model_id', model_data['model_name'])
            if model_id not in existing_model_ids:
                model = LlmModel(
                    provider_id=provider_id,
                    model_name=model_data['model_name'],
                    model_id=model_id,
                    is_active=False,  # New models start inactive
                    capabilities=model_data.get('capabilities'),
                    last_updated=datetime.utcnow()
                )
                session.add(model)
        
        # Update existing models
        discovered_model_ids = {model_data.get('model_id', model_data['model_name']) for model_data in models}
        for existing_model in existing_models:
            if existing_model.model_id in discovered_model_ids:
                existing_model.last_updated = datetime.utcnow()
                # Update capabilities if provided
                model_data = next((m for m in models if m.get('model_id', m['model_name']) == existing_model.model_id), None)
                if model_data and 'capabilities' in model_data:
                    existing_model.capabilities = model_data['capabilities']
    
    def _provider_to_dict(self, provider: LlmProvider) -> Dict[str, Any]:
        """Convert provider model to dictionary"""
        return {
            'id': provider.id,
            'name': provider.name,
            'provider_type': provider.provider_type,
            'default_base_url': provider.default_base_url,
            'supports_model_discovery': provider.supports_model_discovery,
            'auth_type': provider.auth_type,
            'notes': provider.notes,
            'created_at': provider.created_at.isoformat() if provider.created_at else None
        }
    
    def _model_to_dict(self, model: LlmModel) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return {
            'id': model.id,
            'provider_id': model.provider_id,
            'model_name': model.model_name,
            'model_id': model.model_id,
            'is_active': model.is_active,
            'capabilities': model.capabilities,
            'last_updated': model.last_updated.isoformat() if model.last_updated else None
        }

# Global service instance
llm_provider_service = LlmProviderService()
