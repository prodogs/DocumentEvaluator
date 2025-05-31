"""
Model Management Service

This service handles CRUD operations for Models and their relationships
with Service Providers.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session as SQLSession, joinedload

from server.database import Session
from server.models import Model, ProviderModel, ModelAlias, LlmProvider
from server.services.model_normalization_service import model_normalization_service

logger = logging.getLogger(__name__)

class ModelService:
    """Service for managing Models and Provider-Model relationships"""
    
    def get_all_models(self) -> List[Dict[str, Any]]:
        """Get all models with their provider relationships"""
        session = Session()
        try:
            models = session.query(Model).options(
                joinedload(Model.provider_models).joinedload(ProviderModel.provider),
                joinedload(Model.aliases)
            ).all()
            
            return [self._model_to_dict(model) for model in models]
        finally:
            session.close()
    
    def get_model_by_id(self, model_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific model by ID"""
        session = Session()
        try:
            model = session.query(Model).options(
                joinedload(Model.provider_models).joinedload(ProviderModel.provider),
                joinedload(Model.aliases)
            ).filter(Model.id == model_id).first()
            
            return self._model_to_dict(model) if model else None
        finally:
            session.close()
    
    def create_model(self, model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new model"""
        session = Session()
        try:
            model = Model(
                common_name=model_data['common_name'],
                display_name=model_data['display_name'],
                notes=model_data.get('notes'),
                model_family=model_data.get('model_family'),
                parameter_count=model_data.get('parameter_count'),
                context_length=model_data.get('context_length'),
                capabilities=model_data.get('capabilities')
            )
            
            session.add(model)
            session.commit()
            
            logger.info(f"Created model: {model.common_name}")
            return self._model_to_dict(model)
        finally:
            session.close()
    
    def update_model(self, model_id: int, model_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing model"""
        session = Session()
        try:
            model = session.query(Model).filter(Model.id == model_id).first()
            if not model:
                return None

            # Update fields
            for field in ['display_name', 'notes', 'model_family', 'parameter_count', 'context_length', 'capabilities', 'is_globally_active']:
                if field in model_data:
                    setattr(model, field, model_data[field])

            model.updated_at = datetime.utcnow()
            session.commit()

            logger.info(f"Updated model: {model.common_name}")
            return self._model_to_dict(model)
        finally:
            session.close()

    def toggle_global_model_status(self, model_id: int, is_active: bool) -> bool:
        """Toggle the global activation status of a model"""
        session = Session()
        try:
            model = session.query(Model).filter(Model.id == model_id).first()
            if not model:
                return False

            model.is_globally_active = is_active
            model.updated_at = datetime.utcnow()
            session.commit()

            logger.info(f"Model {model.common_name} globally {'activated' if is_active else 'deactivated'}")
            return True
        finally:
            session.close()
    
    def delete_model(self, model_id: int) -> bool:
        """Delete a model and all its relationships"""
        session = Session()
        try:
            model = session.query(Model).filter(Model.id == model_id).first()
            if not model:
                return False
            
            # Delete associated provider relationships and aliases
            session.query(ProviderModel).filter(ProviderModel.model_id == model_id).delete()
            session.query(ModelAlias).filter(ModelAlias.model_id == model_id).delete()
            
            # Delete model
            session.delete(model)
            session.commit()
            
            logger.info(f"Deleted model: {model.common_name}")
            return True
        finally:
            session.close()
    
    def get_models_by_provider(self, provider_id: int) -> List[Dict[str, Any]]:
        """Get all models available through a specific provider"""
        session = Session()
        try:
            provider_models = session.query(ProviderModel).options(
                joinedload(ProviderModel.model).joinedload(Model.aliases)
            ).filter(ProviderModel.provider_id == provider_id).all()
            
            return [self._provider_model_to_dict(pm) for pm in provider_models]
        finally:
            session.close()
    
    def link_model_to_provider(self, model_id: int, provider_id: int, provider_model_name: str) -> Dict[str, Any]:
        """Link a model to a provider"""
        session = Session()
        try:
            # Check if relationship already exists
            existing = session.query(ProviderModel).filter(
                ProviderModel.model_id == model_id,
                ProviderModel.provider_id == provider_id
            ).first()
            
            if existing:
                # Update existing relationship
                existing.provider_model_name = provider_model_name
                existing.last_checked = datetime.utcnow()
                session.commit()
                return self._provider_model_to_dict(existing)
            
            # Create new relationship
            provider_model = ProviderModel(
                model_id=model_id,
                provider_id=provider_id,
                provider_model_name=provider_model_name,
                is_active=False,
                is_available=True
            )
            
            session.add(provider_model)
            session.commit()
            
            logger.info(f"Linked model {model_id} to provider {provider_id}")
            return self._provider_model_to_dict(provider_model)
        finally:
            session.close()
    
    def toggle_provider_model_status(self, provider_id: int, model_id: int, is_active: bool) -> bool:
        """Toggle the active status of a model for a specific provider"""
        session = Session()
        try:
            provider_model = session.query(ProviderModel).filter(
                ProviderModel.provider_id == provider_id,
                ProviderModel.model_id == model_id
            ).first()
            
            if not provider_model:
                return False
            
            provider_model.is_active = is_active
            provider_model.last_checked = datetime.utcnow()
            session.commit()
            
            logger.info(f"Model {model_id} {'activated' if is_active else 'deactivated'} for provider {provider_id}")
            return True
        finally:
            session.close()
    
    def discover_and_link_models(self, provider_id: int, discovered_models: List[Dict[str, Any]]) -> Tuple[int, int]:
        """
        Process discovered models from a provider and link them
        Returns (new_models_count, linked_models_count)
        """
        session = Session()
        new_models = 0
        linked_models = 0
        
        try:
            for model_data in discovered_models:
                provider_model_name = model_data['model_name']
                
                # Get or create model
                model_id, was_created = model_normalization_service.get_or_create_model(
                    provider_model_name, provider_id
                )
                
                if was_created:
                    new_models += 1
                
                # Link to provider
                self.link_model_to_provider(model_id, provider_id, provider_model_name)
                linked_models += 1
            
            logger.info(f"Discovered {new_models} new models, linked {linked_models} total for provider {provider_id}")
            return new_models, linked_models
            
        except Exception as e:
            logger.error(f"Error discovering models for provider {provider_id}: {e}")
            raise
        finally:
            session.close()
    
    def _model_to_dict(self, model: Model) -> Dict[str, Any]:
        """Convert model to dictionary"""
        if not model:
            return {}

        return {
            'id': model.id,
            'common_name': model.common_name,
            'display_name': model.display_name,
            'notes': model.notes,
            'model_family': model.model_family,
            'parameter_count': model.parameter_count,
            'context_length': model.context_length,
            'capabilities': model.capabilities,
            'is_globally_active': getattr(model, 'is_globally_active', True),
            'created_at': model.created_at.isoformat() if model.created_at else None,
            'updated_at': model.updated_at.isoformat() if model.updated_at else None,
            'providers': [
                {
                    'provider_id': pm.provider_id,
                    'provider_name': pm.provider.name if pm.provider else None,
                    'provider_model_name': pm.provider_model_name,
                    'is_active': pm.is_active,
                    'is_available': pm.is_available
                }
                for pm in (model.provider_models or [])
            ],
            'aliases': [alias.alias_name for alias in (model.aliases or [])]
        }
    
    def _provider_model_to_dict(self, provider_model: ProviderModel) -> Dict[str, Any]:
        """Convert provider model relationship to dictionary"""
        return {
            'id': provider_model.id,
            'provider_id': provider_model.provider_id,
            'model_id': provider_model.model_id,
            'provider_model_name': provider_model.provider_model_name,
            'is_active': provider_model.is_active,
            'is_available': provider_model.is_available,
            'last_checked': provider_model.last_checked.isoformat() if provider_model.last_checked else None,
            'model': self._model_to_dict(provider_model.model) if provider_model.model else None
        }

# Global service instance
model_service = ModelService()
