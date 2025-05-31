import React, { useState, useEffect } from 'react';
import axios from 'axios';
import '../styles/management.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001';

const ModelManager = ({ onDataChange }) => {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingModel, setEditingModel] = useState(null);
  const [expandedModels, setExpandedModels] = useState({});
  const [modelFamilies, setModelFamilies] = useState([]);

  const [formData, setFormData] = useState({
    common_name: '',
    display_name: '',
    notes: '',
    model_family: 'Other',
    parameter_count: '',
    context_length: '',
    is_globally_active: true
  });

  useEffect(() => {
    loadModels();
    loadModelFamilies();
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

  const loadModelFamilies = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/models/families`);
      if (response.data.success) {
        setModelFamilies(response.data.families);
      }
    } catch (error) {
      console.error('Error loading model families:', error);
    }
  };

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const url = editingModel 
        ? `${API_BASE_URL}/api/models/${editingModel.id}`
        : `${API_BASE_URL}/api/models`;
      
      const method = editingModel ? 'PUT' : 'POST';
      
      const response = await axios({
        method,
        url,
        data: formData
      });

      if (response.data.success) {
        setMessage(`✅ Model ${editingModel ? 'updated' : 'created'} successfully`);
        resetForm();
        loadModels();
        if (onDataChange) onDataChange();
      }
    } catch (error) {
      console.error('Error saving model:', error);
      setMessage(`❌ Error: ${error.response?.data?.error || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (model) => {
    setEditingModel(model);
    setFormData({
      common_name: model.common_name,
      display_name: model.display_name,
      notes: model.notes || '',
      model_family: model.model_family || 'Other',
      parameter_count: model.parameter_count || '',
      context_length: model.context_length || '',
      is_globally_active: model.is_globally_active
    });
    setShowForm(true);
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
      common_name: '',
      display_name: '',
      notes: '',
      model_family: 'Other',
      parameter_count: '',
      context_length: '',
      is_globally_active: true
    });
    setEditingModel(null);
    setShowForm(false);
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
        <p>Manage AI models independently from service providers. Models can be offered by multiple providers.</p>
        
        {message && (
          <div className={`message ${message.includes('❌') ? 'error' : 'success'}`}>
            {message}
          </div>
        )}

        <div className="header-actions">
          <button 
            onClick={() => setShowForm(!showForm)} 
            className="btn btn-primary"
            disabled={loading}
          >
            {showForm ? 'Cancel' : 'Add Model'}
          </button>
        </div>
      </div>

      {showForm && (
        <div className="form-container">
          <h3>{editingModel ? 'Edit Model' : 'Add New Model'}</h3>
          <form onSubmit={handleSubmit} className="management-form">
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="common_name">Common Name *</label>
                <input
                  type="text"
                  id="common_name"
                  name="common_name"
                  value={formData.common_name}
                  onChange={handleInputChange}
                  disabled={loading || editingModel}
                  placeholder="e.g., gpt-4, claude-3-opus, llama-2-7b"
                  required
                />
                {editingModel && (
                  <small>Common name cannot be changed after creation</small>
                )}
              </div>

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
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="model_family">Model Family</label>
                <select
                  id="model_family"
                  name="model_family"
                  value={formData.model_family}
                  onChange={handleInputChange}
                  disabled={loading}
                >
                  {modelFamilies.map(family => (
                    <option key={family} value={family}>{family}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="parameter_count">Parameter Count</label>
                <input
                  type="text"
                  id="parameter_count"
                  name="parameter_count"
                  value={formData.parameter_count}
                  onChange={handleInputChange}
                  disabled={loading}
                  placeholder="e.g., 7B, 13B, 70B"
                />
              </div>

              <div className="form-group">
                <label htmlFor="context_length">Context Length</label>
                <input
                  type="number"
                  id="context_length"
                  name="context_length"
                  value={formData.context_length}
                  onChange={handleInputChange}
                  disabled={loading}
                  placeholder="e.g., 4096, 8192, 32768"
                />
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
                {loading ? 'Saving...' : (editingModel ? 'Update Model' : 'Create Model')}
              </button>
              <button type="button" onClick={resetForm} className="btn btn-secondary" disabled={loading}>
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="models-list">
        <h4>Existing Models ({models.length})</h4>
        
        {loading ? (
          <div className="loading">Loading models...</div>
        ) : models.length === 0 ? (
          <div className="no-data">No models found. Add one to get started.</div>
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
                    <div><strong>Family:</strong> {model.model_family}</div>
                    {model.parameter_count && (
                      <div><strong>Parameters:</strong> {model.parameter_count}</div>
                    )}
                    {model.context_length && (
                      <div><strong>Context:</strong> {model.context_length.toLocaleString()} tokens</div>
                    )}
                    <div><strong>Providers:</strong> {activeProviders}/{totalProviders} active</div>
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
