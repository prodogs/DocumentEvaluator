import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001';

const MaintenanceManager = ({ onNavigateBack }) => {
  const [stats, setStats] = useState(null);
  const [isResetting, setIsResetting] = useState(false);
  const [resetTaskId, setResetTaskId] = useState(null);
  const [resetStatus, setResetStatus] = useState(null);
  const [progressLogs, setProgressLogs] = useState([]);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [loading, setLoading] = useState(false);

  // Snapshot state
  const [isCreatingSnapshot, setIsCreatingSnapshot] = useState(false);
  const [snapshotTaskId, setSnapshotTaskId] = useState(null);
  const [snapshotStatus, setSnapshotStatus] = useState(null);
  const [snapshots, setSnapshots] = useState([]);
  const [showSnapshotDialog, setShowSnapshotDialog] = useState(false);
  const [snapshotName, setSnapshotName] = useState('');
  const [snapshotDescription, setSnapshotDescription] = useState('');

  // Load/Delete/Edit state
  const [isLoadingSnapshot, setIsLoadingSnapshot] = useState(false);
  const [loadTaskId, setLoadTaskId] = useState(null);
  const [loadStatus, setLoadStatus] = useState(null);
  const [showLoadDialog, setShowLoadDialog] = useState(false);
  const [selectedSnapshot, setSelectedSnapshot] = useState(null);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [editingSnapshot, setEditingSnapshot] = useState(null);
  const [editName, setEditName] = useState('');
  const [editDescription, setEditDescription] = useState('');
  
  const progressWindowRef = useRef(null);
  const pollIntervalRef = useRef(null);

  // Load initial stats and snapshots
  useEffect(() => {
    loadStats();
    loadSnapshots();
  }, []);

  // Auto-scroll progress window
  useEffect(() => {
    if (progressWindowRef.current) {
      progressWindowRef.current.scrollTop = progressWindowRef.current.scrollHeight;
    }
  }, [progressLogs]);

  const loadStats = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE_URL}/api/maintenance/stats`);
      if (response.data.success) {
        setStats(response.data.stats);
      }
    } catch (error) {
      console.error('Error loading maintenance stats:', error);
      addProgressLog('❌ Error loading database statistics', 'error');
    } finally {
      setLoading(false);
    }
  };

  const loadSnapshots = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/maintenance/snapshots`);
      if (response.data.success) {
        setSnapshots(response.data.snapshots);
      }
    } catch (error) {
      console.error('Error loading snapshots:', error);
      addProgressLog('❌ Error loading snapshots', 'error');
    }
  };

  const addProgressLog = (message, type = 'info') => {
    const timestamp = new Date().toLocaleTimeString();
    setProgressLogs(prev => [...prev, {
      id: Date.now(),
      timestamp,
      message,
      type
    }]);
  };

  const startReset = async () => {
    try {
      setIsResetting(true);
      setResetStatus(null);
      setProgressLogs([]);
      
      addProgressLog('🚀 Starting database reset operation...', 'info');
      
      const response = await axios.post(`${API_BASE_URL}/api/maintenance/reset`);
      
      if (response.data.success) {
        const taskId = response.data.task_id;
        setResetTaskId(taskId);
        addProgressLog(`✅ Reset operation started (Task: ${taskId.substring(0, 8)}...)`, 'success');
        
        // Start polling for status
        startStatusPolling(taskId);
      } else {
        throw new Error(response.data.error || 'Failed to start reset');
      }
    } catch (error) {
      console.error('Error starting reset:', error);
      addProgressLog(`❌ Failed to start reset: ${error.message}`, 'error');
      setIsResetting(false);
    }
  };

  const startStatusPolling = (taskId) => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
    }

    pollIntervalRef.current = setInterval(async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/api/maintenance/reset/status/${taskId}`);
        
        if (response.data.success) {
          const status = response.data;
          setResetStatus(status);
          
          // Add progress log
          const stepInfo = `Step ${status.current_step}/${status.total_steps}: ${status.step_name}`;
          addProgressLog(`📊 ${stepInfo} (${status.progress}%)`, 'info');
          
          // Check if completed
          if (status.status === 'COMPLETED') {
            addProgressLog('🎉 Database reset completed successfully!', 'success');
            addProgressLog(`📈 Summary: ${JSON.stringify(status.deleted_counts)}`, 'info');
            addProgressLog(`⏱️ Total time: ${status.total_time}s`, 'info');
            
            clearInterval(pollIntervalRef.current);
            setIsResetting(false);
            
            // Reload stats
            setTimeout(() => {
              loadStats();
            }, 1000);
            
          } else if (status.status === 'ERROR') {
            addProgressLog(`❌ Reset failed: ${status.error}`, 'error');
            clearInterval(pollIntervalRef.current);
            setIsResetting(false);
          }
        }
      } catch (error) {
        console.error('Error polling reset status:', error);
        addProgressLog(`❌ Error checking status: ${error.message}`, 'error');
      }
    }, 1000); // Poll every second
  };

  const handleResetClick = () => {
    setShowConfirmDialog(true);
  };

  const confirmReset = () => {
    setShowConfirmDialog(false);
    startReset();
  };

  const cancelReset = () => {
    setShowConfirmDialog(false);
  };

  const startSnapshot = async () => {
    try {
      setIsCreatingSnapshot(true);
      setSnapshotStatus(null);

      const snapshotPayload = {
        name: snapshotName || `snapshot_${new Date().toISOString().slice(0, 19).replace(/[:-]/g, '')}`,
        description: snapshotDescription || 'Database snapshot created from maintenance tab'
      };

      addProgressLog('🚀 Starting database snapshot creation...', 'info');

      const response = await axios.post(`${API_BASE_URL}/api/maintenance/snapshot`, snapshotPayload);

      if (response.data.success) {
        const taskId = response.data.task_id;
        setSnapshotTaskId(taskId);
        addProgressLog(`✅ Snapshot operation started (Task: ${taskId.substring(0, 8)}...)`, 'success');

        // Start polling for status
        startSnapshotStatusPolling(taskId);
      } else {
        throw new Error(response.data.error || 'Failed to start snapshot');
      }
    } catch (error) {
      console.error('Error starting snapshot:', error);
      addProgressLog(`❌ Failed to start snapshot: ${error.message}`, 'error');
      setIsCreatingSnapshot(false);
    }
  };

  const startSnapshotStatusPolling = (taskId) => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
    }

    pollIntervalRef.current = setInterval(async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/api/maintenance/snapshot/status/${taskId}`);

        if (response.data.success) {
          const status = response.data;
          setSnapshotStatus(status);

          // Add progress log
          const stepInfo = `Step ${status.current_step}/${status.total_steps}: ${status.step_name}`;
          addProgressLog(`📊 ${stepInfo} (${status.progress}%)`, 'info');

          // Check if completed
          if (status.status === 'COMPLETED') {
            const snapshotInfo = status.snapshot_info;
            addProgressLog('🎉 Database snapshot completed successfully!', 'success');
            addProgressLog(`📁 File: ${snapshotInfo.file_path}`, 'info');
            addProgressLog(`📊 Size: ${(snapshotInfo.file_size / 1024 / 1024).toFixed(1)} MB`, 'info');
            addProgressLog(`⏱️ Total time: ${status.total_time}s`, 'info');

            clearInterval(pollIntervalRef.current);
            setIsCreatingSnapshot(false);

            // Reload snapshots and stats
            setTimeout(() => {
              loadSnapshots();
              loadStats();
            }, 1000);

          } else if (status.status === 'ERROR') {
            addProgressLog(`❌ Snapshot failed: ${status.error}`, 'error');
            clearInterval(pollIntervalRef.current);
            setIsCreatingSnapshot(false);
          }
        }
      } catch (error) {
        console.error('Error polling snapshot status:', error);
        addProgressLog(`❌ Error checking status: ${error.message}`, 'error');
      }
    }, 2000); // Poll every 2 seconds
  };

  const handleSnapshotClick = () => {
    setShowSnapshotDialog(true);
  };

  const confirmSnapshot = () => {
    setShowSnapshotDialog(false);
    startSnapshot();
  };

  const cancelSnapshot = () => {
    setShowSnapshotDialog(false);
    setSnapshotName('');
    setSnapshotDescription('');
  };

  // Load snapshot functions
  const handleLoadSnapshot = (snapshot) => {
    setSelectedSnapshot(snapshot);
    setShowLoadDialog(true);
  };

  const confirmLoadSnapshot = async () => {
    if (!selectedSnapshot) return;

    try {
      setIsLoadingSnapshot(true);
      setLoadStatus(null);
      setShowLoadDialog(false);

      addProgressLog(`🔄 Starting database restore from "${selectedSnapshot.name}"...`, 'info');

      const response = await axios.post(`${API_BASE_URL}/api/maintenance/snapshot/${selectedSnapshot.id}/load`);

      if (response.data.success) {
        const taskId = response.data.task_id;
        setLoadTaskId(taskId);
        addProgressLog(`✅ Restore operation started (Task: ${taskId.substring(0, 8)}...)`, 'success');

        // Start polling for status
        startLoadStatusPolling(taskId);
      } else {
        throw new Error(response.data.error || 'Failed to start restore');
      }
    } catch (error) {
      console.error('Error starting restore:', error);
      addProgressLog(`❌ Failed to start restore: ${error.message}`, 'error');
      setIsLoadingSnapshot(false);
    }
  };

  const startLoadStatusPolling = (taskId) => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
    }

    pollIntervalRef.current = setInterval(async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/api/maintenance/snapshot/status/${taskId}`);

        if (response.data.success) {
          const status = response.data;
          setLoadStatus(status);

          // Add progress log
          const stepInfo = `Step ${status.current_step}/${status.total_steps}: ${status.step_name}`;
          addProgressLog(`📊 ${stepInfo} (${status.progress}%)`, 'info');

          // Check if completed
          if (status.status === 'COMPLETED') {
            addProgressLog('🎉 Database restore completed successfully!', 'success');
            addProgressLog(`📁 Backup created: ${status.backup_created}`, 'info');
            addProgressLog(`⏱️ Total time: ${status.total_time}s`, 'info');

            clearInterval(pollIntervalRef.current);
            setIsLoadingSnapshot(false);

            // Reload stats
            setTimeout(() => {
              loadStats();
            }, 1000);

          } else if (status.status === 'ERROR') {
            addProgressLog(`❌ Restore failed: ${status.error}`, 'error');
            clearInterval(pollIntervalRef.current);
            setIsLoadingSnapshot(false);
          }
        }
      } catch (error) {
        console.error('Error polling restore status:', error);
        addProgressLog(`❌ Error checking restore status: ${error.message}`, 'error');
      }
    }, 2000); // Poll every 2 seconds
  };

  const cancelLoadSnapshot = () => {
    setShowLoadDialog(false);
    setSelectedSnapshot(null);
  };

  // Delete snapshot functions
  const handleDeleteSnapshot = (snapshot) => {
    setSelectedSnapshot(snapshot);
    setShowDeleteDialog(true);
  };

  const confirmDeleteSnapshot = async () => {
    if (!selectedSnapshot) return;

    try {
      addProgressLog(`🗑️ Deleting snapshot "${selectedSnapshot.name}"...`, 'info');

      const response = await axios.delete(`${API_BASE_URL}/api/maintenance/snapshot/${selectedSnapshot.id}`);

      if (response.data.success) {
        addProgressLog(`✅ Snapshot "${selectedSnapshot.name}" deleted successfully`, 'success');
        addProgressLog(`📁 File deleted: ${response.data.file_deleted ? 'Yes' : 'No'}`, 'info');

        // Reload snapshots and stats
        loadSnapshots();
        loadStats();
      } else {
        throw new Error(response.data.error || 'Failed to delete snapshot');
      }
    } catch (error) {
      console.error('Error deleting snapshot:', error);
      addProgressLog(`❌ Failed to delete snapshot: ${error.message}`, 'error');
    } finally {
      setShowDeleteDialog(false);
      setSelectedSnapshot(null);
    }
  };

  const cancelDeleteSnapshot = () => {
    setShowDeleteDialog(false);
    setSelectedSnapshot(null);
  };

  // Edit snapshot functions
  const handleEditSnapshot = (snapshot) => {
    setEditingSnapshot(snapshot);
    setEditName(snapshot.name);
    setEditDescription(snapshot.description || '');
    setShowEditDialog(true);
  };

  const confirmEditSnapshot = async () => {
    if (!editingSnapshot) return;

    try {
      const updateData = {
        name: editName,
        description: editDescription
      };

      addProgressLog(`✏️ Updating snapshot "${editingSnapshot.name}"...`, 'info');

      const response = await axios.patch(`${API_BASE_URL}/api/maintenance/snapshot/${editingSnapshot.id}`, updateData);

      if (response.data.success) {
        addProgressLog(`✅ Snapshot updated successfully`, 'success');

        // Reload snapshots
        loadSnapshots();
      } else {
        throw new Error(response.data.error || 'Failed to update snapshot');
      }
    } catch (error) {
      console.error('Error updating snapshot:', error);
      addProgressLog(`❌ Failed to update snapshot: ${error.message}`, 'error');
    } finally {
      setShowEditDialog(false);
      setEditingSnapshot(null);
      setEditName('');
      setEditDescription('');
    }
  };

  const cancelEditSnapshot = () => {
    setShowEditDialog(false);
    setEditingSnapshot(null);
    setEditName('');
    setEditDescription('');
  };

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  return (
    <div className="maintenance-manager">
      <div className="maintenance-header">
        <div className="header-left">
          <button onClick={onNavigateBack} className="btn btn-secondary nav-back">
            ← Back to Dashboard
          </button>
          <div className="header-title">
            <h2>🔧 System Maintenance</h2>
            <p>Manage database cleanup and system maintenance operations</p>
          </div>
        </div>
      </div>

      <div className="maintenance-content">
        {/* Database Statistics */}
        <div className="maintenance-section">
        <h3>📊 Database Statistics</h3>
        <div className="stats-grid">
          {loading ? (
            <div className="loading-stats">Loading statistics...</div>
          ) : stats ? (
            <>
              <div className="stat-card">
                <div className="stat-number">{stats.llm_responses?.toLocaleString() || 0}</div>
                <div className="stat-label">LLM Responses</div>
              </div>
              <div className="stat-card">
                <div className="stat-number">{stats.documents?.toLocaleString() || 0}</div>
                <div className="stat-label">Documents</div>
              </div>
              <div className="stat-card">
                <div className="stat-number">{stats.docs?.toLocaleString() || 0}</div>
                <div className="stat-label">Document Content</div>
              </div>
              <div className="stat-card total">
                <div className="stat-number">{(stats.llm_responses + stats.documents + stats.docs)?.toLocaleString() || 0}</div>
                <div className="stat-label">Total Records</div>
              </div>
            </>
          ) : (
            <div className="error-stats">Failed to load statistics</div>
          )}
        </div>
        
        <button 
          onClick={loadStats} 
          disabled={loading}
          className="btn btn-secondary refresh-btn"
        >
          🔄 Refresh Stats
        </button>
      </div>

      {/* Reset Operations */}
      <div className="maintenance-section">
        <h3>🗑️ Database Reset</h3>
        <p>Clear all processing data to start fresh. This will delete:</p>
        <ul className="reset-list">
          <li>All LLM responses and analysis results</li>
          <li>All document records</li>
          <li>All stored document content</li>
        </ul>
        
        <div className="reset-controls">
          <button
            onClick={handleResetClick}
            disabled={isResetting || loading}
            className="btn btn-danger reset-btn"
          >
            {isResetting ? '⏳ Resetting...' : '🗑️ Reset Database'}
          </button>
          
          {resetStatus && (
            <div className="reset-progress">
              <div className="progress-bar">
                <div 
                  className="progress-fill"
                  style={{ width: `${resetStatus.progress}%` }}
                ></div>
              </div>
              <div className="progress-text">
                {resetStatus.progress}% - {resetStatus.step_name}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Database Snapshots */}
      <div className="maintenance-section">
        <h3>📸 Database Snapshots</h3>
        <p>Create and manage database snapshots for backup and recovery:</p>

        <div className="snapshot-controls">
          <button
            onClick={handleSnapshotClick}
            disabled={isCreatingSnapshot || loading}
            className="btn btn-primary snapshot-btn"
          >
            {isCreatingSnapshot ? '⏳ Creating Snapshot...' : '📸 Save Snapshot'}
          </button>

          {snapshotStatus && (
            <div className="snapshot-progress">
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${snapshotStatus.progress}%` }}
                ></div>
              </div>
              <div className="progress-text">
                {snapshotStatus.progress}% - {snapshotStatus.step_name}
              </div>
            </div>
          )}
        </div>

        {/* Snapshots List */}
        {snapshots && snapshots.length > 0 && (
          <div className="snapshots-list">
            <h4>📋 Available Snapshots ({snapshots.length})</h4>
            <div className="snapshots-grid">
              {snapshots.map(snapshot => (
                <div key={snapshot.id} className="snapshot-card">
                  <div className="snapshot-header">
                    <h5>{snapshot.name}</h5>
                    <span className={`snapshot-status ${snapshot.status}`}>
                      {snapshot.status}
                    </span>
                  </div>
                  <div className="snapshot-details">
                    <p><strong>Description:</strong> {snapshot.description}</p>
                    <p><strong>Created:</strong> {new Date(snapshot.created_at).toLocaleString()}</p>
                    <p><strong>Size:</strong> {(snapshot.file_size / 1024 / 1024).toFixed(1)} MB</p>
                    {snapshot.record_counts && (
                      <div className="record-counts">
                        <strong>Records:</strong>
                        <div className="counts-grid">
                          {Object.entries(snapshot.record_counts).map(([table, count]) => (
                            <span key={table} className="count-item">
                              {table}: {count.toLocaleString()}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="snapshot-actions">
                    <button
                      onClick={() => handleLoadSnapshot(snapshot)}
                      disabled={isLoadingSnapshot || isCreatingSnapshot}
                      className="btn btn-primary btn-sm"
                      title="Restore this snapshot to the database"
                    >
                      {isLoadingSnapshot ? '⏳ Loading...' : '🔄 Load'}
                    </button>
                    <button
                      onClick={() => handleEditSnapshot(snapshot)}
                      disabled={isLoadingSnapshot || isCreatingSnapshot}
                      className="btn btn-secondary btn-sm"
                      title="Edit snapshot name and description"
                    >
                      ✏️ Edit
                    </button>
                    <button
                      onClick={() => handleDeleteSnapshot(snapshot)}
                      disabled={isLoadingSnapshot || isCreatingSnapshot}
                      className="btn btn-danger btn-sm"
                      title="Delete this snapshot permanently"
                    >
                      🗑️ Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Progress Window */}
      <div className="maintenance-section">
        <h3>📋 Progress Log</h3>
        <div 
          ref={progressWindowRef}
          className="progress-window"
        >
          {progressLogs.length === 0 ? (
            <div className="no-logs">No operations performed yet</div>
          ) : (
            progressLogs.map(log => (
              <div key={log.id} className={`log-entry ${log.type}`}>
                <span className="log-timestamp">{log.timestamp}</span>
                <span className="log-message">{log.message}</span>
              </div>
            ))
          )}
        </div>
        
        {progressLogs.length > 0 && (
          <button 
            onClick={() => setProgressLogs([])}
            className="btn btn-secondary clear-logs-btn"
          >
            🧹 Clear Logs
          </button>
        )}
      </div>

      {/* Confirmation Dialog */}
      {showConfirmDialog && (
        <div className="modal-overlay">
          <div className="confirmation-dialog">
            <h3>⚠️ Confirm Database Reset</h3>
            <p>
              This action will permanently delete all LLM responses, documents, and document content.
              This operation cannot be undone.
            </p>
            <p><strong>Are you sure you want to proceed?</strong></p>
            
            <div className="dialog-actions">
              <button onClick={cancelReset} className="btn btn-secondary">
                Cancel
              </button>
              <button onClick={confirmReset} className="btn btn-danger">
                Yes, Reset Database
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Snapshot Dialog */}
      {showSnapshotDialog && (
        <div className="modal-overlay">
          <div className="confirmation-dialog">
            <h3>📸 Create Database Snapshot</h3>
            <p>Create a compressed backup of the entire database with metadata tracking.</p>

            <div className="snapshot-form">
              <div className="form-group">
                <label htmlFor="snapshotName">Snapshot Name:</label>
                <input
                  id="snapshotName"
                  type="text"
                  value={snapshotName}
                  onChange={(e) => setSnapshotName(e.target.value)}
                  placeholder="Enter snapshot name (optional)"
                  className="form-input"
                />
              </div>

              <div className="form-group">
                <label htmlFor="snapshotDescription">Description:</label>
                <textarea
                  id="snapshotDescription"
                  value={snapshotDescription}
                  onChange={(e) => setSnapshotDescription(e.target.value)}
                  placeholder="Enter description (optional)"
                  className="form-textarea"
                  rows="3"
                />
              </div>
            </div>

            <div className="dialog-actions">
              <button onClick={cancelSnapshot} className="btn btn-secondary">
                Cancel
              </button>
              <button onClick={confirmSnapshot} className="btn btn-primary">
                Create Snapshot
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Load Snapshot Dialog */}
      {showLoadDialog && selectedSnapshot && (
        <div className="modal-overlay">
          <div className="confirmation-dialog">
            <h3>🔄 Load Database Snapshot</h3>
            <p>
              <strong>⚠️ Warning:</strong> This will restore the database to the state captured in this snapshot.
              A backup of the current database will be created automatically before the restore.
            </p>

            <div className="snapshot-info">
              <h4>Snapshot Details:</h4>
              <p><strong>Name:</strong> {selectedSnapshot.name}</p>
              <p><strong>Description:</strong> {selectedSnapshot.description}</p>
              <p><strong>Created:</strong> {new Date(selectedSnapshot.created_at).toLocaleString()}</p>
              <p><strong>Size:</strong> {(selectedSnapshot.file_size / 1024 / 1024).toFixed(1)} MB</p>
            </div>

            <div className="dialog-actions">
              <button onClick={cancelLoadSnapshot} className="btn btn-secondary">
                Cancel
              </button>
              <button onClick={confirmLoadSnapshot} className="btn btn-primary">
                Load Snapshot
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Snapshot Dialog */}
      {showDeleteDialog && selectedSnapshot && (
        <div className="modal-overlay">
          <div className="confirmation-dialog">
            <h3>🗑️ Delete Snapshot</h3>
            <p>
              <strong>⚠️ Warning:</strong> This will permanently delete the snapshot file and database record.
              This action cannot be undone.
            </p>

            <div className="snapshot-info">
              <h4>Snapshot to Delete:</h4>
              <p><strong>Name:</strong> {selectedSnapshot.name}</p>
              <p><strong>Description:</strong> {selectedSnapshot.description}</p>
              <p><strong>Size:</strong> {(selectedSnapshot.file_size / 1024 / 1024).toFixed(1)} MB</p>
            </div>

            <div className="dialog-actions">
              <button onClick={cancelDeleteSnapshot} className="btn btn-secondary">
                Cancel
              </button>
              <button onClick={confirmDeleteSnapshot} className="btn btn-danger">
                Delete Snapshot
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Snapshot Dialog */}
      {showEditDialog && editingSnapshot && (
        <div className="modal-overlay">
          <div className="confirmation-dialog">
            <h3>✏️ Edit Snapshot</h3>
            <p>Update the snapshot name and description:</p>

            <div className="snapshot-form">
              <div className="form-group">
                <label htmlFor="editSnapshotName">Snapshot Name:</label>
                <input
                  id="editSnapshotName"
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  placeholder="Enter snapshot name"
                  className="form-input"
                />
              </div>

              <div className="form-group">
                <label htmlFor="editSnapshotDescription">Description:</label>
                <textarea
                  id="editSnapshotDescription"
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  placeholder="Enter description"
                  className="form-textarea"
                  rows="3"
                />
              </div>
            </div>

            <div className="dialog-actions">
              <button onClick={cancelEditSnapshot} className="btn btn-secondary">
                Cancel
              </button>
              <button onClick={confirmEditSnapshot} className="btn btn-primary">
                Update Snapshot
              </button>
            </div>
          </div>
        </div>
      )}
      </div>
    </div>
  );
};

export default MaintenanceManager;
