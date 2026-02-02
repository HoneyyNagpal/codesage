import { useState, useEffect } from 'react';
import { BrowserRouter } from 'react-router-dom';
import AnalysisForm from './components/AnalysisForm';
import AuthButton from './components/AuthButton';
import { analysisAPI } from './services/api';

function App() {
  const [analyses, setAnalyses] = useState([]);
  const [backendStatus, setBackendStatus] = useState('checking...');

  useEffect(() => {
    checkBackend();
    loadAnalyses();
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

  const handleAnalysisSuccess = (result) => {
    loadAnalyses();
    alert(`Analysis started! ID: ${result.id}`);
  };

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow">
          <div className="max-w-7xl mx-auto py-6 px-4 flex justify-between items-center">
            <h1 className="text-3xl font-bold text-gray-900">
              CodeSage - AI Code Review
            </h1>
            <div className="flex gap-2 text-sm">
              <span className={`px-3 py-1 rounded-full ${backendStatus === 'healthy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                Backend: {backendStatus}
              </span>
              <AuthButton />
            </div>
          </div>
        </header>

        <main className="max-w-7xl mx-auto py-6 px-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Analysis Form */}
            <AnalysisForm onSuccess={handleAnalysisSuccess} />

            {/* Recent Analyses */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-2xl font-bold mb-4">Recent Analyses</h2>
              {analyses.length === 0 ? (
                <p className="text-gray-500">No analyses yet. Submit a repository to get started!</p>
              ) : (
                <div className="space-y-3">
                  {analyses.map((analysis) => (
                    <div key={analysis.id} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <p className="font-medium text-gray-900 truncate">{analysis.repoUrl}</p>
                          <p className="text-sm text-gray-500">
                            {new Date(analysis.createdAt).toLocaleString()}
                          </p>
                        </div>
                        <span className={`px-2 py-1 text-xs rounded-full ${
                          analysis.status === 'completed' ? 'bg-green-100 text-green-800' :
                          analysis.status === 'processing' ? 'bg-blue-100 text-blue-800' :
                          analysis.status === 'failed' ? 'bg-red-100 text-red-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {analysis.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;