import { useState, useEffect } from 'react';
import { BrowserRouter } from 'react-router-dom';
import AnalysisForm from './components/AnalysisForm';
import AuthButton from './components/AuthButton';
import AnalysisDetails from './components/AnalysisDetails';
import { analysisAPI } from './services/api';
import './styles/App.css';
import './styles/AnalysisList.css';

function App() {
  const [analyses, setAnalyses] = useState([]);
  const [backendStatus, setBackendStatus] = useState('checking');

  useEffect(() => {
    checkBackend();
    loadAnalyses();
    const interval = setInterval(loadAnalyses, 5000);
    return () => clearInterval(interval);
  }, []);

  const checkBackend = async () => {
    try {
      const health = await analysisAPI.healthCheck();
      setBackendStatus(health.status === 'healthy' ? 'online' : 'offline');
    } catch {
      setBackendStatus('offline');
    }
  };

  const loadAnalyses = async () => {
    try {
      const data = await analysisAPI.getAllAnalyses();
      setAnalyses(data || []);
    } catch (error) {
      console.error('Failed to load analyses:', error);
    }
  };

  const getScoreBadgeClass = (score) => {
    if (score >= 80) return 'score-pill-high';
    if (score >= 60) return 'score-pill-medium';
    return 'score-pill-low';
  };

  return (
    <BrowserRouter>
      <div className="app-shell">
        <header className="navbar">
          <div className="navbar-container">
            <div className="brand-group">
              <div className="brand-mark">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="16 18 22 12 16 6" />
                  <polyline points="8 6 2 12 8 18" />
                </svg>
              </div>
              <div className="brand-info">
                <span className="brand-name">CodeSage</span>
                <span className="brand-tagline">Automated Code Review</span>
              </div>
            </div>

            <div className="navbar-controls">
              <div className={`system-status ${backendStatus === 'online' ? 'is-online' : 'is-offline'}`}>
                <span className="status-ping" />
                <span>{backendStatus === 'online' ? 'Operational' : 'Disconnected'}</span>
              </div>
              <AuthButton />
            </div>
          </div>
        </header>

        <main className="dashboard-grid">
          <section className="dashboard-column">
            <AnalysisForm onSuccess={loadAnalyses} />
          </section>

          <section className="dashboard-column">
            <div className="surface-card">
              <div className="surface-card-header">
                <div>
                  <h2 className="section-heading">Recent Analyses</h2>
                  <p className="section-subtext">History of scanned repositories and findings</p>
                </div>
                <span className="count-pill">{analyses.length} Total</span>
              </div>

              {analyses.length === 0 ? (
                <div className="blank-slate">
                  <div className="blank-slate-icon">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                      <polyline points="14 2 14 8 20 8" />
                      <line x1="16" y1="13" x2="8" y2="13" />
                      <line x1="16" y1="17" x2="8" y2="17" />
                    </svg>
                  </div>
                  <h3 className="blank-slate-heading">No analyses yet</h3>
                  <p className="blank-slate-body">Submit a repository URL on the left to start your first evaluation.</p>
                </div>
              ) : (
                <div className="analyses-feed">
                  {analyses.map((analysis) => (
                    <article key={analysis.id} className="analysis-row">
                      <div className="analysis-row-top">
                        <div className="repo-meta-block">
                          <a
                            href={analysis.repoUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="repository-link"
                          >
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22" />
                            </svg>
                            {analysis.repoUrl.replace('https://github.com/', '')}
                          </a>
                          <span className="timestamp">
                            {new Date(analysis.createdAt).toLocaleDateString(undefined, {
                              month: 'short',
                              day: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </span>
                        </div>

                        <div className="status-meta-block">
                          {analysis.score !== null && analysis.score !== undefined && (
                            <span className={`score-pill ${getScoreBadgeClass(analysis.score)}`}>
                              Score: {analysis.score}
                            </span>
                          )}
                          <span className={`state-tag state-${analysis.status?.toLowerCase()}`}>
                            {analysis.status}
                          </span>
                        </div>
                      </div>

                      <AnalysisDetails analysis={analysis} />
                    </article>
                  ))}
                </div>
              )}
            </div>
          </section>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;