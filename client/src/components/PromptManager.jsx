import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001';

const PromptManager = ({ onPromptsChange }) => {
  const [prompts, setPrompts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingPrompt, setEditingPrompt] = useState(null);
  const [formData, setFormData] = useState({
    prompt_text: '',
    description: '',
    active: true
  });

  useEffect(() => {
    loadPrompts();
  }, []);

  const loadPrompts = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE_URL}/api/prompts`);
      setPrompts(response.data.prompts || []);
      if (onPromptsChange) {
        onPromptsChange(response.data.prompts || []);
      }
    } catch (error) {
      console.error('Error loading prompts:', error);
      setMessage(`Error loading prompts: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      
      if (editingPrompt) {
        // Update existing prompt
        await axios.put(`${API_BASE_URL}/api/prompts/${editingPrompt.id}`, formData);
        setMessage('Prompt updated successfully');
      } else {
        // Create new prompt
        await axios.post(`${API_BASE_URL}/api/prompts`, formData);
        setMessage('Prompt created successfully');
      }
      
      resetForm();
      loadPrompts();
    } catch (error) {
      console.error('Error saving prompt:', error);
      setMessage(`Error: ${error.response?.data?.error || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (prompt) => {
    setEditingPrompt(prompt);
    setFormData({
      prompt_text: prompt.prompt_text,
      description: prompt.description || '',
      active: prompt.active
    });
    setShowForm(true);
  };

  const handleDelete = async (prompt) => {
    if (!window.confirm(`Are you sure you want to delete this prompt?`)) {
      return;
    }
    
    try {
      setLoading(true);
      await axios.delete(`${API_BASE_URL}/api/prompts/${prompt.id}`);
      setMessage('Prompt deleted successfully');
      loadPrompts();
    } catch (error) {
      console.error('Error deleting prompt:', error);
      setMessage(`Error: ${error.response?.data?.error || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleActive = async (prompt) => {
    try {
      setLoading(true);
      const endpoint = prompt.active ? 'deactivate' : 'activate';
      await axios.post(`${API_BASE_URL}/api/prompts/${prompt.id}/${endpoint}`);
      setMessage(`Prompt ${prompt.active ? 'deactivated' : 'activated'} successfully`);
      loadPrompts();
    } catch (error) {
      console.error('Error toggling prompt:', error);
      setMessage(`Error: ${error.response?.data?.error || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      prompt_text: '',
      description: '',
      active: true
    });
    setEditingPrompt(null);
    setShowForm(false);
  };

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const truncateText = (text, maxLength = 100) => {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  return (
    <div className="prompt-manager">
      <div className="manager-header">
        <h3>Prompt Management</h3>
        <button 
          onClick={() => setShowForm(!showForm)}
          className="btn btn-primary"
          disabled={loading}
        >
          {showForm ? 'Cancel' : 'Add New Prompt'}
        </button>
      </div>

      {message && (
        <div className={`message ${message.includes('Error') ? 'error' : 'success'}`}>
          {message}
        </div>
      )}

      {showForm && (
        <form onSubmit={handleSubmit} className="prompt-form">
          <h4>{editingPrompt ? 'Edit Prompt' : 'Add New Prompt'}</h4>
          
          <div className="form-group">
            <label htmlFor="prompt_text">Prompt Text *</label>
            <textarea
              id="prompt_text"
              name="prompt_text"
              value={formData.prompt_text}
              onChange={handleInputChange}
              required
              disabled={loading}
              rows="6"
              placeholder="Enter your prompt text here..."
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="description">Description</label>
            <input
              type="text"
              id="description"
              name="description"
              value={formData.description}
              onChange={handleInputChange}
              disabled={loading}
              placeholder="Optional description for this prompt"
            />
          </div>

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

          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Saving...' : (editingPrompt ? 'Update' : 'Create')}
            </button>
            <button type="button" onClick={resetForm} className="btn btn-secondary" disabled={loading}>
              Cancel
            </button>
          </div>
        </form>
      )}

      <div className="prompts-list">
        <h4>Existing Prompts ({prompts.length})</h4>
        {loading && <div className="loading">Loading...</div>}
        
        {prompts.length === 0 && !loading ? (
          <div className="no-data">No prompts found. Add one to get started.</div>
        ) : (
          <div className="prompts-grid">
            {prompts.map(prompt => (
              <div key={prompt.id} className={`prompt-card ${prompt.active ? 'active' : 'inactive'}`}>
                <div className="prompt-header">
                  <h5>Prompt #{prompt.id}</h5>
                  <div className="prompt-actions">
                    <button
                      onClick={() => handleToggleActive(prompt)}
                      className={`btn btn-sm ${prompt.active ? 'btn-warning' : 'btn-success'}`}
                      disabled={loading}
                      title={prompt.active ? 'Deactivate' : 'Activate'}
                    >
                      {prompt.active ? '🔴' : '🟢'}
                    </button>
                    <button
                      onClick={() => handleEdit(prompt)}
                      className="btn btn-sm btn-secondary"
                      disabled={loading}
                      title="Edit"
                    >
                      ✏️
                    </button>
                    <button
                      onClick={() => handleDelete(prompt)}
                      className="btn btn-sm btn-danger"
                      disabled={loading}
                      title="Delete"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
                
                <div className="prompt-details">
                  {prompt.description && (
                    <div className="prompt-description">
                      <strong>Description:</strong> {prompt.description}
                    </div>
                  )}
                  <div className="prompt-text">
                    <strong>Prompt:</strong>
                    <div className="prompt-content" title={prompt.prompt_text}>
                      {truncateText(prompt.prompt_text, 150)}
                    </div>
                  </div>
                  <div className="prompt-status">
                    <strong>Status:</strong> 
                    <span className={`status ${prompt.active ? 'active' : 'inactive'}`}>
                      {prompt.active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default PromptManager;
