import React, { useState, useEffect } from 'react';
import { Search, Plus, RefreshCw, TrendingUp, TrendingDown, Minus, Trash2, AlertCircle, Calendar, Clock } from 'lucide-react';

// Backend deployed on Render
const API_URL = 'https://google-scraper-1.onrender.com';

const countryList = [
  { code: '', name: 'Global / Auto' },
  { code: 'us', name: 'United States' },
  { code: 'ca', name: 'Canada' },
  { code: 'gb', name: 'United Kingdom' },
  { code: 'au', name: 'Australia' },
  { code: 'de', name: 'Germany' },
  { code: 'fr', name: 'France' },
  { code: 'es', name: 'Spain' },
  { code: 'it', name: 'Italy' },
  { code: 'jp', name: 'Japan' },
  { code: 'br', name: 'Brazil' },
  { code: 'in', name: 'India' },
];

const RankTrackerDashboard = () => {
  const [keywords, setKeywords] = useState([]);
  const [showAddForm, setShowAddForm] = useState(false);
  const [isChecking, setIsChecking] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [checkingKeywords, setCheckingKeywords] = useState(new Set());
  const [newTrack, setNewTrack] = useState({
    keyword: '',
    url: '',
    country: '',
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

      setNewTrack({ keyword: '', url: '', country: '', proxy: '' });
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

  const handleCheckSingleKeyword = async (keywordId) => {
    setCheckingKeywords(prev => new Set([...prev, keywordId]));
    setError(null);
    try {
      const response = await fetch(`${API_URL}/api/check`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keyword_id: keywordId })
      });

      if (!response.ok) throw new Error('Failed to check ranking');
      
      const result = await response.json();
      
      // Show message about local processing
      if (result.status === 'queued') {
        alert(`✅ Scraping started for selected keyword!\n\nResults will appear automatically when your local scraper processes them.`);
        
        // Start polling for results
        startPollingForResults();
      }
      
    } catch (err) {
      setError(err.message);
      console.error('Error checking ranking:', err);
    } finally {
      setCheckingKeywords(prev => {
        const newSet = new Set(prev);
        newSet.delete(keywordId);
        return newSet;
      });
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

  const getCountryName = (code) => {
    if (!code) return 'Global';
    const country = countryList.find(c => c.code === code);
    return country ? country.name : code.toUpperCase();
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Never';
    const date = new Date(dateString);
    return date.toLocaleString(undefined, {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true
    });
  };

  const getCountryName = (code) => {
    if (!code) return 'Global';
    const country = countryList.find(c => c.code === code);
    return country ? country.name : code.toUpperCase();
  };

  const formatDateShort = (dateString) => {
    if (!dateString) return 'Never';
    const date = new Date(dateString);
    return date.toLocaleDateString(undefined, {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    });
  };

  return (
    <div className="min-h-screen bg-gray-900 p-3 sm:p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold text-white mb-2">Rank Tracker</h1>
          <p className="text-sm sm:text-base text-gray-300">Track your pages in Google's top 30 results</p>
        </div>

        {error && (
          <div className="mb-4 sm:mb-6 bg-red-900/20 border border-red-500/30 rounded-lg p-3 sm:p-4 flex items-start gap-2 sm:gap-3">
            <AlertCircle className="text-red-400 flex-shrink-0 mt-0.5" size={18} />
            <div className="min-w-0">
              <p className="text-red-300 font-medium text-sm">Error</p>
              <p className="text-red-200 text-xs sm:text-sm break-words">{error}</p>
            </div>
          </div>
        )}

        <div className="bg-gray-800 rounded-lg shadow-sm p-3 sm:p-4 mb-4 sm:mb-6 border border-gray-700">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-0">
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-3">
              <button
                onClick={() => setShowAddForm(!showAddForm)}
                className="flex items-center justify-center gap-2 px-3 sm:px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm sm:text-base"
              >
                <Plus size={18} />
                <span className="hidden sm:inline">Add Keyword</span>
                <span className="sm:hidden">Add</span>
              </button>
              <button
                onClick={handleCheckRankings}
                disabled={isChecking || keywords.length === 0}
                className="flex items-center justify-center gap-2 px-3 sm:px-4 py-2 bg-gray-700 text-gray-200 rounded-lg hover:bg-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed border border-gray-600 text-sm sm:text-base"
              >
                <RefreshCw size={18} className={isChecking ? 'animate-spin' : ''} />
                <span className="hidden sm:inline">{isChecking ? 'Checking...' : 'Check All'}</span>
                <span className="sm:hidden">{isChecking ? 'Check...' : 'Check All'}</span>
              </button>
            </div>
            <div className="text-xs sm:text-sm text-gray-300 text-center sm:text-right">
              Tracking {keywords.length} keyword{keywords.length !== 1 ? 's' : ''}
            </div>
          </div>
        </div>

        {showAddForm && (
          <div className="bg-gray-800 rounded-lg shadow-sm p-4 sm:p-6 mb-4 sm:mb-6 border border-gray-700">
            <h3 className="text-base sm:text-lg font-semibold mb-3 sm:mb-4 text-white">Add New Tracking</h3>
            <div className="space-y-3 sm:space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Keyword *
                </label>
                <input
                  type="text"
                  value={newTrack.keyword}
                  onChange={(e) => setNewTrack({...newTrack, keyword: e.target.value})}
                  placeholder="e.g., best productivity tools 2025"
                  className="w-full px-3 sm:px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-white placeholder-gray-400 text-sm sm:text-base"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  URL to Track *
                </label>
                <input
                  type="url"
                  value={newTrack.url}
                  onChange={(e) => setNewTrack({...newTrack, url: e.target.value})}
                  placeholder="https://example.com/your-page"
                  className="w-full px-3 sm:px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-white placeholder-gray-400 text-sm sm:text-base"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Country
                </label>
                <select
                  value={newTrack.country}
                  onChange={(e) => setNewTrack({...newTrack, country: e.target.value})}
                  className="w-full px-3 sm:px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-white placeholder-gray-400 text-sm sm:text-base"
                >
                  {countryList.map(c => <option key={c.code} value={c.code}>{c.name}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Proxy (optional)
                </label>
                <input
                  type="text"
                  value={newTrack.proxy}
                  onChange={(e) => setNewTrack({...newTrack, proxy: e.target.value})}
                  placeholder="http://user:pass@proxy.com:port"
                  className="w-full px-3 sm:px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-white placeholder-gray-400 text-sm sm:text-base"
                />
              </div>
              <div className="flex flex-col sm:flex-row gap-2 sm:gap-3">
                <button
                  onClick={handleAddTrack}
                  className="px-4 sm:px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm sm:text-base"
                >
                  Add Tracking
                </button>
                <button
                  onClick={() => {
                    setShowAddForm(false);
                    setError(null);
                  }}
                  className="px-4 sm:px-6 py-2 bg-gray-700 text-gray-200 rounded-lg hover:bg-gray-600 transition-colors border border-gray-600 text-sm sm:text-base"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        <div className="bg-gray-800 rounded-lg shadow-sm overflow-hidden border border-gray-700">
          {loading ? (
            <div className="text-center py-8 sm:py-12">
              <RefreshCw className="animate-spin mx-auto text-gray-400 mb-3 sm:mb-4" size={40} />
              <p className="text-gray-300 text-sm sm:text-base">Loading keywords...</p>
            </div>
          ) : keywords.length === 0 ? (
            <div className="text-center py-8 sm:py-12">
              <Search size={40} className="mx-auto text-gray-600 mb-3 sm:mb-4" />
              <h3 className="text-base sm:text-lg font-medium text-white mb-2">No keywords tracked yet</h3>
              <p className="text-gray-400 mb-4 text-sm sm:text-base px-4">Add your first keyword to start tracking rankings</p>
              <button
                onClick={() => setShowAddForm(true)}
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm sm:text-base"
              >
                <Plus size={18} />
                Add Keyword
              </button>
            </div>
          ) : (
            <>
            <div className="block sm:hidden">
              {/* Mobile card view */}
              <div className="divide-y divide-gray-700">
                {keywords.map((item) => (
                  <div key={item.id} className="p-4 hover:bg-gray-700/50 transition-colors">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-2 min-w-0 flex-1">
                        <Search size={16} className="text-gray-500 flex-shrink-0" />
                        <div className="flex-grow min-w-0">
                          <span className="text-sm font-medium text-white truncate block">
                            {item.keyword}
                          </span>
                          <span className="text-xs text-gray-400">
                            {getCountryName(item.country)}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 ml-2">
                        <button
                          onClick={() => handleCheckSingleKeyword(item.id)}
                          disabled={checkingKeywords.has(item.id)}
                          className="text-blue-400 hover:text-blue-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          title="Check this keyword"
                        >
                          <RefreshCw size={16} className={checkingKeywords.has(item.id) ? 'animate-spin' : ''} />
                        </button>
                        <button
                          onClick={() => handleDelete(item.id)}
                          className="text-red-400 hover:text-red-300 transition-colors"
                          title="Delete"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </div>
                    
                    <div className="space-y-2">
                      <div>
                        <a
                          href={item.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-blue-400 hover:text-blue-300 break-all transition-colors"
                        >
                          {item.url}
                        </a>
                      </div>
                      
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1">
                          {item.position ? (
                            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-semibold bg-blue-900/50 text-blue-300 border border-blue-700">
                              #{item.position}
                            </span>
                          ) : (
                            <span className="text-xs text-gray-500">Not checked</span>
                          )}
                        </div>
                        
                        <div className="flex items-center gap-2 text-xs text-gray-400">
                          <div className="flex items-center gap-1">
                            <Calendar size={12} />
                            <span>{formatDateShort(item.created_at)}</span>
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-1 text-xs text-gray-400">
                        <Clock size={12} />
                        <span>{formatDate(item.checked_at)}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            
            <div className="hidden sm:block overflow-x-auto">
              {/* Desktop table view */}
              <table className="w-full">
                <thead className="bg-gray-700 border-b border-gray-600">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                      Keyword
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                      URL
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                      Country
                    </th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-300 uppercase tracking-wider">
                      Position
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                      Added Date
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                      Last Checked
                    </th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-300 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700">
                  {keywords.map((item) => (
                    <tr key={item.id} className="hover:bg-gray-700/50 transition-colors">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <Search size={16} className="text-gray-500" />
                          <span className="text-sm font-medium text-white">
                            {item.keyword}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <a
                          href={item.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-blue-400 hover:text-blue-300 truncate block max-w-xs transition-colors"
                        >
                          {item.url}
                        </a>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-sm text-gray-300">{getCountryName(item.country)}</span>
                      </td>
                      <td className="px-6 py-4 text-center">
                        {item.position ? (
                          <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold bg-blue-900/50 text-blue-300 border border-blue-700">
                            #{item.position}
                          </span>
                        ) : (
                          <span className="text-sm text-gray-500">Not checked</span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-1">
                          <Calendar size={14} className="text-gray-500" />
                          <span className="text-sm text-gray-300">
                            {formatDateShort(item.created_at)}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-1">
                          <Clock size={14} className="text-gray-500" />
                          <span className="text-sm text-gray-300">
                            {formatDate(item.checked_at)}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-center">
                        <div className="flex items-center justify-center gap-2">
                          <button
                            onClick={() => handleCheckSingleKeyword(item.id)}
                            disabled={checkingKeywords.has(item.id)}
                            className="text-blue-400 hover:text-blue-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            title="Check this keyword"
                          >
                            <RefreshCw size={16} className={checkingKeywords.has(item.id) ? 'animate-spin' : ''} />
                          </button>
                          <button
                            onClick={() => handleDelete(item.id)}
                            className="text-red-400 hover:text-red-300 transition-colors"
                            title="Delete"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            </>
          )}
        </div>

        <div className="mt-4 sm:mt-6 bg-blue-900/20 border border-blue-700/30 rounded-lg p-3 sm:p-4">
          <p className="text-xs sm:text-sm text-blue-300 leading-relaxed">
            <strong>Note:</strong> This tracks positions 1-30 in Google search results. When you click "Check All" or individual check buttons, keywords are queued for processing on your local PC with visible browser. Results will appear automatically when scraping completes.
          </p>
        </div>
      </div>
    </div>
  );
};

export default RankTrackerDashboard;