import React, { useState, useEffect } from 'react';
import axios from 'axios';
import ModelManager from './ModelManager';
import LlmProviderManager from './LlmProviderManager';
import ConnectionManager from './ConnectionManager';
import '../styles/models-providers.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001';

const ModelsAndProvidersManager = ({ onProvidersChange }) => {
  const [activeSubTab, setActiveSubTab] = useState('models');
  const [stats, setStats] = useState({
    totalModels: 0,
    activeModels: 0,
    totalProviders: 0,
    activeProviders: 0,
    totalConnections: 0,
    activeConnections: 0
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      setLoading(true);
      
      // Load models stats
      const modelsResponse = await axios.get(`${API_BASE_URL}/api/models`);
      const models = modelsResponse.data.models || [];
      
      // Load providers stats
      const providersResponse = await axios.get(`${API_BASE_URL}/api/llm-providers`);
      const providers = providersResponse.data.providers || [];

      // Load connections stats
      const connectionsResponse = await axios.get(`${API_BASE_URL}/api/connections`);
      const connections = connectionsResponse.data.connections || [];

      setStats({
        totalModels: models.length,
        activeModels: models.filter(m => m.is_globally_active).length,
        totalProviders: providers.length,
        activeProviders: providers.length, // All providers are considered active for now
        totalConnections: connections.length,
        activeConnections: connections.filter(c => c.is_active).length
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
    if (onProvidersChange) {
      onProvidersChange();
    }
  };

  return (
    <div className="models-providers-manager">
      {/* Header with stunning gradient */}
      <div className="manager-hero">
        <div className="hero-content">
          <h1 className="hero-title">
            <span className="hero-icon">🤖</span>
            AI Models & Providers
          </h1>
          <p className="hero-subtitle">
            Manage your AI models and service providers with powerful tools and insights
          </p>
        </div>
        
        {/* Stats Dashboard */}
        <div className="stats-dashboard">
          <div className="stat-card models">
            <div className="stat-icon">🧠</div>
            <div className="stat-content">
              <div className="stat-number">{loading ? '...' : stats.totalModels}</div>
              <div className="stat-label">Total Models</div>
              <div className="stat-detail">{loading ? '...' : stats.activeModels} active</div>
            </div>
          </div>
          
          <div className="stat-card providers">
            <div className="stat-icon">🔌</div>
            <div className="stat-content">
              <div className="stat-number">{loading ? '...' : stats.totalProviders}</div>
              <div className="stat-label">Providers</div>
              <div className="stat-detail">{loading ? '...' : stats.activeProviders} connected</div>
            </div>
          </div>
          
          <div className="stat-card connections">
            <div className="stat-icon">🔗</div>
            <div className="stat-content">
              <div className="stat-number">{loading ? '...' : stats.totalConnections}</div>
              <div className="stat-label">Connections</div>
              <div className="stat-detail">{loading ? '...' : stats.activeConnections} active</div>
            </div>
          </div>
        </div>
      </div>

      {/* Sub-navigation tabs */}
      <div className="sub-tabs">
        <button
          className={`sub-tab ${activeSubTab === 'models' ? 'active' : ''}`}
          onClick={() => handleSubTabChange('models')}
        >
          <span className="tab-icon">🧠</span>
          <span className="tab-text">Models</span>
          <span className="tab-badge">{stats.totalModels}</span>
        </button>
        
        <button
          className={`sub-tab ${activeSubTab === 'providers' ? 'active' : ''}`}
          onClick={() => handleSubTabChange('providers')}
        >
          <span className="tab-icon">🔌</span>
          <span className="tab-text">Providers</span>
          <span className="tab-badge">{stats.totalProviders}</span>
        </button>

        <button
          className={`sub-tab ${activeSubTab === 'connections' ? 'active' : ''}`}
          onClick={() => handleSubTabChange('connections')}
        >
          <span className="tab-icon">🔗</span>
          <span className="tab-text">Connections</span>
          <span className="tab-badge">{stats.totalConnections}</span>
        </button>
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {activeSubTab === 'models' && (
          <div className="models-section">
            <ModelManager onDataChange={handleDataChange} />
          </div>
        )}
        
        {activeSubTab === 'providers' && (
          <div className="providers-section">
            <LlmProviderManager onProvidersChange={handleDataChange} />
          </div>
        )}

        {activeSubTab === 'connections' && (
          <div className="connections-section">
            <ConnectionManager onConnectionsChange={handleDataChange} />
          </div>
        )}
      </div>
    </div>
  );
};

export default ModelsAndProvidersManager;
