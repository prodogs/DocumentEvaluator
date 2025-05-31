import React, { useState, useEffect } from 'react';
import axios from 'axios';

import PromptManager from './PromptManager';
import '../styles/configuration.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001';

const ConfigurationManager = ({ onPromptsChange }) => {
  const [activeSubTab, setActiveSubTab] = useState('prompts');
  const [stats, setStats] = useState({
    totalPrompts: 0,
    activePrompts: 0
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      setLoading(true);
      
      // Load LLM configurations stats
      const configsResponse = await axios.get(`${API_BASE_URL}/api/llm-configurations`);
      const configs = configsResponse.data.llm_configurations || [];
      
      // Load prompts stats
      const promptsResponse = await axios.get(`${API_BASE_URL}/api/prompts`);
      const prompts = promptsResponse.data.prompts || [];
      
      // Load providers stats for context
      const providersResponse = await axios.get(`${API_BASE_URL}/api/llm-providers`);
      const providers = providersResponse.data.providers || [];
      
      // Calculate configured providers (those with at least one config)
      const configuredProviderTypes = new Set(configs.map(c => c.provider_type));

      setStats({
        totalConfigs: configs.length,
        activeConfigs: configs.filter(c => c.active).length,
        totalPrompts: prompts.length,
        activePrompts: prompts.filter(p => p.active).length,
        totalProviders: providers.length,
        configuredProviders: configuredProviderTypes.size
      });
    } catch (error) {
      console.error('Error loading stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubTabChange = (tab) => {
    setActiveSubTab(tab);
  };

  const handleDataChange = () => {
    loadStats();
    if (onConfigsChange) onConfigsChange();
    if (onPromptsChange) onPromptsChange();
  };

  return (
    <div className="configuration-manager">
      {/* Hero Section */}
      <div className="config-hero">
        <div className="hero-content">
          <h1 className="hero-title">
            <span className="hero-icon">⚙️</span>
            Configuration Center
          </h1>
          <p className="hero-subtitle">
            Manage LLM configurations and prompts for intelligent document processing
          </p>
        </div>
        
        {/* Stats Dashboard */}
        <div className="config-stats">
          <div className="stat-card configs">
            <div className="stat-icon">🤖</div>
            <div className="stat-content">
              <div className="stat-number">{loading ? '...' : stats.totalConfigs}</div>
              <div className="stat-label">LLM Configs</div>
              <div className="stat-detail">{loading ? '...' : stats.activeConfigs} active</div>
            </div>
          </div>
          
          <div className="stat-card prompts">
            <div className="stat-icon">📝</div>
            <div className="stat-content">
              <div className="stat-number">{loading ? '...' : stats.totalPrompts}</div>
              <div className="stat-label">Prompts</div>
              <div className="stat-detail">{loading ? '...' : stats.activePrompts} active</div>
            </div>
          </div>
          
          <div className="stat-card providers">
            <div className="stat-icon">🔗</div>
            <div className="stat-content">
              <div className="stat-number">{loading ? '...' : stats.configuredProviders}/{loading ? '...' : stats.totalProviders}</div>
              <div className="stat-label">Providers</div>
              <div className="stat-detail">Configured</div>
            </div>
          </div>
        </div>
      </div>

      {/* Sub-navigation tabs */}
      <div className="config-sub-tabs">
        <button
          className={`sub-tab ${activeSubTab === 'llm-configs' ? 'active' : ''}`}
          onClick={() => handleSubTabChange('llm-configs')}
        >
          <span className="tab-icon">🤖</span>
          <span className="tab-text">LLM Configurations</span>
          <span className="tab-badge">{stats.totalConfigs}</span>
        </button>
        
        <button
          className={`sub-tab ${activeSubTab === 'prompts' ? 'active' : ''}`}
          onClick={() => handleSubTabChange('prompts')}
        >
          <span className="tab-icon">📝</span>
          <span className="tab-text">Prompts</span>
          <span className="tab-badge">{stats.totalPrompts}</span>
        </button>
      </div>

      {/* Tab Content */}
      <div className="config-tab-content">
        {activeSubTab === 'llm-configs' && (
          <div className="llm-configs-section">
            <LlmConfigManager onConfigsChange={handleDataChange} />
          </div>
        )}
        
        {activeSubTab === 'prompts' && (
          <div className="prompts-section">
            <PromptManager onPromptsChange={handleDataChange} />
          </div>
        )}
      </div>
    </div>
  );
};

export default ConfigurationManager;
