// This is a fixed version snippet showing how to disable non-working buttons
// Add this to your BatchDetails component in BatchManagement.jsx

// In the button section, update the buttons to show they're deprecated:

{batch.status === 'STAGED' && (
  <button
    disabled={true}
    className="btn btn-secondary btn-sm"
    title="This functionality has been moved to KnowledgeDocuments system"
  >
    {actionLoading === 'run-analysis' ? '⏳' : '▶️'} Run Analysis (Deprecated)
  </button>
)}

{batch.status === 'COMPLETED' && (
  <>
    <button
      disabled={true}
      className="btn btn-secondary btn-sm"
      title="This functionality has been moved to KnowledgeDocuments system"
    >
      {actionLoading === 'rerun-analysis' ? '⏳' : '🔄'} Rerun Analysis (Deprecated)
    </button>
    <button
      disabled={true}
      className="btn btn-warning btn-sm"
      title="This functionality has been moved to KnowledgeDocuments system"
    >
      {actionLoading === 'restage-and-rerun' ? '⏳' : '🔄📄'} Restage & Rerun (Deprecated)
    </button>
  </>
)}

// Add a message explaining the situation:
{(batch.status === 'SAVED' || batch.status === 'STAGED' || batch.status === 'COMPLETED') && (
  <div className="alert alert-info" style={{ marginTop: '10px' }}>
    <strong>Note:</strong> LLM processing has been moved to the KnowledgeDocuments system. 
    Use external tools to process this batch or contact your administrator for the new workflow.
  </div>
)}