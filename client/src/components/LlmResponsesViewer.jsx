import React, { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import DocumentViewer from './DocumentViewer';
import '../styles/llm-responses-viewer.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001';

// Utility functions that can be used by both components
const formatFileSize = (bytes) => {
  if (!bytes || bytes === 0) return 'N/A';
  const units = ['B', 'KB', 'MB', 'GB'];
  let size = bytes;
  let unitIndex = 0;
  
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }
  
  return `${size.toFixed(2)} ${units[unitIndex]}`;
};

const LlmResponsesViewer = () => {
  // State management
  const [responses, setResponses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedResponse, setSelectedResponse] = useState(null);
  const [showDetailModal, setShowDetailModal] = useState(false);
  
  // Pagination
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [totalResponses, setTotalResponses] = useState(0);
  const pageSize = 50;
  
  // Search and filters
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [batchFilter, setBatchFilter] = useState('all');
  const [scoreRange, setScoreRange] = useState({ min: 0, max: 100 });
  const [dateRange, setDateRange] = useState({ start: '', end: '' });
  const [sortBy, setSortBy] = useState('created_desc');
  
  // View modes
  const [viewMode, setViewMode] = useState('grid'); // grid, list, compact
  const [showFilters, setShowFilters] = useState(true);
  
  // Refs for infinite scroll
  const observerRef = useRef();
  const lastResponseRef = useCallback(node => {
    if (loading) return;
    if (observerRef.current) observerRef.current.disconnect();
    observerRef.current = new IntersectionObserver(entries => {
      if (entries[0].isIntersecting && hasMore) {
        setPage(prevPage => prevPage + 1);
      }
    });
    if (node) observerRef.current.observe(node);
  }, [loading, hasMore]);

  // Load responses
  const loadResponses = async (pageNum = 1, append = false) => {
    try {
      setLoading(true);
      const offset = (pageNum - 1) * pageSize;
      
      // Build query parameters
      const params = {
        limit: pageSize,
        offset: offset
      };
      
      // Add filters if set
      if (searchTerm) params.search = searchTerm;
      if (statusFilter !== 'all') params.status = statusFilter;
      if (batchFilter !== 'all') params.batch_id = batchFilter;
      if (scoreRange.min > 0) params.min_score = scoreRange.min;
      if (scoreRange.max < 100) params.max_score = scoreRange.max;
      if (dateRange.start) params.start_date = dateRange.start;
      if (dateRange.end) params.end_date = dateRange.end;
      if (sortBy) params.sort = sortBy;
      
      const response = await axios.get(`${API_BASE_URL}/api/llm-responses`, { params });
      
      const newResponses = response.data.responses || [];
      setResponses(append ? [...responses, ...newResponses] : newResponses);
      setHasMore(response.data.pagination?.has_more || false);
      setTotalResponses(response.data.pagination?.total || 0);
      setError(null);
      
    } catch (err) {
      console.error('Error loading responses:', err);
      setError('Failed to load LLM responses');
    } finally {
      setLoading(false);
    }
  };

  // Load initial data
  useEffect(() => {
    loadResponses(1, false);
  }, [searchTerm, statusFilter, batchFilter, scoreRange, dateRange, sortBy]);

  // Load more on page change
  useEffect(() => {
    if (page > 1) {
      loadResponses(page, true);
    }
  }, [page]);

  // Reset pagination on filter change
  useEffect(() => {
    setPage(1);
    setResponses([]);
  }, [searchTerm, statusFilter, batchFilter, sortBy]);

  // Status helpers
  const getStatusIcon = (status) => {
    const statusMap = {
      'COMPLETED': '✅',
      'FAILED': '❌',
      'PROCESSING': '🔄',
      'QUEUED': '⏳',
      'S': '✅',
      'F': '❌',
      'P': '🔄',
      'N': '⏳'
    };
    return statusMap[status] || '❓';
  };

  const getStatusText = (status) => {
    const statusMap = {
      'COMPLETED': 'Completed',
      'FAILED': 'Failed',
      'PROCESSING': 'Processing',
      'QUEUED': 'Queued',
      'S': 'Success',
      'F': 'Failed',
      'P': 'Processing',
      'N': 'Waiting'
    };
    return statusMap[status] || 'Unknown';
  };

  const getStatusClass = (status) => {
    const classMap = {
      'COMPLETED': 'status-completed',
      'FAILED': 'status-failed',
      'PROCESSING': 'status-processing',
      'QUEUED': 'status-queued',
      'S': 'status-completed',
      'F': 'status-failed',
      'P': 'status-processing',
      'N': 'status-queued'
    };
    return classMap[status] || 'status-unknown';
  };

  // Score helpers
  const getScoreClass = (score) => {
    if (score === null || score === undefined) return 'score-na';
    if (score >= 80) return 'score-excellent';
    if (score >= 60) return 'score-good';
    if (score >= 40) return 'score-fair';
    return 'score-poor';
  };

  const getScoreEmoji = (score) => {
    if (score === null || score === undefined) return '➖';
    if (score >= 80) return '🌟';
    if (score >= 60) return '👍';
    if (score >= 40) return '👌';
    return '👎';
  };

  // Format helpers
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatDuration = (ms) => {
    if (!ms) return 'N/A';
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  const truncateText = (text, maxLength = 50) => {
    if (!text || text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  // Handle response selection
  const handleResponseClick = (response) => {
    setSelectedResponse(response);
    setShowDetailModal(true);
  };

  // Response card component
  const ResponseCard = ({ response, isLast }) => {
    const cardClass = `response-card ${viewMode} ${getStatusClass(response.status)}`;
    
    return (
      <div 
        ref={isLast ? lastResponseRef : null}
        className={cardClass}
        onClick={() => handleResponseClick(response)}
      >
        <div className="response-header">
          <div className="response-status">
            <span className="status-icon">{getStatusIcon(response.status)}</span>
            <span className="status-text">{getStatusText(response.status)}</span>
          </div>
          {response.overall_score !== null && (
            <div className={`response-score ${getScoreClass(response.overall_score)}`}>
              <span className="score-emoji">{getScoreEmoji(response.overall_score)}</span>
              <span className="score-value">{Math.round(response.overall_score)}</span>
            </div>
          )}
        </div>

        <div className="response-content">
          <div className="response-document">
            <span className="label">📄 Document:</span>
            <span className="value" title={response.document?.filepath}>
              {response.document?.filename || 'Unknown'}
            </span>
          </div>

          {viewMode !== 'compact' && (
            <>
              <div className="response-connection">
                <span className="label">🤖 Model:</span>
                <span className="value">
                  {response.connection?.model_name || response.connection?.name || 'Unknown'}
                </span>
              </div>

              <div className="response-prompt">
                <span className="label">📝 Prompt:</span>
                <span className="value" title={response.prompt?.prompt_text}>
                  {response.prompt?.description || 'No description'}
                </span>
              </div>
            </>
          )}

          {viewMode === 'list' && response.response_text && (
            <div className="response-preview">
              <span className="label">💬 Response:</span>
              <span className="value">{truncateText(response.response_text, 100)}</span>
            </div>
          )}
        </div>

        <div className="response-footer">
          <div className="response-meta">
            {response.batch_id && (
              <span className="meta-item">
                <span className="meta-icon">📦</span>
                <span className="meta-value">Batch {response.batch_id}</span>
              </span>
            )}
            {response.response_time_ms && (
              <span className="meta-item">
                <span className="meta-icon">⏱️</span>
                <span className="meta-value">{formatDuration(response.response_time_ms)}</span>
              </span>
            )}
            <span className="meta-item">
              <span className="meta-icon">📅</span>
              <span className="meta-value">{formatDate(response.created_at)}</span>
            </span>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="llm-responses-viewer">
      {/* Header */}
      <div className="viewer-header">
        <div className="header-left">
          <h2>🔍 LLM Responses Explorer</h2>
          <span className="response-count">
            {totalResponses > 0 ? `${totalResponses.toLocaleString()} responses` : 'Loading...'}
          </span>
        </div>
        
        <div className="header-controls">
          <div className="view-mode-selector">
            <button 
              className={`view-mode-btn ${viewMode === 'grid' ? 'active' : ''}`}
              onClick={() => setViewMode('grid')}
              title="Grid View"
            >
              <span className="icon">⊞</span>
            </button>
            <button 
              className={`view-mode-btn ${viewMode === 'list' ? 'active' : ''}`}
              onClick={() => setViewMode('list')}
              title="List View"
            >
              <span className="icon">☰</span>
            </button>
            <button 
              className={`view-mode-btn ${viewMode === 'compact' ? 'active' : ''}`}
              onClick={() => setViewMode('compact')}
              title="Compact View"
            >
              <span className="icon">▦</span>
            </button>
          </div>
          
          <button 
            className="toggle-filters-btn"
            onClick={() => setShowFilters(!showFilters)}
          >
            <span className="icon">🔧</span> Filters {showFilters ? '▼' : '▶'}
          </button>
        </div>
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <div className="filters-panel">
          <div className="filter-row">
            {/* Search */}
            <div className="filter-group search-group">
              <label>🔍 Search</label>
              <input
                type="text"
                placeholder="Search documents, prompts, responses..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="search-input"
              />
            </div>

            {/* Status Filter */}
            <div className="filter-group">
              <label>📊 Status</label>
              <select 
                value={statusFilter} 
                onChange={(e) => setStatusFilter(e.target.value)}
                className="filter-select"
              >
                <option value="all">All Status</option>
                <option value="COMPLETED">✅ Completed</option>
                <option value="FAILED">❌ Failed</option>
                <option value="PROCESSING">🔄 Processing</option>
                <option value="QUEUED">⏳ Queued</option>
              </select>
            </div>

            {/* Sort */}
            <div className="filter-group">
              <label>📈 Sort By</label>
              <select 
                value={sortBy} 
                onChange={(e) => setSortBy(e.target.value)}
                className="filter-select"
              >
                <option value="created_desc">Newest First</option>
                <option value="created_asc">Oldest First</option>
                <option value="score_desc">Highest Score</option>
                <option value="score_asc">Lowest Score</option>
                <option value="duration_desc">Longest Duration</option>
                <option value="duration_asc">Shortest Duration</option>
              </select>
            </div>
          </div>

          <div className="filter-row">
            {/* Score Range */}
            <div className="filter-group score-filter">
              <label>🎯 Score Range</label>
              <div className="range-inputs">
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={scoreRange.min}
                  onChange={(e) => setScoreRange({...scoreRange, min: parseInt(e.target.value) || 0})}
                  className="range-input"
                  placeholder="Min"
                />
                <span className="range-separator">-</span>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={scoreRange.max}
                  onChange={(e) => setScoreRange({...scoreRange, max: parseInt(e.target.value) || 100})}
                  className="range-input"
                  placeholder="Max"
                />
              </div>
            </div>

            {/* Date Range */}
            <div className="filter-group date-filter">
              <label>📅 Date Range</label>
              <div className="date-inputs">
                <input
                  type="date"
                  value={dateRange.start}
                  onChange={(e) => setDateRange({...dateRange, start: e.target.value})}
                  className="date-input"
                />
                <span className="date-separator">to</span>
                <input
                  type="date"
                  value={dateRange.end}
                  onChange={(e) => setDateRange({...dateRange, end: e.target.value})}
                  className="date-input"
                />
              </div>
            </div>

            {/* Clear Filters */}
            <div className="filter-group">
              <label>&nbsp;</label>
              <button 
                className="clear-filters-btn"
                onClick={() => {
                  setSearchTerm('');
                  setStatusFilter('all');
                  setBatchFilter('all');
                  setScoreRange({ min: 0, max: 100 });
                  setDateRange({ start: '', end: '' });
                  setSortBy('created_desc');
                }}
              >
                🔄 Clear All
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="error-banner">
          <span className="error-icon">⚠️</span>
          <span className="error-text">{error}</span>
          <button onClick={() => loadResponses(1, false)} className="retry-btn">
            🔄 Retry
          </button>
        </div>
      )}

      {/* Responses Grid/List */}
      <div className={`responses-container ${viewMode}`}>
        {responses.length === 0 && !loading ? (
          <div className="no-responses">
            <div className="no-responses-icon">🔍</div>
            <h3>No responses found</h3>
            <p>Try adjusting your filters or search criteria</p>
          </div>
        ) : (
          <div className={`responses-${viewMode}`}>
            {responses.map((response, index) => (
              <ResponseCard 
                key={response.id} 
                response={response}
                isLast={index === responses.length - 1}
              />
            ))}
          </div>
        )}
        
        {/* Loading indicator */}
        {loading && (
          <div className="loading-indicator">
            <div className="spinner"></div>
            <span>Loading responses...</span>
          </div>
        )}
      </div>

      {/* Detail Modal */}
      {showDetailModal && selectedResponse && (
        <ResponseDetailModal
          response={selectedResponse}
          onClose={() => {
            setShowDetailModal(false);
            setSelectedResponse(null);
          }}
        />
      )}
    </div>
  );
};

// Response Detail Modal Component
const ResponseDetailModal = ({ response, onClose }) => {
  const [activeTab, setActiveTab] = useState('overview');
  const [activePromptIndex, setActivePromptIndex] = useState(0);
  const [copySuccess, setCopySuccess] = useState('');
  const [leftPanelWidth, setLeftPanelWidth] = useState(50); // percentage
  const [isDragging, setIsDragging] = useState(false);
  const [showDocumentViewer, setShowDocumentViewer] = useState(false);
  const [viewingDocumentId, setViewingDocumentId] = useState(null);
  const containerRef = useRef(null);

  const handleCopy = (text, label) => {
    navigator.clipboard.writeText(text);
    setCopySuccess(label);
    setTimeout(() => setCopySuccess(''), 2000);
  };

  // Handle divider drag
  const handleMouseDown = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleMouseMove = useCallback((e) => {
    if (!isDragging || !containerRef.current) return;
    
    const container = containerRef.current;
    const containerRect = container.getBoundingClientRect();
    const containerWidth = containerRect.width;
    const relativeX = e.clientX - containerRect.left;
    const percentage = (relativeX / containerWidth) * 100;
    
    // Limit the width between 20% and 80%
    const newWidth = Math.min(Math.max(percentage, 20), 80);
    setLeftPanelWidth(newWidth);
  }, [isDragging]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Add and remove mouse event listeners
  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
      
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      };
    }
  }, [isDragging, handleMouseMove, handleMouseUp]);

  const handleViewDocument = (documentId) => {
    setViewingDocumentId(documentId);
    setShowDocumentViewer(true);
  };

  const formatJson = (json) => {
    try {
      const parsed = typeof json === 'string' ? JSON.parse(json) : json;
      return JSON.stringify(parsed, null, 2);
    } catch {
      return json;
    }
  };

  // Parse response JSON for better display
  const parseResponseData = () => {
    try {
      if (!response.response_json) return null;
      const data = typeof response.response_json === 'string' 
        ? JSON.parse(response.response_json) 
        : response.response_json;
      return data;
    } catch {
      return null;
    }
  };

  // Format the analysis text into readable sections
  const formatAnalysisText = (text) => {
    if (!text) return 'No analysis available';
    
    // Split by common section markers
    const sections = text.split(/(?=\d+\.|##|###|\n\n)/g).filter(s => s.trim());
    
    return sections.map((section, idx) => {
      // Check if it's a heading
      if (section.match(/^##?\s/)) {
        return <h5 key={idx} className="analysis-heading">{section.replace(/^##?\s/, '')}</h5>;
      }
      // Check if it's a numbered point
      if (section.match(/^\d+\./)) {
        return <p key={idx} className="analysis-point">{section}</p>;
      }
      // Regular paragraph
      return <p key={idx} className="analysis-paragraph">{section}</p>;
    });
  };

  // Parse prompts array from response data
  const getPromptsArray = () => {
    const responseData = parseResponseData();
    
    // Check for results array (new format)
    if (responseData?.results && Array.isArray(responseData.results)) {
      return responseData.results.map((result, index) => ({
        prompt: result.prompt,
        description: result.prompt ? result.prompt.substring(0, 50) + (result.prompt.length > 50 ? '...' : '') : `Prompt ${index + 1}`,
        response: result.response || '',
        status: result.status,
        error_message: result.error_message,
        input_tokens: result.input_tokens,
        output_tokens: result.output_tokens,
        time_taken_seconds: result.time_taken_seconds
      }));
    }
    
    // Check for raw_data.results array
    if (responseData?.raw_data?.results && Array.isArray(responseData.raw_data.results)) {
      return responseData.raw_data.results.map((result, index) => ({
        prompt: result.prompt,
        description: result.prompt ? result.prompt.substring(0, 50) + (result.prompt.length > 50 ? '...' : '') : `Prompt ${index + 1}`,
        response: result.response || '',
        status: result.status,
        error_message: result.error_message,
        input_tokens: result.input_tokens,
        output_tokens: result.output_tokens,
        time_taken_seconds: result.time_taken_seconds
      }));
    }
    
    // Check for prompts array (old format)
    if (responseData?.prompts && Array.isArray(responseData.prompts)) {
      return responseData.prompts;
    }
    
    // Fallback to single prompt if available
    if (response.prompt) {
      return [{
        prompt: response.prompt.prompt_text,
        description: response.prompt.description,
        response: response.response_text
      }];
    }
    
    return [];
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="response-detail-modal" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="modal-header">
          <div className="modal-title">
            <h3>📄 Response Details</h3>
            <span className="response-id">ID: {response.id}</span>
          </div>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        {/* Tab Navigation */}
        <div className="modal-tabs">
          <button 
            className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            📊 Overview
          </button>
          <button 
            className={`tab-btn ${activeTab === 'response' ? 'active' : ''}`}
            onClick={() => setActiveTab('response')}
          >
            💬 Response
          </button>
          <button 
            className={`tab-btn ${activeTab === 'metadata' ? 'active' : ''}`}
            onClick={() => setActiveTab('metadata')}
          >
            📋 Metadata
          </button>
          <button 
            className={`tab-btn ${activeTab === 'technical' ? 'active' : ''}`}
            onClick={() => setActiveTab('technical')}
          >
            🔧 Technical
          </button>
        </div>

        {/* Tab Content */}
        <div className="modal-content">
          {activeTab === 'overview' && (
            <div className="tab-content overview-tab">
              {/* Status and Score */}
              <div className="detail-section">
                <h4>📈 Status & Performance</h4>
                <div className="detail-grid">
                  <div className="detail-item">
                    <label>Status</label>
                    <div className={`status-badge ${response.status?.toLowerCase()}`}>
                      {response.status}
                    </div>
                  </div>
                  {response.overall_score !== null && (
                    <div className="detail-item">
                      <label>Suitability Score</label>
                      <div className="score-display">
                        <div className="score-bar">
                          <div 
                            className="score-fill" 
                            style={{width: `${response.overall_score}%`}}
                          />
                        </div>
                        <span className="score-text">{Math.round(response.overall_score)}/100</span>
                      </div>
                    </div>
                  )}
                  {response.response_time_ms && (
                    <div className="detail-item">
                      <label>Response Time</label>
                      <value>{(response.response_time_ms / 1000).toFixed(2)}s</value>
                    </div>
                  )}
                  {(response.input_tokens || response.output_tokens) && (
                    <div className="detail-item">
                      <label>Token Usage</label>
                      <value>
                        {response.input_tokens || 0} in / {response.output_tokens || 0} out
                      </value>
                    </div>
                  )}
                </div>
              </div>

              {/* Document Info */}
              <div className="detail-section">
                <h4>📄 Document Information</h4>
                <div className="detail-grid">
                  <div className="detail-item full-width">
                    <label>Filename</label>
                    <value>{response.document?.filename || 'Unknown'}</value>
                  </div>
                  <div className="detail-item full-width">
                    <label>Path</label>
                    <value className="small">{response.document?.filepath || 'N/A'}</value>
                  </div>
                  <div className="detail-item">
                    <label>Document Type</label>
                    <value>{response.document?.doc_type || response.doc_type || 'Unknown'}</value>
                  </div>
                  <div className="detail-item">
                    <label>Size</label>
                    <value>{formatFileSize(response.document?.file_size || response.file_size)}</value>
                  </div>
                  {(response.document?.id || response.doc_eval_document_id) && (
                    <div className="detail-item">
                      <label>Actions</label>
                      <button 
                        className="view-document-btn"
                        onClick={() => handleViewDocument(response.document?.id || response.doc_eval_document_id)}
                      >
                        📄 View Document
                      </button>
                    </div>
                  )}
                  {response.batch_id && (
                    <div className="detail-item">
                      <label>Batch</label>
                      <value>#{response.batch_id} - {response.batch_name || 'Unnamed'}</value>
                    </div>
                  )}
                </div>
              </div>

              {/* Connection Info */}
              <div className="detail-section">
                <h4>🤖 Model & Connection</h4>
                <div className="detail-grid">
                  <div className="detail-item">
                    <label>Connection</label>
                    <value>{response.connection?.name || 'Unknown'}</value>
                  </div>
                  <div className="detail-item">
                    <label>Model</label>
                    <value>{response.connection?.model_name || 'Unknown'}</value>
                  </div>
                  <div className="detail-item">
                    <label>Provider</label>
                    <value>{response.connection?.provider_type || 'Unknown'}</value>
                  </div>
                </div>
              </div>

              {/* Prompt Info */}
              <div className="detail-section">
                <h4>📝 Prompt</h4>
                <div className="detail-grid">
                  <div className="detail-item full-width">
                    <label>Description</label>
                    <value>{response.prompt?.description || 'No description'}</value>
                  </div>
                  {response.prompt?.prompt_text && (
                    <div className="detail-item full-width">
                      <label>Prompt Text</label>
                      <div className="prompt-text-box">
                        {response.prompt.prompt_text}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Timestamps */}
              <div className="detail-section">
                <h4>🕐 Timeline</h4>
                <div className="detail-grid">
                  <div className="detail-item">
                    <label>Created</label>
                    <value>{new Date(response.created_at).toLocaleString()}</value>
                  </div>
                  {response.started_processing_at && (
                    <div className="detail-item">
                      <label>Started</label>
                      <value>{new Date(response.started_processing_at).toLocaleString()}</value>
                    </div>
                  )}
                  {response.completed_processing_at && (
                    <div className="detail-item">
                      <label>Completed</label>
                      <value>{new Date(response.completed_processing_at).toLocaleString()}</value>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'response' && (
            <div className="tab-content response-tab">
              {response.error_message ? (
                <div className="error-response">
                  <h4>❌ Error Message</h4>
                  <div className="error-content">{response.error_message}</div>
                </div>
              ) : (
                <>
                  {(() => {
                    const prompts = getPromptsArray();
                    const responseData = parseResponseData();
                    
                    // If we have multiple prompts, show them as tabs
                    if (prompts.length > 0) {
                      const currentPrompt = prompts[activePromptIndex] || prompts[0];
                      
                      return (
                        <>
                          {/* Prompt Tabs - show for all prompts with label */}
                          <div className="prompt-tabs-section">
                            <h4 className="prompts-section-label">📝 Prompts</h4>
                            <div className="prompt-tabs">
                              {prompts.map((prompt, index) => (
                                <button
                                  key={index}
                                  className={`prompt-tab-btn ${activePromptIndex === index ? 'active' : ''}`}
                                  onClick={() => setActivePromptIndex(index)}
                                >
                                  <span className="prompt-tab-icon">📝</span>
                                  <span className="prompt-tab-text">
                                    {prompt.description || `Prompt ${index + 1}`}
                                  </span>
                                </button>
                              ))}
                            </div>
                          </div>
                          
                          {/* Prompt Form UI with resizable panels */}
                          <div className="prompt-form-container resizable" ref={containerRef}>
                            {/* Prompt Details Form */}
                            <div className="prompt-details-form" style={{ width: `${leftPanelWidth}%` }}>
                              <h4>📋 Prompt Details</h4>
                              
                              <div className="form-group">
                                <label className="form-label">Prompt ID</label>
                                <div className="form-value">{response.prompt_id || 'N/A'}</div>
                              </div>
                              
                              <div className="form-group">
                                <label className="form-label">Description</label>
                                <div className="form-value">
                                  {currentPrompt.description || response.prompt?.description || 'No description'}
                                </div>
                              </div>
                              
                              <div className="form-group full-width">
                                <label className="form-label">Prompt Text</label>
                                <div className="form-textarea">
                                  {currentPrompt.prompt || response.prompt?.prompt_text || 'No prompt text'}
                                </div>
                              </div>
                              
                              {/* Model Information */}
                              {response.connection && (
                                <>
                                  <div className="form-group">
                                    <label className="form-label">Model</label>
                                    <div className="form-value">
                                      {response.connection.model_name || 'Unknown'}
                                    </div>
                                  </div>
                                  
                                  <div className="form-group">
                                    <label className="form-label">Provider</label>
                                    <div className="form-value">
                                      {response.connection.provider_type || 'Unknown'}
                                    </div>
                                  </div>
                                </>
                              )}
                            </div>
                            
                            {/* Resizable Divider */}
                            <div 
                              className="resize-divider vertical"
                              onMouseDown={handleMouseDown}
                              style={{ cursor: isDragging ? 'col-resize' : 'ew-resize' }}
                            >
                              <div className="divider-handle"></div>
                            </div>
                            
                            {/* Response Section */}
                            <div className="prompt-response-section" style={{ width: `${100 - leftPanelWidth}%` }}>
                              <div className="section-header">
                                <h4>💬 Response</h4>
                                <button 
                                  className="copy-btn-small"
                                  onClick={() => handleCopy(currentPrompt.response || response.response_text || '', 'Response')}
                                >
                                  {copySuccess === 'Response' ? '✅' : '📋'}
                                </button>
                              </div>
                              
                              {/* Always show the prompt's response first */}
                              <div className="response-content-section">
                                <h5>Response Content</h5>
                                {currentPrompt.error_message ? (
                                  <div className="error-response">
                                    <div className="error-content">{currentPrompt.error_message}</div>
                                  </div>
                                ) : (
                                  <div className="response-raw-text">
                                    {/* The response is in response.response_text for single responses */}
                                    {formatAnalysisText(
                                      response.response_text || 
                                      currentPrompt.response || 
                                      response.response ||
                                      (responseData && responseData.response) ||
                                      (responseData && responseData.raw_data && responseData.raw_data.response) ||
                                      (responseData && responseData.raw_data && responseData.raw_data.results && responseData.raw_data.results[activePromptIndex] && responseData.raw_data.results[activePromptIndex].response) ||
                                      (responseData && responseData.results && responseData.results[activePromptIndex] && responseData.results[activePromptIndex].response) ||
                                      'No response available'
                                    )}
                                  </div>
                                )}
                              </div>

                              {/* Additional structured data if available */}
                              {responseData && responseData.raw_data && (
                                <>
                                  {/* Scoring if available */}
                                  {responseData.raw_data.scoring_result && (
                                    <div className="response-scoring">
                                      <h5>Scores</h5>
                                      {responseData.raw_data.scoring_result.overall_score !== undefined && (
                                        <div className="inline-score">
                                          <span className="score-label">Overall Score:</span>
                                          <span className="score-value">{responseData.raw_data.scoring_result.overall_score}/100</span>
                                        </div>
                                      )}
                                    </div>
                                  )}
                                  
                                      {/* Metrics */}
                                  <div className="response-metrics">
                                    <h5>Metrics</h5>
                                    <div className="inline-metrics">
                                      {(currentPrompt.input_tokens || responseData.raw_data.input_tokens) && (
                                        <div className="metric">
                                          <span className="metric-label">Input:</span>
                                          <span className="metric-value">{currentPrompt.input_tokens || responseData.raw_data.input_tokens} tokens</span>
                                        </div>
                                      )}
                                      {(currentPrompt.output_tokens || responseData.raw_data.output_tokens) && (
                                        <div className="metric">
                                          <span className="metric-label">Output:</span>
                                          <span className="metric-value">{currentPrompt.output_tokens || responseData.raw_data.output_tokens} tokens</span>
                                        </div>
                                      )}
                                      {(currentPrompt.time_taken_seconds || responseData.raw_data.time_taken_seconds) && (
                                        <div className="metric">
                                          <span className="metric-label">Time:</span>
                                          <span className="metric-value">{(currentPrompt.time_taken_seconds || responseData.raw_data.time_taken_seconds).toFixed(2)}s</span>
                                        </div>
                                      )}
                                      {currentPrompt.status && (
                                        <div className="metric">
                                          <span className="metric-label">Status:</span>
                                          <span className="metric-value">{currentPrompt.status}</span>
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                </>
                              )}
                            </div>
                          </div>
                        </>
                      );
                    }
                    
                    // Fallback if no prompts array
                    return (
                      <div className="response-text-container">
                        <div className="section-header">
                          <h4>💬 Response</h4>
                          <button 
                            className="copy-btn-small"
                            onClick={() => handleCopy(response.response_text || '', 'Response')}
                          >
                            {copySuccess === 'Response' ? '✅' : '📋'}
                          </button>
                        </div>
                        <div className="response-text-formatted">
                          {formatAnalysisText(response.response_text || 'No response text available')}
                        </div>
                      </div>
                    );
                  })()}
                </>
              )}
            </div>
          )}

          {activeTab === 'metadata' && (
            <div className="tab-content metadata-tab">
              <div className="metadata-grid">
                {/* IDs */}
                <div className="metadata-section">
                  <h4>🔑 Identifiers</h4>
                  <div className="metadata-items">
                    <div className="metadata-item">
                      <label>Response ID</label>
                      <value>{response.id}</value>
                    </div>
                    <div className="metadata-item">
                      <label>Document ID</label>
                      <value>{response.document_id || response.kb_document_id}</value>
                    </div>
                    <div className="metadata-item">
                      <label>Task ID</label>
                      <value className="small">{response.task_id || 'N/A'}</value>
                    </div>
                    <div className="metadata-item">
                      <label>Batch ID</label>
                      <value>{response.batch_id || 'N/A'}</value>
                    </div>
                  </div>
                </div>

                {/* Connection Details */}
                {response.connection_details && (
                  <div className="metadata-section">
                    <h4>🔌 Connection Configuration</h4>
                    <pre className="json-display">
                      {formatJson(response.connection_details)}
                    </pre>
                  </div>
                )}

                {/* Scoring Details */}
                {(() => {
                  const responseData = parseResponseData();
                  if (responseData?.raw_data?.scoring_result) {
                    const scoring = responseData.raw_data.scoring_result;
                    return (
                      <div className="metadata-section">
                        <h4>📊 Detailed Scoring Analysis</h4>
                        
                        {/* Overall Score */}
                        {scoring.overall_score !== undefined && (
                          <div className="metadata-overall-score">
                            <div className="score-header">
                              <span className="score-title">Overall Suitability Score</span>
                              <span className="score-number">{scoring.overall_score}/100</span>
                            </div>
                            <div className="score-visual">
                              <div className="score-bar">
                                <div 
                                  className="score-fill"
                                  style={{
                                    width: `${scoring.overall_score}%`,
                                    background: scoring.overall_score >= 80 ? '#4caf50' : 
                                               scoring.overall_score >= 60 ? '#ff9800' : '#f44336'
                                  }}
                                />
                              </div>
                            </div>
                            {scoring.overall_comment && (
                              <p className="score-explanation">{scoring.overall_comment}</p>
                            )}
                          </div>
                        )}
                        
                        {/* Category Scores */}
                        {scoring.subscores && (
                          <div className="metadata-subscores">
                            <h5>Category Breakdown</h5>
                            {Object.entries(scoring.subscores).map(([category, details]) => (
                              <div key={category} className="metadata-subscore">
                                <div className="subscore-info">
                                  <span className="subscore-name">
                                    {category.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                                  </span>
                                  <span className={`subscore-score ${
                                    details.score >= 80 ? 'high' : 
                                    details.score >= 60 ? 'medium' : 'low'
                                  }`}>
                                    {details.score}/100
                                  </span>
                                </div>
                                <div className="subscore-visual">
                                  <div className="subscore-bar">
                                    <div 
                                      className="subscore-fill"
                                      style={{
                                        width: `${details.score}%`,
                                        background: details.score >= 80 ? '#4caf50' : 
                                                   details.score >= 60 ? '#ff9800' : '#f44336'
                                      }}
                                    />
                                  </div>
                                </div>
                                {details.comment && (
                                  <p className="subscore-explanation">{details.comment}</p>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  }
                  return null;
                })()}
              </div>
            </div>
          )}

          {activeTab === 'technical' && (
            <div className="tab-content technical-tab">
              <div className="technical-actions">
                <button 
                  className="copy-btn"
                  onClick={() => handleCopy(JSON.stringify(response, null, 2), 'Technical')}
                >
                  {copySuccess === 'Technical' ? '✅ Copied!' : '📋 Copy All Data'}
                </button>
              </div>
              
              <h4>🔧 Complete Response Object</h4>
              <pre className="technical-json">
                {JSON.stringify(response, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
      
      {/* Document Viewer Modal */}
      {showDocumentViewer && viewingDocumentId && (
        <DocumentViewer
          documentId={viewingDocumentId}
          onClose={() => {
            setShowDocumentViewer(false);
            setViewingDocumentId(null);
          }}
        />
      )}
    </div>
  );
};

export default LlmResponsesViewer;