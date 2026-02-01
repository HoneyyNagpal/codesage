import { BrowserRouter, Routes, Route } from 'react-router-dom';

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow">
          <div className="max-w-7xl mx-auto py-6 px-4">
            <h1 className="text-3xl font-bold text-gray-900">
              CodeSage - AI Code Review Platform
            </h1>
          </div>
        </header>
        
        <main className="max-w-7xl mx-auto py-6 px-4">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-2xl font-semibold mb-4">Welcome to CodeSage!</h2>
            <p className="text-gray-600">
              Your AI-powered code review platform is running successfully.
            </p>
            <div className="mt-6">
              <p className="text-sm text-gray-500">
                ✅ Frontend: Running on port 3000
              </p>
              <p className="text-sm text-gray-500">
                ✅ Backend: Running on port 5000
              </p>
              <p className="text-sm text-gray-500">
                ✅ Analyzer: Running on port 8000
              </p>
            </div>
          </div>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;