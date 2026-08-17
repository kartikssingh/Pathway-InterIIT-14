// Component to display when backend servers are unavailable
'use client';

import { AlertCircle, RefreshCw, Server } from 'lucide-react';
import { Button } from '@/components/ui/button';

export interface ServerDownProps {
  onRetry?: () => void;
  consecutiveFailures?: number;
  lastCheckTime?: Date | null;
  error?: Error | null;
}

export function ServerDown({ 
  onRetry, 
  consecutiveFailures = 0,
  lastCheckTime,
  error 
}: ServerDownProps) {
  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <div className="max-w-2xl mx-auto px-6 py-12 text-center">
        {/* Icon */}
        <div className="flex justify-center mb-8">
          <div className="relative">
            <Server className="w-24 h-24 text-slate-600" strokeWidth={1.5} />
            <div className="absolute -top-2 -right-2 bg-red-500 rounded-full p-2">
              <AlertCircle className="w-8 h-8 text-white" strokeWidth={2} />
            </div>
          </div>
        </div>

        {/* Title */}
        <h1 className="text-4xl font-bold text-white mb-4">
          Servers Unavailable
        </h1>

        {/* Description */}
        <p className="text-xl text-slate-300 mb-6">
          We're unable to connect to the backend servers at this time.
        </p>

        <div className="bg-slate-800/50 rounded-lg p-6 mb-8 border border-slate-700">
          <div className="space-y-3 text-left">
            <div className="flex items-start gap-3">
              <div className="mt-1">
                <div className="w-2 h-2 rounded-full bg-red-500"></div>
              </div>
              <div>
                <p className="text-slate-300 text-sm">
                  <span className="font-semibold">Status:</span> Connection Failed
                </p>
              </div>
            </div>
            
            {consecutiveFailures > 0 && (
              <div className="flex items-start gap-3">
                <div className="mt-1">
                  <div className="w-2 h-2 rounded-full bg-slate-500"></div>
                </div>
                <div>
                  <p className="text-slate-300 text-sm">
                    <span className="font-semibold">Failed Attempts:</span> {consecutiveFailures}
                  </p>
                </div>
              </div>
            )}

            {lastCheckTime && (
              <div className="flex items-start gap-3">
                <div className="mt-1">
                  <div className="w-2 h-2 rounded-full bg-slate-500"></div>
                </div>
                <div>
                  <p className="text-slate-300 text-sm">
                    <span className="font-semibold">Last Check:</span>{' '}
                    {lastCheckTime.toLocaleTimeString()}
                  </p>
                </div>
              </div>
            )}

            {error && (
              <div className="flex items-start gap-3">
                <div className="mt-1">
                  <div className="w-2 h-2 rounded-full bg-orange-500"></div>
                </div>
                <div>
                  <p className="text-slate-300 text-sm">
                    <span className="font-semibold">Error:</span>{' '}
                    {error.message || 'Unknown error'}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Suggestions */}
        <div className="text-slate-400 mb-8 space-y-2">
          <p className="text-sm">This could be due to:</p>
          <ul className="text-sm space-y-1">
            <li>• Server maintenance or updates</li>
            <li>• Network connectivity issues</li>
            <li>• Backend service is temporarily down</li>
          </ul>
        </div>

        {/* Action Button */}
        {onRetry && (
          <Button
            onClick={onRetry}
            size="lg"
            className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-lg font-semibold transition-all duration-200 shadow-lg hover:shadow-xl"
          >
            <RefreshCw className="w-5 h-5 mr-2" />
            Retry Connection
          </Button>
        )}

        {/* Footer message */}
        <p className="text-slate-500 text-sm mt-8">
          The system will automatically retry connecting to the servers
        </p>
      </div>
    </div>
  );
}
