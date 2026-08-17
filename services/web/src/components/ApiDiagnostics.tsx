/**
 * Developer tool: probes each dashboard endpoint and reports status and latency.
 *
 * Not mounted by any page — drop it into a route while debugging connectivity.
 * The base URL and the health endpoint now come from the shared API client, so
 * this cannot drift from what the rest of the app talks to (it was hard-coding
 * port 8000 while `lib/api` used 8001).
 */
"use client";

import { useEffect, useState } from 'react';

import { API_BASE_URL } from '@/lib/api';

interface ConnectionTest {
  endpoint: string;
  status: 'pending' | 'success' | 'error';
  message: string;
  responseTime?: number;
}

export default function ApiDiagnostics() {
  const [tests, setTests] = useState<ConnectionTest[]>([]);
  const [testing, setTesting] = useState(false);

  const endpoints = [
    '/health/ready',
    '/dashboard/summary',
    '/dashboard/risk-distribution',
    '/dashboard/flagged-transactions?limit=5',
    '/dashboard/critical-alerts?limit=5',
    '/dashboard/live-alerts?limit=5',
    '/dashboard/alert-trend?period=1h&interval=5m',
    '/compliance/alerts?limit=5',
  ];

  const runDiagnostics = async () => {
    setTesting(true);
    const results: ConnectionTest[] = [];

    for (const endpoint of endpoints) {
      const test: ConnectionTest = {
        endpoint,
        status: 'pending',
        message: 'Testing...',
      };
      results.push(test);
      setTests([...results]);

      const startTime = Date.now();
      try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
          method: 'GET',
          headers: {
            'Accept': 'application/json',
          },
        });

        const responseTime = Date.now() - startTime;

        if (response.ok) {
          await response.json(); // Verify JSON is valid
          test.status = 'success';
          test.message = `Success (${responseTime}ms)`;
          test.responseTime = responseTime;
        } else {
          const errorData = await response.json().catch(() => ({}));
          test.status = 'error';
          test.message = `HTTP ${response.status}: ${errorData.detail || response.statusText}`;
        }
      } catch (error) {
        test.status = 'error';
        test.message = error instanceof Error ? error.message : 'Network error';
      }

      results[results.length - 1] = test;
      setTests([...results]);
    }

    setTesting(false);
  };

  useEffect(() => {
    runDiagnostics();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="p-8">
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-2xl font-semibold text-gray-900">API Connection Diagnostics</h2>
              <p className="text-sm text-gray-500 mt-1">
                Testing connection to: <code className="bg-gray-100 px-2 py-1 rounded">{API_BASE_URL}</code>
              </p>
            </div>
            <button
              onClick={runDiagnostics}
              disabled={testing}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400"
            >
              {testing ? 'Testing...' : 'Retest'}
            </button>
          </div>

          <div className="space-y-3">
            {tests.map((test, index) => (
              <div
                key={index}
                className={`p-4 rounded-lg border-2 ${
                  test.status === 'success'
                    ? 'bg-green-50 border-green-200'
                    : test.status === 'error'
                    ? 'bg-red-50 border-red-200'
                    : 'bg-gray-50 border-gray-200'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      {test.status === 'success' && (
                        <svg className="h-5 w-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                        </svg>
                      )}
                      {test.status === 'error' && (
                        <svg className="h-5 w-5 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                        </svg>
                      )}
                      {test.status === 'pending' && (
                        <div className="h-5 w-5 border-2 border-gray-400 border-t-transparent rounded-full animate-spin"></div>
                      )}
                      <code className="text-sm font-mono font-medium">
                        {test.endpoint}
                      </code>
                    </div>
                    <p className={`text-sm mt-1 ${
                      test.status === 'success' ? 'text-green-700' :
                      test.status === 'error' ? 'text-red-700' :
                      'text-gray-700'
                    }`}>
                      {test.message}
                    </p>
                  </div>
                  {test.responseTime && (
                    <span className={`text-xs font-medium px-2 py-1 rounded ${
                      test.responseTime < 200 ? 'bg-green-100 text-green-700' :
                      test.responseTime < 500 ? 'bg-yellow-100 text-yellow-700' :
                      'bg-red-100 text-red-700'
                    }`}>
                      {test.responseTime}ms
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <h3 className="font-medium text-blue-900 mb-2">Quick Fixes:</h3>
            <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
              <li>Make sure backend server is running on port 8000</li>
              <li>Check CORS configuration in backend allows http://localhost:3000</li>
              <li>Verify database is connected and seeded with data</li>
              <li>Check browser console (F12) for detailed error messages</li>
              <li>Try running: <code className="bg-blue-100 px-1 rounded">curl http://localhost:8000/health</code></li>
            </ul>
          </div>

          <div className="mt-4 p-4 bg-gray-50 border border-gray-200 rounded-lg">
            <h3 className="font-medium text-gray-900 mb-2">Environment:</h3>
            <div className="text-sm text-gray-700 space-y-1 font-mono">
              <div>API_BASE_URL: {API_BASE_URL}</div>
              <div>Frontend URL: {typeof window !== 'undefined' ? window.location.origin : 'N/A'}</div>
              <div>Node ENV: {process.env.NODE_ENV}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
