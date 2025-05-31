import React, { useState, useEffect } from 'react';
import axios from 'axios';
import '../styles/management.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001';

const ConnectionManager = ({ onConnectionsChange }) => {
  const [connections, setConnections] = useState([]);
  const [models, setModels] = useState([]);
  const [providers, setProviders] = useState([]);
  const [filteredProviders, setFilteredProviders] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingConnection, setEditingConnection] = useState(null);
  const [testingConnection, setTestingConnection] = useState(null);
  const [syncingModels, setSyncingModels] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    model_id: '',
    provider_id: '',
    is_active: true,
    supports_model_discovery: true,
    notes: ''
  });
  const [showModelPreview, setShowModelPreview] = useState(false);
  const [showProviderPreview, setShowProviderPreview] = useState(false);
  const [selectedModelForPreview, setSelectedModelForPreview] = useState(null);
  const [selectedProviderForPreview, setSelectedProviderForPreview] = useState(null);

  useEffect(() => {
    loadConnections();
    loadProviders();
    loadModels();
  }, []);

  const loadConnections = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE_URL}/api/connections`);
      setConnections(response.data.connections || []);
      setMessage(`Loaded ${response.data.connections?.length || 0} connections`);
    } catch (error) {
      console.error('Error loading connections:', error);
      setMessage(`Error: ${error.response?.data?.error || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const loadProviders = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/llm-providers`);
      setProviders(response.data.providers || []);
    } catch (error) {
      console.error('Error loading providers:', error);
    }
  };

  const loadModels = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/models`);
      setModels(response.data.models || []);
    } catch (error) {
      console.error('Error loading models:', error);
    }
  };

  const handleModelChange = async (modelId) => {
    setFormData({...formData, model_id: modelId, provider_id: ''});

    if (modelId) {
      try {
        const response = await axios.get(`${API_BASE_URL}/api/models/${modelId}/providers`);
        setFilteredProviders(response.data.providers || []);
      } catch (error) {
        console.error('Error loading providers for model:', error);
        setFilteredProviders([]);
      }
    } else {
      setFilteredProviders([]);
    }
  };

  const handleProviderChange = (providerId) => {
    setFormData({...formData, provider_id: providerId});
  };

  const showModelDetails = (modelId) => {
    const model = models.find(m => m.id.toString() === modelId);
    if (model) {
      setSelectedModelForPreview(model);
      setShowModelPreview(true);
    }
  };

  const showProviderDetails = (providerId) => {
    const provider = filteredProviders.find(p => p.id.toString() === providerId);
    if (provider) {
      setSelectedProviderForPreview(provider);
      setShowProviderPreview(true);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);

      // Convert IDs to integers
      const submitData = {
        ...formData,
        provider_id: parseInt(formData.provider_id),
        model_id: formData.model_id ? parseInt(formData.model_id) : null
      };

      if (editingConnection) {
        await axios.put(`${API_BASE_URL}/api/connections/${editingConnection.id}`, submitData);
        setMessage('Connection updated successfully');
      } else {
        await axios.post(`${API_BASE_URL}/api/connections`, submitData);
        setMessage('Connection created successfully');
      }

      resetForm();
      loadConnections();
      if (onConnectionsChange) onConnectionsChange();
    } catch (error) {
      console.error('Error saving connection:', error);
      setMessage(`Error: ${error.response?.data?.error || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = async (connection) => {
    setEditingConnection(connection);

    // Set form data with proper string conversion for IDs
    const formDataToSet = {
      name: connection.name,
      description: connection.description || '',
      model_id: connection.model_id ? connection.model_id.toString() : '',
      provider_id: connection.provider_id ? connection.provider_id.toString() : '',
      is_active: connection.is_active,
      supports_model_discovery: connection.supports_model_discovery,
      notes: connection.notes || ''
    };

    setFormData(formDataToSet);

    // If editing and there's a model_id, load the providers for that model
    if (connection.model_id) {
      try {
        const response = await axios.get(`${API_BASE_URL}/api/models/${connection.model_id}/providers`);
        setFilteredProviders(response.data.providers || []);
      } catch (error) {
        console.error('Error loading providers for model:', error);
        setFilteredProviders([]);
      }
    } else {
      setFilteredProviders([]);
    }

    setShowForm(true);
  };

  const handleDelete = async (connectionId) => {
    if (!window.confirm('Are you sure you want to delete this connection?')) {
      return;
    }

    try {
      setLoading(true);
      await axios.delete(`${API_BASE_URL}/api/connections/${connectionId}`);
      setMessage('Connection deleted successfully');
      loadConnections();
      if (onConnectionsChange) onConnectionsChange();
    } catch (error) {
      console.error('Error deleting connection:', error);
      setMessage(`Error: ${error.response?.data?.error || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleTestConnection = async (connection) => {
    try {
      setTestingConnection(connection.id);

      // Update the connection status to 'testing' in the UI
      setConnections(prevConnections =>
        prevConnections.map(conn =>
          conn.id === connection.id
            ? { ...conn, connection_status: 'testing' }
            : conn
        )
      );

      const response = await axios.post(`${API_BASE_URL}/api/connections/${connection.id}/test`, {}, {
        headers: {
          'Content-Type': 'application/json'
        }
      });
      setMessage(`Test ${response.data.success ? 'successful' : 'failed'}: ${response.data.message}`);
      loadConnections(); // Reload to get updated status
    } catch (error) {
      console.error('Error testing connection:', error);
      setMessage(`Test failed: ${error.response?.data?.error || error.message}`);
      loadConnections(); // Reload to get updated status even on error
    } finally {
      setTestingConnection(null);
    }
  };

  const handleSyncModels = async (connection) => {
    try {
      setSyncingModels(connection.id);
      const response = await axios.post(`${API_BASE_URL}/api/connections/${connection.id}/sync-models`, {}, {
        headers: {
          'Content-Type': 'application/json'
        }
      });
      setMessage(`Model sync ${response.data.success ? 'successful' : 'failed'}: ${response.data.message}`);
      loadConnections(); // Reload to get updated models
    } catch (error) {
      console.error('Error syncing models:', error);
      setMessage(`Sync failed: ${error.response?.data?.error || error.message}`);
    } finally {
      setSyncingModels(null);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      model_id: '',
      provider_id: '',
      is_active: true,
      supports_model_discovery: true,
      notes: ''
    });
    setFilteredProviders([]);
    setEditingConnection(null);
    setShowForm(false);
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'connected': return 'text-success';
      case 'failed': return 'text-danger';
      case 'unknown': return 'text-warning';
      case 'testing': return 'text-info';
      default: return 'text-muted';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'connected': return '✅';
      case 'failed': return '❌';
      case 'unknown': return '⚠️';
      case 'testing': return '🔄';
      default: return '❓';
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'connected': return 'CONNECTED';
      case 'failed': return 'FAILED';
      case 'unknown': return 'UNTESTED';
      case 'testing': return 'TESTING';
      default: return 'UNKNOWN';
    }
  };

  return (
    <div className="connection-manager">
      <div className="manager-header">
        <h3>Connection Management</h3>
        <p>Create connections by selecting a model first, then choosing a compatible provider. All technical configuration (base URL, port, API key) is handled by the provider. Use the preview buttons to see detailed information about models and providers.</p>
        
        <div className="header-actions">
          <button
            onClick={() => setShowForm(!showForm)}
            className="btn btn-primary"
            disabled={loading}
          >
            {showForm ? 'Cancel' : 'Add Connection'}
          </button>
        </div>
      </div>

      {message && (
        <div className={`message ${message.includes('Error') ? 'error' : 'success'}`}>
          {message}
        </div>
      )}

      {showForm && (
        <div className="form-container">
          <h4>{editingConnection ? 'Edit Connection' : 'Add New Connection'}</h4>
          <form onSubmit={handleSubmit}>
            <div className="form-row">
              <div className="form-group">
                <label>Connection Name *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                  required
                  placeholder="e.g., My OpenAI GPT-4 Connection"
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Model *</label>
                <div style={{display: 'flex', gap: '10px', alignItems: 'flex-end'}}>
                  <select
                    value={formData.model_id}
                    onChange={(e) => handleModelChange(e.target.value)}
                    required
                    style={{flex: 1}}
                  >
                    <option value="">Select Model First</option>
                    {models.map(model => (
                      <option key={model.id} value={model.id}>
                        {model.display_name} ({model.common_name})
                      </option>
                    ))}
                  </select>
                  {formData.model_id && (
                    <button
                      type="button"
                      onClick={() => showModelDetails(formData.model_id)}
                      className="btn btn-outline-info btn-sm"
                      title="View model details"
                    >
                      📋 Preview
                    </button>
                  )}
                </div>
              </div>

              <div className="form-group">
                <label>Provider *</label>
                <div style={{display: 'flex', gap: '10px', alignItems: 'flex-end'}}>
                  <select
                    value={formData.provider_id}
                    onChange={(e) => handleProviderChange(e.target.value)}
                    required
                    disabled={!formData.model_id}
                    style={{flex: 1}}
                  >
                    <option value="">
                      {!formData.model_id ? 'Select Model First' : 'Select Provider'}
                    </option>
                    {filteredProviders.map(provider => (
                      <option key={provider.id} value={provider.id}>
                        {provider.name} ({provider.provider_type})
                      </option>
                    ))}
                  </select>
                  {formData.provider_id && (
                    <button
                      type="button"
                      onClick={() => showProviderDetails(formData.provider_id)}
                      className="btn btn-outline-info btn-sm"
                      title="View provider details"
                    >
                      🔌 Preview
                    </button>
                  )}
                </div>
              </div>
            </div>

            <div className="form-group">
              <label>Description</label>
              <input
                type="text"
                value={formData.description}
                onChange={(e) => setFormData({...formData, description: e.target.value})}
                placeholder="Brief description of this connection"
              />
            </div>



            <div className="form-group">
              <label>Notes</label>
              <textarea
                value={formData.notes}
                onChange={(e) => setFormData({...formData, notes: e.target.value})}
                placeholder="Additional notes about this connection"
                rows="3"
              />
            </div>

            <div className="form-row">
              <div className="form-group checkbox">
                <input
                  type="checkbox"
                  id="is_active"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({...formData, is_active: e.target.checked})}
                />
                <label htmlFor="is_active">Active Connection</label>
              </div>
              
              <div className="form-group checkbox">
                <input
                  type="checkbox"
                  id="supports_model_discovery"
                  checked={formData.supports_model_discovery}
                  onChange={(e) => setFormData({...formData, supports_model_discovery: e.target.checked})}
                />
                <label htmlFor="supports_model_discovery">Supports Model Discovery</label>
              </div>
            </div>

            <div className="form-actions">
              <button type="submit" className="btn btn-primary" disabled={loading}>
                {loading ? 'Saving...' : (editingConnection ? 'Update' : 'Create')}
              </button>
              <button type="button" onClick={resetForm} className="btn btn-secondary">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="connections-list">
        <h4>Existing Connections ({connections.length})</h4>
        
        {connections.length === 0 && !loading ? (
          <div className="no-data">No connections found. Add one to get started.</div>
        ) : (
          <div className="connections-grid">
            {connections.map(connection => (
              <div key={connection.id} className={`connection-card ${connection.is_active ? 'active' : 'inactive'}`}>
                <div className="connection-header">
                  <h5>{connection.name}</h5>
                  <div className="connection-status">
                    <span className={`status ${getStatusColor(connection.connection_status)}`}>
                      {getStatusIcon(connection.connection_status)} {getStatusText(connection.connection_status)}
                    </span>
                  </div>
                </div>
                
                <div className="connection-details">
                  {connection.model_name && (
                    <p><strong>Model:</strong> {connection.model_name} ({connection.model_common_name})</p>
                  )}
                  <p><strong>Provider:</strong> {connection.provider_name} ({connection.provider_type})</p>
                  {connection.description && <p><strong>Description:</strong> {connection.description}</p>}
                  {connection.base_url && <p><strong>URL:</strong> {connection.base_url}</p>}
                  {connection.available_models && connection.available_models.length > 0 && (
                    <p><strong>Models:</strong> {connection.available_models.length} available</p>
                  )}
                  {connection.last_tested && (
                    <p><strong>Last Tested:</strong> {new Date(connection.last_tested).toLocaleString()}</p>
                  )}
                  {connection.notes && <p><strong>Notes:</strong> {connection.notes}</p>}
                </div>

                <div className="connection-actions">
                  <button
                    onClick={() => handleTestConnection(connection)}
                    className="btn btn-sm btn-info"
                    disabled={loading || testingConnection === connection.id}
                    title="Test Connection"
                  >
                    {testingConnection === connection.id ? '⏳' : '🧪'}
                  </button>
                  
                  {connection.supports_model_discovery && (
                    <button
                      onClick={() => handleSyncModels(connection)}
                      className="btn btn-sm btn-warning"
                      disabled={loading || syncingModels === connection.id}
                      title="Sync Models"
                    >
                      {syncingModels === connection.id ? '⏳' : '🔄'}
                    </button>
                  )}
                  
                  <button
                    onClick={() => handleEdit(connection)}
                    className="btn btn-sm btn-primary"
                    disabled={loading}
                    title="Edit Connection"
                  >
                    ✏️
                  </button>
                  
                  <button
                    onClick={() => handleDelete(connection.id)}
                    className="btn btn-sm btn-danger"
                    disabled={loading}
                    title="Delete Connection"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Model Preview Modal */}
      {showModelPreview && selectedModelForPreview && (
        <div className="modal-overlay" onClick={() => setShowModelPreview(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h4>📋 Model Details</h4>
              <button
                className="close-btn"
                onClick={() => setShowModelPreview(false)}
              >
                ×
              </button>
            </div>
            <div className="modal-body">
              <div className="detail-row">
                <strong>Display Name:</strong> {selectedModelForPreview.display_name}
              </div>
              <div className="detail-row">
                <strong>Common Name:</strong> {selectedModelForPreview.common_name}
              </div>
              <div className="detail-row">
                <strong>Family:</strong> {selectedModelForPreview.family}
              </div>
              <div className="detail-row">
                <strong>Context Length:</strong> {selectedModelForPreview.context_length?.toLocaleString() || 'Not specified'}
              </div>
              <div className="detail-row">
                <strong>Parameter Count:</strong> {selectedModelForPreview.parameter_count || 'Not specified'}
              </div>
              {selectedModelForPreview.description && (
                <div className="detail-row">
                  <strong>Description:</strong> {selectedModelForPreview.description}
                </div>
              )}
              {selectedModelForPreview.notes && (
                <div className="detail-row">
                  <strong>Notes:</strong> {selectedModelForPreview.notes}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Provider Preview Modal */}
      {showProviderPreview && selectedProviderForPreview && (
        <div className="modal-overlay" onClick={() => setShowProviderPreview(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h4>🔌 Provider Details</h4>
              <button
                className="close-btn"
                onClick={() => setShowProviderPreview(false)}
              >
                ×
              </button>
            </div>
            <div className="modal-body">
              <div className="detail-row">
                <strong>Name:</strong> {selectedProviderForPreview.name}
              </div>
              <div className="detail-row">
                <strong>Type:</strong> {selectedProviderForPreview.provider_type}
              </div>
              <div className="detail-row">
                <strong>Base URL:</strong> {selectedProviderForPreview.default_base_url || 'Not configured'}
              </div>
              <div className="detail-row">
                <strong>Authentication:</strong> {selectedProviderForPreview.auth_type || 'Not specified'}
              </div>
              <div className="detail-row">
                <strong>Model Discovery:</strong> {selectedProviderForPreview.supports_model_discovery ? 'Supported' : 'Not supported'}
              </div>
              <div className="detail-row">
                <strong>Status:</strong> {selectedProviderForPreview.is_active ? 'Active' : 'Inactive'}
              </div>
              {selectedProviderForPreview.notes && (
                <div className="detail-row">
                  <strong>Notes:</strong> {selectedProviderForPreview.notes}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ConnectionManager;
