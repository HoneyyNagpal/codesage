import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { 
  Activity, 
  AlertCircle, 
  CheckCircle, 
  Clock,
  TrendingUp,
  GitBranch,
  Code
} from 'lucide-react';

import RepositoryList from './RepositoryList';
import AnalysisHistory from './AnalysisHistory';
import MetricsOverview from './MetricsOverview';
import { api } from '../../services/api';

const Dashboard = () => {
  const [activeTab, setActiveTab] = useState('overview');

  // Fetch dashboard stats
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => api.get('/api/analysis/stats'),
  });

  // Fetch recent analyses
  const { data: recentAnalyses, isLoading: analysesLoading } = useQuery({
    queryKey: ['recent-analyses'],
    queryFn: () => api.get('/api/analysis/recent?limit=5'),
  });

  const statCards = [
    {
      title: 'Total Analyses',
      value: stats?.data?.totalAnalyses || 0,
      icon: Activity,
      color: 'blue',
      trend: '+12%'
    },
    {
      title: 'Active Repositories',
      value: stats?.data?.activeRepositories || 0,
      icon: GitBranch,
      color: 'green',
      trend: '+3'
    },
    {
      title: 'Issues Found',
      value: stats?.data?.totalIssues || 0,
      icon: AlertCircle,
      color: 'red',
      trend: '-8%'
    },
    {
      title: 'Avg Quality Score',
      value: `${stats?.data?.averageQualityScore || 0}/100`,
      icon: TrendingUp,
      color: 'purple',
      trend: '+5.2'
    }
  ];

  const getColorClasses = (color) => {
    const colors = {
      blue: 'bg-blue-500 text-blue-100',
      green: 'bg-green-500 text-green-100',
      red: 'bg-red-500 text-red-100',
      purple: 'bg-purple-500 text-purple-100'
    };
    return colors[color] || colors.blue;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Dashboard
          </h1>
          <p className="text-gray-600">
            Monitor your code quality and analysis insights
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {statCards.map((stat, index) => {
            const Icon = stat.icon;
            return (
              <motion.div
                key={stat.title}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className="bg-white rounded-xl shadow-sm hover:shadow-md transition-shadow p-6"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className={`p-3 rounded-lg ${getColorClasses(stat.color)}`}>
                    <Icon className="w-6 h-6" />
                  </div>
                  {stat.trend && (
                    <span className="text-sm font-medium text-green-600">
                      {stat.trend}
                    </span>
                  )}
                </div>
                <h3 className="text-gray-600 text-sm font-medium mb-1">
                  {stat.title}
                </h3>
                <p className="text-3xl font-bold text-gray-900">
                  {stat.value}
                </p>
              </motion.div>
            );
          })}
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-xl shadow-sm mb-6">
          <div className="border-b border-gray-200">
            <nav className="flex -mb-px">
              {['overview', 'repositories', 'history'].map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`
                    px-6 py-4 text-sm font-medium capitalize transition-colors
                    ${activeTab === tab
                      ? 'border-b-2 border-blue-500 text-blue-600'
                      : 'text-gray-600 hover:text-gray-900 hover:border-gray-300'
                    }
                  `}
                >
                  {tab}
                </button>
              ))}
            </nav>
          </div>

          <div className="p-6">
            {activeTab === 'overview' && (
              <MetricsOverview stats={stats?.data} />
            )}
            {activeTab === 'repositories' && (
              <RepositoryList />
            )}
            {activeTab === 'history' && (
              <AnalysisHistory />
            )}
          </div>
        </div>

        {/* Recent Analyses */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-gray-900">
              Recent Analyses
            </h2>
            <button className="text-sm text-blue-600 hover:text-blue-700 font-medium">
              View All
            </button>
          </div>

          {analysesLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          ) : recentAnalyses?.data?.analyses?.length === 0 ? (
            <div className="text-center py-12">
              <Code className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600">No analyses yet</p>
              <p className="text-sm text-gray-500 mt-2">
                Start by analyzing your first repository
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {recentAnalyses?.data?.analyses?.map((analysis) => (
                <motion.div
                  key={analysis.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:border-blue-300 transition-colors cursor-pointer"
                  onClick={() => window.location.href = `/analysis/${analysis.id}`}
                >
                  <div className="flex items-center space-x-4">
                    <div className={`
                      p-2 rounded-lg
                      ${analysis.status === 'completed' ? 'bg-green-100 text-green-600' :
                        analysis.status === 'processing' ? 'bg-blue-100 text-blue-600' :
                        analysis.status === 'failed' ? 'bg-red-100 text-red-600' :
                        'bg-gray-100 text-gray-600'}
                    `}>
                      {analysis.status === 'completed' ? <CheckCircle className="w-5 h-5" /> :
                       analysis.status === 'processing' ? <Activity className="w-5 h-5 animate-spin" /> :
                       <AlertCircle className="w-5 h-5" />}
                    </div>
                    <div>
                      <h3 className="font-medium text-gray-900">
                        {analysis.Repository?.name || 'Unknown Repository'}
                      </h3>
                      <p className="text-sm text-gray-600">
                        Branch: {analysis.branch || 'main'} • 
                        {analysis.filesAnalyzed || 0} files analyzed
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-4">
                    {analysis.qualityScore && (
                      <div className="text-right">
                        <div className="text-2xl font-bold text-gray-900">
                          {analysis.qualityScore}
                        </div>
                        <div className="text-xs text-gray-500">Quality Score</div>
                      </div>
                    )}
                    <div className="flex items-center text-sm text-gray-500">
                      <Clock className="w-4 h-4 mr-1" />
                      {new Date(analysis.createdAt).toLocaleDateString()}
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;