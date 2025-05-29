import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001';

const FolderManager = ({ onFoldersChange }) => {
  const [folders, setFolders] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingFolder, setEditingFolder] = useState(null);
  const [formData, setFormData] = useState({
    folder_path: '',
    folder_name: '',
    active: false  // Changed default to false - folders should not be active until preprocessed
  });

  useEffect(() => {
    loadFolders();
  }, []);

  const loadFolders = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE_URL}/api/folders`);
      setFolders(response.data.folders || []);
      if (onFoldersChange) {
        onFoldersChange(response.data.folders || []);
      }
    } catch (error) {
      console.error('Error loading folders:', error);
      setMessage(`Error loading folders: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);

      if (editingFolder) {
        // Update existing folder
        await axios.put(`${API_BASE_URL}/api/folders/${editingFolder.id}`, formData);
        setMessage('Folder updated successfully');
      } else {
        // Create new folder
        await axios.post(`${API_BASE_URL}/api/folders`, formData);
        setMessage('Folder added successfully');
      }

      resetForm();
      loadFolders();
    } catch (error) {
      console.error('Error saving folder:', error);
      setMessage(`Error: ${error.response?.data?.error || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (folder) => {
    setEditingFolder(folder);
    setFormData({
      folder_path: folder.folder_path,
      folder_name: folder.folder_name || '',
      active: folder.active
    });
    setShowForm(true);
  };

  const handleDelete = async (folder) => {
    if (!window.confirm(`Are you sure you want to delete "${folder.folder_name || folder.folder_path}"?`)) {
      return;
    }

    try {
      setLoading(true);
      await axios.delete(`${API_BASE_URL}/api/folders/${folder.id}`);
      setMessage('Folder deleted successfully');
      loadFolders();
    } catch (error) {
      console.error('Error deleting folder:', error);
      setMessage(`Error: ${error.response?.data?.error || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleActive = async (folder) => {
    // Only allow activation if folder is preprocessed (status = READY)
    if (!folder.active && folder.status !== 'READY') {
      setMessage('Folder must be preprocessed before it can be activated. Click "Preprocess" first.');
      return;
    }

    try {
      setLoading(true);
      const endpoint = folder.active ? 'deactivate' : 'activate';
      await axios.post(`${API_BASE_URL}/api/folders/${folder.id}/${endpoint}`);
      setMessage(`Folder ${folder.active ? 'deactivated' : 'activated'} successfully`);
      loadFolders();
    } catch (error) {
      console.error('Error toggling folder:', error);
      setMessage(`Error: ${error.response?.data?.error || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handlePreprocessFolder = async (folder) => {
    if (!window.confirm(`Start preprocessing "${folder.folder_name || folder.folder_path}"?\n\nThis will scan all files in the folder and prepare them for batch processing.`)) {
      return;
    }

    try {
      setLoading(true);
      setMessage('Starting folder preprocessing...');

      const response = await axios.post(`${API_BASE_URL}/api/folders/preprocess`, {
        folder_path: folder.folder_path,
        folder_name: folder.folder_name || folder.folder_path.split('/').pop()
      });

      const results = response.data.results;
      setMessage(`Preprocessing completed! Found ${results.total_files} files (${results.valid_files} valid, ${results.invalid_files} invalid). Total size: ${(results.total_size / 1024).toFixed(1)} KB`);

      // Refresh folders to show updated status
      loadFolders();
    } catch (error) {
      console.error('Error preprocessing folder:', error);
      setMessage(`Preprocessing failed: ${error.response?.data?.error || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleViewDocuments = async (folder) => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE_URL}/api/folders/${folder.id}/documents`);
      const data = response.data;

      const summary = `Documents in "${folder.folder_name || folder.folder_path}":

Total: ${data.total_documents}
Valid: ${data.valid_documents}
Invalid: ${data.invalid_documents}

${data.documents.slice(0, 10).map(doc =>
        `${doc.valid ? '✅' : '❌'} ${doc.filename} (${(doc.file_size / 1024).toFixed(1)} KB)`
      ).join('\n')}${data.documents.length > 10 ? `\n... and ${data.documents.length - 10} more files` : ''}`;

      alert(summary);
    } catch (error) {
      console.error('Error loading documents:', error);
      setMessage(`Error loading documents: ${error.response?.data?.error || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      folder_path: '',
      folder_name: '',
      active: true
    });
    setEditingFolder(null);
    setShowForm(false);
  };

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handlePathTemplateClick = () => {
    const currentPath = formData.folder_path;
    const isWindows = navigator.userAgent.includes('Windows');
    const template = isWindows
      ? `C:\\Users\\username\\Documents\\${currentPath || 'FolderName'}`
      : `/Users/username/Documents/${currentPath || 'FolderName'}`;

    setFormData(prev => ({
      ...prev,
      folder_path: template
    }));

    setMessage(`Path template applied. Please replace 'username' with your actual username and adjust the path as needed.`);
  };

  const handleFolderSelect = (e) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      // Get the folder path from the first file
      const firstFile = files[0];
      const pathParts = firstFile.webkitRelativePath.split('/');
      const folderName = pathParts[0];

      // Create a relative path structure
      let folderPath = folderName;
      if (pathParts.length > 2) {
        // If there are subdirectories, include them
        folderPath = pathParts.slice(0, -1).join('/');
      }

      // Use the relative path as a starting point for the user to complete
      setFormData(prev => ({
        ...prev,
        folder_path: folderPath,
        folder_name: prev.folder_name || folderName
      }));

      // Show a more detailed helpful message
      setMessage(`Selected folder: "${folderName}". Browser security prevents showing the full path. Please update the path field with the complete absolute path to this folder on your server (e.g., /full/path/to/${folderName}).`);
    }

    // Reset the file input
    e.target.value = '';
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
  };

  const getProcessingStatusDisplay = (status) => {
    switch (status) {
      case 'READY':
        return '✅ Ready';
      case 'PREPROCESSING':
        return '⏳ Processing...';
      case 'ERROR':
        return '❌ Error';
      case 'NOT_PROCESSED':
      default:
        return '⚪ Not Processed';
    }
  };

  return (
    <div className="folder-manager">
      <div className="manager-header">
        <h3>Folder Management</h3>
        <button
          onClick={() => setShowForm(!showForm)}
          className="btn btn-primary"
          disabled={loading}
        >
          {showForm ? 'Cancel' : 'Add New Folder'}
        </button>
      </div>

      {message && (
        <div className={`message ${message.includes('Error') ? 'error' : 'success'}`}>
          {message}
        </div>
      )}

      {showForm && (
        <form onSubmit={handleSubmit} className="folder-form">
          <h4>{editingFolder ? 'Edit Folder' : 'Add New Folder'}</h4>

          <div className="form-group">
            <label htmlFor="folder_path">Folder Path *</label>
            <div className="folder-path-input">
              <input
                type="text"
                id="folder_path"
                name="folder_path"
                value={formData.folder_path}
                onChange={handleInputChange}
                required
                disabled={loading}
                placeholder="/path/to/your/documents"
                className="folder-path-text"
              />
              <input
                type="file"
                id="folder_chooser"
                webkitdirectory=""
                multiple
                onChange={handleFolderSelect}
                disabled={loading}
                style={{ display: 'none' }}
              />
              <button
                type="button"
                onClick={() => document.getElementById('folder_chooser').click()}
                className="btn btn-secondary folder-chooser-btn"
                disabled={loading}
                title="Choose folder"
              >
                📁 Browse
              </button>
              <button
                type="button"
                onClick={handlePathTemplateClick}
                className="btn btn-info folder-chooser-btn"
                disabled={loading}
                title="Apply path template"
              >
                📝 Template
              </button>
            </div>
            <small className="form-help">
              Enter the full absolute path to the folder containing documents to process (e.g., /Users/username/Documents/D250 or C:\Users\username\Documents\D250).
              Click Browse to help identify the folder name, or Template to apply a common path format, then manually complete the full path.
            </small>
          </div>

          <div className="form-group">
            <label htmlFor="folder_name">Folder Name</label>
            <input
              type="text"
              id="folder_name"
              name="folder_name"
              value={formData.folder_name}
              onChange={handleInputChange}
              disabled={loading}
              placeholder="Optional display name (defaults to folder name)"
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
              {loading ? 'Saving...' : (editingFolder ? 'Update' : 'Add')}
            </button>
            <button type="button" onClick={resetForm} className="btn btn-secondary" disabled={loading}>
              Cancel
            </button>
          </div>
        </form>
      )}

      <div className="folders-list">
        <h4>Existing Folders ({folders.length})</h4>
        {loading && <div className="loading">Loading...</div>}

        {folders.length === 0 && !loading ? (
          <div className="no-data">No folders found. Add one to get started.</div>
        ) : (
          <div className="folders-grid">
            {folders.map(folder => (
              <div key={folder.id} className={`folder-card ${folder.active ? 'active' : 'inactive'} ${folder.status || 'not-processed'}`}>
                <div className="folder-header">
                  <h5>{folder.folder_name || folder.folder_path.split('/').pop()}</h5>
                  <div className="folder-actions">
                    {/* Preprocess button - only show if not READY */}
                    {folder.status !== 'READY' && (
                      <button
                        onClick={() => handlePreprocessFolder(folder)}
                        className="btn btn-sm btn-info"
                        disabled={loading || folder.status === 'PREPROCESSING'}
                        title="Preprocess folder to scan and validate files"
                      >
                        {folder.status === 'PREPROCESSING' ? '⏳' : '🔄'}
                      </button>
                    )}

                    {/* View documents button - only show if READY */}
                    {folder.status === 'READY' && (
                      <button
                        onClick={() => handleViewDocuments(folder)}
                        className="btn btn-sm btn-info"
                        disabled={loading}
                        title="View processed documents"
                      >
                        📄
                      </button>
                    )}

                    <button
                      onClick={() => handleToggleActive(folder)}
                      className={`btn btn-sm ${folder.active ? 'btn-warning' : 'btn-success'}`}
                      disabled={loading || folder.status !== 'READY'}
                      title={folder.status !== 'READY' ? 'Preprocess folder first' : (folder.active ? 'Deactivate' : 'Activate')}
                    >
                      {folder.active ? '🔴' : '🟢'}
                    </button>
                    <button
                      onClick={() => handleEdit(folder)}
                      className="btn btn-sm btn-secondary"
                      disabled={loading}
                      title="Edit"
                    >
                      ✏️
                    </button>
                    <button
                      onClick={() => handleDelete(folder)}
                      className="btn btn-sm btn-danger"
                      disabled={loading}
                      title="Delete"
                    >
                      🗑️
                    </button>
                  </div>
                </div>

                <div className="folder-details">
                  <div className="folder-path">
                    <strong>Path:</strong>
                    <code>{folder.folder_path}</code>
                  </div>
                  <div className="folder-meta">
                    <div><strong>ID:</strong> {folder.id}</div>
                    <div><strong>Added:</strong> {formatDate(folder.created_at)}</div>
                    <div><strong>Status:</strong>
                      <span className={`status ${folder.active ? 'active' : 'inactive'}`}>
                        {folder.active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                    <div><strong>Processing:</strong>
                      <span className={`processing-status ${folder.status || 'not-processed'}`}>
                        {getProcessingStatusDisplay(folder.status)}
                      </span>
                    </div>
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

export default FolderManager;
