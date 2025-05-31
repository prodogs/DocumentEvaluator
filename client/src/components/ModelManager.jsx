import React, { useState, useEffect } from 'react';
import axios from 'axios';
import '../styles/management.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001';

const ModelManager = ({ onDataChange }) => {
  const [models, setModels] = useState([]);
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [showEditForm, setShowEditForm] = useState(false);
  const [editingModel, setEditingModel] = useState(null);
  const [expandedModels, setExpandedModels] = useState({});
  const [discoveringModels, setDiscoveringModels] = useState(false);
  const [selectedProviders, setSelectedProviders] = useState([]);

  const [formData, setFormData] = useState({
    display_name: '',
    notes: '',
    is_globally_active: true
  });

  useEffect(() => {
    loadModels();
    loadProviders();
  }, []);

  const loadModels = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE_URL}/api/models`);
      if (response.data.success) {
        setModels(response.data.models);
      }
    } catch (error) {
      console.error('Error loading models:', error);
      setMessage(`Error loading models: ${error.response?.data?.error || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const loadProviders = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/llm-providers`);
      if (response.data.success) {
        setProviders(response.data.providers);
      }
    } catch (error) {
      console.error('Error loading providers:', error);
    }
  };

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleDiscoverModels = async () => {
    if (selectedProviders.length === 0) {
      setMessage('❌ Please select at least one provider to discover models from');
      return;
    }

    setDiscoveringModels(true);
    setMessage('🔍 Discovering models from selected providers...');

    try {
      let totalDiscovered = 0;

      for (const providerId of selectedProviders) {
        const provider = providers.find(p => p.id === providerId);
        if (!provider) continue;

        try {
          // Get default config for the provider
          const configResponse = await axios.get(`${API_BASE_URL}/api/llm-providers/${providerId}/default-config`);
          const defaultConfig = configResponse.data.default_config;

          // Discover models
          const response = await axios.post(`${API_BASE_URL}/api/llm-providers/${providerId}/discover-models`, defaultConfig);

          if (response.data.success) {
            totalDiscovered += response.data.count;
          }
        } catch (error) {
          console.error(`Error discovering models for ${provider.name}:`, error);
        }
      }

      setMessage(`✅ Discovered ${totalDiscovered} models from ${selectedProviders.length} provider(s)`);
      loadModels();
      if (onDataChange) onDataChange();
    } catch (error) {
      console.error('Error discovering models:', error);
      setMessage(`❌ Error discovering models: ${error.message}`);
    } finally {
      setDiscoveringModels(false);
    }
  };

  const handleUpdateModel = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await axios.put(`${API_BASE_URL}/api/models/${editingModel.id}`, formData);

      if (response.data.success) {
        setMessage(`✅ Model updated successfully`);
        resetForm();
        loadModels();
        if (onDataChange) onDataChange();
      }
    } catch (error) {
      console.error('Error updating model:', error);
      setMessage(`❌ Error: ${error.response?.data?.error || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (model) => {
    setEditingModel(model);
    setFormData({
      display_name: model.display_name,
      notes: model.notes || '',
      is_globally_active: model.is_globally_active
    });
    setShowEditForm(true);
  };

  const handleDelete = async (model) => {
    if (!window.confirm(`Are you sure you want to delete the model "${model.display_name}"? This will remove all provider relationships.`)) {
      return;
    }

    try {
      const response = await axios.delete(`${API_BASE_URL}/api/models/${model.id}`);
      if (response.data.success) {
        setMessage(`✅ Model "${model.display_name}" deleted successfully`);
        loadModels();
        if (onDataChange) onDataChange();
      }
    } catch (error) {
      console.error('Error deleting model:', error);
      setMessage(`❌ Error: ${error.response?.data?.error || error.message}`);
    }
  };

  const toggleGlobalStatus = async (model) => {
    try {
      const response = await axios.put(`${API_BASE_URL}/api/models/${model.id}/toggle-global`, {
        is_globally_active: !model.is_globally_active
      });
      
      if (response.data.success) {
        setMessage(response.data.message);
        loadModels();
        if (onDataChange) onDataChange();
      }
    } catch (error) {
      console.error('Error toggling model status:', error);
      setMessage(`❌ Error: ${error.response?.data?.error || error.message}`);
    }
  };

  const toggleExpandModel = (modelId) => {
    setExpandedModels(prev => ({
      ...prev,
      [modelId]: !prev[modelId]
    }));
  };

  const resetForm = () => {
    setFormData({
      display_name: '',
      notes: '',
      is_globally_active: true
    });
    setEditingModel(null);
    setShowEditForm(false);
  };

  const getModelFamilyIcon = (family) => {
    const icons = {
      'GPT': '🤖',
      'Claude': '🧠',
      'LLaMA': '🦙',
      'Mistral': '🌪️',
      'Qwen': '🐉',
      'Gemini': '💎',
      'PaLM': '🌴',
      'Other': '📝'
    };
    return icons[family] || icons['Other'];
  };

  return (
    <div className="management-container">
      <div className="management-header">
        <h2>Model Management</h2>
        <p>Models are automatically discovered from configured providers. You can customize display names and manage model settings.</p>

        {message && (
          <div className={`message ${message.includes('❌') ? 'error' : 'success'}`}>
            {message}
          </div>
        )}

        <div className="discovery-section">
          <h3>Discover Models from Providers</h3>
          <div className="provider-selection">
            <div className="provider-checkboxes">
              {providers.map(provider => (
                <label key={provider.id} className="provider-checkbox">
                  <input
                    type="checkbox"
                    checked={selectedProviders.includes(provider.id)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedProviders(prev => [...prev, provider.id]);
                      } else {
                        setSelectedProviders(prev => prev.filter(id => id !== provider.id));
                      }
                    }}
                    disabled={discoveringModels || !provider.supports_model_discovery}
                  />
                  <span className={`provider-name ${!provider.supports_model_discovery ? 'disabled' : ''}`}>
                    {provider.name}
                    {!provider.supports_model_discovery && ' (No Discovery)'}
                  </span>
                </label>
              ))}
            </div>
            <button
              onClick={handleDiscoverModels}
              className="btn btn-primary"
              disabled={discoveringModels || selectedProviders.length === 0}
            >
              {discoveringModels ? '🔍 Discovering...' : '🔍 Discover Models'}
            </button>
          </div>
        </div>
      </div>

      {showEditForm && editingModel && (
        <div className="form-container">
          <h3>Edit Model: {editingModel.common_name}</h3>
          <div className="model-info">
            <div className="info-row">
              <strong>Common Name:</strong> {editingModel.common_name} <small>(Auto-generated, cannot be changed)</small>
            </div>
            <div className="info-row">
              <strong>Model Family:</strong> {editingModel.model_family || 'Unknown'} <small>(Auto-detected from provider)</small>
            </div>
            <div className="info-row">
              <strong>Parameter Count:</strong> {editingModel.parameter_count || 'Unknown'} <small>(Auto-detected from provider)</small>
            </div>
            <div className="info-row">
              <strong>Context Length:</strong> {editingModel.context_length ? `${editingModel.context_length.toLocaleString()} tokens` : 'Unknown'} <small>(Auto-detected from provider)</small>
            </div>
          </div>

          <form onSubmit={handleUpdateModel} className="management-form">
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="display_name">Display Name *</label>
                <input
                  type="text"
                  id="display_name"
                  name="display_name"
                  value={formData.display_name}
                  onChange={handleInputChange}
                  disabled={loading}
                  placeholder="e.g., GPT-4, Claude 3 Opus, LLaMA 2 7B"
                  required
                />
                <small>Customize how this model appears in the interface</small>
              </div>
            </div>

            <div className="form-row">
              <div className="form-group full-width">
                <label htmlFor="notes">Notes</label>
                <textarea
                  id="notes"
                  name="notes"
                  value={formData.notes}
                  onChange={handleInputChange}
                  disabled={loading}
                  placeholder="Add any notes about this model..."
                  rows="3"
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    name="is_globally_active"
                    checked={formData.is_globally_active}
                    onChange={handleInputChange}
                    disabled={loading}
                  />
                  Globally Active
                </label>
                <small>When disabled, this model won't be available for new configurations</small>
              </div>
            </div>

            <div className="form-actions">
              <button type="submit" className="btn btn-primary" disabled={loading}>
                {loading ? 'Updating...' : 'Update Model'}
              </button>
              <button type="button" onClick={resetForm} className="btn btn-secondary" disabled={loading}>
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="models-list">
        <h4>Discovered Models ({models.length})</h4>
        <p>Models automatically discovered from configured providers. Click "Edit" to customize display names.</p>

        {loading ? (
          <div className="loading">Loading models...</div>
        ) : models.length === 0 ? (
          <div className="no-data">
            <p>No models discovered yet.</p>
            <p>Use the "Discover Models" section above to find models from your configured providers.</p>
          </div>
        ) : (
          <div className="models-grid">
            {models.map(model => {
              const isExpanded = expandedModels[model.id];
              const activeProviders = model.providers?.filter(p => p.is_active).length || 0;
              const totalProviders = model.providers?.length || 0;

              return (
                <div key={model.id} className="model-card">
                  <div className="model-header">
                    <div className="model-title">
                      <span className="model-icon">{getModelFamilyIcon(model.model_family)}</span>
                      <div>
                        <h5>{model.display_name}</h5>
                        <span className="model-common-name">{model.common_name}</span>
                      </div>
                    </div>
                    
                    <div className="model-actions">
                      <button
                        onClick={() => toggleGlobalStatus(model)}
                        className={`btn btn-xs ${model.is_globally_active ? 'btn-success' : 'btn-warning'}`}
                        title={model.is_globally_active ? 'Globally Active' : 'Globally Inactive'}
                      >
                        {model.is_globally_active ? '🟢' : '🟡'}
                      </button>
                      
                      <button
                        onClick={() => toggleExpandModel(model.id)}
                        className="btn btn-xs btn-info"
                        title={isExpanded ? 'Collapse' : 'Expand'}
                      >
                        {isExpanded ? '🔼' : '🔽'}
                      </button>
                      
                      <button
                        onClick={() => handleEdit(model)}
                        className="btn btn-xs btn-primary"
                        title="Edit"
                      >
                        ✏️
                      </button>
                      
                      <button
                        onClick={() => handleDelete(model)}
                        className="btn btn-xs btn-danger"
                        title="Delete"
                      >
                        🗑️
                      </button>
                    </div>
                  </div>

                  <div className="model-details">
                    <div><strong>Common Name:</strong> <code>{model.common_name}</code> <small>(Auto-generated)</small></div>
                    <div><strong>Family:</strong> {model.model_family || 'Unknown'} <small>(Auto-detected)</small></div>
                    {model.parameter_count && (
                      <div><strong>Parameters:</strong> {model.parameter_count} <small>(Auto-detected)</small></div>
                    )}
                    {model.context_length && (
                      <div><strong>Context:</strong> {model.context_length.toLocaleString()} tokens <small>(Auto-detected)</small></div>
                    )}
                    <div><strong>Discovered by:</strong> {totalProviders} provider{totalProviders !== 1 ? 's' : ''} ({activeProviders} active)</div>
                    <div><strong>Status:</strong>
                      <span className={`status ${model.is_globally_active ? 'active' : 'inactive'}`}>
                        {model.is_globally_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                    {model.notes && (
                      <div><strong>Notes:</strong> {model.notes}</div>
                    )}
                  </div>

                  {isExpanded && (
                    <div className="model-expanded">
                      {model.providers && model.providers.length > 0 && (
                        <div className="model-providers">
                          <h6>Available Providers ({model.providers.length})</h6>
                          <div className="providers-list">
                            {model.providers.map(provider => (
                              <div key={`${provider.provider_id}-${model.id}`} className={`provider-item ${provider.is_active ? 'active' : 'inactive'}`}>
                                <div className="provider-info">
                                  <span className="provider-name">{provider.provider_name}</span>
                                  <span className="provider-model-name">({provider.provider_model_name})</span>
                                </div>
                                <span className={`status ${provider.is_active ? 'active' : 'inactive'}`}>
                                  {provider.is_active ? 'Active' : 'Inactive'}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {model.aliases && model.aliases.length > 0 && (
                        <div className="model-aliases">
                          <h6>Aliases ({model.aliases.length})</h6>
                          <div className="aliases-list">
                            {model.aliases.map(alias => (
                              <span key={alias} className="alias-tag">{alias}</span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default ModelManager;
