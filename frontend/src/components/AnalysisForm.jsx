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
      setError(err.response?.data?.error || 'Failed to submit analysis');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card analysis-form">
      <div className="form-icon">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
        </svg>
      </div>
      
      <div className="card-header">
        <h2 className="card-title">Analyze Repository</h2>
        <p className="card-subtitle">
          Submit a GitHub repository for comprehensive AI-powered code review covering security, performance, and best practices
        </p>
      </div>
      
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label className="form-label">
            GitHub Repository URL
          </label>
          <input
            type="url"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            placeholder="https://github.com/username/repository"
            className="form-input"
            required
          />
        </div>

        {error && (
          <div className="error-message">
            <svg width="20" height="20" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd"/>
            </svg>
            <span>{error}</span>
          </div>
        )}

        <button type="submit" disabled={loading} className="submit-button">
          <span className="button-content">
            {loading ? (
              <>
                <span className="spinner"></span>
                Analyzing Repository...
              </>
            ) : (
              
              
                   'Start AI Analysis'
              
            )}
          </span>
        </button>

        <div className="form-stats">
          <div className="stat-item">
            <div className="stat-value">Security</div>
            <div className="stat-label">Check</div>
          </div>
          <div className="stat-item">
            <div className="stat-value">Performance</div>
            <div className="stat-label">Analysis</div>
          </div>
          <div className="stat-item">
            <div className="stat-value">Quality</div>
            <div className="stat-label">Review</div>
          </div>
        </div>
      </form>
    </div>
  );
}

export default AnalysisForm;