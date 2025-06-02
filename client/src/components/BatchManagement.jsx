import React, { useState, useEffect } from 'react';
import axios from 'axios';
import '../styles/batch-management.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001';

const BatchManagement = ({ onNavigateBack }) => {
  const [batches, setBatches] = useState([]);
  const [selectedBatch, setSelectedBatch] = useState(null);
  const [batchDetails, setBatchDetails] = useState(null);
  const [llmResponses, setLlmResponses] = useState([]);
  const [responsesLoading, setResponsesLoading] = useState(false);
  const [responsesPagination, setResponsesPagination] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState(null);
  
  // New state for search and filters
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [responseStatusFilter, setResponseStatusFilter] = useState('all');
  const [scoreFilter, setScoreFilter] = useState({ min: 0, max: 100 });
  const [sortBy, setSortBy] = useState('created_desc');

  // Progress tracking state
  const [progressPolling, setProgressPolling] = useState(null);
  const [progressMessage, setProgressMessage] = useState('');

  // Detailed view modal state
  const [selectedResponseDetail, setSelectedResponseDetail] = useState(null);
  const [showDetailModal, setShowDetailModal] = useState(false);

  // Resizer state
  const [isResizing, setIsResizing] = useState(false);
  const [leftPaneWidth, setLeftPaneWidth] = useState(400);

  // Load batches on component mount
  useEffect(() => {
    loadBatches();
  }, []);

  // Cleanup progress polling on unmount
  useEffect(() => {
    return () => {
      if (progressPolling) {
        clearInterval(progressPolling);
      }
    };
  }, [progressPolling]);

  // Resizer functionality
  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!isResizing) return;

      const container = document.querySelector('.batch-management-content');
      if (!container) return;

      const containerRect = container.getBoundingClientRect();
      const newWidth = e.clientX - containerRect.left;

      // Constrain width between min and max
      const minWidth = 250;
      const maxWidth = containerRect.width * 0.6;
      const constrainedWidth = Math.max(minWidth, Math.min(newWidth, maxWidth));

      setLeftPaneWidth(constrainedWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isResizing]);

  const handleResizerMouseDown = (e) => {
    e.preventDefault();
    setIsResizing(true);
  };

  const loadBatches = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE_URL}/api/batches?limit=50`);
      setBatches(response.data.batches || []);
      setError(null);
    } catch (error) {
      console.error('Error loading batches:', error);
      setError('Failed to load batches');
    } finally {
      setLoading(false);
    }
  };

  const loadBatchDetails = async (batchId) => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE_URL}/api/batches/${batchId}`);
      setBatchDetails(response.data.batch);
      setError(null);
    } catch (error) {
      console.error('Error loading batch details:', error);
      setError('Failed to load batch details');
      setBatchDetails(null);
    } finally {
      setLoading(false);
    }
  };

  const loadLlmResponses = async (batchId, offset = 0) => {
    try {
      setResponsesLoading(true);
      const response = await axios.get(`${API_BASE_URL}/api/batches/${batchId}/llm-responses`, {
        params: { limit: 50, offset }
      });

      if (offset === 0) {
        setLlmResponses(response.data.responses);
      } else {
        setLlmResponses(prev => [...prev, ...response.data.responses]);
      }

      setResponsesPagination(response.data.pagination);
      setError(null);
    } catch (error) {
      console.error('Error loading LLM responses:', error);
      setError('Failed to load LLM responses');
      if (offset === 0) {
        setLlmResponses([]);
      }
    } finally {
      setResponsesLoading(false);
    }
  };

  const handleBatchSelect = (batch) => {
    setSelectedBatch(batch);
    setLlmResponses([]); // Clear previous responses
    setResponsesPagination(null);
    loadBatchDetails(batch.id);
    loadLlmResponses(batch.id);
  };

  const handleLoadMoreResponses = () => {
    if (selectedBatch && responsesPagination?.has_more) {
      loadLlmResponses(selectedBatch.id, responsesPagination.offset + responsesPagination.limit);
    }
  };

  const handleRunBatch = async (batchId) => {
    try {
      setActionLoading('run');
      const response = await axios.post(`${API_BASE_URL}/api/batches/${batchId}/run`);
      if (response.data.success) {
        // Refresh batch list and details
        await loadBatches();
        if (selectedBatch && selectedBatch.id === batchId) {
          await loadBatchDetails(batchId);
        }
      }
    } catch (error) {
      console.error('Error running batch:', error);
      setError('Failed to run batch');
    } finally {
      setActionLoading(null);
    }
  };

  const handlePauseBatch = async (batchId) => {
    try {
      setActionLoading('pause');
      const response = await axios.post(`${API_BASE_URL}/api/batches/${batchId}/pause`);
      if (response.data.success) {
        // Refresh batch list and details
        await loadBatches();
        if (selectedBatch && selectedBatch.id === batchId) {
          await loadBatchDetails(batchId);
        }
      }
    } catch (error) {
      console.error('Error pausing batch:', error);
      setError('Failed to pause batch');
    } finally {
      setActionLoading(null);
    }
  };

  const handleResumeBatch = async (batchId) => {
    try {
      setActionLoading('resume');
      const response = await axios.post(`${API_BASE_URL}/api/batches/${batchId}/resume`);
      if (response.data.success) {
        // Refresh batch list and details
        await loadBatches();
        if (selectedBatch && selectedBatch.id === batchId) {
          await loadBatchDetails(batchId);
        }
      }
    } catch (error) {
      console.error('Error resuming batch:', error);
      setError('Failed to resume batch');
    } finally {
      setActionLoading(null);
    }
  };

  const handleDeleteBatch = async (batchId, batchName) => {
    if (!window.confirm(`Are you sure you want to delete batch "${batchName}"? This action cannot be undone.`)) {
      return;
    }

    try {
      setActionLoading('delete');
      const response = await axios.delete(`${API_BASE_URL}/api/batches/${batchId}`, {
        data: {
          archived_by: 'User',
          archive_reason: 'Manual deletion via Batch Management'
        }
      });

      if (response.data.success) {
        // Clear selection if deleted batch was selected
        if (selectedBatch && selectedBatch.id === batchId) {
          setSelectedBatch(null);
          setBatchDetails(null);
        }
        // Refresh batch list
        await loadBatches();
      }
    } catch (error) {
      console.error('Error deleting batch:', error);
      setError('Failed to delete batch');
    } finally {
      setActionLoading(null);
    }
  };

  const handleReprocessStaging = async (batchId, batchName) => {
    if (!window.confirm(`Are you sure you want to reprocess staging for batch "${batchName}"?`)) {
      return;
    }

    try {
      setActionLoading('reprocess-staging');
      setProgressMessage(`⚙️ Starting staging for batch "${batchName}"...`);

      const response = await axios.post(`${API_BASE_URL}/api/batches/${batchId}/reprocess-staging`);

      if (response.data.success) {
        setError(null);
        setProgressMessage(`✅ Staging completed successfully! Batch "${batchName}" is now ready for analysis.`);

        // Refresh batch details and list immediately
        if (selectedBatch && selectedBatch.id === batchId) {
          await loadBatchDetails(batchId);
        }
        await loadBatches();

        // Start progress polling to monitor status changes
        startProgressPolling(batchId);

        // Force an additional refresh after a short delay to ensure UI consistency
        setTimeout(async () => {
          await loadBatches();
        }, 1000);

        // Clear progress message after 3 seconds
        setTimeout(() => {
          setProgressMessage('');
        }, 3000);
      } else {
        setError(response.data.error || 'Failed to reprocess staging');
        setProgressMessage('');
      }
    } catch (error) {
      console.error('Error reprocessing staging:', error);
      setError('Failed to reprocess staging');
      setProgressMessage('');
    } finally {
      setActionLoading(null);
    }
  };

  const handleRunAnalysis = async (batchId, batchName) => {
    if (!window.confirm(`Are you sure you want to start analysis for batch "${batchName}"?`)) {
      return;
    }

    try {
      setActionLoading('run-analysis');
      setProgressMessage(`🚀 Starting analysis for batch "${batchName}"...`);

      const response = await axios.post(`${API_BASE_URL}/api/batches/${batchId}/run`);

      if (response.data.success) {
        setError(null);
        setProgressMessage(`✅ Analysis started successfully! Processing ${batchName}...`);

        // Start progress polling for this batch
        startProgressPolling(batchId);

        // Refresh batch details
        if (selectedBatch && selectedBatch.id === batchId) {
          await loadBatchDetails(batchId);
        }
        await loadBatches();
      } else {
        setError(response.data.error || 'Failed to start analysis');
        setProgressMessage('');
      }
    } catch (error) {
      console.error('Error starting analysis:', error);
      setError('Failed to start analysis');
      setProgressMessage('');
    } finally {
      setActionLoading(null);
    }
  };

  const handleRerunAnalysis = async (batchId, batchName) => {
    if (!window.confirm(`Are you sure you want to rerun analysis for batch "${batchName}"? This will reset all LLM responses.`)) {
      return;
    }

    try {
      setActionLoading('rerun-analysis');
      const response = await axios.post(`${API_BASE_URL}/api/batches/${batchId}/rerun`);

      if (response.data.success) {
        setError(null);
        // Refresh batch details
        if (selectedBatch && selectedBatch.id === batchId) {
          await loadBatchDetails(batchId);
        }
        await loadBatches();
      } else {
        setError(response.data.error || 'Failed to rerun analysis');
      }
    } catch (error) {
      console.error('Error rerunning analysis:', error);
      setError('Failed to rerun analysis');
    } finally {
      setActionLoading(null);
    }
  };

  const handleRestageAndRerun = async (batchId, batchName) => {
    if (!window.confirm(`Are you sure you want to restage and rerun analysis for batch "${batchName}"?\n\nThis will:\n• Delete all existing LLM responses\n• Refresh all documents (check for file changes)\n• Recreate LLM responses for all connections and prompts\n• Start analysis from the beginning\n\nThis is useful when files have changed or you want a complete refresh.`)) {
      return;
    }

    try {
      setActionLoading('restage-and-rerun');
      const response = await axios.post(`${API_BASE_URL}/api/batches/${batchId}/restage-and-rerun`);

      if (response.data.success) {
        setError(null);
        setProgressMessage(`🔄 Restaging and rerunning batch "${batchName}"...`);

        // Start progress polling for the restaged batch
        startProgressPolling(batchId);

        // Refresh batch details
        if (selectedBatch && selectedBatch.id === batchId) {
          await loadBatchDetails(batchId);
        }
        await loadBatches();
      } else {
        setError(response.data.error || 'Failed to restage and rerun analysis');
      }
    } catch (error) {
      console.error('Error restaging and rerunning analysis:', error);
      setError('Failed to restage and rerun analysis');
    } finally {
      setActionLoading(null);
    }
  };

  const handleResetToPrestage = async (batchId, batchName) => {
    if (!window.confirm(`Are you sure you want to reset batch "${batchName}" to prestage state?\n\nThis will:\n• Reset the batch status to SAVED (prestage)\n• Unassign all documents from the batch\n• Clear processing progress\n• Allow you to restart the batch from the beginning\n\nThe batch configuration will be preserved, but you'll need to stage and run it again.`)) {
      return;
    }

    try {
      setActionLoading('reset-to-prestage');
      const response = await axios.post(`${API_BASE_URL}/api/batches/${batchId}/reset-to-prestage`);

      if (response.data.success) {
        setError(null);
        setProgressMessage(`🔄💾 Batch "${batchName}" reset to prestage state. ${response.data.next_steps}`);

        // Refresh batch details
        if (selectedBatch && selectedBatch.id === batchId) {
          await loadBatchDetails(batchId);
        }
        await loadBatches();

        // Clear message after 5 seconds
        setTimeout(() => {
          setProgressMessage('');
        }, 5000);
      } else {
        setError(response.data.error || 'Failed to reset batch to prestage');
      }
    } catch (error) {
      console.error('Error resetting batch to prestage:', error);
      setError('Failed to reset batch to prestage');
    } finally {
      setActionLoading(null);
    }
  };

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'N/A';
    return new Date(timestamp).toLocaleString();
  };

  // Filter and sort batches
  const getFilteredBatches = () => {
    let filtered = batches;
    
    // Search filter
    if (searchTerm) {
      filtered = filtered.filter(batch => 
        batch.batch_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        batch.id.toString().includes(searchTerm) ||
        batch.batch_number?.toString().includes(searchTerm)
      );
    }
    
    // Status filter
    if (statusFilter !== 'all') {
      filtered = filtered.filter(batch => batch.status === statusFilter);
    }
    
    // Sort
    const sorted = [...filtered].sort((a, b) => {
      switch (sortBy) {
        case 'created_desc':
          return new Date(b.created_at) - new Date(a.created_at);
        case 'created_asc':
          return new Date(a.created_at) - new Date(b.created_at);
        case 'name_asc':
          return (a.batch_name || '').localeCompare(b.batch_name || '');
        case 'name_desc':
          return (b.batch_name || '').localeCompare(a.batch_name || '');
        case 'progress':
          return getProgressPercentage(b) - getProgressPercentage(a);
        default:
          return 0;
      }
    });
    
    return sorted;
  };

  // Filter LLM responses
  const getFilteredResponses = () => {
    let filtered = llmResponses;
    
    // Status filter
    if (responseStatusFilter !== 'all') {
      filtered = filtered.filter(response => response.status === responseStatusFilter);
    }
    
    // Score filter
    filtered = filtered.filter(response => {
      if (response.overall_score === null || response.overall_score === undefined) return true;
      return response.overall_score >= scoreFilter.min && response.overall_score <= scoreFilter.max;
    });
    
    return filtered;
  };

  // Progress polling functions
  const startProgressPolling = (batchId) => {
    // Clear any existing polling
    if (progressPolling) {
      clearInterval(progressPolling);
    }

    // Start new polling interval
    const intervalId = setInterval(async () => {
      try {
        // Refresh batch details to get updated progress
        if (selectedBatch && selectedBatch.id === batchId) {
          await loadBatchDetails(batchId);
        }
        await loadBatches();

        // Check if batch status has changed to a final state
        const currentBatch = selectedBatch && selectedBatch.id === batchId ?
          await getBatchStatus(batchId) : null;

        if (currentBatch) {
          // Check for completion states
          if (currentBatch.status === 'COMPLETED' || currentBatch.status === 'C') {
            setProgressMessage(`🎉 Analysis completed for batch "${currentBatch.batch_name}"!`);
            clearInterval(intervalId);
            setProgressPolling(null);

            // Clear message after 5 seconds
            setTimeout(() => {
              setProgressMessage('');
            }, 5000);
          }
          // Check for staging completion
          else if (currentBatch.status === 'STAGED') {
            setProgressMessage(`✅ Staging completed! Batch "${currentBatch.batch_name}" is ready for analysis.`);
            clearInterval(intervalId);
            setProgressPolling(null);

            // Force refresh of batch list to ensure UI is updated
            await loadBatches();

            // Clear message after 3 seconds
            setTimeout(() => {
              setProgressMessage('');
            }, 3000);
          }
          // Check for staging failure
          else if (currentBatch.status === 'FAILED_STAGING') {
            setProgressMessage(`❌ Staging failed for batch "${currentBatch.batch_name}".`);
            clearInterval(intervalId);
            setProgressPolling(null);

            // Clear message after 5 seconds
            setTimeout(() => {
              setProgressMessage('');
            }, 5000);
          }
        }
      } catch (error) {
        console.error('Error polling progress:', error);
      }
    }, 3000); // Poll every 3 seconds

    setProgressPolling(intervalId);
  };

  const getBatchStatus = async (batchId) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/batches/${batchId}`);
      return response.data.batch;
    } catch (error) {
      console.error('Error getting batch status:', error);
      return null;
    }
  };

  const getStatusDisplay = (status) => {
    const statusMap = {
      // New staging statuses
      'SAVED': { text: '💾 Saved', class: 'saved' },
      'READY_FOR_STAGING': { text: '📋 Ready for Staging', class: 'ready-for-staging' },
      'STAGING': { text: '⚙️ Staging', class: 'staging' },
      'STAGED': { text: '✅ Staged', class: 'staged' },
      'FAILED_STAGING': { text: '❌ Staging Failed', class: 'failed-staging' },
      'ANALYZING': { text: '🔄 Analyzing', class: 'analyzing' },
      'COMPLETED': { text: '✅ Completed', class: 'completed' },

      // Legacy statuses for backward compatibility
      'PREPARED': { text: '📋 Prepared', class: 'prepared' },
      'PROCESSING': { text: '🔄 Processing', class: 'processing' },
      'P': { text: '🔄 Processing', class: 'processing' },
      'PAUSED': { text: '⏸️ Paused', class: 'paused' },
      'PA': { text: '⏸️ Paused', class: 'paused' }, // Legacy compatibility
      'C': { text: '✅ Completed', class: 'completed' },
      'FAILED': { text: '❌ Failed', class: 'failed' },
      'F': { text: '❌ Failed', class: 'failed' }
    };
    return statusMap[status] || { text: status, class: 'unknown' };
  };

  const getProgressPercentage = (batch) => {
    if (!batch || !batch.total_responses || batch.total_responses === 0) return 0;
    const completed = (batch.status_counts?.S || 0) + (batch.status_counts?.F || 0);
    return Math.round((completed / batch.total_responses) * 100);
  };

  const handleResponseDoubleClick = (response) => {
    setSelectedResponseDetail(response);
    setShowDetailModal(true);
  };

  const handleCloseDetailModal = () => {
    setShowDetailModal(false);
    setSelectedResponseDetail(null);
  };

  return (
    <div className="batch-management">
      <div className="batch-management-header">
        <div className="header-left">
          <button onClick={onNavigateBack} className="btn btn-secondary nav-back">
            ← Back to Dashboard
          </button>
          <h2>📊 Batch Management</h2>
        </div>
        <button onClick={loadBatches} className="btn btn-secondary" disabled={loading}>
          🔄 Refresh
        </button>
      </div>

      {error && (
        <div className="batch-error-message">
          ⚠️ {error}
        </div>
      )}

      <div className={`batch-management-content ${isResizing ? 'resizing' : ''}`}>
        {/* Left Pane - Batch List */}
        <div
          className="batch-list-pane"
          style={{ width: `${leftPaneWidth}px` }}
        >
          <div className="batch-list-header">
            <h3>Batches ({getFilteredBatches().length})</h3>
          </div>

          {/* Search and Filter Controls */}
          <div className="batch-filters">
            <div className="search-container">
              <span className="search-icon">🔍</span>
              <input
                type="text"
                placeholder="Search by name, ID, or batch number..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="search-input"
              />
            </div>
            
            <div className="filter-controls">
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="filter-select"
              >
                <option value="all">All Status</option>
                <option value="SAVED">💾 Saved</option>
                <option value="STAGING">⚙️ Staging</option>
                <option value="STAGED">✅ Staged</option>
                <option value="ANALYZING">🔄 Analyzing</option>
                <option value="COMPLETED">✅ Completed</option>
                <option value="FAILED_STAGING">❌ Failed Staging</option>
                <option value="FAILED">❌ Failed</option>
                <option value="PAUSED">⏸️ Paused</option>
              </select>
              
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="sort-select"
              >
                <option value="created_desc">Newest First</option>
                <option value="created_asc">Oldest First</option>
                <option value="name_asc">Name (A-Z)</option>
                <option value="name_desc">Name (Z-A)</option>
                <option value="progress">Progress</option>
              </select>
            </div>
          </div>

          {loading && !batches.length ? (
            <div className="loading">Loading batches...</div>
          ) : getFilteredBatches().length === 0 ? (
            <div className="no-batches">
              {batches.length === 0 ? (
                <>
                  <p>🆕 No batches found.</p>
                  <p>Create your first batch using the "🔍 Analyze Documents" tab!</p>
                </>
              ) : (
                <p>No batches match your search criteria.</p>
              )}
            </div>
          ) : (
            <div className="batch-table-container">
              <table className="batch-table">
                <thead>
                  <tr>
                    <th>Batch ID</th>
                    <th>Name</th>
                    <th>Status</th>
                    <th>Progress</th>
                    <th>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {getFilteredBatches().map(batch => {
                    const statusInfo = getStatusDisplay(batch.status);
                    const progress = getProgressPercentage(batch);

                    return (
                      <tr
                        key={batch.id}
                        className={`batch-row ${selectedBatch?.id === batch.id ? 'selected' : ''}`}
                        onClick={() => handleBatchSelect(batch)}
                      >
                        <td className="batch-number">#{batch.id}</td>
                        <td className="batch-name" title={batch.batch_name}>
                          {batch.batch_name || 'Unnamed Batch'}
                        </td>
                        <td className={`batch-status ${statusInfo.class}`}>
                          {statusInfo.text}
                        </td>
                        <td className="batch-progress">
                          <div className="progress-container">
                            <div className="progress-bar">
                              <div
                                className="progress-fill"
                                style={{ width: `${progress}%` }}
                              ></div>
                            </div>
                            <span className="progress-text">{progress}%</span>
                          </div>
                        </td>
                        <td className="batch-created">
                          {formatTimestamp(batch.created_at)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Resizer Handle */}
        <div
          className="resizer"
          onMouseDown={handleResizerMouseDown}
          title="Drag to resize panes"
        />

        {/* Right Pane - Batch Details */}
        <div className="batch-details-pane">
          {!selectedBatch ? (
            <div className="no-selection">
              <h3>📋 Batch Details</h3>
              <p>Select a batch from the list to view details</p>
            </div>
          ) : loading ? (
            <div className="loading">Loading batch details...</div>
          ) : !batchDetails ? (
            <div className="error">Failed to load batch details</div>
          ) : (
            <BatchDetails
              batch={batchDetails}
              llmResponses={llmResponses}
              responsesLoading={responsesLoading}
              responsesPagination={responsesPagination}
              onRunBatch={handleRunBatch}
              onPauseBatch={handlePauseBatch}
              onResumeBatch={handleResumeBatch}
              onDeleteBatch={handleDeleteBatch}
              onReprocessStaging={handleReprocessStaging}
              onRunAnalysis={handleRunAnalysis}
              onRerunAnalysis={handleRerunAnalysis}
              onRestageAndRerun={handleRestageAndRerun}
              onResetToPrestage={handleResetToPrestage}
              onLoadMoreResponses={handleLoadMoreResponses}
              onResponseDoubleClick={handleResponseDoubleClick}
              actionLoading={actionLoading}
              progressMessage={progressMessage}
              formatTimestamp={formatTimestamp}
              getStatusDisplay={getStatusDisplay}
              getFilteredResponses={getFilteredResponses}
              responseStatusFilter={responseStatusFilter}
              setResponseStatusFilter={setResponseStatusFilter}
              scoreFilter={scoreFilter}
              setScoreFilter={setScoreFilter}
            />
          )}
        </div>
      </div>

      {/* Detailed Response Modal */}
      {showDetailModal && selectedResponseDetail && (
        <ResponseDetailModal
          response={selectedResponseDetail}
          onClose={handleCloseDetailModal}
          formatTimestamp={formatTimestamp}
        />
      )}
    </div>
  );
};

// BatchDetails component for the right pane
const BatchDetails = ({
  batch,
  llmResponses,
  responsesLoading,
  responsesPagination,
  onRunBatch,
  onPauseBatch,
  onResumeBatch,
  onDeleteBatch,
  onReprocessStaging,
  onRunAnalysis,
  onRerunAnalysis,
  onRestageAndRerun,
  onResetToPrestage,
  onLoadMoreResponses,
  onResponseDoubleClick,
  actionLoading,
  progressMessage,
  formatTimestamp,
  getStatusDisplay,
  getFilteredResponses,
  responseStatusFilter,
  setResponseStatusFilter,
  scoreFilter,
  setScoreFilter
}) => {
  const statusInfo = getStatusDisplay(batch.status);
  const totalResponses = batch.total_responses || 0;
  const progressPercent = batch.completion_percentage || 0;

  return (
    <div className="batch-details">

      {/* Compact Summary */}
      <div className="batch-summary-compact">
        {/* Header Row with Name/Description and Actions */}
        <div className="summary-header">
          <div className="summary-info">
            <div className="batch-title">
              <span className="batch-number">#{batch.id}</span>
              <span className="batch-name">{batch.batch_name || 'Unnamed Batch'}</span>
              <div className={`status-badge-compact ${statusInfo.class}`}>
                {statusInfo.text}
              </div>
              {batch.description && (
                <span className="batch-description">- {batch.description}</span>
              )}
            </div>
          </div>

          <div className="summary-actions">
            {/* Staging Lifecycle Actions */}
            {(batch.status === 'SAVED' || batch.status === 'FAILED_STAGING') && (
              <button
                onClick={() => onReprocessStaging(batch.id, batch.batch_name)}
                disabled={actionLoading === 'reprocess-staging'}
                className="btn btn-primary btn-sm"
              >
                {actionLoading === 'reprocess-staging' ? '⏳' : '⚙️'} {batch.status === 'SAVED' ? 'Stage' : 'Restage'}
              </button>
            )}

            {batch.status === 'STAGED' && (
              <button
                onClick={() => onRunAnalysis(batch.id, batch.batch_name)}
                disabled={actionLoading === 'run-analysis'}
                className="btn btn-success btn-sm"
              >
                {actionLoading === 'run-analysis' ? '⏳' : '▶️'} Run Analysis
              </button>
            )}

            {batch.status === 'COMPLETED' && (
              <>
                <button
                  onClick={() => onRerunAnalysis(batch.id, batch.batch_name)}
                  disabled={actionLoading === 'rerun-analysis'}
                  className="btn btn-secondary btn-sm"
                >
                  {actionLoading === 'rerun-analysis' ? '⏳' : '🔄'} Rerun Analysis
                </button>
                <button
                  onClick={() => onRestageAndRerun(batch.id, batch.batch_name)}
                  disabled={actionLoading === 'restage-and-rerun'}
                  className="btn btn-warning btn-sm"
                  title="Refresh documents and recreate all LLM responses"
                >
                  {actionLoading === 'restage-and-rerun' ? '⏳' : '🔄📄'} Restage & Rerun
                </button>
              </>
            )}

            {/* Legacy Actions for backward compatibility */}
            {batch.status === 'PREPARED' && (
              <button
                onClick={() => onRunBatch(batch.id)}
                disabled={actionLoading === 'run'}
                className="btn btn-primary btn-sm"
              >
                {actionLoading === 'run' ? '⏳' : '▶️'} Run
              </button>
            )}

            {(batch.status === 'PROCESSING' || batch.status === 'P' || batch.status === 'ANALYZING') && (
              <button
                onClick={() => onPauseBatch(batch.id)}
                disabled={actionLoading === 'pause'}
                className="btn btn-warning btn-sm"
              >
                {actionLoading === 'pause' ? '⏳' : '⏸️'} Pause
              </button>
            )}

            {(batch.status === 'PAUSED' || batch.status === 'PA') && (
              <button
                onClick={() => onResumeBatch(batch.id)}
                disabled={actionLoading === 'resume'}
                className="btn btn-success btn-sm"
              >
                {actionLoading === 'resume' ? '⏳' : '▶️'} Resume
              </button>
            )}

            {/* Reset to Prestage button for stuck batches */}
            {(batch.status === 'ANALYZING' || batch.status === 'STAGING' || batch.status === 'FAILED_STAGING' ||
              batch.status === 'PROCESSING' || batch.status === 'P' || batch.status === 'PAUSED' || batch.status === 'PA') && (
              <button
                onClick={() => onResetToPrestage(batch.id, batch.batch_name)}
                disabled={actionLoading === 'reset-to-prestage'}
                className="btn btn-warning btn-sm"
                title="Reset batch to prestage (SAVED) state - allows restarting from the beginning"
              >
                {actionLoading === 'reset-to-prestage' ? '⏳' : '🔄💾'} Reset
              </button>
            )}

            <button
              onClick={() => onDeleteBatch(batch.id, batch.batch_name)}
              disabled={actionLoading === 'delete'}
              className="btn btn-danger btn-sm summary-delete"
            >
              {actionLoading === 'delete' ? '⏳' : '🗑️'} Delete
            </button>
          </div>
        </div>

        {/* Progress Message */}
        {progressMessage && (
          <div className="progress-message">
            {progressMessage}
          </div>
        )}

        {/* Progress Bar */}
        <div className="summary-progress">
          <div className="progress-bar-compact">
            <div
              className="progress-fill"
              style={{ width: `${progressPercent}%` }}
            ></div>
          </div>
          <span className="progress-text">{progressPercent}% Complete</span>
        </div>

        {/* Key Stats Row */}
        <div className="summary-stats">
          <div className="stat-compact">
            <span className="stat-number">{batch.total_documents || 0}</span>
            <span className="stat-text">Docs</span>
          </div>
          <div className="stat-compact">
            <span className="stat-number">{totalResponses}</span>
            <span className="stat-text">Responses</span>
          </div>
          <div className="stat-compact success">
            <span className="stat-number">{batch.status_counts?.S || 0}</span>
            <span className="stat-text">✅</span>
          </div>
          <div className="stat-compact failed">
            <span className="stat-number">{batch.status_counts?.F || 0}</span>
            <span className="stat-text">❌</span>
          </div>
          <div className="stat-compact processing">
            <span className="stat-number">{batch.status_counts?.P || 0}</span>
            <span className="stat-text">🔄</span>
          </div>
          <div className="stat-compact waiting">
            <span className="stat-number">{batch.status_counts?.N || 0}</span>
            <span className="stat-text">⏳</span>
          </div>
        </div>

        {/* Timing Info (if available) */}
        {batch.elapsed_time && (
          <div className="summary-timing">
            <span>⏱️ {batch.elapsed_time}</span>
            {batch.average_processing_time && (
              <span>📊 Avg: {batch.average_processing_time}s</span>
            )}
            {batch.estimated_completion && (
              <span>🎯 ETA: {batch.estimated_completion}</span>
            )}
          </div>
        )}
      </div>

      {/* LLM Responses */}
      <div className="details-section">
        <div className="responses-header">
          <h4>🔍 LLM Responses ({getFilteredResponses().length})</h4>
          
          {/* Response Filters */}
          {llmResponses.length > 0 && (
            <div className="response-filters">
              <select
                value={responseStatusFilter}
                onChange={(e) => setResponseStatusFilter(e.target.value)}
                className="response-filter-select"
              >
                <option value="all">All Status</option>
                <option value="S">✅ Success</option>
                <option value="F">❌ Failed</option>
                <option value="P">🔄 Processing</option>
                <option value="N">⏳ Waiting</option>
              </select>
              
              {/* Score Range Filter */}
              <div className="score-filter">
                <label>Score:</label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={scoreFilter.min}
                  onChange={(e) => setScoreFilter({ ...scoreFilter, min: parseInt(e.target.value) || 0 })}
                  className="score-input"
                  placeholder="Min"
                />
                <span>-</span>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={scoreFilter.max}
                  onChange={(e) => setScoreFilter({ ...scoreFilter, max: parseInt(e.target.value) || 100 })}
                  className="score-input"
                  placeholder="Max"
                />
              </div>
            </div>
          )}
        </div>
        
        {responsesLoading && llmResponses.length === 0 ? (
          <div className="loading">Loading responses...</div>
        ) : llmResponses.length === 0 ? (
          <div className="no-responses">
            <p>No LLM responses found for this batch.</p>
          </div>
        ) : getFilteredResponses().length === 0 ? (
          <div className="no-responses">
            <p>No responses match your filter criteria.</p>
          </div>
        ) : (
          <div className="responses-container">
            <div className="responses-list">
              {getFilteredResponses().map(response => (
                <LlmResponseItem
                  key={response.id}
                  response={response}
                  formatTimestamp={formatTimestamp}
                  onDoubleClick={onResponseDoubleClick}
                />
              ))}
            </div>

            {responsesPagination?.has_more && (
              <div className="load-more-container">
                <button
                  onClick={onLoadMoreResponses}
                  disabled={responsesLoading}
                  className="btn btn-secondary"
                >
                  {responsesLoading ? '⏳ Loading...' : `📄 Load More (${responsesPagination.total - llmResponses.length} remaining)`}
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Metadata */}
      {batch.meta_data && Object.keys(batch.meta_data).length > 0 && (
        <div className="details-section">
          <h4>🏷️ Metadata</h4>
          <div className="metadata-container">
            <pre className="metadata-json">
              {JSON.stringify(batch.meta_data, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
};

// LLM Response Item component
const LlmResponseItem = ({ response, formatTimestamp, onDoubleClick }) => {
  const getStatusIcon = (status) => {
    switch (status) {
      case 'S': return '✅';
      case 'F': return '❌';
      case 'P': return '🔄';
      case 'N': return '⏳';
      default: return '❓';
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'S': return 'Success';
      case 'F': return 'Failed';
      case 'P': return 'Processing';
      case 'N': return 'Waiting';
      default: return 'Unknown';
    }
  };

  const handleDoubleClick = () => {
    if (onDoubleClick) {
      onDoubleClick(response);
    }
  };

  const getScoreDisplay = (score) => {
    if (score === null || score === undefined) return 'N/A';
    return `${Math.round(score)}/100`;
  };

  const getScoreClass = (score) => {
    if (score === null || score === undefined) return 'score-na';
    if (score >= 80) return 'score-excellent';
    if (score >= 60) return 'score-good';
    if (score >= 40) return 'score-fair';
    return 'score-poor';
  };

  return (
    <div
      className={`response-item status-${response.status.toLowerCase()}`}
      onDoubleClick={handleDoubleClick}
      title="Double-click to view detailed response data"
      style={{ cursor: 'pointer' }}
    >
      <div className="response-header">
        <div className="response-document">
          <span className="document-icon">📄</span>
          <span className="document-name" title={response.document?.filepath}>
            {response.document?.filename || 'Unknown Document'}
          </span>
        </div>
        <div className="response-status">
          <span className="status-icon">{getStatusIcon(response.status)}</span>
          <span className="status-text">{getStatusText(response.status)}</span>
          {response.overall_score !== null && response.overall_score !== undefined && (
            <div className={`suitability-score ${getScoreClass(response.overall_score)}`}>
              <span className="score-label">Suitability:</span>
              <span className="score-value">{getScoreDisplay(response.overall_score)}</span>
            </div>
          )}
        </div>
      </div>

      <div className="response-details">
        <div className="response-config">
          <span className="config-icon">🤖</span>
          <span className="config-name">{response.connection?.name || 'Unknown LLM'}</span>
          {response.connection?.model_name && (
            <span className="model-name">({response.connection.model_name})</span>
          )}
        </div>

        <div className="response-prompt">
          <span className="prompt-icon">📝</span>
          <span className="prompt-description" title={response.prompt?.prompt_text}>
            {response.prompt?.description || 'No description'}
          </span>
        </div>
      </div>

      <div className="response-meta">
        {response.response_time_ms && (
          <span className="processing-time">
            ⏱️ {(response.response_time_ms / 1000).toFixed(2)}s
          </span>
        )}
        {response.completed_processing_at && (
          <span className="completed-time">
            🕒 {formatTimestamp(response.completed_processing_at)}
          </span>
        )}
        {response.error_message && (
          <span className="error-message" title={response.error_message}>
            ⚠️ {response.error_message.substring(0, 50)}...
          </span>
        )}
      </div>
    </div>
  );
};

// Response Detail Modal component
const ResponseDetailModal = ({ response, onClose, formatTimestamp }) => {
  const [modalSize, setModalSize] = React.useState({ width: 800, height: 600 });
  const [isResizing, setIsResizing] = React.useState(false);
  const [resizeStart, setResizeStart] = React.useState({ x: 0, y: 0, width: 0, height: 0 });
  const [isMaximized, setIsMaximized] = React.useState(false);
  const [previousSize, setPreviousSize] = React.useState({ width: 800, height: 600 });
  const modalRef = React.useRef(null);

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const handleResizeStart = (e) => {
    e.preventDefault();
    setIsResizing(true);
    setResizeStart({
      x: e.clientX,
      y: e.clientY,
      width: modalSize.width,
      height: modalSize.height
    });
  };

  const handleMaximizeToggle = () => {
    if (isMaximized) {
      // Restore to previous size
      setModalSize(previousSize);
      setIsMaximized(false);
    } else {
      // Maximize
      setPreviousSize(modalSize);
      setModalSize({
        width: window.innerWidth - 40,
        height: window.innerHeight - 40
      });
      setIsMaximized(true);
    }
  };

  React.useEffect(() => {
    const handleMouseMove = (e) => {
      if (!isResizing) return;

      const deltaX = e.clientX - resizeStart.x;
      const deltaY = e.clientY - resizeStart.y;

      const newWidth = Math.max(400, Math.min(window.innerWidth - 40, resizeStart.width + deltaX));
      const newHeight = Math.max(300, Math.min(window.innerHeight - 40, resizeStart.height + deltaY));

      setModalSize({ width: newWidth, height: newHeight });

      // If user is manually resizing, exit maximized state
      if (isMaximized) {
        setIsMaximized(false);
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    const handleKeyDown = (e) => {
      // Allow ESC key to close modal
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'nw-resize';
      document.body.style.userSelect = 'none';
    }

    // Add keyboard listener
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isResizing, resizeStart, onClose]);

  const getScoreDisplay = (score) => {
    if (score === null || score === undefined) return 'N/A';
    return `${Math.round(score)}/100`;
  };

  const getScoreClass = (score) => {
    if (score === null || score === undefined) return 'score-na';
    if (score >= 80) return 'score-excellent';
    if (score >= 60) return 'score-good';
    if (score >= 40) return 'score-fair';
    return 'score-poor';
  };

  // Parse response_json if it's a string
  let responseData = null;
  try {
    responseData = typeof response.response_json === 'string'
      ? JSON.parse(response.response_json)
      : response.response_json;
  } catch (e) {
    responseData = { error: 'Failed to parse response JSON', raw: response.response_json };
  }

  return (
    <div className="modal-backdrop" onClick={handleBackdropClick}>
      <div
        ref={modalRef}
        className="response-detail-modal resizable-modal"
        style={{
          width: `${modalSize.width}px`,
          height: `${modalSize.height}px`,
          maxWidth: 'none',
          maxHeight: 'none'
        }}
      >
        <div className="modal-header" onDoubleClick={handleMaximizeToggle}>
          <h3>📄 Response Details</h3>
          <div className="modal-header-controls">
            <span className="modal-size-indicator">
              {modalSize.width} × {modalSize.height}
            </span>
            <button
              className="modal-maximize"
              onClick={handleMaximizeToggle}
              title={isMaximized ? "Restore" : "Maximize"}
            >
              {isMaximized ? "🗗" : "🗖"}
            </button>
            <button className="modal-close" onClick={onClose} title="Close">✕</button>
          </div>
        </div>

        <div className="modal-content modal-content-scrollable">
          {/* Basic Information */}
          <div className="detail-section">
            <h4>📋 Basic Information</h4>
            <div className="detail-grid">
              <div className="modal-detail-item">
                <span className="detail-label">Document:</span>
                <span className="detail-value">{response.document?.filename || 'Unknown'}</span>
              </div>
              <div className="modal-detail-item">
                <span className="detail-label">Connection:</span>
                <span className="detail-value">{response.connection?.name || 'Unknown'}</span>
              </div>
              <div className="modal-detail-item">
                <span className="detail-label">Model:</span>
                <span className="detail-value">{response.connection?.model_name || 'Unknown'}</span>
              </div>
              <div className="modal-detail-item">
                <span className="detail-label">Provider:</span>
                <span className="detail-value">{response.connection?.provider_type || 'Unknown'}</span>
              </div>
              <div className="modal-detail-item">
                <span className="detail-label">Status:</span>
                <span className="detail-value">{response.status}</span>
              </div>
              <div className="modal-detail-item">
                <span className="detail-label">Processing Time:</span>
                <span className="detail-value">
                  {response.response_time_ms ? `${(response.response_time_ms / 1000).toFixed(2)}s` : 'N/A'}
                </span>
              </div>
              <div className="modal-detail-item">
                <span className="detail-label">Completed:</span>
                <span className="detail-value">
                  {response.completed_processing_at ? formatTimestamp(response.completed_processing_at) : 'N/A'}
                </span>
              </div>
            </div>
          </div>

          {/* Suitability Score */}
          {response.overall_score !== null && response.overall_score !== undefined && (
            <div className="detail-section">
              <h4>🎯 Suitability Score</h4>
              <div className={`score-display-large ${getScoreClass(response.overall_score)}`}>
                <span className="score-value-large">{getScoreDisplay(response.overall_score)}</span>
                <span className="score-description">LLM Readiness Score</span>
              </div>
            </div>
          )}

          {/* Prompt Information */}
          <div className="detail-section">
            <h4>📝 Prompt</h4>
            <div className="modal-detail-item">
              <span className="detail-label">Description:</span>
              <span className="detail-value">{response.prompt?.description || 'No description'}</span>
            </div>
            <div className="prompt-text">
              <strong>Prompt Text:</strong>
              <pre className="prompt-content">{response.prompt?.prompt_text || 'No prompt text available'}</pre>
            </div>
          </div>

          {/* Error Message (if any) */}
          {response.error_message && (
            <div className="detail-section">
              <h4>⚠️ Error Message</h4>
              <div className="error-content">
                {response.error_message}
              </div>
            </div>
          )}

          {/* Response Text */}
          {response.response_text && (
            <div className="detail-section">
              <h4>📄 Response Text</h4>
              <div className="response-text-content">
                <pre>{response.response_text}</pre>
              </div>
            </div>
          )}

          {/* Full JSON Response */}
          <div className="detail-section">
            <h4>🔍 Complete Response Data (JSON)</h4>
            <div className="json-content">
              <pre>{JSON.stringify(responseData, null, 2)}</pre>
            </div>
          </div>
        </div>

        {/* Resize Handle */}
        <div
          className="modal-resize-handle"
          onMouseDown={handleResizeStart}
          title="Drag to resize"
        >
          ⟲
        </div>
      </div>
    </div>
  );
};

export default BatchManagement;
