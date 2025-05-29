import React, { useState } from 'react';
import axios from 'axios';

// Use environment variable for API URL, fallback to localhost:5004
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5004';

const AsyncProcessingButton = ({ batchName, selectedLlmConfigs, selectedPrompts, onComplete, onError, onProgress }) => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [taskId, setTaskId] = useState(null);
  const [message, setMessage] = useState('');

  const handleStartProcessing = async () => {
    if (!batchName || !batchName.trim()) {
      alert('Please enter a batch name');
      return;
    }

    if (!selectedLlmConfigs || selectedLlmConfigs.length === 0) {
      alert('Please select at least one LLM configuration');
      return;
    }

    if (!selectedPrompts || selectedPrompts.length === 0) {
      alert('Please select at least one prompt');
      return;
    }

    try {
      setIsProcessing(true);
      setProgress(0);
      setMessage('Starting folder processing...');

      // Start processing and get task ID
      const response = await axios.post(`${API_BASE_URL}/process-db-folders`, {
        batch_name: batchName.trim()
      }, {
        headers: {
          'Content-Type': 'application/json',
        },
      });

      // Validate that we received a valid task ID
      if (!response.data.task_id) {
        throw new Error(response.data.message || 'No task ID received from server');
      }

      setTaskId(response.data.task_id);
      setMessage(response.data.message);

      // Start polling for status updates
      startPolling(response.data.task_id);

    } catch (error) {
      console.error('Processing failed:', error);
      setIsProcessing(false);
      setMessage(`Error: ${error.response?.data?.message || error.message}`);
      if (onError) onError(error.response?.data?.message || error.message);
    }
  };

  const startPolling = (taskId) => {
    // Validate task ID before starting polling
    if (!taskId || taskId === 'null' || taskId === 'undefined') {
      console.error('Invalid task ID for polling:', taskId);
      setIsProcessing(false);
      setMessage('Error: Invalid task ID received');
      if (onError) onError('Invalid task ID received');
      return;
    }

    const interval = setInterval(async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/analyze_status/${taskId}`);
        const { totalDocuments, processedDocuments, status, error_message } = response.data;

        const currentProgress = totalDocuments > 0 ? Math.round((processedDocuments / totalDocuments) * 100) : 0;
        setProgress(currentProgress);

        if (onProgress) {
          onProgress({
            totalDocuments,
            processedDocuments,
            progress: currentProgress,
            status
          });
        }

        if (status === 'COMPLETED' || processedDocuments === totalDocuments) {
          clearInterval(interval);
          setIsProcessing(false);
          setMessage('Processing completed!');
          if (onComplete) onComplete();
        } else if (status === 'ERROR' || error_message) {
          clearInterval(interval);
          setIsProcessing(false);
          setMessage(`Error: ${error_message}`);
          if (onError) onError(error_message);
        }
      } catch (error) {
        console.error('Error polling status:', error);
        clearInterval(interval);
        setIsProcessing(false);
        setMessage(`Error polling status: ${error.message}`);
        if (onError) onError(error.message);
      }
    }, 3000); // Poll every 3 seconds

    // Cleanup interval on component unmount
    return () => clearInterval(interval);
  };

  return (
    <div className="async-processing-container">
      <button
        onClick={handleStartProcessing}
        disabled={isProcessing || !batchName || !batchName.trim() || !selectedLlmConfigs || selectedLlmConfigs.length === 0 || !selectedPrompts || selectedPrompts.length === 0}
        className="processing-button"
      >
        {isProcessing ? 'Processing Folders...' : 'Start Folder Processing'}
      </button>

      {message && (
        <div className="message-container">
          <small>{message}</small>
        </div>
      )}

      {isProcessing && (
        <div className="progress-container">
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="progress-text">{Math.round(progress)}%</div>
        </div>
      )}

      {taskId && (
        <div className="task-id-container">
          <small>Task ID: {taskId}</small>
        </div>
      )}
    </div>
  );
};

export default AsyncProcessingButton;
