/**
 * API client for document processing
 */

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:5000';

/**
 * Start asynchronous document processing
 * @param {string} folderPath - Path to the folder to process
 * @returns {Promise<Object>} - Response with task_id
 */
export const startProcessingAsync = async (folderPath) => {
  try {
    const response = await fetch(`${API_BASE_URL}/process_documents_async`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ folder_path: folderPath }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to start processing');
    }

    return response.json();
  } catch (error) {
    console.error('Error starting document processing:', error);
    throw error;
  }
};

/**
 * Get status of an asynchronous processing task
 * @param {string} taskId - Task ID returned from startProcessingAsync
 * @returns {Promise<Object>} - Task status information
 */
export const getProcessingStatus = async (taskId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/process_status/${taskId}`);

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to get processing status');
    }

    return response.json();
  } catch (error) {
    console.error('Error getting processing status:', error);
    throw error;
  }
};

/**
 * Poll for processing status until completion or failure
 * @param {string} taskId - Task ID returned from startProcessingAsync
 * @param {function} onProgress - Callback function for progress updates
 * @param {number} interval - Polling interval in milliseconds (default: 2000)
 * @returns {Promise<Object>} - Final task status
 */
export const pollProcessingStatus = async (taskId, onProgress, interval = 2000) => {
  return new Promise((resolve, reject) => {
    const poll = async () => {
      try {
        const status = await getProcessingStatus(taskId);

        // Call progress callback
        if (onProgress && typeof onProgress === 'function') {
          onProgress(status);
        }

        // Check if processing is complete
        if (status.status === 'COMPLETED') {
          resolve(status);
          return;
        }

        // Check if processing failed
        if (status.status === 'FAILED') {
          reject(new Error(status.error || 'Processing failed'));
          return;
        }

        // Continue polling
        setTimeout(poll, interval);
      } catch (error) {
        reject(error);
      }
    };

    // Start polling
    poll();
  });
};
