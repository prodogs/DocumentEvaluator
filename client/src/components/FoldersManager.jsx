import React, { useState, useEffect } from 'react';
import axios from 'axios';
import FolderManager from './FolderManager';
import '../styles/folders.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001';

const FoldersManager = ({ onFoldersChange }) => {
  const [stats, setStats] = useState({
    totalFolders: 0,
    activeFolders: 0,
    totalFiles: 0,
    processedFiles: 0,
    totalSize: 0,
    avgFilesPerFolder: 0
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      setLoading(true);
      
      // Load folders stats
      const foldersResponse = await axios.get(`${API_BASE_URL}/api/folders`);
      const folders = foldersResponse.data.folders || [];
      
      // Calculate aggregated stats
      let totalFiles = 0;
      let processedFiles = 0;
      let totalSize = 0;
      
      for (const folder of folders) {
        if (folder.file_count) totalFiles += folder.file_count;
        if (folder.processed_count) processedFiles += folder.processed_count;
        if (folder.total_size) totalSize += folder.total_size;
      }
      
      const avgFilesPerFolder = folders.length > 0 ? Math.round(totalFiles / folders.length) : 0;

      setStats({
        totalFolders: folders.length,
        activeFolders: folders.filter(f => f.active !== false).length,
        totalFiles,
        processedFiles,
        totalSize,
        avgFilesPerFolder
      });
    } catch (error) {
      console.error('Error loading stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDataChange = () => {
    loadStats();
    if (onFoldersChange) onFoldersChange();
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <div className="folders-manager">
      {/* Hero Section */}
      <div className="folders-hero">
        <div className="hero-content">
          <h1 className="hero-title">
            <span className="hero-icon">📁</span>
            Document Folders
          </h1>
          <p className="hero-subtitle">
            Organize and manage document collections for intelligent processing
          </p>
        </div>
        
        {/* Stats Dashboard */}
        <div className="folders-stats">
          <div className="stat-card folders">
            <div className="stat-icon">📂</div>
            <div className="stat-content">
              <div className="stat-number">{loading ? '...' : stats.totalFolders}</div>
              <div className="stat-label">Total Folders</div>
              <div className="stat-detail">{loading ? '...' : stats.activeFolders} active</div>
            </div>
          </div>
          
          <div className="stat-card files">
            <div className="stat-icon">📄</div>
            <div className="stat-content">
              <div className="stat-number">{loading ? '...' : stats.totalFiles.toLocaleString()}</div>
              <div className="stat-label">Total Files</div>
              <div className="stat-detail">{loading ? '...' : stats.processedFiles.toLocaleString()} processed</div>
            </div>
          </div>
          
          <div className="stat-card storage">
            <div className="stat-icon">💾</div>
            <div className="stat-content">
              <div className="stat-number">{loading ? '...' : formatFileSize(stats.totalSize)}</div>
              <div className="stat-label">Storage Used</div>
              <div className="stat-detail">Avg {loading ? '...' : stats.avgFilesPerFolder} files/folder</div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="folders-content">
        <div className="folders-section">
          <FolderManager onFoldersChange={handleDataChange} />
        </div>
      </div>
    </div>
  );
};

export default FoldersManager;
