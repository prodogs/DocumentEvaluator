import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001';

const LlmConfigManager = ({ onConfigsChange }) => {
  const [configs, setConfigs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingConfig, setEditingConfig] = useState(null);
  const [testingConfig, setTestingConfig] = useState(null);
  const [testResults, setTestResults] = useState({});
  const [availableModels, setAvailableModels] = useState([]);
  const [fetchingModels, setFetchingModels] = useState(false);
  const [modelsError, setModelsError] = useState('');
  const [formData, setFormData] = useState({
    llm_name: '',
    base_url: '',
    model_name: '',
    provider_type: 'ollama',
    api_key: '',
    port_no: 0,
    active: true
  });

  useEffect(() => {
    loadConfigs();
  }, []);

  const loadConfigs = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE_URL}/api/llm-configurations`);
      setConfigs(response.data.llm_configurations || []);
      if (onConfigsChange) {
        onConfigsChange(response.data.llm_configurations || []);
      }
    } catch (error) {
      console.error('Error loading LLM configurations:', error);
      setMessage(`Error loading configurations: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);

      if (editingConfig) {
        // Update existing config
        await axios.put(`${API_BASE_URL}/api/llm-configurations/${editingConfig.id}`, formData);
        setMessage('Configuration updated successfully');
      } else {
        // Create new config
        await axios.post(`${API_BASE_URL}/api/llm-configurations`, formData);
        setMessage('Configuration created successfully');
      }

      resetForm();
      loadConfigs();
    } catch (error) {
      console.error('Error saving configuration:', error);
      setMessage(`Error: ${error.response?.data?.error || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (config) => {
    setEditingConfig(config);
    setFormData({
      llm_name: config.llm_name,
      base_url: config.base_url,
      model_name: config.model_name,
      provider_type: config.provider_type,
      api_key: config.api_key || '',
      port_no: config.port_no || 0,
      active: config.active
    });
    setShowForm(true);
  };

  const handleDelete = async (config) => {
    if (!window.confirm(`Are you sure you want to delete "${config.llm_name}"?`)) {
      return;
    }

    try {
      setLoading(true);
      await axios.delete(`${API_BASE_URL}/api/llm-configurations/${config.id}`);
      setMessage('Configuration deleted successfully');
      loadConfigs();
    } catch (error) {
      console.error('Error deleting configuration:', error);
      setMessage(`Error: ${error.response?.data?.error || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleActive = async (config) => {
    try {
      setLoading(true);
      const endpoint = config.active ? 'deactivate' : 'activate';
      await axios.post(`${API_BASE_URL}/api/llm-configurations/${config.id}/${endpoint}`);
      setMessage(`Configuration ${config.active ? 'deactivated' : 'activated'} successfully`);
      loadConfigs();
    } catch (error) {
      console.error('Error toggling configuration:', error);
      setMessage(`Error: ${error.response?.data?.error || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleTestConfig = async (config) => {
    try {
      setTestingConfig(config.id);
      setMessage('Testing LLM configuration...');

      const response = await axios.post(`${API_BASE_URL}/api/llm-configurations/${config.id}/test`);

      const testResult = {
        success: true,
        ...response.data,
        timestamp: new Date().toISOString()
      };

      console.log('Test successful, storing result:', testResult);

      setTestResults(prev => ({
        ...prev,
        [config.id]: testResult
      }));

      setMessage(`Test successful! Response time: ${response.data.response_time_ms}ms`);

    } catch (error) {
      console.error('Error testing configuration:', error);
      const errorData = error.response?.data;

      const errorResult = {
        success: false,
        message: errorData?.message || 'Test failed',
        error: errorData?.error || error.message,
        response_time_ms: errorData?.response_time_ms || 0,
        timestamp: new Date().toISOString()
      };

      console.log('Test failed, storing result:', errorResult);

      setTestResults(prev => ({
        ...prev,
        [config.id]: errorResult
      }));

      setMessage(`Test failed: ${errorData?.error || error.message}`);
    } finally {
      setTestingConfig(null);
    }
  };

  const resetForm = () => {
    setFormData({
      llm_name: '',
      base_url: '',
      model_name: '',
      provider_type: 'ollama',
      api_key: '',
      port_no: 0,
      active: true
    });
    setEditingConfig(null);
    setShowForm(false);
  };

  const fetchAvailableModels = async (baseUrl, providerType, apiKey = '') => {
    if (!baseUrl || !providerType) return;

    setFetchingModels(true);
    setModelsError('');

    try {
      const response = await axios.post(`${API_BASE_URL}/api/llm-configurations/models`, {
        base_url: baseUrl,
        provider_type: providerType,
        api_key: apiKey
      });

      if (response.data.success) {
        setAvailableModels(response.data.models || []);
        setMessage(`Found ${response.data.total_models} available models`);
      } else {
        setModelsError(response.data.error || 'Failed to fetch models');
        setAvailableModels([]);
      }
    } catch (error) {
      console.error('Error fetching models:', error);
      const errorMsg = error.response?.data?.error || error.message || 'Failed to fetch models';
      setModelsError(errorMsg);
      setAvailableModels([]);
    } finally {
      setFetchingModels(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    const newValue = type === 'checkbox' ? checked : (name === 'port_no' ? parseInt(value) || 0 : value);

    setFormData(prev => ({
      ...prev,
      [name]: newValue
    }));

    // Auto-fetch models when base_url or provider_type changes
    if (name === 'base_url' || name === 'provider_type') {
      const updatedFormData = { ...formData, [name]: newValue };

      // Only fetch if we have both base_url and provider_type
      if (updatedFormData.base_url && updatedFormData.provider_type) {
        // Debounce the API call
        setTimeout(() => {
          fetchAvailableModels(
            updatedFormData.base_url,
            updatedFormData.provider_type,
            updatedFormData.api_key
          );
        }, 500);
      } else {
        // Clear models if incomplete data
        setAvailableModels([]);
        setModelsError('');
      }
    }
  };

  return (
    <div className="llm-config-manager">
      <div className="manager-header">
        <h3>LLM Configuration Management</h3>
        <button
          onClick={() => setShowForm(!showForm)}
          className="btn btn-primary"
          disabled={loading}
        >
          {showForm ? 'Cancel' : 'Add New Configuration'}
        </button>
      </div>

      {message && (
        <div className={`message ${message.includes('Error') ? 'error' : 'success'}`}>
          {message}
        </div>
      )}

      {showForm && (
        <form onSubmit={handleSubmit} className="config-form">
          <h4>{editingConfig ? 'Edit Configuration' : 'Add New Configuration'}</h4>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="llm_name">LLM Name *</label>
              <input
                type="text"
                id="llm_name"
                name="llm_name"
                value={formData.llm_name}
                onChange={handleInputChange}
                required
                disabled={loading}
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
                <option value="ollama">Ollama</option>
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic</option>
                <option value="huggingface">Hugging Face</option>
                <option value="custom">Custom</option>
              </select>
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="base_url">Base URL *</label>
              <div className="url-input-group">
                <input
                  type="url"
                  id="base_url"
                  name="base_url"
                  value={formData.base_url}
                  onChange={handleInputChange}
                  required
                  disabled={loading}
                  placeholder="http://localhost:11434"
                />
                <button
                  type="button"
                  onClick={() => fetchAvailableModels(formData.base_url, formData.provider_type, formData.api_key)}
                  disabled={loading || fetchingModels || !formData.base_url || !formData.provider_type}
                  className="btn btn-sm btn-secondary fetch-models-btn"
                  title="Fetch Available Models"
                >
                  {fetchingModels ? '⏳' : '🔄'}
                </button>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="model_name">Model Name *</label>
              {availableModels.length > 0 ? (
                <div className="model-selection">
                  <select
                    id="model_name"
                    name="model_name"
                    value={formData.model_name}
                    onChange={handleInputChange}
                    required
                    disabled={loading}
                  >
                    <option value="">Select a model...</option>
                    {availableModels.map(model => (
                      <option key={model.id} value={model.id}>
                        {model.name} {model.size && `(${(model.size / 1024 / 1024 / 1024).toFixed(1)}GB)`}
                      </option>
                    ))}
                  </select>
                  <div className="model-info">
                    {fetchingModels && <span className="fetching">🔄 Fetching models...</span>}
                    {!fetchingModels && availableModels.length > 0 && (
                      <span className="model-count">✅ {availableModels.length} models available</span>
                    )}
                  </div>
                </div>
              ) : (
                <div className="model-input-fallback">
                  <input
                    type="text"
                    id="model_name"
                    name="model_name"
                    value={formData.model_name}
                    onChange={handleInputChange}
                    required
                    disabled={loading}
                    placeholder={fetchingModels ? "Fetching models..." : "Enter model name manually"}
                  />
                  <div className="model-info">
                    {fetchingModels && <span className="fetching">🔄 Fetching models...</span>}
                    {modelsError && <span className="error">⚠️ {modelsError}</span>}
                    {!fetchingModels && !modelsError && formData.base_url && formData.provider_type && (
                      <span className="hint">💡 Enter base URL and provider type to auto-fetch models</span>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="api_key">API Key</label>
              <input
                type="password"
                id="api_key"
                name="api_key"
                value={formData.api_key}
                onChange={handleInputChange}
                disabled={loading}
                placeholder="Optional for some providers"
              />
            </div>

            <div className="form-group">
              <label htmlFor="port_no">Port Number</label>
              <input
                type="number"
                id="port_no"
                name="port_no"
                value={formData.port_no}
                onChange={handleInputChange}
                disabled={loading}
                min="0"
                max="65535"
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  name="active"
                  checked={formData.active}
                  onChange={handleInputChange}
                  disabled={loading}
                />
                Active
              </label>
            </div>
          </div>

          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Saving...' : (editingConfig ? 'Update' : 'Create')}
            </button>
            <button type="button" onClick={resetForm} className="btn btn-secondary" disabled={loading}>
              Cancel
            </button>
          </div>
        </form>
      )}

      <div className="configs-list">
        <h4>Existing Configurations ({configs.length})</h4>
        {loading && <div className="loading">Loading...</div>}

        {configs.length === 0 && !loading ? (
          <div className="no-data">No configurations found. Add one to get started.</div>
        ) : (
          <div className="configs-grid">
            {configs.map(config => (
              <div key={config.id} className={`config-card ${config.active ? 'active' : 'inactive'}`}>
                <div className="config-header">
                  <h5>{config.llm_name}</h5>
                  <div className="config-actions">
                    <button
                      onClick={() => handleTestConfig(config)}
                      className="btn btn-sm btn-info"
                      disabled={loading || testingConfig === config.id}
                      title="Test Configuration"
                    >
                      {testingConfig === config.id ? '⏳' : '🧪'}
                    </button>
                    <button
                      onClick={() => handleToggleActive(config)}
                      className={`btn btn-sm ${config.active ? 'btn-warning' : 'btn-success'}`}
                      disabled={loading}
                      title={config.active ? 'Deactivate' : 'Activate'}
                    >
                      {config.active ? '🔴' : '🟢'}
                    </button>
                    <button
                      onClick={() => handleEdit(config)}
                      className="btn btn-sm btn-secondary"
                      disabled={loading}
                      title="Edit"
                    >
                      ✏️
                    </button>
                    <button
                      onClick={() => handleDelete(config)}
                      className="btn btn-sm btn-danger"
                      disabled={loading}
                      title="Delete"
                    >
                      🗑️
                    </button>
                  </div>
                </div>

                <div className="config-details">
                  <div><strong>Provider:</strong> {config.provider_type}</div>
                  <div><strong>Model:</strong> {config.model_name}</div>
                  <div><strong>Base URL:</strong> {config.base_url}</div>
                  {config.port_no > 0 && <div><strong>Port:</strong> {config.port_no}</div>}
                  <div><strong>Status:</strong>
                    <span className={`status ${config.active ? 'active' : 'inactive'}`}>
                      {config.active ? 'Active' : 'Inactive'}
                    </span>
                  </div>

                  {testResults[config.id] && (
                    <div className="test-results">
                      <div className="test-results-header">
                        <strong>Last Test:</strong>
                        <span className={`test-status ${testResults[config.id].success ? 'success' : 'failed'}`}>
                          {testResults[config.id].success ? '✅ Passed' : '❌ Failed'}
                        </span>
                      </div>

                      <div className="test-details">
                        <div><strong>Response Time:</strong> {testResults[config.id].response_time_ms}ms</div>
                        <div><strong>Tested:</strong> {new Date(testResults[config.id].timestamp).toLocaleString()}</div>

                        {testResults[config.id].success ? (
                          <div className="test-response">
                            <strong>Response:</strong>
                            <div className="response-text">
                              {typeof testResults[config.id].response === 'string'
                                ? testResults[config.id].response.substring(0, 100)
                                : JSON.stringify(testResults[config.id].response).substring(0, 100)
                              }
                              {(typeof testResults[config.id].response === 'string'
                                ? testResults[config.id].response.length
                                : JSON.stringify(testResults[config.id].response).length) > 100 && '...'}
                            </div>
                          </div>
                        ) : (
                          <div className="test-error">
                            <strong>Error:</strong> {testResults[config.id].error}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default LlmConfigManager;
