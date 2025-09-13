import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ClipboardDocumentListIcon, ShieldExclamationIcon, ChartBarIcon } from '@heroicons/react/24/outline';
import axios from 'axios';

function AdminDashboard() {
  const [stats, setStats] = useState({
    total_verifications: 0,
    flagged_certificates: 0,
    blacklisted_certificates: 0,
    daily_stats: []
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await axios.get('/api/admin/stats');
        setStats(response.data);
      } catch (err) {
        console.error('Error fetching admin stats:', err);
        setError('Failed to load dashboard statistics');
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <h2 className="text-lg font-medium text-red-800">Error Loading Dashboard</h2>
          <p className="mt-2 text-red-700">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Admin Dashboard</h1>
        <p className="mt-2 text-lg text-gray-600">
          Monitor certificate verification activities and manage flagged certificates
        </p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 mb-8">
        {/* Total Verifications */}
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0 bg-primary-100 rounded-md p-3">
                <ClipboardDocumentListIcon className="h-6 w-6 text-primary-600" aria-hidden="true" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Total Verifications</dt>
                  <dd>
                    <div className="text-lg font-medium text-gray-900">{stats.total_verifications}</div>
                  </dd>
                </dl>
              </div>
            </div>
          </div>
          <div className="bg-gray-50 px-5 py-3">
            <div className="text-sm">
              <Link to="/admin/logs" className="font-medium text-primary-700 hover:text-primary-900">
                View all verifications
              </Link>
            </div>
          </div>
        </div>

        {/* Flagged Certificates */}
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0 bg-yellow-100 rounded-md p-3">
                <ShieldExclamationIcon className="h-6 w-6 text-yellow-600" aria-hidden="true" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Flagged Certificates</dt>
                  <dd>
                    <div className="text-lg font-medium text-gray-900">{stats.flagged_certificates}</div>
                  </dd>
                </dl>
              </div>
            </div>
          </div>
          <div className="bg-gray-50 px-5 py-3">
            <div className="text-sm">
              <Link to="/admin/logs?status=FLAG" className="font-medium text-primary-700 hover:text-primary-900">
                View flagged certificates
              </Link>
            </div>
          </div>
        </div>

        {/* Blacklisted Certificates */}
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0 bg-red-100 rounded-md p-3">
                <ShieldExclamationIcon className="h-6 w-6 text-red-600" aria-hidden="true" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Blacklisted Certificates</dt>
                  <dd>
                    <div className="text-lg font-medium text-gray-900">{stats.blacklisted_certificates}</div>
                  </dd>
                </dl>
              </div>
            </div>
          </div>
          <div className="bg-gray-50 px-5 py-3">
            <div className="text-sm">
              <Link to="/admin/blacklist" className="font-medium text-primary-700 hover:text-primary-900">
                Manage blacklist
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Daily Verification Chart */}
      <div className="bg-white shadow rounded-lg p-6 mb-8">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Verification Trends (Last 7 Days)</h2>
        
        {stats.daily_stats.length > 0 ? (
          <div className="h-64">
            {/* Simple bar chart visualization */}
            <div className="flex h-48 items-end space-x-2">
              {stats.daily_stats.map((day, index) => {
                const passHeight = (day.pass_count / Math.max(...stats.daily_stats.map(d => d.pass_count + d.flag_count))) * 100;
                const flagHeight = (day.flag_count / Math.max(...stats.daily_stats.map(d => d.pass_count + d.flag_count))) * 100;
                
                return (
                  <div key={index} className="flex-1 flex flex-col items-center">
                    <div className="w-full flex flex-col-reverse">
                      <div 
                        className="bg-red-500 w-full" 
                        style={{ height: `${flagHeight}%` }}
                        title={`Flagged: ${day.flag_count}`}
                      ></div>
                      <div 
                        className="bg-green-500 w-full" 
                        style={{ height: `${passHeight}%` }}
                        title={`Passed: ${day.pass_count}`}
                      ></div>
                    </div>
                    <div className="text-xs text-gray-500 mt-2">
                      {new Date(day.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                    </div>
                  </div>
                );
              })}
            </div>
            
            {/* Legend */}
            <div className="flex justify-center mt-4 space-x-6">
              <div className="flex items-center">
                <div className="w-3 h-3 bg-green-500 mr-2"></div>
                <span className="text-sm text-gray-600">Passed</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-red-500 mr-2"></div>
                <span className="text-sm text-gray-600">Flagged</span>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center py-12 text-gray-500">
            <ChartBarIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No data available</h3>
            <p className="mt-1 text-sm text-gray-500">Start verifying certificates to see trends.</p>
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Link 
            to="/admin/logs" 
            className="relative rounded-lg border border-gray-300 bg-white px-6 py-5 shadow-sm flex items-center space-x-3 hover:border-gray-400 focus-within:ring-2 focus-within:ring-offset-2 focus-within:ring-primary-500"
          >
            <div className="flex-shrink-0 bg-primary-100 rounded-md p-2">
              <ClipboardDocumentListIcon className="h-5 w-5 text-primary-600" aria-hidden="true" />
            </div>
            <div className="flex-1 min-w-0">
              <span className="absolute inset-0" aria-hidden="true" />
              <p className="text-sm font-medium text-gray-900">View Verification Logs</p>
              <p className="text-sm text-gray-500">Review all verification attempts with filters</p>
            </div>
          </Link>

          <Link 
            to="/admin/blacklist" 
            className="relative rounded-lg border border-gray-300 bg-white px-6 py-5 shadow-sm flex items-center space-x-3 hover:border-gray-400 focus-within:ring-2 focus-within:ring-offset-2 focus-within:ring-primary-500"
          >
            <div className="flex-shrink-0 bg-red-100 rounded-md p-2">
              <ShieldExclamationIcon className="h-5 w-5 text-red-600" aria-hidden="true" />
            </div>
            <div className="flex-1 min-w-0">
              <span className="absolute inset-0" aria-hidden="true" />
              <p className="text-sm font-medium text-gray-900">Manage Blacklist</p>
              <p className="text-sm text-gray-500">Add or remove certificates from blacklist</p>
            </div>
          </Link>
        </div>
      </div>
    </div>
  );
}

export default AdminDashboard;