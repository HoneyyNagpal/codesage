import { useState } from 'react';
import '../styles/AnalysisDetails.css';

function AnalysisDetails({ analysis }) {
  const [isOpen, setIsOpen] = useState(false);

  if (!analysis.score && analysis.status !== 'completed') {
    return null;
  }

  const getScoreText = (score) => {
    if (score >= 80) return 'Excellent - Outstanding code quality';
    if (score >= 60) return 'Good - Minor improvements recommended';
    return 'Needs Work - Several issues need attention';
  };

  return (
    <div>
      <button onClick={() => setIsOpen(!isOpen)} className="details-toggle">
        {isOpen ? '▼ Hide Analysis Details' : '▶ View Detailed Analysis'}
      </button>

      {isOpen && (
        <div className="details-content">
          {/* Score Card */}
          <div className="score-card">
            <h4>Overall Code Quality Score</h4>
            <div className="score-display">
              <span className="score-number">{analysis.score}</span>
              <span className="score-total">/100</span>
            </div>
            <p className="score-label">
              {getScoreText(analysis.score)}
            </p>
          </div>

          {/* Issues Section */}
          {analysis.issues && analysis.issues.length > 0 && (
            <div className="issues-section">
              <div className="issues-header">
                <h3 className="issues-title">Issues Found</h3>
                <span className="issues-badge">{analysis.issues.length}</span>
              </div>

              <div className="issues-list">
                {analysis.issues.map((issue, idx) => (
                  <div key={idx} className="issue-card">
                    <div className="issue-badges">
                      <span className={`severity-badge ${issue.severity}`}>
                        {issue.severity}
                      </span>
                      <span className="type-badge">
                        {issue.type.replace('_', ' ')}
                      </span>
                    </div>
                    
                    <h5 className="issue-message">{issue.message}</h5>
                    
                    <p className="issue-location">
                      {issue.file}:{issue.line}
                    </p>
                    
                    <div className="recommendation-box">
                      <p className="recommendation-title">Recommendation</p>
                      <p className="recommendation-text">{issue.recommendation}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Summary */}
          {analysis.recommendations && analysis.recommendations[0] && (
            <div className="summary-box">
              <p className="summary-text">
                {analysis.recommendations[0]}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default AnalysisDetails;