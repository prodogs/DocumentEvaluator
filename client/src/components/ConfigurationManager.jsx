import React, { useState, useEffect } from 'react';
import axios from 'axios';

import PromptManager from './PromptManager';
import '../styles/configuration.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001';

const ConfigurationManager = ({ onPromptsChange }) => {
  const [stats, setStats] = useState({
    totalPrompts: 0,
    activePrompts: 0
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      setLoading(true);

      // Load prompts stats
      const promptsResponse = await axios.get(`${API_BASE_URL}/api/prompts`);
      const prompts = promptsResponse.data.prompts || [];

      setStats({
        totalPrompts: prompts.length,
        activePrompts: prompts.filter(p => p.active).length
      });
    } catch (error) {
      console.error('Error loading stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDataChange = () => {
    loadStats();
    if (onPromptsChange) onPromptsChange();
  };

  return (
    <div className="configuration-manager">
      {/* Hero Section */}
      <div className="config-hero">
        <div className="hero-content">
          <h1 className="hero-title">
            <span className="hero-icon">📝</span>
            Prompt Management
          </h1>
          <p className="hero-subtitle">
            Create and manage prompts for intelligent document processing
          </p>
        </div>

        {/* Stats Dashboard */}
        <div className="config-stats">
          <div className="stat-card prompts">
            <div className="stat-icon">📝</div>
            <div className="stat-content">
              <div className="stat-number">{loading ? '...' : stats.totalPrompts}</div>
              <div className="stat-label">Total Prompts</div>
              <div className="stat-detail">{loading ? '...' : stats.activePrompts} active</div>
            </div>
          </div>
        </div>
      </div>

      {/* Prompt Management Content */}
      <div className="config-content">
        <PromptManager onPromptsChange={handleDataChange} />
      </div>
    </div>
  );
};

export default ConfigurationManager;
