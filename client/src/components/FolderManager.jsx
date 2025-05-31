import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001';

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
  const [folderStats, setFolderStats] = useState({});
  const [pollingIntervals, setPollingIntervals] = useState({});
  const [expandedFolders, setExpandedFolders] = useState({});
  const [failedFilesModal, setFailedFilesModal] = useState({ show: false, folderId: null, files: [] });
  const [loadingFailedFiles, setLoadingFailedFiles] = useState(false);

  useEffect(() => {
    loadFolders();
  }, []);

  // Cleanup polling intervals on unmount
  useEffect(() => {
    return () => {
      Object.values(pollingIntervals).forEach(interval => {
        if (interval) clearInterval(interval);
      });
    };
  }, [pollingIntervals]);

  const startTaskPolling = (folderId, taskId) => {
    // Clear existing interval if any
    if (pollingIntervals[folderId]) {
      clearInterval(pollingIntervals[folderId]);
    }

    const interval = setInterval(async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/api/folders/task/${taskId}/status`);
        const taskStatus = response.data;

        console.log(`Polling folder ${folderId}, task ${taskId}: status=${taskStatus.status}, progress=${taskStatus.progress}`);

        // Update folder stats with task progress
        setFolderStats(prev => ({
          ...prev,
          [folderId]: {
            ...taskStatus,
            status: taskStatus.status === 'COMPLETED' ? 'READY' :
              taskStatus.status === 'ERROR' ? 'ERROR' : 'PREPROCESSING'
          }
        }));

        // Update folder status in the list
        setFolders(prev => prev.map(f =>
          f.id === folderId ? {
            ...f,
            status: taskStatus.status === 'COMPLETED' ? 'READY' :
              taskStatus.status === 'ERROR' ? 'ERROR' : 'PREPROCESSING'
          } : f
        ));

        // If processing is complete, stop polling and refresh folders
        if (taskStatus.status === 'COMPLETED' || taskStatus.status === 'ERROR') {
          clearInterval(interval);
          setPollingIntervals(prev => {
            const newIntervals = { ...prev };
            delete newIntervals[folderId];
            return newIntervals;
          });

          // Update the folder status immediately to READY/ERROR
          const finalStatus = taskStatus.status === 'COMPLETED' ? 'READY' : 'ERROR';
          console.log(`Task completed for folder ${folderId}: setting status to ${finalStatus}`);

          setFolders(prev => prev.map(f =>
            f.id === folderId ? {
              ...f,
              status: finalStatus
            } : f
          ));

          // Refresh folders to get final status from server (with longer delay to ensure server is updated)
          setTimeout(() => {
            console.log(`Refreshing folders after task completion for folder ${folderId}`);
            loadFolders();
          }, 2000);
        }
      } catch (error) {
        console.error(`Error polling task ${taskId} status:`, error);
        clearInterval(interval);
        setPollingIntervals(prev => {
          const newIntervals = { ...prev };
          delete newIntervals[folderId];
          return newIntervals;
        });
      }
    }, 1000); // Poll every 1 second for better responsiveness

    setPollingIntervals(prev => ({
      ...prev,
      [folderId]: interval
    }));
  };

  const loadFolders = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE_URL}/api/folders`);
      const folders = response.data.folders || [];

      console.log('Loaded folders from server:', folders.map(f => ({ id: f.id, name: f.folder_name, status: f.status })));

      // Fix any folders that are active but not processed
      const invalidActiveFolders = folders.filter(folder =>
        folder.active && (!folder.status || folder.status === 'NOT_PROCESSED' || folder.status === null)
      );

      for (const folder of invalidActiveFolders) {
        try {
          console.log(`Deactivating folder ${folder.id} - active but not processed`);
          await axios.put(`${API_BASE_URL}/api/folders/${folder.id}`, { active: false });
          folder.active = false; // Update local state
        } catch (error) {
          console.error(`Error deactivating folder ${folder.id}:`, error);
        }
      }

      setFolders(folders);

      // Load statistics for READY folders
      const readyFolders = folders.filter(folder => folder.status === 'READY');
      for (const folder of readyFolders) {
        try {
          const statsResponse = await axios.get(`${API_BASE_URL}/api/folders/${folder.id}/status`);
          setFolderStats(prev => ({
            ...prev,
            [folder.id]: statsResponse.data.folder_status
          }));
        } catch (error) {
          console.error(`Error loading stats for folder ${folder.id}:`, error);
        }
      }

      if (onFoldersChange) {
        onFoldersChange(folders);
      }

      // Show message if we deactivated any folders
      if (invalidActiveFolders.length > 0) {
        setMessage(`Automatically deactivated ${invalidActiveFolders.length} folder(s) that were active but not processed. Please preprocess them first.`);
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
    const isReprocessing = folder.status === 'READY';

    try {
      // Don't set global loading - only disable the specific button
      setMessage('');

      const response = await axios.post(`${API_BASE_URL}/api/folders/preprocess`, {
        folder_path: folder.folder_path,
        folder_name: folder.folder_name || folder.folder_path.split('/').pop()
      });

      const taskId = response.data.task_id;
      if (taskId) {
        // Start polling for task progress
        startTaskPolling(folder.id, taskId);

        // Update folder status to show it's processing
        setFolders(prev => prev.map(f =>
          f.id === folder.id ? { ...f, status: 'PREPROCESSING' } : f
        ));
      }
    } catch (error) {
      console.error('Error starting preprocessing:', error);
      setMessage(`${isReprocessing ? 'Reprocessing' : 'Preprocessing'} failed to start: ${error.response?.data?.error || error.message}`);
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

  const handleViewFailedFiles = async (folder) => {
    try {
      setLoadingFailedFiles(true);
      const response = await axios.get(`${API_BASE_URL}/api/folders/${folder.id}/failed-files`);
      const data = response.data;

      setFailedFilesModal({
        show: true,
        folderId: folder.id,
        folderName: folder.folder_name || folder.folder_path.split('/').pop(),
        files: data.failed_files || []
      });
    } catch (error) {
      console.error('Error loading failed files:', error);
      setMessage(`Error loading failed files: ${error.response?.data?.error || error.message}`);
    } finally {
      setLoadingFailedFiles(false);
    }
  };

  const closeFailedFilesModal = () => {
    setFailedFilesModal({ show: false, folderId: null, files: [] });
  };

  const resetForm = () => {
    setFormData({
      folder_path: '',
      folder_name: '',
      active: false  // New folders should not be active by default
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

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
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
            <small className="form-help">
              Note: Folders must be preprocessed before they can be activated. New folders will need to be processed first.
            </small>
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
                    {/* Preprocess button - show if not READY */}
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

                    {/* Reprocess button - show if READY */}
                    {folder.status === 'READY' && (
                      <button
                        onClick={() => handlePreprocessFolder(folder)}
                        className="btn btn-sm btn-warning"
                        disabled={loading}
                        title="Reprocess folder (files may have changed)"
                      >
                        🔄
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
                  <div className="folder-meta">
                    <div><strong>ID:</strong> {folder.id}</div>
                    <div><strong>Added:</strong> {formatDate(folder.created_at)}</div>
                    <div className="status-line">
                      <div className="status-badges">
                        <span className={`status-badge ${folder.active ? 'active' : 'inactive'}`}>
                          {folder.active ? 'ACTIVE' : 'INACTIVE'}
                        </span>
                        <span className={`status-badge processing-status ${folder.status || 'not-processed'}`}>
                          {getProcessingStatusDisplay(folder.status)}
                        </span>
                      </div>
                    </div>
                    <div className="folder-path-toggle">
                      <button
                        className="btn btn-sm btn-outline-secondary"
                        onClick={() => setExpandedFolders(prev => ({
                          ...prev,
                          [folder.id]: !prev[folder.id]
                        }))}
                        title="Toggle details"
                      >
                        {expandedFolders[folder.id] ? '▼' : '▶'} Details
                      </button>
                    </div>
                  </div>

                  {/* Summary Information - Always visible for READY folders */}
                  {folder.status === 'READY' && folderStats[folder.id] && (
                    <div className="folder-summary">
                      <div className="summary-compact">
                        <span className="summary-item">
                          <strong>{folderStats[folder.id].valid_files || 0}</strong> ready
                        </span>
                        <span className="summary-divider">•</span>
                        <span className="summary-item">
                          <strong>{folderStats[folder.id].invalid_files || 0}</strong> failed
                        </span>
                        {folderStats[folder.id].invalid_files > 0 && (
                          <>
                            <span className="summary-divider">•</span>
                            <button
                              onClick={() => handleViewFailedFiles(folder)}
                              className="btn btn-sm btn-link-compact"
                              disabled={loadingFailedFiles}
                              title="View files that failed processing"
                            >
                              {loadingFailedFiles ? 'Loading...' : 'View Failed'}
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Collapsible details */}
                  {expandedFolders[folder.id] && (
                    <div className="folder-expanded-details">
                      <div className="folder-path">
                        <strong>Path:</strong>
                        <code>{folder.folder_path}</code>
                      </div>

                      {/* Processing Status Section */}
                      <div className="folder-processing-section">

                        {/* Show statistics if folder is READY */}
                        {folder.status === 'READY' && folderStats[folder.id] && (
                          <div className="folder-statistics">
                            <div className="stats-header">
                              <h6>📊 Processing Summary</h6>
                            </div>
                            <div className="stats-grid">
                              <div className="stat-item">
                                <span className="stat-label">📁 Folders:</span>
                                <span className="stat-value">{folderStats[folder.id].total_directories || 0}</span>
                              </div>
                              <div className="stat-item">
                                <span className="stat-label">📄 Files:</span>
                                <span className="stat-value">{folderStats[folder.id].total_files || 0}</span>
                              </div>
                              <div className="stat-item">
                                <span className="stat-label">✅ Ready:</span>
                                <span className="stat-value">{folderStats[folder.id].valid_files || 0}</span>
                              </div>
                              <div className="stat-item">
                                <span className="stat-label">❌ Failed:</span>
                                <span className="stat-value">{folderStats[folder.id].invalid_files || 0}</span>
                              </div>
                              <div className="stat-item">
                                <span className="stat-label">💾 Total Size:</span>
                                <span className="stat-value">{formatFileSize(folderStats[folder.id].total_size || 0)}</span>
                              </div>
                              <div className="stat-item">
                                <span className="stat-label">✅ Ready Size:</span>
                                <span className="stat-value">{formatFileSize(folderStats[folder.id].ready_files_size || 0)}</span>
                              </div>
                            </div>
                            {folderStats[folder.id].invalid_files > 0 && (
                              <div className="failed-files-section">
                                <button
                                  onClick={() => handleViewFailedFiles(folder)}
                                  className="btn btn-sm btn-warning"
                                  disabled={loadingFailedFiles}
                                  title="View files that failed processing"
                                >
                                  {loadingFailedFiles ? '⏳' : '🔍'} View Failed Files ({folderStats[folder.id].invalid_files})
                                </button>
                              </div>
                            )}
                          </div>
                        )}

                        {/* Show real-time processing progress if PREPROCESSING */}
                        {folder.status === 'PREPROCESSING' && folderStats[folder.id] && (
                          <div className="processing-progress">
                            <div className="progress-header">
                              <strong>Processing Progress:</strong>
                              <span className="progress-percentage">{folderStats[folder.id].progress || 0}%</span>
                            </div>
                            <div className="progress-bar">
                              <div
                                className="progress-fill"
                                style={{ width: `${folderStats[folder.id].progress || 0}%` }}
                              ></div>
                            </div>
                            <div className="progress-details">
                              <div>Files: {folderStats[folder.id].processed_files || 0} / {folderStats[folder.id].total_files || 0}</div>
                              <div>Valid: {folderStats[folder.id].valid_files || 0}</div>
                              <div>Invalid: {folderStats[folder.id].invalid_files || 0}</div>
                              <div>Status: {folderStats[folder.id].status || 'Processing'}</div>
                            </div>
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

      {/* Failed Files Modal */}
      {failedFilesModal.show && (
        <div className="modal-overlay" onClick={closeFailedFilesModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h4>❌ Failed Files - {failedFilesModal.folderName}</h4>
              <button className="modal-close" onClick={closeFailedFilesModal}>×</button>
            </div>
            <div className="modal-body">
              {failedFilesModal.files.length === 0 ? (
                <div className="no-failed-files">
                  <p>✅ No failed files found! All files were processed successfully.</p>
                </div>
              ) : (
                <div className="failed-files-list">
                  <div className="failed-files-summary">
                    <p><strong>Total Failed Files:</strong> {failedFilesModal.files.length}</p>
                  </div>
                  <div className="failed-files-table">
                    <table>
                      <thead>
                        <tr>
                          <th>File Name</th>
                          <th>Path</th>
                          <th>Size</th>
                          <th>Reason</th>
                        </tr>
                      </thead>
                      <tbody>
                        {failedFilesModal.files.map((file, index) => (
                          <tr key={index}>
                            <td className="file-name">{file.filename}</td>
                            <td className="file-path" title={file.relative_path}>
                              {file.relative_path.length > 50
                                ? `...${file.relative_path.slice(-47)}`
                                : file.relative_path}
                            </td>
                            <td className="file-size">{formatFileSize(file.file_size)}</td>
                            <td className="failure-reason">{file.validation_reason}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={closeFailedFilesModal}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FolderManager;
