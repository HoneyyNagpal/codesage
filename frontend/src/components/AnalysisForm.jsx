import { useState } from 'react';
import { analysisAPI } from '../services/api';
import '../styles/AnalysisForm.css';

function AnalysisForm({ onSuccess }) {
  const [repoUrl, setRepoUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const result = await analysisAPI.submitAnalysis(repoUrl);
      onSuccess(result);
      setRepoUrl('');
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to submit repository for review');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="surface-card form-sticky">
      <div className="form-heading-area">
        <h2 className="section-heading">Analyze Repository</h2>
        <p className="section-subtext">Run a full static check covering architecture, security, and maintainability.</p>
      </div>

      <form onSubmit={handleSubmit} className="repository-form">
        <div className="field-group">
          <label htmlFor="repo-url" className="field-label">
            GitHub Repository URL
          </label>
          <div className="field-input-wrap">
            <svg className="field-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
            </svg>
            <input
              id="repo-url"
              type="url"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              placeholder="https://github.com/organization/repo"
              className="text-input"
              required
            />
          </div>
        </div>

        {error && (
          <div className="alert-box">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <span>{error}</span>
          </div>
        )}

        <button type="submit" disabled={loading} className="submit-action">
          {loading ? (
            <span className="btn-loading-state">
              <span className="inline-spinner" />
              Analyzing Repository...
            </span>
          ) : (
            'Start AI Analysis'
          )}
        </button>

        <div className="feature-badges-row">
          <div className="feature-pill">
            <span className="feature-dot dot-security" />
            <span>Security Audits</span>
          </div>
          <div className="feature-pill">
            <span className="feature-dot dot-perf" />
            <span>Performance</span>
          </div>
          <div className="feature-pill">
            <span className="feature-dot dot-quality" />
            <span>Clean Code</span>
          </div>
        </div>
      </form>
    </div>
  );
}

export default AnalysisForm;