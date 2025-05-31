import React, { useState, useEffect } from 'react';
import '../styles/analyze-documents.css';

const AnalyzeDocumentsManager = ({
  batchName,
  setBatchName,
  batchMetaData,
  setBatchMetaData,
  llmConfigs,
  prompts,
  folders,
  selectedLlmConfigs,
  setSelectedLlmConfigs,
  selectedPrompts,
  setSelectedPrompts,
  selectedFolders,
  setSelectedFolders,
  currentBatch,
  isProcessing,
  startFolderProcessing,
  stopProcessing,
  pauseBatch,
  resumeBatch,
  batchActionLoading,
  errors,
  handleShowErrors
}) => {
  const [stats, setStats] = useState({
    totalConfigs: 0,
    selectedConfigs: 0,
    totalPrompts: 0,
    selectedPrompts: 0,
    totalFolders: 0,
    selectedFolders: 0
  });

  useEffect(() => {
    setStats({
      totalConfigs: llmConfigs.length,
      selectedConfigs: selectedLlmConfigs.length,
      totalPrompts: prompts.length,
      selectedPrompts: selectedPrompts.length,
      totalFolders: folders.length,
      selectedFolders: selectedFolders.length
    });
  }, [llmConfigs, prompts, folders, selectedLlmConfigs, selectedPrompts, selectedFolders]);

  const handleConfigToggle = (configId) => {
    if (selectedLlmConfigs.includes(configId)) {
      setSelectedLlmConfigs(selectedLlmConfigs.filter(id => id !== configId));
    } else {
      setSelectedLlmConfigs([...selectedLlmConfigs, configId]);
    }
  };

  const handlePromptToggle = (promptId) => {
    if (selectedPrompts.includes(promptId)) {
      setSelectedPrompts(selectedPrompts.filter(id => id !== promptId));
    } else {
      setSelectedPrompts([...selectedPrompts, promptId]);
    }
  };

  const handleFolderToggle = (folderId) => {
    if (selectedFolders.includes(folderId)) {
      setSelectedFolders(selectedFolders.filter(id => id !== folderId));
    } else {
      setSelectedFolders([...selectedFolders, folderId]);
    }
  };

  const canStartProcessing = selectedLlmConfigs.length > 0 && 
                           selectedPrompts.length > 0 && 
                           selectedFolders.length > 0 && 
                           batchName.trim() && 
                           !isProcessing;

  return (
    <div className="analyze-documents-manager">
      {/* Hero Section */}
      <div className="analyze-hero">
        <div className="hero-content">
          <h1 className="hero-title">
            <span className="hero-icon">🔍</span>
            Document Analysis
          </h1>
          <p className="hero-subtitle">
            Configure and execute intelligent document processing with AI models
          </p>
        </div>
        
        {/* Stats Dashboard */}
        <div className="analyze-stats">
          <div className="stat-card configs">
            <div className="stat-icon">🤖</div>
            <div className="stat-content">
              <div className="stat-number">{stats.selectedConfigs}/{stats.totalConfigs}</div>
              <div className="stat-label">LLM Configs</div>
              <div className="stat-detail">Selected</div>
            </div>
          </div>
          
          <div className="stat-card prompts">
            <div className="stat-icon">📝</div>
            <div className="stat-content">
              <div className="stat-number">{stats.selectedPrompts}/{stats.totalPrompts}</div>
              <div className="stat-label">Prompts</div>
              <div className="stat-detail">Selected</div>
            </div>
          </div>
          
          <div className="stat-card folders">
            <div className="stat-icon">📁</div>
            <div className="stat-content">
              <div className="stat-number">{stats.selectedFolders}/{stats.totalFolders}</div>
              <div className="stat-label">Folders</div>
              <div className="stat-detail">Selected</div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="analyze-content">
        {/* Batch Configuration */}
        <div className="batch-config-section">
          <div className="config-card">
            <h3>Batch Configuration</h3>
            <div className="batch-inputs">
              <div className="input-group">
                <label htmlFor="batch-name">Batch Name</label>
                <input
                  id="batch-name"
                  type="text"
                  value={batchName}
                  onChange={(e) => setBatchName(e.target.value)}
                  placeholder="Enter batch name..."
                  disabled={isProcessing}
                  className="batch-name-input"
                />
              </div>
              
              <div className="input-group">
                <label htmlFor="batch-metadata">Metadata (JSON)</label>
                <textarea
                  id="batch-metadata"
                  value={batchMetaData}
                  onChange={(e) => setBatchMetaData(e.target.value)}
                  placeholder='Optional JSON metadata for LLM context, e.g., {"project": "analysis", "version": "1.0"}'
                  disabled={isProcessing}
                  rows={4}
                  className="batch-metadata-input"
                />
                <small className="input-hint">
                  This JSON will be sent to the LLM for additional context during document processing.
                </small>
              </div>
            </div>
          </div>
        </div>

        {/* Selection Grid */}
        <div className="selection-grid">
          {/* LLM Configurations */}
          <div className="selection-section">
            <div className="section-header">
              <h3>🤖 LLM Configurations</h3>
              <span className="selection-count">{selectedLlmConfigs.length} selected</span>
            </div>
            
            <div className="selection-cards">
              {llmConfigs.length === 0 ? (
                <div className="no-items">
                  <p>⚠️ No active LLM configurations found.</p>
                  <p>Please go to the <strong>⚙️ Configuration</strong> tab to add configurations.</p>
                </div>
              ) : (
                llmConfigs.map(config => (
                  <div 
                    key={config.id} 
                    className={`selection-card ${selectedLlmConfigs.includes(config.id) ? 'selected' : ''}`}
                    onClick={() => handleConfigToggle(config.id)}
                  >
                    <div className="card-header">
                      <span className="card-title">{config.llm_name}</span>
                      <span className="card-badge">{config.provider_type}</span>
                    </div>
                    <div className="card-details">
                      <span>Model: {config.model_name}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Prompts */}
          <div className="selection-section">
            <div className="section-header">
              <h3>📝 Prompts</h3>
              <span className="selection-count">{selectedPrompts.length} selected</span>
            </div>
            
            <div className="selection-cards">
              {prompts.length === 0 ? (
                <div className="no-items">
                  <p>⚠️ No active prompts found.</p>
                  <p>Please go to the <strong>⚙️ Configuration</strong> tab to add prompts.</p>
                </div>
              ) : (
                prompts.map(prompt => (
                  <div 
                    key={prompt.id} 
                    className={`selection-card ${selectedPrompts.includes(prompt.id) ? 'selected' : ''}`}
                    onClick={() => handlePromptToggle(prompt.id)}
                  >
                    <div className="card-header">
                      <span className="card-title">
                        {prompt.description || 'Untitled Prompt'}
                      </span>
                    </div>
                    <div className="card-details">
                      <span>{prompt.prompt_text.substring(0, 80)}...</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Folders */}
          <div className="selection-section">
            <div className="section-header">
              <h3>📁 Folders</h3>
              <span className="selection-count">{selectedFolders.length} selected</span>
            </div>
            
            <div className="selection-cards">
              {folders.length === 0 ? (
                <div className="no-items">
                  <p>⚠️ No folders found.</p>
                  <p>Please go to the <strong>📁 Folders</strong> tab to add folders.</p>
                </div>
              ) : (
                folders.map(folder => (
                  <div 
                    key={folder.id} 
                    className={`selection-card ${selectedFolders.includes(folder.id) ? 'selected' : ''}`}
                    onClick={() => handleFolderToggle(folder.id)}
                  >
                    <div className="card-header">
                      <span className="card-title">
                        {folder.folder_name || folder.folder_path.split('/').pop()}
                      </span>
                    </div>
                    <div className="card-details">
                      <span>{folder.folder_path}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Current Batch Info */}
        {currentBatch && (
          <div className="current-batch-section">
            <div className="batch-info-card">
              <h4>Current Batch: {currentBatch.batch_name}</h4>
              <div className="batch-status">
                <span className={`status-badge ${currentBatch.status.toLowerCase()}`}>
                  {currentBatch.status === 'P' ? 'Processing' : 
                   currentBatch.status === 'PA' ? 'Paused' : 
                   currentBatch.status === 'C' ? 'Completed' : currentBatch.status}
                </span>
                <span className="batch-date">
                  Created: {new Date(currentBatch.created_at).toLocaleString()}
                </span>
              </div>
              
              <div className="batch-actions">
                {currentBatch.status === 'P' && (
                  <button
                    onClick={() => pauseBatch(currentBatch.id)}
                    disabled={batchActionLoading === 'pause'}
                    className="btn btn-warning"
                  >
                    {batchActionLoading === 'pause' ? '⏳ Pausing...' : '⏸️ Pause Batch'}
                  </button>
                )}
                {currentBatch.status === 'PA' && (
                  <button
                    onClick={() => resumeBatch(currentBatch.id)}
                    disabled={batchActionLoading === 'resume'}
                    className="btn btn-success"
                  >
                    {batchActionLoading === 'resume' ? '⏳ Resuming...' : '▶️ Resume Batch'}
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Control Panel */}
        <div className="control-panel">
          <button
            onClick={startFolderProcessing}
            disabled={!canStartProcessing}
            className={`btn btn-primary btn-large ${canStartProcessing ? 'pulse' : ''}`}
          >
            🚀 Start Document Analysis
          </button>
          
          <button 
            onClick={stopProcessing} 
            disabled={!isProcessing}
            className="btn btn-danger"
          >
            🛑 Stop Processing
          </button>
          
          <button 
            onClick={handleShowErrors} 
            disabled={errors.length === 0}
            className="btn btn-warning"
          >
            ⚠️ Errors ({errors.length})
          </button>
        </div>
      </div>
    </div>
  );
};

export default AnalyzeDocumentsManager;
