import React, { useState, useEffect } from 'react';
import { Search, Plus, RefreshCw, TrendingUp, TrendingDown, Minus, Trash2, AlertCircle } from 'lucide-react';

// CONFIGURE THIS: Change to your Render backend URL
const API_URL = 'https://your-backend-app-name.onrender.com'; // Replace with your actual Render backend URL

const RankTrackerDashboard = () => {
  const [keywords, setKeywords] = useState([]);
  const [showAddForm, setShowAddForm] = useState(false);
  const [isChecking, setIsChecking] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [newTrack, setNewTrack] = useState({
    keyword: '',
    url: '',
    proxy: ''
  });

  // Fetch keywords on mount
  useEffect(() => {
    fetchKeywords();
  }, []);

  const fetchKeywords = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_URL}/api/keywords`);
      if (!response.ok) throw new Error('Failed to fetch keywords');
      const data = await response.json();
      setKeywords(data.keywords || []);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching keywords:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddTrack = async () => {
    if (!newTrack.keyword || !newTrack.url) {
      setError('Keyword and URL are required');
      return;
    }

    setError(null);
    try {
      const response = await fetch(`${API_URL}/api/track`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newTrack)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to add keyword');
      }

      setNewTrack({ keyword: '', url: '', proxy: '' });
      setShowAddForm(false);
      await fetchKeywords();
    } catch (err) {
      setError(err.message);
      console.error('Error adding keyword:', err);
    }
  };

  const handleCheckRankings = async () => {
    setIsChecking(true);
    setError(null);
    try {
      const response = await fetch(`${API_URL}/api/check`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });

      if (!response.ok) throw new Error('Failed to check rankings');
      
      const result = await response.json();
      
      // Show message about local processing
      if (result.status === 'queued') {
        alert(`✅ Scraping started! ${result.total_keywords} keyword(s) queued for local processing with visible browser.\n\nResults will appear automatically when your local scraper processes them.`);
        
        // Start polling for results
        startPollingForResults();
      }
      
    } catch (err) {
      setError(err.message);
      console.error('Error checking rankings:', err);
    } finally {
      setIsChecking(false);
    }
  };

  const startPollingForResults = () => {
    // Poll every 10 seconds for updated results
    const pollInterval = setInterval(async () => {
      try {
        await fetchKeywords();
      } catch (err) {
        console.error('Error polling for results:', err);
      }
    }, 10000);

    // Stop polling after 5 minutes
    setTimeout(() => {
      clearInterval(pollInterval);
    }, 300000);
  };

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this keyword?')) return;

    try {
      const response = await fetch(`${API_URL}/api/keyword/${id}`, {
        method: 'DELETE'
      });

      if (!response.ok) throw new Error('Failed to delete keyword');
      
      await fetchKeywords();
    } catch (err) {
      setError(err.message);
      console.error('Error deleting keyword:', err);
    }
  };

  const getPositionTrend = (current, previous) => {
    if (!previous || !current) return null;
    if (current < previous) return 'up';
    if (current > previous) return 'down';
    return 'same';
  };

  const getTrendColor = (trend) => {
    if (trend === 'up') return 'text-green-500';
    if (trend === 'down') return 'text-red-500';
    return 'text-gray-400';
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Never';
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Rank Tracker</h1>
          <p className="text-gray-600">Track your pages in Google's top 30 results</p>
        </div>

        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
            <AlertCircle className="text-red-500 flex-shrink-0 mt-0.5" size={20} />
            <div>
              <p className="text-red-800 font-medium">Error</p>
              <p className="text-red-700 text-sm">{error}</p>
            </div>
          </div>
        )}

        <div className="bg-white rounded-lg shadow-sm p-4 mb-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowAddForm(!showAddForm)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Plus size={20} />
              Add Keyword
            </button>
            <button
              onClick={handleCheckRankings}
              disabled={isChecking || keywords.length === 0}
              className="flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <RefreshCw size={20} className={isChecking ? 'animate-spin' : ''} />
              {isChecking ? 'Checking...' : 'Check All'}
            </button>
          </div>
          <div className="text-sm text-gray-500">
            Tracking {keywords.length} keyword{keywords.length !== 1 ? 's' : ''}
          </div>
        </div>

        {showAddForm && (
          <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
            <h3 className="text-lg font-semibold mb-4">Add New Tracking</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Keyword *
                </label>
                <input
                  type="text"
                  value={newTrack.keyword}
                  onChange={(e) => setNewTrack({...newTrack, keyword: e.target.value})}
                  placeholder="e.g., best productivity tools 2025"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  URL to Track *
                </label>
                <input
                  type="url"
                  value={newTrack.url}
                  onChange={(e) => setNewTrack({...newTrack, url: e.target.value})}
                  placeholder="https://example.com/your-page"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Proxy (optional)
                </label>
                <input
                  type="text"
                  value={newTrack.proxy}
                  onChange={(e) => setNewTrack({...newTrack, proxy: e.target.value})}
                  placeholder="http://user:pass@proxy.com:port"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              <div className="flex gap-3">
                <button
                  onClick={handleAddTrack}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Add Tracking
                </button>
                <button
                  onClick={() => {
                    setShowAddForm(false);
                    setError(null);
                  }}
                  className="px-6 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        <div className="bg-white rounded-lg shadow-sm overflow-hidden">
          {loading ? (
            <div className="text-center py-12">
              <RefreshCw className="animate-spin mx-auto text-gray-400 mb-4" size={48} />
              <p className="text-gray-600">Loading keywords...</p>
            </div>
          ) : keywords.length === 0 ? (
            <div className="text-center py-12">
              <Search size={48} className="mx-auto text-gray-300 mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No keywords tracked yet</h3>
              <p className="text-gray-500 mb-4">Add your first keyword to start tracking rankings</p>
              <button
                onClick={() => setShowAddForm(true)}
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <Plus size={20} />
                Add Keyword
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Keyword
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      URL
                    </th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Position
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Last Checked
                    </th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {keywords.map((item) => (
                    <tr key={item.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <Search size={16} className="text-gray-400" />
                          <span className="text-sm font-medium text-gray-900">
                            {item.keyword}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <a
                          href={item.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-blue-600 hover:text-blue-800 truncate block max-w-xs"
                        >
                          {item.url}
                        </a>
                      </td>
                      <td className="px-6 py-4 text-center">
                        {item.position ? (
                          <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold bg-blue-100 text-blue-800">
                            #{item.position}
                          </span>
                        ) : (
                          <span className="text-sm text-gray-400">Not checked</span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-sm text-gray-600">
                          {formatDate(item.checked_at)}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-center">
                        <button
                          onClick={() => handleDelete(item.id)}
                          className="text-red-600 hover:text-red-800 transition-colors"
                          title="Delete"
                        >
                          <Trash2 size={18} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-sm text-blue-800">
            <strong>Note:</strong> This tracks positions 1-30 in Google search results. When you click "Check All", keywords are queued for processing on your local PC with visible browser. Results will appear automatically when scraping completes.
          </p>
        </div>
      </div>
    </div>
  );
};

export default RankTrackerDashboard;