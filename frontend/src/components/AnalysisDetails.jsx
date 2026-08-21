import { useState } from 'react';
import '../styles/AnalysisDetails.css';

function AnalysisDetails({ analysis }) {
  const [isOpen, setIsOpen] = useState(false);

  if (!analysis.score && analysis.status !== 'completed') {
    return null;
  }

  return (
    <div className="details-wrapper">
      <button 
        type="button"
        onClick={() => setIsOpen(!isOpen)} 
        className="details-toggle-btn"
      >
        <svg 
          className={`toggle-caret ${isOpen ? 'is-open' : ''}`}
          width="14" 
          height="14" 
          viewBox="0 0 24 24" 
          fill="none" 
          stroke="currentColor" 
          strokeWidth="2" 
          strokeLinecap="round" 
          strokeLinejoin="round"
        >
          <polyline points="9 18 15 12 9 6" />
        </svg>
        <span>{isOpen ? 'Hide findings' : `View ${analysis.issues?.length || 0} findings`}</span>
      </button>

      {isOpen && (
        <div className="details-expanded-panel">
          {analysis.issues && analysis.issues.length > 0 ? (
            <div className="findings-table">
              {analysis.issues.map((issue, idx) => (
                <div key={idx} className="finding-row">
                  <div className="finding-main">
                    <div className="finding-header">
                      <span className={`finding-tag tag-${issue.severity?.toLowerCase()}`}>
                        {issue.severity}
                      </span>
                      <span className="finding-category">
                        {issue.type?.replace('_', ' ')}
                      </span>
                      {issue.file && (
                        <code className="finding-file-badge">
                          {issue.file}{issue.line ? `:${issue.line}` : ''}
                        </code>
                      )}
                    </div>

                    <p className="finding-title">{issue.message}</p>
                    
                    {issue.recommendation && (
                      <p className="finding-recommendation">{issue.recommendation}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}

export default AnalysisDetails;