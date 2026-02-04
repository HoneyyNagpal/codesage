import { useState, useEffect } from 'react';
import { BrowserRouter } from 'react-router-dom';
import AnalysisForm from './components/AnalysisForm';
import AuthButton from './components/AuthButton';
import { analysisAPI } from './services/api';
import './styles/App.css';
import './styles/AnalysisList.css';
import AnalysisDetails from './components/AnalysisDetails';

function App() {
  const [analyses, setAnalyses] = useState([]);
  const [backendStatus, setBackendStatus] = useState('checking...');

  useEffect(() => {
    checkBackend();
    loadAnalyses();
    const interval = setInterval(loadAnalyses, 5000);
    return () => clearInterval(interval);
  }, []);

  const checkBackend = async () => {
    try {
      const health = await analysisAPI.healthCheck();
      setBackendStatus(health.status);
    } catch {
      setBackendStatus('disconnected');
    }
  };

  const loadAnalyses = async () => {
    try {
      const data = await analysisAPI.getAllAnalyses();
      setAnalyses(data);
    } catch (error) {
      console.error('Failed to load analyses:', error);
    }
  };

  const handleAnalysisSuccess = () => {
    loadAnalyses();
  };

  const getScoreClass = (score) => {
    if (score >= 80) return 'high';
    if (score >= 60) return 'medium';
    return 'low';
  };

  return (
    <BrowserRouter>
      <div className="app-container">
        <header className="header">
          <div className="header-content">
            <div className="logo-section">
              <div className="logo">CS</div>
              <div className="logo-text">
                <h1>CodeSage</h1>
                <p>AI-Powered Code Review Platform</p>
              </div>
            </div>
            <div className="header-actions">
              <div className={`status-badge ${backendStatus === 'healthy' ? 'online' : 'offline'}`}>
                <span className={`status-dot ${backendStatus === 'healthy' ? 'online' : 'offline'}`}></span>
                {backendStatus === 'healthy' ? 'Online' : 'Offline'}
              </div>
              <AuthButton />
            </div>
          </div>
        </header>

        <main className="main-content">
          <AnalysisForm onSuccess={handleAnalysisSuccess} />

          <div className="card">
            <div className="analyses-header">
              <h2 className="card-title">Recent Analyses</h2>
              <span className="analyses-count">{analyses.length} total</span>
            </div>
            
            {analyses.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <h3 className="empty-title">No analyses yet</h3>
                <p className="empty-text">Submit a repository to get started!</p>
              </div>
            ) : (
              <div className="analyses-list">
                {analyses.map((analysis) => (
                  <div key={analysis.id} className="analysis-item">
                    <div className="analysis-header">
                      <div className="analysis-info">
                        <a 
                          href={analysis.repoUrl} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="repo-link"
                        >
                          {analysis.repoUrl.replace('https://github.com/', '')}
                        </a>
                        <p className="analysis-date">
                          {new Date(analysis.createdAt).toLocaleString()}
                        </p>
                        {analysis.score !== null && (
                          <div className="score-bar">
                            <div className="score-progress">
                              <div 
                                className={`score-fill ${getScoreClass(analysis.score)}`}
                                style={{ width: `${analysis.score}%` }}
                              />
                            </div>
                            <span className="score-value">{analysis.score}/100</span>
                          </div>
                        )}
                      </div>
                      <span className={`status-badge-small ${analysis.status}`}>
                        {analysis.status}
                      </span>
                    </div>
                    <AnalysisDetails analysis={analysis} />
                  </div>
                ))}
              </div>
            )}
          </div>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;