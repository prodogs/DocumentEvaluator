import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001';

const LlmProviderManager = ({ onProvidersChange }) => {
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingProvider, setEditingProvider] = useState(null);
  const [testingProvider, setTestingProvider] = useState(null);
  const [discoveringModels, setDiscoveringModels] = useState(null);
  const [providerModels, setProviderModels] = useState({});
  const [expandedProviders, setExpandedProviders] = useState({});
  const [providerTypes, setProviderTypes] = useState([]);
  const [testResults, setTestResults] = useState({});

  const [formData, setFormData] = useState({
    name: '',
    provider_type: 'ollama',
    default_base_url: '',
    supports_model_discovery: true,
    auth_type: 'api_key',
    notes: ''
  });

  useEffect(() => {
    loadProviders();
    loadProviderTypes();
  }, []);

  const loadProviders = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE_URL}/api/llm-providers`);
      if (response.data.success) {
        setProviders(response.data.providers);
        if (onProvidersChange) {
          onProvidersChange(response.data.providers);
        }
      }
    } catch (error) {
      console.error('Error loading providers:', error);
      setMessage(`Error loading providers: ${error.response?.data?.error || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const loadProviderTypes = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/llm-providers/types`);
      if (response.data.success) {
        setProviderTypes(response.data.provider_types);
      }
    } catch (error) {
      console.error('Error loading provider types:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);

      if (editingProvider) {
        // Update existing provider
        await axios.put(`${API_BASE_URL}/api/llm-providers/${editingProvider.id}`, formData);
        setMessage('Provider updated successfully');
      } else {
        // Create new provider
        await axios.post(`${API_BASE_URL}/api/llm-providers`, formData);
        setMessage('Provider created successfully');
      }

      resetForm();
      loadProviders();
    } catch (error) {
      console.error('Error saving provider:', error);
      setMessage(`Error: ${error.response?.data?.error || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (provider) => {
    setEditingProvider(provider);
    setFormData({
      name: provider.name,
      provider_type: provider.provider_type,
      default_base_url: provider.default_base_url || '',
      supports_model_discovery: provider.supports_model_discovery,
      auth_type: provider.auth_type,
      notes: provider.notes || ''
    });
    setShowForm(true);
  };

  const handleDelete = async (providerId) => {
    if (!window.confirm('Are you sure you want to delete this provider? This will also delete all associated models.')) {
      return;
    }

    try {
      setLoading(true);
      await axios.delete(`${API_BASE_URL}/api/llm-providers/${providerId}`);
      setMessage('Provider deleted successfully');
      loadProviders();
    } catch (error) {
      console.error('Error deleting provider:', error);
      setMessage(`Error: ${error.response?.data?.error || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleTestConnection = async (provider) => {
    const startTime = Date.now();
    try {
      setTestingProvider(provider.id);

      // Get default config for the provider
      const configResponse = await axios.get(`${API_BASE_URL}/api/llm-providers/${provider.id}/default-config`);
      const defaultConfig = configResponse.data.default_config;

      // Test connection with default config
      const response = await axios.post(`${API_BASE_URL}/api/llm-providers/${provider.id}/test-connection`, defaultConfig);
      const responseTime = Date.now() - startTime;

      // Store test results
      setTestResults(prev => ({
        ...prev,
        [provider.id]: {
          success: response.data.success,
          message: response.data.message,
          response_time_ms: responseTime,
          timestamp: new Date().toISOString(),
          error: response.data.success ? null : response.data.message
        }
      }));

      if (response.data.success) {
        setMessage(`✅ ${provider.name}: Connection successful`);
      } else {
        setMessage(`❌ ${provider.name}: ${response.data.message}`);
      }
    } catch (error) {
      const responseTime = Date.now() - startTime;
      console.error('Error testing connection:', error);
      const errorMessage = error.response?.data?.error || error.message;

      // Store test results for failed connection
      setTestResults(prev => ({
        ...prev,
        [provider.id]: {
          success: false,
          message: errorMessage,
          response_time_ms: responseTime,
          timestamp: new Date().toISOString(),
          error: errorMessage
        }
      }));

      setMessage(`❌ ${provider.name}: ${errorMessage}`);
    } finally {
      setTestingProvider(null);
    }
  };

  const handleDiscoverModels = async (provider) => {
    try {
      setDiscoveringModels(provider.id);
      
      // Get default config for the provider
      const configResponse = await axios.get(`${API_BASE_URL}/api/llm-providers/${provider.id}/default-config`);
      const defaultConfig = configResponse.data.default_config;
      
      // Discover models
      const response = await axios.post(`${API_BASE_URL}/api/llm-providers/${provider.id}/discover-models`, defaultConfig);
      
      if (response.data.success) {
        setMessage(`✅ Discovered ${response.data.count} models for ${provider.name}`);
        loadProviderModels(provider.id);
      } else {
        setMessage(`❌ ${provider.name}: ${response.data.error}`);
      }
    } catch (error) {
      console.error('Error discovering models:', error);
      setMessage(`❌ ${provider.name}: ${error.response?.data?.error || error.message}`);
    } finally {
      setDiscoveringModels(null);
    }
  };

  const loadProviderModels = async (providerId) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/providers/${providerId}/models`);
      if (response.data.success) {
        setProviderModels(prev => ({
          ...prev,
          [providerId]: response.data.models
        }));
      }
    } catch (error) {
      console.error('Error loading provider models:', error);
    }
  };

  const toggleModelStatus = async (providerId, modelId, currentStatus) => {
    try {
      const response = await axios.put(`${API_BASE_URL}/api/providers/${providerId}/models/${modelId}/toggle`, {
        is_active: !currentStatus
      });

      if (response.data.success) {
        setMessage(response.data.message);
        loadProviderModels(providerId);
      }
    } catch (error) {
      console.error('Error toggling model status:', error);
      setMessage(`Error: ${error.response?.data?.error || error.message}`);
    }
  };

  const toggleExpandProvider = (providerId) => {
    setExpandedProviders(prev => ({
      ...prev,
      [providerId]: !prev[providerId]
    }));

    // Load models if not already loaded and expanding
    if (!expandedProviders[providerId] && !providerModels[providerId]) {
      loadProviderModels(providerId);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      provider_type: 'ollama',
      default_base_url: '',
      supports_model_discovery: true,
      auth_type: 'api_key',
      notes: ''
    });
    setEditingProvider(null);
    setShowForm(false);
  };

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const getProviderTypeInfo = (providerType) => {
    return providerTypes.find(type => type.type === providerType) || {};
  };

  return (
    <div className="provider-manager">
      <div className="manager-header">
        <h3>LLM Provider Management</h3>
        <button
          onClick={() => setShowForm(!showForm)}
          className="btn btn-primary"
          disabled={loading}
        >
          {showForm ? 'Cancel' : 'Add New Provider'}
        </button>
      </div>

      {message && (
        <div className={`message ${message.includes('Error') || message.includes('❌') ? 'error' : 'success'}`}>
          {message}
        </div>
      )}

      {showForm && (
        <form onSubmit={handleSubmit} className="provider-form">
          <h4>{editingProvider ? 'Edit Provider' : 'Add New Provider'}</h4>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="name">Provider Name *</label>
              <input
                type="text"
                id="name"
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                required
                disabled={loading}
                placeholder="e.g., My Ollama Server"
              />
            </div>

            <div className="form-group">
              <label htmlFor="provider_type">Provider Type *</label>
              <select
                id="provider_type"
                name="provider_type"
                value={formData.provider_type}
                onChange={handleInputChange}
                required
                disabled={loading}
              >
                {providerTypes.map(type => (
                  <option key={type.type} value={type.type}>
                    {type.name} - {type.description}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="default_base_url">Default Base URL</label>
              <input
                type="url"
                id="default_base_url"
                name="default_base_url"
                value={formData.default_base_url}
                onChange={handleInputChange}
                disabled={loading}
                placeholder="e.g., http://localhost:11434"
              />
            </div>

            <div className="form-group">
              <label htmlFor="auth_type">Authentication Type</label>
              <select
                id="auth_type"
                name="auth_type"
                value={formData.auth_type}
                onChange={handleInputChange}
                disabled={loading}
              >
                <option value="none">None</option>
                <option value="api_key">API Key</option>
                <option value="oauth">OAuth</option>
                <option value="aws_credentials">AWS Credentials</option>
              </select>
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  name="supports_model_discovery"
                  checked={formData.supports_model_discovery}
                  onChange={handleInputChange}
                  disabled={loading}
                />
                Supports Model Discovery
              </label>
            </div>
          </div>

          <div className="form-row">
            <div className="form-group full-width">
              <label htmlFor="notes">Notes</label>
              <textarea
                id="notes"
                name="notes"
                value={formData.notes || ''}
                onChange={handleInputChange}
                disabled={loading}
                placeholder="Add any notes about this provider..."
                rows="3"
              />
            </div>
          </div>

          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Saving...' : (editingProvider ? 'Update' : 'Create')}
            </button>
            <button type="button" onClick={resetForm} className="btn btn-secondary" disabled={loading}>
              Cancel
            </button>
          </div>
        </form>
      )}

      <div className="providers-list">
        <h4>Existing Providers ({providers.length})</h4>
        {loading && <div className="loading">Loading...</div>}

        {providers.length === 0 && !loading ? (
          <div className="no-data">No providers found. Add one to get started.</div>
        ) : (
          <div className="providers-grid">
            {providers.map(provider => {
              const typeInfo = getProviderTypeInfo(provider.provider_type);
              const models = providerModels[provider.id] || [];
              const activeModels = models.filter(m => m.is_active).length;
              const isExpanded = expandedProviders[provider.id];

              return (
                <div key={provider.id} className="provider-card">
                  <div className="provider-header">
                    <h5>{provider.name}</h5>
                    <div className="provider-actions">
                      <button
                        onClick={() => handleTestConnection(provider)}
                        className="btn btn-sm btn-info"
                        disabled={loading || testingProvider === provider.id}
                        title="Test Connection"
                      >
                        {testingProvider === provider.id ? '⏳' : '🧪'}
                      </button>

                      {provider.supports_model_discovery && (
                        <button
                          onClick={() => handleDiscoverModels(provider)}
                          className="btn btn-sm btn-success"
                          disabled={loading || discoveringModels === provider.id}
                          title="Discover Models"
                        >
                          {discoveringModels === provider.id ? '⏳' : '🔍'}
                        </button>
                      )}

                      <button
                        onClick={() => toggleExpandProvider(provider.id)}
                        className="btn btn-sm btn-secondary"
                        title={isExpanded ? 'Collapse' : 'Expand'}
                      >
                        {isExpanded ? '🔼' : '🔽'}
                      </button>

                      <button
                        onClick={() => handleEdit(provider)}
                        className="btn btn-sm btn-secondary"
                        disabled={loading}
                        title="Edit"
                      >
                        ✏️
                      </button>

                      <button
                        onClick={() => handleDelete(provider.id)}
                        className="btn btn-sm btn-danger"
                        disabled={loading}
                        title="Delete"
                      >
                        🗑️
                      </button>
                    </div>
                  </div>

                  <div className="provider-details">
                    <div><strong>Provider:</strong> {typeInfo.name || provider.provider_type}</div>
                    <div><strong>Type:</strong> {provider.provider_type}</div>
                    <div><strong>Auth Type:</strong> {provider.auth_type}</div>
                    {provider.default_base_url && (
                      <div><strong>Base URL:</strong> {provider.default_base_url}</div>
                    )}
                    <div><strong>Model Discovery:</strong> {provider.supports_model_discovery ? 'Enabled' : 'Disabled'}</div>
                    {models.length > 0 && (
                      <div><strong>Models:</strong> {activeModels}/{models.length} active</div>
                    )}
                    <div><strong>Status:</strong>
                      <span className={`status active`}>
                        Active
                      </span>
                    </div>
                    {provider.notes && (
                      <div><strong>Notes:</strong> {provider.notes}</div>
                    )}

                    {testResults[provider.id] && (
                      <div className="test-results">
                        <div className="test-results-header">
                          <strong>Last Test:</strong>
                          <span className={`test-status ${testResults[provider.id].success ? 'success' : 'failed'}`}>
                            {testResults[provider.id].success ? '✅ Passed' : '❌ Failed'}
                          </span>
                        </div>

                        <div className="test-details">
                          <div><strong>Response Time:</strong> {testResults[provider.id].response_time_ms}ms</div>
                          <div><strong>Tested:</strong> {new Date(testResults[provider.id].timestamp).toLocaleString()}</div>

                          {testResults[provider.id].success ? (
                            <div className="test-response">
                              <strong>Message:</strong> {testResults[provider.id].message}
                            </div>
                          ) : (
                            <div className="test-error">
                              <strong>Error:</strong> {testResults[provider.id].error}
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {isExpanded && models.length > 0 && (
                      <div className="provider-models">
                        <h6>Models ({models.length})</h6>
                        <div className="models-list">
                          {models.map(model => (
                            <div key={model.id} className={`model-item ${model.is_active ? 'active' : 'inactive'}`}>
                              <div className="model-info">
                                <span className="model-name">{model.model?.display_name || model.provider_model_name}</span>
                                <span className="model-common-name">({model.model?.common_name})</span>
                              </div>
                              <button
                                onClick={() => toggleModelStatus(provider.id, model.model_id, model.is_active)}
                                className={`btn btn-xs ${model.is_active ? 'btn-warning' : 'btn-success'}`}
                                title={model.is_active ? 'Deactivate' : 'Activate'}
                              >
                                {model.is_active ? '🔴' : '🟢'}
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {isExpanded && models.length === 0 && (
                      <div className="no-models">
                        <p>No models discovered yet. Click "🔍" to discover models.</p>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default LlmProviderManager;
