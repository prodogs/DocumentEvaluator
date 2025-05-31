import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import './styles/management.css';
import './styles/batch-dashboard.css';
import './styles/models-providers.css';
import './styles/staging.css';
import './styles/configuration.css';
import './styles/folders.css';

import ModelsAndProvidersManager from './components/ModelsAndProvidersManager';
import StagingManager from './components/StagingManager';
import ConfigurationManager from './components/ConfigurationManager';
import FoldersManager from './components/FoldersManager';
import PromptManager from './components/PromptManager';
import FolderManager from './components/FolderManager';
import BatchDashboard from './components/BatchDashboard';
import BatchManagement from './components/BatchManagement';

// Use environment variable for API URL, fallback to localhost:5001
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001';
console.log('🔧 API_BASE_URL configured as:', API_BASE_URL);

function App() {
  // Document processing state
  const [totalDocuments, setTotalDocuments] = useState(0);
  const [processedDocuments, setProcessedDocuments] = useState(0);
  const [outstandingDocuments, setOutstandingDocuments] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [errors, setErrors] = useState([]);
  const [showErrorModal, setShowErrorModal] = useState(false);
  const [message, setMessage] = useState('Ready to process documents.');
  const [taskId, setTaskId] = useState(null);
  const [pollingInterval, setPollingInterval] = useState(null); // Track polling interval

  // Configuration state
  const [connections, setConnections] = useState([]);
  const [llmProviders, setLlmProviders] = useState([]);
  const [prompts, setPrompts] = useState([]);
  const [folders, setFolders] = useState([]);
  const [selectedConnections, setSelectedConnections] = useState([]);
  const [selectedPrompts, setSelectedPrompts] = useState([]);
  const [selectedFolders, setSelectedFolders] = useState([]);

  // Batch state
  const [batches, setBatches] = useState([]);
  const [currentBatch, setCurrentBatch] = useState(null);
  const [batchName, setBatchName] = useState('');
  const [batchMetaData, setBatchMetaData] = useState('');

  // UI state
  const [activeTab, setActiveTab] = useState('dashboard'); // 'dashboard', 'process', 'config', 'providers', 'folders', 'batches'
  const [showConfigModal, setShowConfigModal] = useState(false);

  // Accordion state for Analyze Documents page
  const [accordionState, setAccordionState] = useState({
    llmConfigs: true,
    prompts: true,
    folders: true
  });

  // Toggle accordion sections
  const toggleAccordion = (section) => {
    setAccordionState(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  // Load configuration data on component mount
  useEffect(() => {
    // Clear any invalid task IDs and polling intervals on mount
    if (!taskId || taskId === 'null' || taskId === null) {
      setTaskId(null);
      setIsProcessing(false);
    }

    // Clear any existing polling intervals
    if (pollingInterval) {
      clearInterval(pollingInterval);
      setPollingInterval(null);
    }

    loadConnections();
    loadPrompts();
    loadFolders();
    loadCurrentBatch(false, 'component-mount');

    // Cleanup function to clear intervals on unmount
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  }, []);

  // Load batches when batches tab is selected
  useEffect(() => {
    if (activeTab === 'batches') {
      loadBatches();
    }
  }, [activeTab]);

  // Load staging data when staging tab is selected
  useEffect(() => {
    if (activeTab === 'process') {
      console.log('Staging tab selected - loading connections, prompts, folders, and current batch');
      loadConnections();
      loadPrompts();
      loadFolders();
      loadCurrentBatch();
    }
  }, [activeTab]);

  const loadConnections = async () => {
    try {
      console.log('Loading connections from:', `${API_BASE_URL}/api/connections`);
      const response = await axios.get(`${API_BASE_URL}/api/connections`);
      console.log('Connections response:', response.data);

      // Only show active connections
      const activeConnections = (response.data.connections || []).filter(connection => connection.is_active === true);
      console.log('Filtered active connections:', activeConnections);
      setConnections(activeConnections);
      // Don't auto-select - let user choose for each batch
      setSelectedConnections([]);
      setMessage(`Loaded ${activeConnections.length} active connections`);
    } catch (error) {
      console.error('Error loading connections:', error);
      setMessage(`Error loading connections: ${error.message}`);
    }
  };

  const loadPrompts = async () => {
    try {
      console.log('Loading prompts from:', `${API_BASE_URL}/api/prompts`);
      const response = await axios.get(`${API_BASE_URL}/api/prompts`);
      console.log('Prompts response:', response.data);
      // Only show active prompts
      const activePrompts = (response.data.prompts || []).filter(prompt => prompt.active === true);
      setPrompts(activePrompts);
      // Don't auto-select - let user choose for each batch
      setSelectedPrompts([]);
      setMessage(`Loaded ${activePrompts.length} active prompts`);
    } catch (error) {
      console.error('Error loading prompts:', error);
      setMessage(`Error loading prompts: ${error.message}`);
    }
  };

  const loadFolders = async () => {
    try {
      console.log('Loading folders from:', `${API_BASE_URL}/api/folders`);
      const response = await axios.get(`${API_BASE_URL}/api/folders`);
      console.log('Folders response:', response.data);
      // Only show active folders in Analyze Documents tab
      const activeFolders = (response.data.folders || []).filter(folder => folder.active === true);
      console.log('Active folders filtered:', activeFolders);
      setFolders(activeFolders);
      // Don't auto-select - let user choose for each batch
      setSelectedFolders([]);
      setMessage(`Loaded ${activeFolders.length} active folders`);
    } catch (error) {
      console.error('Error loading folders:', error);
      setMessage('Error loading folders');
    }
  };

  const loadCurrentBatch = async (skipIfPending = false, source = 'unknown') => {
    try {
      console.log(`loadCurrentBatch called from: ${source}, skipIfPending: ${skipIfPending}, pendingUpdate:`, pendingBatchUpdate);

      // Skip loading if we have a pending update and skipIfPending is true
      if (skipIfPending && pendingBatchUpdate) {
        console.log('Skipping current batch load due to pending update');
        return;
      }

      const response = await axios.get(`${API_BASE_URL}/api/batches/current`);
      const serverBatch = response.data.current_batch;

      console.log(`Server batch status: ${serverBatch?.status}, Current batch status: ${currentBatch?.status}`);

      // If we have a pending update, only update if the server status matches our expectation
      if (pendingBatchUpdate && serverBatch && serverBatch.id === pendingBatchUpdate.batchId) {
        console.log(`Checking pending update: server=${serverBatch.status}, expected=${pendingBatchUpdate.expectedStatus}`);
        if (serverBatch.status === pendingBatchUpdate.expectedStatus) {
          // Server status matches our expectation, clear pending update
          console.log('Server status matches expectation, updating batch');
          setPendingBatchUpdate(null);
          setCurrentBatch(serverBatch);
        } else {
          // Server status doesn't match, keep our immediate update for now
          console.log(`Server status (${serverBatch.status}) doesn't match expected (${pendingBatchUpdate.expectedStatus}), keeping immediate update`);
          return;
        }
      } else if (pendingBatchUpdate) {
        // We have a pending update but for a different batch or no server batch
        console.log('Pending update exists but batch ID mismatch or no server batch, keeping current state');
        return;
      } else {
        // No pending update, use server data
        console.log('No pending update, using server data');
        setCurrentBatch(serverBatch);
      }
    } catch (error) {
      console.error('Error loading current batch:', error);
    }
  };

  const loadBatches = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/batches?limit=20`);
      setBatches(response.data.batches || []);
    } catch (error) {
      console.error('Error loading batches:', error);
    }
  };

  const resetBatchConfiguration = () => {
    // Reset all batch configuration fields
    setBatchName('');
    setBatchMetaData('');
    setSelectedConnections([]);
    setSelectedPrompts([]);
    setSelectedFolders([]);
  };

  const saveAnalysis = async () => {
    // Enhanced validation with better error messages
    if (connections.length === 0) {
      alert('No active connections available. Please go to the Models & Providers tab to add and activate connections.');
      return;
    }

    if (selectedConnections.length === 0) {
      alert('Please select at least one connection for this batch.');
      return;
    }

    if (prompts.length === 0) {
      alert('No active prompts available. Please go to the Prompts tab to add and activate prompts.');
      return;
    }

    if (selectedPrompts.length === 0) {
      alert('Please select at least one prompt for this batch.');
      return;
    }

    if (folders.length === 0) {
      alert('No active folders available. Please go to the Folders tab to add and activate folders.');
      return;
    }

    if (selectedFolders.length === 0) {
      alert('Please select at least one folder for this batch.');
      return;
    }

    if (!batchName.trim()) {
      alert('Please enter a batch name for this submission.');
      return;
    }

    // Validate JSON metadata if provided
    let parsedMetaData = null;
    if (batchMetaData.trim()) {
      try {
        parsedMetaData = JSON.parse(batchMetaData.trim());
      } catch (error) {
        alert('Invalid JSON in metadata field. Please check your JSON syntax.');
        return;
      }
    }

    setMessage('Saving analysis configuration...');

    try {
      const requestBody = {
        batch_name: batchName.trim(),
        folder_ids: selectedFolders,
        llm_config_ids: selectedConnections, // ✅ FIX: Send selected connections (LLM configs)
        prompt_ids: selectedPrompts, // ✅ FIX: Send selected prompts
        action: 'save' // Indicate this is a save operation
      };

      // Add meta_data if provided
      if (parsedMetaData) {
        requestBody.meta_data = parsedMetaData;
      }

      const response = await axios.post(`${API_BASE_URL}/api/batches/save`, requestBody, {
        headers: {
          'Content-Type': 'application/json',
        },
      });

      // Show success message and reset configuration
      setMessage(`✅ Analysis saved successfully: ${response.data.message}`);

      // Reset batch configuration after successful save
      setTimeout(() => {
        resetBatchConfiguration();
        setMessage('✅ Analysis saved! Configuration has been reset for your next batch.');
      }, 1500);

      loadCurrentBatch(); // Refresh current batch info
    } catch (error) {
      console.error('Error saving analysis:', error);
      setMessage(`❌ Error: ${error.response?.data?.message || error.message}`);
    }
  };

  const stageAnalysis = async () => {
    // Enhanced validation with better error messages
    if (connections.length === 0) {
      alert('No active connections available. Please go to the Models & Providers tab to add and activate connections.');
      return;
    }

    if (selectedConnections.length === 0) {
      alert('Please select at least one connection for this batch.');
      return;
    }

    if (prompts.length === 0) {
      alert('No active prompts available. Please go to the Prompts tab to add and activate prompts.');
      return;
    }

    if (selectedPrompts.length === 0) {
      alert('Please select at least one prompt for this batch.');
      return;
    }

    if (folders.length === 0) {
      alert('No active folders available. Please go to the Folders tab to add and activate folders.');
      return;
    }

    if (selectedFolders.length === 0) {
      alert('Please select at least one folder for this batch.');
      return;
    }

    if (!batchName.trim()) {
      alert('Please enter a batch name for this submission.');
      return;
    }

    // Validate JSON metadata if provided
    let parsedMetaData = null;
    if (batchMetaData.trim()) {
      try {
        parsedMetaData = JSON.parse(batchMetaData.trim());
      } catch (error) {
        alert('Invalid JSON in metadata field. Please check your JSON syntax.');
        return;
      }
    }

    setIsProcessing(true);
    setMessage('Starting staging process...');

    try {
      const requestBody = {
        batch_name: batchName.trim(),
        folder_ids: selectedFolders,
        llm_config_ids: selectedConnections, // ✅ FIX: Send selected connections (LLM configs)
        prompt_ids: selectedPrompts, // ✅ FIX: Send selected prompts
        action: 'stage' // Indicate this is a stage operation
      };

      // Add meta_data if provided
      if (parsedMetaData) {
        requestBody.meta_data = parsedMetaData;
      }

      const response = await axios.post(`${API_BASE_URL}/api/batches/stage`, requestBody, {
        headers: {
          'Content-Type': 'application/json',
        },
      });

      // Show success message and reset configuration
      setMessage(`✅ Staging started successfully: ${response.data.message}`);
      setTotalDocuments(response.data.totalFiles || 0);

      // Reset batch configuration after successful staging
      setTimeout(() => {
        resetBatchConfiguration();
        setMessage('✅ Staging started! Configuration has been reset for your next batch.');
      }, 2000);

      // Ensure task_id is properly handled - don't set if null or "null"
      const taskId = response.data.task_id;
      if (taskId && taskId !== 'null' && taskId !== null) {
        setTaskId(taskId);
        startPolling();
      } else {
        console.log('No valid task ID returned from server, not starting polling');
        setTaskId(null);
        setIsProcessing(false);
      }
      loadCurrentBatch(); // Refresh current batch info
    } catch (error) {
      console.error('Error staging analysis:', error);
      setMessage(`❌ Error: ${error.response?.data?.message || error.message}`);
      setIsProcessing(false);
    }
  };

  const startFolderProcessing = async () => {
    // Enhanced validation with better error messages
    if (connections.length === 0) {
      alert('No active connections available. Please go to the Models & Providers tab to add and activate connections.');
      return;
    }

    if (selectedConnections.length === 0) {
      alert('Please select at least one connection for this batch.');
      return;
    }

    if (prompts.length === 0) {
      alert('No active prompts available. Please go to the Prompts tab to add and activate prompts.');
      return;
    }

    if (selectedPrompts.length === 0) {
      alert('Please select at least one prompt for this batch.');
      return;
    }

    if (folders.length === 0) {
      alert('No active folders available. Please go to the Folders tab to add and activate folders.');
      return;
    }

    if (selectedFolders.length === 0) {
      alert('Please select at least one folder for this batch.');
      return;
    }

    if (!batchName.trim()) {
      alert('Please enter a batch name for this submission.');
      return;
    }

    // Validate JSON metadata if provided
    let parsedMetaData = null;
    if (batchMetaData.trim()) {
      try {
        parsedMetaData = JSON.parse(batchMetaData.trim());
      } catch (error) {
        alert('Invalid JSON in metadata field. Please check your JSON syntax.');
        return;
      }
    }

    setIsProcessing(true);
    setMessage('Starting folder processing...');

    try {
      const requestBody = {
        batch_name: batchName.trim(),
        folder_ids: selectedFolders
      };

      // Add meta_data if provided
      if (parsedMetaData) {
        requestBody.meta_data = parsedMetaData;
      }

      const response = await axios.post(`${API_BASE_URL}/process-db-folders`, requestBody, {
        headers: {
          'Content-Type': 'application/json',
        },
      });
      setMessage(response.data.message);
      setTotalDocuments(response.data.totalFiles || 0);

      // Ensure task_id is properly handled - don't set if null or "null"
      const taskId = response.data.task_id;
      if (taskId && taskId !== 'null' && taskId !== null) {
        setTaskId(taskId);
        startPolling();
      } else {
        console.log('No valid task ID returned from server, not starting polling');
        setTaskId(null);
        setIsProcessing(false);
      }
      loadCurrentBatch(); // Refresh current batch info
    } catch (error) {
      console.error('Error starting processing:', error);
      setMessage(`Error: ${error.response?.data?.message || error.message}`);
      setIsProcessing(false);
    }
  };

  const stopProcessing = () => {
    // In a real application, you'd send a signal to the backend to stop processing
    // For this example, we'll just stop the frontend polling and reset state

    // Clear any active polling interval
    if (pollingInterval) {
      clearInterval(pollingInterval);
      setPollingInterval(null);
    }

    setIsProcessing(false);
    setMessage('Processing stopped by user.');
    // Optionally, clear progress and errors
    setProcessedDocuments(0);
    setOutstandingDocuments(0);
    setTotalDocuments(0);
    setErrors([]);
    setTaskId(null);
  };

  const [batchActionLoading, setBatchActionLoading] = useState(null); // Track which action is loading
  const [pendingBatchUpdate, setPendingBatchUpdate] = useState(null); // Track pending status updates

  const pauseBatch = async (batchId) => {
    setBatchActionLoading('pause');
    setMessage('Pausing batch...');

    try {
      const response = await axios.post(`${API_BASE_URL}/api/batches/${batchId}/pause`);
      if (response.data.success) {
        setMessage(`Batch paused: ${response.data.message}`);
        // Immediately update current batch status for instant feedback
        if (currentBatch && currentBatch.id === batchId) {
          setCurrentBatch({ ...currentBatch, status: 'PA' });
          // Set pending update to track expected status
          setPendingBatchUpdate({ batchId, expectedStatus: 'PA' });

          // Clear pending update after 10 seconds to prevent it from being stuck
          setTimeout(() => {
            setPendingBatchUpdate(null);
          }, 10000);
        }
        // Delay server refresh to allow backend to update
        setTimeout(() => {
          loadCurrentBatch(false, 'pause-action-delayed');
        }, 6000); // 6 second delay to allow backend to update and avoid dashboard interference
      } else {
        setMessage(`Error pausing batch: ${response.data.error}`);
      }
    } catch (error) {
      console.error('Error pausing batch:', error);
      setMessage(`Error pausing batch: ${error.response?.data?.error || error.message}`);
    } finally {
      setBatchActionLoading(null);
    }
  };

  const resumeBatch = async (batchId) => {
    setBatchActionLoading('resume');
    setMessage('Resuming batch...');

    try {
      const response = await axios.post(`${API_BASE_URL}/api/batches/${batchId}/resume`);
      if (response.data.success) {
        setMessage(`Batch resumed: ${response.data.message}`);
        // Immediately update current batch status for instant feedback
        if (currentBatch && currentBatch.id === batchId) {
          setCurrentBatch({ ...currentBatch, status: 'P' });
          // Set pending update to track expected status
          setPendingBatchUpdate({ batchId, expectedStatus: 'P' });

          // Clear pending update after 10 seconds to prevent it from being stuck
          setTimeout(() => {
            setPendingBatchUpdate(null);
          }, 10000);
        }
        // Delay server refresh to allow backend to update
        setTimeout(() => {
          loadCurrentBatch(false, 'resume-action-delayed');
        }, 6000); // 6 second delay to allow backend to update and avoid dashboard interference
      } else {
        setMessage(`Error resuming batch: ${response.data.error}`);
      }
    } catch (error) {
      console.error('Error resuming batch:', error);
      setMessage(`Error resuming batch: ${error.response?.data?.error || error.message}`);
    } finally {
      setBatchActionLoading(null);
    }
  };

  const fetchProgress = async () => {
    if (!taskId || taskId === 'null' || taskId === null) {
      console.log('No valid task ID available, skipping progress fetch');
      return;
    }

    try {
      const response = await axios.get(`${API_BASE_URL}/analyze_status/${taskId}`);
      setProcessedDocuments(response.data.processedDocuments);
      setOutstandingDocuments(response.data.outstandingDocuments);
      // Only update totalDocuments if it's not already set or if it changes
      if (totalDocuments === 0 || response.data.totalDocuments > totalDocuments) {
        setTotalDocuments(response.data.totalDocuments);
      }
      if (response.data.processedDocuments === response.data.totalDocuments && response.data.totalDocuments > 0) {
        setIsProcessing(false);
        setMessage('All documents processed!');
        loadCurrentBatch(false, 'processing-complete'); // Refresh batch info when complete
      }
    } catch (error) {
      console.error('Error fetching progress:', error);
      // If we get a 400 error (likely invalid task ID), stop processing
      if (error.response?.status === 400) {
        console.log('Invalid task ID, stopping processing');
        setIsProcessing(false);
        setTaskId(null);
        setMessage('Processing stopped due to invalid task ID');
      } else {
        setMessage(`Error fetching progress: ${error.message}`);
      }
    }
  };

  const fetchErrors = async () => {
    try {
      // Use the new dedicated errors endpoint
      const response = await axios.get(`${API_BASE_URL}/api/errors`);
      setErrors(response.data.errors || []);
    } catch (error) {
      console.error('Error fetching errors:', error);
      setMessage(`Error fetching errors: ${error.message}`);
    }
  };

  const startPolling = () => {
    if (!taskId || taskId === 'null' || taskId === null) {
      console.log('No valid task ID available, cannot start polling');
      return () => { }; // Return empty cleanup function
    }

    // Clear any existing polling interval
    if (pollingInterval) {
      clearInterval(pollingInterval);
    }

    const interval = setInterval(() => {
      // Double-check task ID is still valid before polling
      if (taskId && taskId !== 'null' && taskId !== null) {
        fetchProgress();
        fetchErrors();
      } else {
        console.log('Task ID became invalid, stopping polling');
        clearInterval(interval);
        setPollingInterval(null);
        setIsProcessing(false);
      }
      if (!isProcessing && processedDocuments === totalDocuments && totalDocuments > 0) {
        clearInterval(interval); // Stop polling when all done
        setPollingInterval(null);
      }
    }, 3000); // Poll every 3 seconds

    setPollingInterval(interval);
    return () => {
      clearInterval(interval);
      setPollingInterval(null);
    }; // Cleanup on unmount
  };

  useEffect(() => {
    if (isProcessing && taskId && taskId !== 'null' && taskId !== null) {
      const cleanup = startPolling();
      return cleanup;
    }
  }, [isProcessing, processedDocuments, totalDocuments, taskId]); // Re-run effect if processing state or counts change

  const handleShowErrors = () => {
    fetchErrors(); // Ensure latest errors are fetched
    setShowErrorModal(true);
  };

  const handleCloseErrorModal = () => {
    setShowErrorModal(false);
  };

  // Clear selections when switching to Analyze Documents tab for fresh batch submission
  const handleTabChange = (newTab) => {
    if (newTab === 'process' && activeTab !== 'process') {
      // Clear selections for fresh batch submission
      setSelectedConnections([]);
      setSelectedPrompts([]);
      setSelectedFolders([]);
      setBatchName('');
      setBatchMetaData('');
    }
    setActiveTab(newTab);
  };

  return (
    <div className={`App ${activeTab === 'batches' ? 'full-width' : ''}`}>
      {activeTab !== 'batches' && (
        <>
          <div className="banner-container">
            <img src="/banner2.png" alt="Document Batch Processor" className="banner-image" />
            <div className="banner-text-overlay">
              <h1 className="banner-title">Knowledge Sync</h1>
              <p className="banner-subtitle">Creating Intelligence from Enterprise Knowledge</p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="tabs">
            <button
              className={activeTab === 'dashboard' ? 'tab active' : 'tab'}
              onClick={() => handleTabChange('dashboard')}
            >
              📊 Dashboard
            </button>
            <button
              className={activeTab === 'process' ? 'tab active' : 'tab'}
              onClick={() => handleTabChange('process')}
            >
              🎯 Staging
            </button>
            <button
              className={activeTab === 'config' ? 'tab active' : 'tab'}
              onClick={() => handleTabChange('config')}
            >
              📝 Prompts
            </button>
            <button
              className={activeTab === 'models' ? 'tab active' : 'tab'}
              onClick={() => handleTabChange('models')}
            >
              🤖 Models
            </button>
            <button
              className={activeTab === 'folders' ? 'tab active' : 'tab'}
              onClick={() => handleTabChange('folders')}
            >
              📁 Folders
            </button>
            <button
              className={activeTab === 'batches' ? 'tab active' : 'tab'}
              onClick={() => handleTabChange('batches')}
            >
              📦 Batches
            </button>
          </div>

          {activeTab === 'dashboard' && (
            <BatchDashboard />
          )}

          {activeTab === 'process' && (
            <StagingManager
              batchName={batchName}
              setBatchName={setBatchName}
              batchMetaData={batchMetaData}
              setBatchMetaData={setBatchMetaData}
              connections={connections}
              prompts={prompts}
              folders={folders}
              selectedConnections={selectedConnections}
              setSelectedConnections={setSelectedConnections}
              selectedPrompts={selectedPrompts}
              setSelectedPrompts={setSelectedPrompts}
              selectedFolders={selectedFolders}
              setSelectedFolders={setSelectedFolders}
              currentBatch={currentBatch}
              isProcessing={isProcessing}
              onSaveAnalysis={saveAnalysis}
              onStageAnalysis={stageAnalysis}
              pauseBatch={pauseBatch}
              resumeBatch={resumeBatch}
              batchActionLoading={batchActionLoading}
            />
          )}

          {activeTab === 'config' && (
            <ConfigurationManager
              onPromptsChange={() => loadPrompts()}
            />
          )}

          {activeTab === 'models' && (
            <div className="models-tab">
              <ModelsAndProvidersManager onProvidersChange={setLlmProviders} />
            </div>
          )}

          {activeTab === 'folders' && (
            <FoldersManager onFoldersChange={() => loadFolders()} />
          )}

          {activeTab === 'process' && (
            <div className="status">
              <p>Status: {message}</p>
              <p>Files Processed: {processedDocuments} / {totalDocuments}</p>
              <p>Outstanding Tasks: {outstandingDocuments}</p>
            </div>
          )}

          {showErrorModal && (
            <div className="modal-overlay">
              <div className="modal-content">
                <h2>Processing Errors</h2>
                {errors.length === 0 ? (
                  <p>No errors to display.</p>
                ) : (
                  <ul>
                    {errors.map((error, index) => (
                      <li key={`error-${index}`}>
                        <strong>File:</strong> {error.filename || 'Unknown'} <br />
                        <strong>LLM:</strong> {error.llm_name || 'Unknown'} <br />
                        <strong>Prompt:</strong> {error.prompt_text ? error.prompt_text.substring(0, 50) + '...' : 'Unknown'} <br />
                        <strong>Error:</strong> {error.error_message || error} <br />
                        <strong>Time:</strong> {error.timestamp ? new Date(error.timestamp).toLocaleString() : 'Unknown'} <br />
                      </li>
                    ))}
                  </ul>
                )}
                <button onClick={handleCloseErrorModal}>Close</button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Batch Management - Full Screen */}
      {activeTab === 'batches' && (
        <BatchManagement onNavigateBack={() => setActiveTab('dashboard')} />
      )}
    </div>
  );
}

export default App;
