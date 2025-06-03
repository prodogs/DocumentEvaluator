import React, { useState, useEffect } from 'react';
import axios from 'axios';
import '../styles/document-viewer.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001';

const DocumentViewer = ({ documentId, onClose }) => {
  const [document, setDocument] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [viewMode, setViewMode] = useState('auto'); // auto, text, html, pdf, image, download

  useEffect(() => {
    if (documentId) {
      loadDocument();
    }
  }, [documentId]);

  const loadDocument = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await axios.get(`${API_BASE_URL}/api/documents/${documentId}`);
      
      if (response.data.success) {
        const doc = response.data.document;
        setDocument(doc);
        
        // Determine the best view mode based on file type
        const fileExt = doc.doc_type?.toLowerCase() || '';
        const fileName = doc.filename?.toLowerCase() || '';
        
        if (fileExt === 'pdf' || fileName.endsWith('.pdf')) {
          setViewMode('pdf');
        } else if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'].includes(fileExt) || 
                   fileName.match(/\.(jpg|jpeg|png|gif|bmp|webp|svg)$/)) {
          setViewMode('image');
        } else if (['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'].includes(fileExt) || 
                   fileName.match(/\.(doc|docx|xls|xlsx|ppt|pptx)$/)) {
          setViewMode('office');
        } else if (['html', 'htm'].includes(fileExt) || fileName.match(/\.(html|htm)$/)) {
          setViewMode('html');
        } else if (doc.is_binary) {
          setViewMode('download');
        } else {
          setViewMode('text');
        }
      } else {
        setError(response.data.error || 'Failed to load document');
      }
    } catch (err) {
      console.error('Error loading document:', err);
      setError(err.message || 'Error loading document');
    } finally {
      setLoading(false);
    }
  };

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

  const downloadDocument = () => {
    if (!document) return;
    
    // Create a download link
    const link = window.document.createElement('a');
    link.href = `${API_BASE_URL}/api/documents/${documentId}/download`;
    link.download = document.filename || 'document';
    link.target = '_blank';
    window.document.body.appendChild(link);
    link.click();
    window.document.body.removeChild(link);
  };

  const renderDocumentContent = () => {
    if (!document) return null;

    switch (viewMode) {
      case 'pdf':
        const pdfUrl = document.base64_content ? 
          `data:application/pdf;base64,${document.base64_content}` : 
          document.filepath ? `${API_BASE_URL}/api/documents/${documentId}/view` : null;
        
        return (
          <div className="pdf-viewer">
            {pdfUrl ? (
              <>
                <div className="viewer-toolbar">
                  <div className="toolbar-info">
                    <span>📑 {document.filename}</span>
                  </div>
                  <div className="toolbar-actions">
                    <button 
                      onClick={() => window.open(pdfUrl, '_blank')} 
                      className="fullscreen-btn"
                      title="Open in new tab for full browser PDF viewer"
                    >
                      🔳 Full Screen
                    </button>
                    <button onClick={downloadDocument} className="download-btn">
                      📥 Download
                    </button>
                  </div>
                </div>
                <iframe
                  src={pdfUrl}
                  width="100%"
                  height="100%"
                  title={document.filename}
                  className="pdf-iframe"
                />
              </>
            ) : (
              <div className="viewer-message">
                <p>PDF preview not available</p>
                <button onClick={downloadDocument} className="download-btn">
                  📥 Download PDF
                </button>
              </div>
            )}
          </div>
        );

      case 'image':
        return (
          <div className="image-viewer">
            {document.base64_content ? (
              <img
                src={`data:${document.mime_type || 'image/jpeg'};base64,${document.base64_content}`}
                alt={document.filename}
                style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
              />
            ) : (
              <div className="viewer-message">
                <p>Image preview not available</p>
                <button onClick={downloadDocument} className="download-btn">
                  📥 Download Image
                </button>
              </div>
            )}
          </div>
        );

      case 'office':
        // For Office documents, we can use Google Docs Viewer or Office Online
        const officeViewerUrl = document.filepath ? 
          `https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(`${window.location.origin}${API_BASE_URL}/api/documents/${documentId}/download`)}` :
          null;
        
        return (
          <div className="office-viewer">
            {officeViewerUrl && viewMode === 'office' ? (
              <>
                <div className="viewer-toolbar">
                  <div className="toolbar-info">
                    <span>📄 {document.filename}</span>
                    <span className="viewer-notice">Using Microsoft Office Online Viewer</span>
                  </div>
                  <div className="toolbar-actions">
                    <button onClick={() => setViewMode('office-fallback')} className="fallback-btn">
                      ⚠️ Not loading? Try alternative view
                    </button>
                    <button onClick={downloadDocument} className="download-btn">
                      📥 Download
                    </button>
                  </div>
                </div>
                <iframe
                  src={officeViewerUrl}
                  width="100%"
                  height="100%"
                  frameBorder="0"
                  title={document.filename}
                  className="office-iframe"
                />
              </>
            ) : (
              <div className="viewer-message">
                <div className="office-icon">
                  {document.doc_type === 'DOCX' || document.doc_type === 'DOC' ? '📄' :
                   document.doc_type === 'XLSX' || document.doc_type === 'XLS' ? '📊' :
                   document.doc_type === 'PPTX' || document.doc_type === 'PPT' ? '📊' : '📎'}
                </div>
                <h3>Microsoft Office Document</h3>
                <p>Online preview requires a publicly accessible URL</p>
                <div className="office-actions">
                  <button onClick={downloadDocument} className="download-btn primary">
                    📥 Download {document.doc_type}
                  </button>
                  {document.content && (
                    <button onClick={() => setViewMode('text')} className="view-text-btn">
                      📝 View Extracted Text
                    </button>
                  )}
                  <button 
                    onClick={() => window.open(`https://docs.google.com/viewer?url=${encodeURIComponent(`${window.location.origin}${API_BASE_URL}/api/documents/${documentId}/download`)}&embedded=true`, '_blank')} 
                    className="google-viewer-btn"
                  >
                    🔍 Try Google Docs Viewer
                  </button>
                </div>
              </div>
            )}
          </div>
        );

      case 'html':
        return (
          <div className="html-viewer">
            {document.content ? (
              <iframe
                srcDoc={document.content}
                width="100%"
                height="100%"
                title={document.filename}
                sandbox="allow-same-origin"
              />
            ) : (
              <div className="viewer-message">
                <p>HTML preview not available</p>
                <button onClick={() => setViewMode('text')} className="view-text-btn">
                  📝 View as Text
                </button>
              </div>
            )}
          </div>
        );

      case 'text':
        return (
          <div className="text-viewer">
            <pre className="document-text">
              {document.content || 'No text content available'}
            </pre>
          </div>
        );

      case 'download':
        return (
          <div className="download-viewer">
            <div className="viewer-message">
              <div className="binary-icon">📦</div>
              <h3>Binary File</h3>
              <p>This file cannot be displayed in the browser</p>
              <button onClick={downloadDocument} className="download-btn primary">
                📥 Download File
              </button>
            </div>
          </div>
        );

      default:
        return (
          <div className="text-viewer">
            <pre className="document-text">
              {document.content || document.base64_content ? 
                (document.content || atob(document.base64_content)) : 
                'Document content not available'}
            </pre>
          </div>
        );
    }
  };

  if (loading) {
    return (
      <div className="document-viewer-modal">
        <div className="document-viewer">
          <div className="viewer-loading">
            <div className="spinner"></div>
            <p>Loading document...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="document-viewer-modal">
        <div className="document-viewer">
          <div className="viewer-header">
            <h2>Document Viewer</h2>
            <button className="close-btn" onClick={onClose}>✕</button>
          </div>
          <div className="viewer-error">
            <p>❌ {error}</p>
            <button onClick={loadDocument} className="retry-btn">🔄 Retry</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="document-viewer-modal" onClick={onClose}>
      <div className="document-viewer" onClick={(e) => e.stopPropagation()}>
        <div className="viewer-header">
          <div className="header-info">
            <h2>📄 {document?.filename || 'Document'}</h2>
            <div className="doc-meta">
              <span className="doc-type">{document?.doc_type || 'Unknown'}</span>
              <span className="doc-size">{formatFileSize(document?.file_size)}</span>
              <span className="doc-id">ID: {documentId}</span>
            </div>
          </div>
          <div className="header-actions">
            <div className="view-mode-selector">
              {viewMode !== 'office' && viewMode !== 'download' && (
                <>
                  {document?.content && (
                    <button
                      className={`mode-btn ${viewMode === 'text' ? 'active' : ''}`}
                      onClick={() => setViewMode('text')}
                      title="Text View"
                    >
                      📝
                    </button>
                  )}
                  {(document?.doc_type === 'PDF' || document?.filename?.toLowerCase().endsWith('.pdf')) && (
                    <button
                      className={`mode-btn ${viewMode === 'pdf' ? 'active' : ''}`}
                      onClick={() => setViewMode('pdf')}
                      title="PDF View"
                    >
                      📑
                    </button>
                  )}
                  {['HTML', 'HTM'].includes(document?.doc_type) && (
                    <button
                      className={`mode-btn ${viewMode === 'html' ? 'active' : ''}`}
                      onClick={() => setViewMode('html')}
                      title="HTML View"
                    >
                      🌐
                    </button>
                  )}
                </>
              )}
              <button
                className="mode-btn"
                onClick={downloadDocument}
                title="Download"
              >
                📥
              </button>
            </div>
            <button className="close-btn" onClick={onClose}>✕</button>
          </div>
        </div>
        
        <div className="viewer-content">
          {renderDocumentContent()}
        </div>
        
        {document?.filepath && (
          <div className="viewer-footer">
            <span className="file-path" title={document.filepath}>
              📁 {document.filepath}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export default DocumentViewer;