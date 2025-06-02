import React, { useState, useEffect } from 'react';
import axios from 'axios';

const BatchDashboard = () => {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(5000); // 5 seconds
  const [selectedBatches, setSelectedBatches] = useState(new Set());

  const fetchDashboardData = async (batchIds = null) => {
    try {
      let url = `/api/batches/dashboard`;
      if (batchIds && batchIds.length > 0) {
        url += `?batch_ids=${batchIds.join(',')}`;
      }

      const response = await axios.get(url);
      if (response.data.success) {
        setDashboardData(response.data.dashboard);
        setError('');
      } else {
        setError(response.data.error || 'Failed to fetch dashboard data');
      }
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      setError(error.response?.data?.error || error.message || 'Failed to fetch dashboard data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  useEffect(() => {
    if (autoRefresh) {
      const batchIds = selectedBatches.size > 0 ? Array.from(selectedBatches) : null;
      const interval = setInterval(() => fetchDashboardData(batchIds), refreshInterval);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, refreshInterval, selectedBatches]);

  // Handle batch selection
  const handleBatchToggle = (batchId) => {
    const newSelected = new Set(selectedBatches);
    if (newSelected.has(batchId)) {
      newSelected.delete(batchId);
    } else {
      newSelected.add(batchId);
    }
    setSelectedBatches(newSelected);
  };

  const handleSelectAll = () => {
    if (dashboardData?.recent_batches) {
      const allBatchIds = new Set(dashboardData.recent_batches.map(batch => batch.id));
      setSelectedBatches(allBatchIds);
    }
  };

  const handleSelectNone = () => {
    setSelectedBatches(new Set());
  };

  // Update dashboard when selection changes
  useEffect(() => {
    if (dashboardData) {
      const batchIds = selectedBatches.size > 0 ? Array.from(selectedBatches) : null;
      fetchDashboardData(batchIds);
    }
  }, [selectedBatches]);

  const [batchActionLoading, setBatchActionLoading] = useState(null); // Track which action is loading

  // Handle batch pause
  const handlePauseBatch = async (batchId, batchName) => {
    setBatchActionLoading(`pause-${batchId}`);

    try {
      const response = await axios.post(`/api/batches/${batchId}/pause`);
      if (response.data.success) {
        // Immediately update the batch status in the dashboard data for instant feedback
        setDashboardData(prevData => ({
          ...prevData,
          active_batches: prevData.active_batches.map(batch =>
            batch.batch_id === batchId ? { ...batch, status: 'PAUSED' } : batch
          )
        }));
        // Also refresh from server
        fetchDashboardData();
      } else {
        alert(`❌ Failed to pause batch: ${response.data.error}`);
      }
    } catch (error) {
      console.error('Error pausing batch:', error);
      alert(`❌ Error pausing batch: ${error.response?.data?.error || error.message}`);
    } finally {
      setBatchActionLoading(null);
    }
  };

  // Handle batch resume
  const handleResumeBatch = async (batchId, batchName) => {
    setBatchActionLoading(`resume-${batchId}`);

    try {
      const response = await axios.post(`/api/batches/${batchId}/resume`);
      if (response.data.success) {
        // Immediately update the batch status in the dashboard data for instant feedback
        setDashboardData(prevData => ({
          ...prevData,
          active_batches: prevData.active_batches.map(batch =>
            batch.batch_id === batchId ? { ...batch, status: 'P' } : batch
          )
        }));
        // Also refresh from server
        fetchDashboardData();
      } else {
        alert(`❌ Failed to resume batch: ${response.data.error}`);
      }
    } catch (error) {
      console.error('Error resuming batch:', error);
      alert(`❌ Error resuming batch: ${error.response?.data?.error || error.message}`);
    } finally {
      setBatchActionLoading(null);
    }
  };

  // Handle batch deletion
  const handleDeleteBatch = async (batchId, batchName) => {
    if (!window.confirm(`Are you sure you want to delete batch "${batchName}"?\n\nThis will:\n• Archive all batch data to JSON\n• Delete the batch, documents, and responses\n• This action cannot be undone`)) {
      return;
    }

    try {
      const response = await axios.delete(`/api/batches/${batchId}`, {
        headers: {
          'Content-Type': 'application/json'
        },
        data: {
          archived_by: 'Dashboard User',
          archive_reason: 'Manual deletion from dashboard'
        }
      });

      if (response.data.success) {
        // Remove from selected batches if it was selected
        if (selectedBatches.has(batchId)) {
          const newSelected = new Set(selectedBatches);
          newSelected.delete(batchId);
          setSelectedBatches(newSelected);
        }

        // Refresh dashboard data
        fetchDashboardData();
      } else {
        alert(`❌ Failed to delete batch: ${response.data.error}`);
      }
    } catch (error) {
      console.error('Error deleting batch:', error);
      alert(`❌ Error deleting batch: ${error.response?.data?.error || error.message}`);
    }
  };

  const formatDuration = (timeObj) => {
    if (!timeObj) return 'N/A';
    if (timeObj.hours >= 1) return `${timeObj.hours}h`;
    if (timeObj.minutes >= 1) return `${timeObj.minutes}m`;
    return `${timeObj.seconds}s`;
  };

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'N/A';
    return new Date(timestamp).toLocaleString();
  };

  if (loading) {
    return (
      <div className="batch-dashboard">
        <div className="loading-container">
          <div className="loading-spinner">⏳</div>
          <p>Loading batch dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="batch-dashboard">
        <div className="error-container">
          <h2>❌ Error Loading Dashboard</h2>
          <p>{error}</p>
          <button onClick={fetchDashboardData} className="btn btn-primary">
            🔄 Retry
          </button>
        </div>
      </div>
    );
  }

  const { summary_stats, active_batches, recent_batches } = dashboardData;

  return (
    <div className="batch-dashboard">
      <div className="dashboard-header">
        <h1>📊 Document Batch Processor Dashboard</h1>
        <div className="dashboard-controls">
          <label className="auto-refresh-control">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            Auto-refresh
          </label>
          {autoRefresh && (
            <select
              value={refreshInterval}
              onChange={(e) => setRefreshInterval(parseInt(e.target.value))}
              className="refresh-interval-select"
            >
              <option value={2000}>2s</option>
              <option value={5000}>5s</option>
              <option value={10000}>10s</option>
              <option value={30000}>30s</option>
            </select>
          )}
          <button onClick={fetchDashboardData} className="btn btn-sm btn-secondary">
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Summary Statistics */}
      <div className="summary-stats">
        <div className="overview-header">
          <h2>📈 System Overview {selectedBatches.size > 0 && `(${selectedBatches.size} selected batches)`}</h2>
          {summary_stats.stats_context && (
            <div className="stats-context">
              {summary_stats.stats_context === 'active_only' && (
                <span className="context-badge active">
                  🔄 Showing metrics for active batches only
                </span>
              )}
              {summary_stats.stats_context === 'all_batches' && (
                <span className="context-badge all">
                  📈 Showing metrics for all batches
                </span>
              )}
              {summary_stats.stats_context === 'filtered' && (
                <span className="context-badge filtered">
                  🔍 Showing metrics for selected batches
                </span>
              )}
            </div>
          )}
        </div>
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-value">{summary_stats.total_batches}</div>
            <div className="stat-label">
              {summary_stats.stats_context === 'active_only' ? 'Active Batches' : 'Total Batches'}
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{summary_stats.active_batches}</div>
            <div className="stat-label">
              {summary_stats.stats_context === 'active_only' ? 'Processing' : 'Active Batches'}
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{summary_stats.total_documents}</div>
            <div className="stat-label">Total Documents</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{summary_stats.total_responses}</div>
            <div className="stat-label">Total Responses</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{summary_stats.success_rate}%</div>
            <div className="stat-label">Success Rate</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">
              {summary_stats.avg_processing_time_ms
                ? (parseFloat(summary_stats.avg_processing_time_ms) / 1000).toFixed(2) + 's'
                : 'N/A'}
            </div>
            <div className="stat-label">Avg Processing Time</div>
          </div>
        </div>
      </div>

      {/* Active Batches */}
      <div className="active-batches">
        <h2>🔄 Active Batches ({active_batches.length})</h2>
        {active_batches.length === 0 ? (
          <div className="no-active-batches">
            <p>✅ No batches currently processing</p>
            {recent_batches.length > 0 && (
              <div className="batch-selection-controls">
                <p>📊 Analyze specific batches by selecting them below:</p>
                <div className="selection-buttons">
                  <button
                    onClick={handleSelectAll}
                    className="btn btn-sm btn-secondary"
                    disabled={selectedBatches.size === recent_batches.length}
                  >
                    ✅ Select All
                  </button>
                  <button
                    onClick={handleSelectNone}
                    className="btn btn-sm btn-secondary"
                    disabled={selectedBatches.size === 0}
                  >
                    ❌ Select None
                  </button>
                  <span className="selection-info">
                    {selectedBatches.size === 0
                      ? "Showing aggregate of all batches"
                      : `Showing data for ${selectedBatches.size} selected batch${selectedBatches.size > 1 ? 'es' : ''}`
                    }
                  </span>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="batch-cards">
            {active_batches.map(batch => (
              <div key={batch.batch_id} className="batch-card active">
                <div className="batch-header">
                  <h3>#{batch.batch_number} - {batch.batch_name}</h3>
                  <div className={`batch-status ${batch.status === 'PAUSED' ? 'paused' : 'processing'}`}>
                    {batch.status === 'PAUSED' ? '⏸️ Paused' :
                     batch.status === 'ANALYZING' ? '🔄 Analyzing' : '🔄 Processing'}
                  </div>
                  <div className="batch-controls">
                    {(batch.status === 'P' || batch.status === 'ANALYZING') && (
                      <button
                        onClick={() => handlePauseBatch(batch.batch_id, batch.batch_name)}
                        className="btn btn-sm btn-warning"
                        title="Pause this batch"
                      >
                        ⏸️ Pause
                      </button>
                    )}
                    {batch.status === 'PAUSED' && (
                      <button
                        onClick={() => handleResumeBatch(batch.batch_id, batch.batch_name)}
                        className="btn btn-sm btn-success"
                        title="Resume this batch"
                      >
                        ▶️ Resume
                      </button>
                    )}
                  </div>
                </div>

                <div className="batch-progress">
                  <div className="progress-bar">
                    <div
                      className="progress-fill"
                      style={{ width: `${batch.responses.progress_percent}%` }}
                    ></div>
                  </div>
                  <div className="progress-text">
                    {batch.documents.completed} / {batch.documents.total} documents
                    ({batch.responses.progress_percent}%)
                  </div>
                </div>

                <div className="batch-stats">
                  <div className="stat-row">
                    <span>✅ Completed:</span>
                    <span>{batch.documents.completed} docs</span>
                  </div>
                  {batch.documents.failed > 0 && (
                    <div className="stat-row">
                      <span>❌ Failed:</span>
                      <span>{batch.documents.failed} docs</span>
                    </div>
                  )}
                  <div className="stat-row">
                    <span>⏳ Processing:</span>
                    <span>{batch.documents.processing} docs</span>
                  </div>
                  <div className="stat-row">
                    <span>⏸️ Waiting:</span>
                    <span>{batch.documents.waiting} docs</span>
                  </div>
                  <div className="stat-row">
                    <span>📄 Total Responses:</span>
                    <span>{batch.responses.total}</span>
                  </div>
                  <div className="stat-row">
                    <span>⏱️ Elapsed:</span>
                    <span>{formatDuration(batch.elapsed_time)}</span>
                  </div>
                  <div className="stat-row">
                    <span>🎯 Success Rate:</span>
                    <span>{batch.responses.success_rate}%</span>
                  </div>
                  <div className="stat-row">
                    <span>⚡ Throughput:</span>
                    <span>{batch.performance.throughput_docs_per_minute} docs/min</span>
                  </div>
                  {batch.estimated_completion && (
                    <div className="stat-row">
                      <span>🏁 ETA:</span>
                      <span>{formatDuration(batch.estimated_completion)}</span>
                    </div>
                  )}
                </div>

                {/* Folder Progress */}
                {batch.folder_progress && batch.folder_progress.length > 0 && (
                  <div className="folder-progress">
                    <h4>📁 Folder Progress</h4>
                    {batch.folder_progress.map(folder => (
                      <div key={folder.folder_id} className="folder-item">
                        <div className="folder-name">{folder.folder_name}</div>
                        <div className="folder-stats">
                          <span>{folder.completed}/{folder.total_responses} ({folder.progress_percent}%)</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recent Batches */}
      <div className="recent-batches">
        <h2>📋 Recent Batches</h2>
        {recent_batches.length === 0 ? (
          <div className="no-recent-batches">
            <p>🆕 No batches found. Create your first batch using the "🔍 Analyze Documents" tab!</p>
          </div>
        ) : (
          <div className="batch-list">
            {recent_batches.map(batch => (
              <div key={batch.id} className={`batch-item ${batch.status.toLowerCase()} ${selectedBatches.has(batch.id) ? 'selected' : ''}`}>
                {active_batches.length === 0 && (
                  <div className="batch-checkbox">
                    <input
                      type="checkbox"
                      checked={selectedBatches.has(batch.id)}
                      onChange={() => handleBatchToggle(batch.id)}
                      id={`batch-${batch.id}`}
                    />
                    <label htmlFor={`batch-${batch.id}`}>Select batch</label>
                  </div>
                )}
                <div className="batch-info">
                  <span className="batch-number">#{batch.batch_number}</span>
                  <span className="batch-name">{batch.batch_name}</span>
                  <span className={`batch-status ${batch.status.toLowerCase()}`}>
                    {batch.status === 'P' ? '🔄 Processing' :
                      batch.status === 'ANALYZING' ? '🔄 Analyzing' :
                      batch.status === 'PAUSED' ? '⏸️ Paused' :
                        batch.status === 'C' ? '✅ Completed' :
                          batch.status === 'F' ? '❌ Failed' : batch.status}
                  </span>
                </div>
                <div className="batch-meta">
                  <span>Created: {formatTimestamp(batch.created_at)}</span>
                  <span>Documents: {batch.total_documents}</span>
                </div>
                <div className="batch-actions">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteBatch(batch.id, batch.batch_name);
                    }}
                    className="btn btn-sm btn-danger"
                    title="Archive and delete this batch"
                    disabled={batch.status === 'P'}
                  >
                    🗑️ Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="dashboard-footer">
        <p>Last updated: {formatTimestamp(dashboardData.last_updated)}</p>
      </div>
    </div>
  );
};

export default BatchDashboard;
