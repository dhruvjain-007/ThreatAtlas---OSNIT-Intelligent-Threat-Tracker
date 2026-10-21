import React, { useState } from 'react';
import { Shield, RefreshCw, AlertTriangle, Layers, Bell, Zap } from 'lucide-react';
import { processPendingPosts, dispatchTestEvent } from '../api/client';
import type { ProcessPendingResponse, EventGlobalMetrics, Event } from '../types';
import { AlertsModal } from './AlertsModal';

interface HeaderProps {
  isOnline: boolean;
  globalMetrics: EventGlobalMetrics;
  onRefresh: () => void;
  onSelectEvent?: (event: Event) => void;
}

export const Header: React.FC<HeaderProps> = ({
  isOnline,
  globalMetrics,
  onRefresh,
  onSelectEvent,
}) => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [isDispatchingTest, setIsDispatchingTest] = useState(false);
  const [processResult, setProcessResult] = useState<ProcessPendingResponse | null>(null);
  const [testNotification, setTestNotification] = useState<string | null>(null);
  const [isAlertsModalOpen, setIsAlertsModalOpen] = useState(false);

  const handleProcessPending = async () => {
    setIsProcessing(true);
    setProcessResult(null);
    try {
      const res = await processPendingPosts();
      setProcessResult(res);
      onRefresh();
    } catch (err) {
      console.error('Failed to process pending posts:', err);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleTriggerTestEvent = async () => {
    setIsDispatchingTest(true);
    setTestNotification(null);
    try {
      const testEvt = await dispatchTestEvent();
      setTestNotification(`Dispatched "${testEvt.title}"`);
      if (onSelectEvent) {
        onSelectEvent(testEvt);
      }
      onRefresh();
      setTimeout(() => setTestNotification(null), 5000);
    } catch (err) {
      console.error('Failed to dispatch test threat event:', err);
    } finally {
      setIsDispatchingTest(false);
    }
  };

  return (
    <header className="h-16 bg-slate-950/70 border-b border-slate-800/60 px-6 flex items-center justify-between backdrop-blur-md z-30 relative select-none shadow-[0_4px_30px_rgba(0,0,0,0.5)]">
      {/* Brand & System Title */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-blue-600/10 border border-blue-500/20 rounded-lg flex items-center justify-center text-blue-400 shadow-[0_0_10px_rgba(59,130,246,0.2)]">
          <Shield className="w-6 h-6" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold tracking-wider text-slate-100 uppercase">
              Threat<span className="text-blue-400 font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-cyan-300">Atlas</span>
            </h1>
            <span className="px-2 py-0.5 text-[10px] font-mono tracking-widest bg-blue-950/50 text-blue-400 border border-blue-800/50 rounded uppercase shadow-[0_0_8px_rgba(59,130,246,0.15)]">
              OSINT v1.0
            </span>
          </div>
          <p className="text-[10px] text-slate-400 font-mono tracking-wider opacity-80">DEFENSIVE INTELLIGENCE PLATFORM</p>
        </div>
      </div>

      {/* Metrics & System Status */}
      <div className="hidden md:flex items-center gap-6">
        <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-900/40 border border-slate-800/60 rounded-md font-mono text-xs backdrop-blur-sm shadow-[0_0_10px_rgba(15,23,42,0.5)]">
          <Layers className="w-4 h-4 text-blue-400/80" />
          <span className="text-slate-400 uppercase text-[10px] tracking-wider">Active Events:</span>
          <span className="text-slate-200 font-bold">{globalMetrics.total}</span>
        </div>

        {globalMetrics.high > 0 && (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-red-950/30 border border-red-900/40 rounded-md font-mono text-xs backdrop-blur-sm animate-soc-pulse shadow-[0_0_15px_rgba(220,38,38,0.15)]">
            <AlertTriangle className="w-4 h-4 text-red-400" />
            <span className="text-red-300 uppercase text-[10px] tracking-wider">High Threat:</span>
            <span className="text-red-400 font-bold">{globalMetrics.high}</span>
          </div>
        )}

        <div className="flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${
              isOnline ? 'bg-emerald-500 shadow-[0_0_10px_#10b981] animate-soc-pulse' : 'bg-red-500 shadow-[0_0_10px_#ef4444]'
            }`}
          />
          <span className="text-[10px] font-mono text-slate-300 uppercase tracking-widest">
            {isOnline ? 'SYSTEM ONLINE' : 'DISCONNECTED'}
          </span>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2.5">
        <button
          onClick={() => setIsAlertsModalOpen(true)}
          className="flex items-center gap-2 px-3.5 py-2 bg-slate-900/50 hover:bg-slate-800/60 text-slate-300 font-medium text-xs rounded-lg border border-slate-700/60 transition-all cursor-pointer backdrop-blur-sm hover:shadow-[0_0_12px_rgba(148,163,184,0.1)] focus:ring-2 focus:ring-slate-600 outline-none"
        >
          <Bell className="w-3.5 h-3.5" />
          <span>Alerts</span>
        </button>

        <button
          onClick={handleTriggerTestEvent}
          disabled={isDispatchingTest}
          title="Dispatch a real-time high-threat incident to test instant WebSocket pin drops on the Cesium globe"
          className="flex items-center gap-2 px-3.5 py-2 bg-amber-600/20 hover:bg-amber-600/30 disabled:bg-slate-800/50 text-amber-300 hover:text-amber-200 font-medium text-xs rounded-lg border border-amber-500/40 transition-all shadow-[0_0_12px_rgba(245,158,11,0.15)] hover:shadow-[0_0_16px_rgba(245,158,11,0.3)] cursor-pointer backdrop-blur-md hover:-translate-y-0.5 focus:ring-2 focus:ring-amber-400 outline-none"
        >
          <Zap className={`w-3.5 h-3.5 text-amber-400 ${isDispatchingTest ? 'animate-bounce' : ''}`} />
          <span>{isDispatchingTest ? 'Dispatching...' : 'Test Threat'}</span>
        </button>

        <button
          onClick={handleProcessPending}
          disabled={isProcessing}
          title="Fetch latest RSS feeds and run end-to-end NLP & intelligence clustering"
          className="flex items-center gap-2 px-3.5 py-2 bg-blue-600/80 hover:bg-blue-500/90 disabled:bg-slate-800/50 disabled:text-slate-500/50 text-white font-medium text-xs rounded-lg border border-blue-400/30 transition-all shadow-[0_0_15px_rgba(37,99,235,0.3)] hover:shadow-[0_0_20px_rgba(59,130,246,0.5)] cursor-pointer backdrop-blur-md hover:-translate-y-0.5 focus:ring-2 focus:ring-blue-400 outline-none"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isProcessing ? 'animate-spin' : ''}`} />
          <span>{isProcessing ? 'Syncing Feeds...' : 'Sync & Ingest OSINT'}</span>
        </button>

        {testNotification && (
          <div className="hidden xl:flex items-center gap-1.5 text-[10px] font-mono text-amber-300 bg-amber-950/40 border border-amber-700/50 px-3 py-1.5 rounded-md backdrop-blur-sm shadow-[0_0_10px_rgba(245,158,11,0.15)] animate-feed-in">
            <Zap className="w-3 h-3 text-amber-400" />
            <span>{testNotification}</span>
          </div>
        )}

        {processResult && !testNotification && (
          <div className="hidden lg:block text-[10px] font-mono text-emerald-400 bg-emerald-950/30 border border-emerald-800/40 px-3 py-1.5 rounded-md backdrop-blur-sm shadow-[0_0_10px_rgba(16,185,129,0.1)] animate-feed-in">
            {processResult.status === 'ingestion_and_processing_started' || processResult.status === 'processing_started'
              ? 'Feed ingestion & intelligence pipeline running...'
              : `+${processResult.processed_count ?? 0} Processed (${processResult.events_created ?? 0} Created)`}
          </div>
        )}
      </div>

      <AlertsModal
        isOpen={isAlertsModalOpen}
        onClose={() => setIsAlertsModalOpen(false)}
      />
    </header>
  );
};
