import { useState } from 'react';
import '../styles/AnalysisDetails.css';

function AnalysisDetails({ analysis }) {
  const [isOpen, setIsOpen] = useState(false);

  if (!analysis.score && analysis.status !== 'completed') {
    return null;
  }

  const getScoreSummary = (score) => {
    if (score >= 80) return 'High code health and best practice adherence.';
    if (score >= 60) return 'Acceptable quality with specific maintenance recommendations.';
    return 'Critical attention required across security or architecture areas.';
  };

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
        <span>{isOpen ? 'Hide breakdown' : 'View full breakdown'}</span>
      </button>

      {isOpen && (
        <div className="details-expanded-panel">
          <div className="metric-highlight-card">
            <div className="metric-score-group">
              <span className="metric-value">{analysis.score}</span>
              <span className="metric-base">/ 100</span>
            </div>
            <p className="metric-caption">{getScoreSummary(analysis.score)}</p>
          </div>

          {analysis.issues && analysis.issues.length > 0 && (
            <div className="findings-section">
              <div className="findings-header">
                <span className="findings-label">Detected Findings</span>
                <span className="findings-count">{analysis.issues.length}</span>
              </div>

              <div className="findings-list">
                {analysis.issues.map((issue, idx) => (
                  <div key={idx} className="finding-card">
                    <div className="finding-header">
                      <span className={`finding-tag tag-${issue.severity?.toLowerCase()}`}>
                        {issue.severity}
                      </span>
                      <span className="finding-category">
                        {issue.type?.replace('_', ' ')}
                      </span>
                    </div>

                    <p className="finding-message">{issue.message}</p>

                    {issue.file && (
                      <p className="finding-path">
                        {issue.file}{issue.line ? `:${issue.line}` : ''}
                      </p>
                    )}

                    {issue.recommendation && (
                      <div className="remediation-note">
                        <span className="remediation-title">Suggested fix</span>
                        <p className="remediation-body">{issue.recommendation}</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {analysis.recommendations && analysis.recommendations[0] && (
            <div className="summary-banner">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="16" x2="12" y2="12" />
                <line x1="12" y1="8" x2="12.01" y2="8" />
              </svg>
              <p>{analysis.recommendations[0]}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default AnalysisDetails;