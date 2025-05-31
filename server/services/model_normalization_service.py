"""
Model Normalization Service

This service handles the normalization of provider-specific model names
to standardized common names, and manages model aliases.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session as SQLSession

from database import Session
from models import Model, ModelAlias, ProviderModel

logger = logging.getLogger(__name__)

class ModelNormalizationService:
    """Service for normalizing model names across providers"""
    
    def __init__(self):
        self.normalization_rules = self._load_normalization_rules()
    
    def _load_normalization_rules(self) -> Dict[str, Dict]:
        """Load model normalization rules"""
        return {
            # GPT Models
            'gpt-4': {
                'common_name': 'gpt-4',
                'display_name': 'GPT-4',
                'family': 'GPT',
                'aliases': ['gpt-4', 'gpt4', 'openai/gpt-4']
            },
            'gpt-4-turbo': {
                'common_name': 'gpt-4-turbo',
                'display_name': 'GPT-4 Turbo',
                'family': 'GPT',
                'aliases': ['gpt-4-turbo', 'gpt4-turbo', 'openai/gpt-4-turbo']
            },
            'gpt-3.5-turbo': {
                'common_name': 'gpt-3.5-turbo',
                'display_name': 'GPT-3.5 Turbo',
                'family': 'GPT',
                'aliases': ['gpt-3.5-turbo', 'gpt35-turbo', 'openai/gpt-3.5-turbo']
            },
            
            # Claude Models
            'claude-3-opus': {
                'common_name': 'claude-3-opus',
                'display_name': 'Claude 3 Opus',
                'family': 'Claude',
                'aliases': ['claude-3-opus', 'anthropic/claude-3-opus']
            },
            'claude-3-sonnet': {
                'common_name': 'claude-3-sonnet',
                'display_name': 'Claude 3 Sonnet',
                'family': 'Claude',
                'aliases': ['claude-3-sonnet', 'anthropic/claude-3-sonnet']
            },
            'claude-3-haiku': {
                'common_name': 'claude-3-haiku',
                'display_name': 'Claude 3 Haiku',
                'family': 'Claude',
                'aliases': ['claude-3-haiku', 'anthropic/claude-3-haiku']
            },
            
            # LLaMA Models
            'llama-2-7b': {
                'common_name': 'llama-2-7b',
                'display_name': 'LLaMA 2 7B',
                'family': 'LLaMA',
                'parameter_count': '7B',
                'aliases': ['llama2:7b', 'llama-2-7b', 'meta-llama/llama-2-7b']
            },
            'llama-2-13b': {
                'common_name': 'llama-2-13b',
                'display_name': 'LLaMA 2 13B',
                'family': 'LLaMA',
                'parameter_count': '13B',
                'aliases': ['llama2:13b', 'llama-2-13b', 'meta-llama/llama-2-13b']
            },
            'llama-2-70b': {
                'common_name': 'llama-2-70b',
                'display_name': 'LLaMA 2 70B',
                'family': 'LLaMA',
                'parameter_count': '70B',
                'aliases': ['llama2:70b', 'llama-2-70b', 'meta-llama/llama-2-70b']
            },
            
            # Qwen Models
            'qwen2-7b': {
                'common_name': 'qwen2-7b',
                'display_name': 'Qwen2 7B',
                'family': 'Qwen',
                'parameter_count': '7B',
                'aliases': ['qwen2:7b', 'qwen/qwen2-7b', 'qwen2-7b']
            },
            'qwen2-14b': {
                'common_name': 'qwen2-14b',
                'display_name': 'Qwen2 14B',
                'family': 'Qwen',
                'parameter_count': '14B',
                'aliases': ['qwen2:14b', 'qwen/qwen2-14b', 'qwen2-14b']
            },
            'qwen2-72b': {
                'common_name': 'qwen2-72b',
                'display_name': 'Qwen2 72B',
                'family': 'Qwen',
                'parameter_count': '72B',
                'aliases': ['qwen2:72b', 'qwen/qwen2-72b', 'qwen2-72b']
            },
            
            # Mistral Models
            'mistral-7b': {
                'common_name': 'mistral-7b',
                'display_name': 'Mistral 7B',
                'family': 'Mistral',
                'parameter_count': '7B',
                'aliases': ['mistral:7b', 'mistral-7b', 'mistralai/mistral-7b']
            }
        }
    
    def normalize_model_name(self, provider_model_name: str) -> str:
        """Normalize a provider-specific model name to a common name"""
        name = provider_model_name.lower().strip()
        
        # Remove common prefixes
        prefixes_to_remove = [
            'qwen/', 'microsoft/', 'meta-llama/', 'mistralai/', 'anthropic/',
            'openai/', 'google/', 'cohere/', 'huggingface/', 'ollama/'
        ]
        
        for prefix in prefixes_to_remove:
            if name.startswith(prefix):
                name = name[len(prefix):]
                break
        
        # Normalize separators
        name = name.replace(':', '-').replace('_', '-')
        
        # Check against known rules
        for common_name, rule in self.normalization_rules.items():
            if name in [alias.lower() for alias in rule['aliases']]:
                return common_name
        
        # If no rule found, return normalized name
        return name
    
    def get_or_create_model(self, provider_model_name: str, provider_id: int) -> Tuple[int, bool]:
        """
        Get or create a model based on provider model name
        Returns (model_id, was_created)
        """
        session = Session()
        try:
            common_name = self.normalize_model_name(provider_model_name)
            
            # Check if model already exists
            existing_model = session.query(Model).filter(Model.common_name == common_name).first()
            
            if existing_model:
                return existing_model.id, False
            
            # Create new model
            rule = self.normalization_rules.get(common_name, {})
            
            model = Model(
                common_name=common_name,
                display_name=rule.get('display_name', provider_model_name),
                model_family=rule.get('family', self._extract_family(common_name)),
                parameter_count=rule.get('parameter_count', self._extract_parameter_count(common_name))
            )
            
            session.add(model)
            session.flush()  # Get the ID
            
            # Create aliases
            aliases = rule.get('aliases', [provider_model_name])
            for alias in aliases:
                if alias.lower() != common_name:
                    alias_obj = ModelAlias(
                        model_id=model.id,
                        alias_name=alias
                    )
                    session.add(alias_obj)
            
            session.commit()
            logger.info(f"Created new model: {common_name} (ID: {model.id})")
            
            return model.id, True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating model for {provider_model_name}: {e}")
            raise
        finally:
            session.close()
    
    def _extract_family(self, common_name: str) -> str:
        """Extract model family from common name"""
        name_lower = common_name.lower()
        
        if 'gpt' in name_lower:
            return 'GPT'
        elif 'claude' in name_lower:
            return 'Claude'
        elif 'llama' in name_lower:
            return 'LLaMA'
        elif 'mistral' in name_lower:
            return 'Mistral'
        elif 'qwen' in name_lower:
            return 'Qwen'
        elif 'gemini' in name_lower:
            return 'Gemini'
        elif 'palm' in name_lower:
            return 'PaLM'
        else:
            return 'Other'
    
    def _extract_parameter_count(self, common_name: str) -> Optional[str]:
        """Extract parameter count from model name"""
        # Look for patterns like 7b, 13b, 70b, etc.
        match = re.search(r'(\d+(?:\.\d+)?)\s*b(?:illion)?', common_name.lower())
        if match:
            return f"{match.group(1)}B"
        
        return None
    
    def find_model_by_alias(self, alias_name: str) -> Optional[int]:
        """Find model ID by alias name"""
        session = Session()
        try:
            alias = session.query(ModelAlias).filter(ModelAlias.alias_name == alias_name).first()
            return alias.model_id if alias else None
        finally:
            session.close()
    
    def get_model_aliases(self, model_id: int) -> List[str]:
        """Get all aliases for a model"""
        session = Session()
        try:
            aliases = session.query(ModelAlias).filter(ModelAlias.model_id == model_id).all()
            return [alias.alias_name for alias in aliases]
        finally:
            session.close()

# Global service instance
model_normalization_service = ModelNormalizationService()
