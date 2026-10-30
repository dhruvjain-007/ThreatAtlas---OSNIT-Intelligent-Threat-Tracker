import React, { useEffect, useState } from 'react';
import { Radio, RefreshCw, AlertCircle, MapPin, Clock, ArrowRight, Layers } from 'lucide-react';
import { fetchEvents, fetchGlobalMetrics } from '../../api/client';
import type { Event, EventGlobalMetrics } from '../../types';

interface LivePreviewSectionProps {
  onNavigateDashboard: () => void;
}

export const LivePreviewSection: React.FC<LivePreviewSectionProps> = ({ onNavigateDashboard }) => {
  const [events, setEvents] = useState<Event[]>([]);
  const [metrics, setMetrics] = useState<EventGlobalMetrics | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Fetch real events with a small limit
      const res = await fetchEvents({}, 4);
      setEvents(res.items || []);

      // 2. Fetch verified global metrics from the backend
      try {
        const m = await fetchGlobalMetrics();
        setMetrics(m);
      } catch {
        // Non-critical, leave metrics null
      }
    } catch (err: any) {
      console.warn('[LivePreviewSection] Backend intelligence feed unavailable:', err);
      setError('Live intelligence stream temporarily unavailable. The backend may be warming up or offline.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const formatTimestamp = (isoString?: string) => {
    if (!isoString) return 'Recent';
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        timeZoneName: 'short',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <section id="preview" className="scroll-mt-20 relative py-20 bg-[#101923]/40 border-y border-slate-800/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-10">
          <div>
            <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded bg-cyan-950/40 border border-cyan-800/40 text-cyan-400 font-mono text-[10px] tracking-widest uppercase mb-3">
              <Radio className="w-3 h-3 animate-pulse" />
              <span>REAL-TIME INCIDENT MONITOR</span>
            </div>
            <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-slate-100 uppercase">
              Live Threat Stream
            </h2>
            <p className="mt-2 text-sm text-slate-400 max-w-xl">
              Live events extracted, geocoded, and classified by the ThreatAtlas intelligence pipeline.
            </p>
          </div>

          {/* Action Row */}
          <div className="flex items-center gap-3">
            <button
              onClick={loadData}
              disabled={loading}
              className="flex items-center gap-1.5 px-3 py-2 bg-slate-900/60 hover:bg-slate-800 disabled:opacity-50 text-slate-300 font-mono text-xs rounded-lg border border-slate-700/60 transition-all cursor-pointer focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none"
              title="Refresh intelligence preview"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-cyan-400 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>

            <button
              onClick={onNavigateDashboard}
              className="flex items-center gap-1.5 px-4 py-2 bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 font-mono text-xs rounded-lg border border-cyan-500/30 transition-all cursor-pointer focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none"
            >
              <span>Open in Globe</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Verified Stats Strip (Only displayed if backend returns real metrics) */}
        {metrics && metrics.total > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8 font-mono text-xs">
            <div className="p-3 rounded-lg bg-[#080D14]/80 border border-slate-800 flex items-center justify-between">
              <span className="text-slate-400 text-[11px] uppercase tracking-wider">Active Incidents</span>
              <span className="text-slate-100 font-bold text-base">{metrics.total}</span>
            </div>
            <div className="p-3 rounded-lg bg-[#080D14]/80 border border-slate-800 flex items-center justify-between">
              <span className="text-amber-400/90 text-[11px] uppercase tracking-wider">High Threat</span>
              <span className="text-amber-400 font-bold text-base">{metrics.high}</span>
            </div>
            <div className="p-3 rounded-lg bg-[#080D14]/80 border border-slate-800 flex items-center justify-between">
              <span className="text-sky-400/90 text-[11px] uppercase tracking-wider">Medium Threat</span>
              <span className="text-sky-300 font-bold text-base">{metrics.medium}</span>
            </div>
            <div className="p-3 rounded-lg bg-[#080D14]/80 border border-slate-800 flex items-center justify-between">
              <span className="text-emerald-400/90 text-[11px] uppercase tracking-wider">Low Threat</span>
              <span className="text-emerald-400 font-bold text-base">{metrics.low}</span>
            </div>
          </div>
        )}

        {/* Content Area */}
        {loading && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[1, 2, 3, 4].map((n) => (
              <div
                key={n}
                className="p-5 rounded-xl bg-[#141F2B]/60 border border-slate-800/80 animate-pulse space-y-3"
              >
                <div className="flex justify-between items-center">
                  <div className="h-4 w-24 bg-slate-800 rounded" />
                  <div className="h-4 w-16 bg-slate-800 rounded" />
                </div>
                <div className="h-5 w-3/4 bg-slate-800 rounded" />
                <div className="h-4 w-1/2 bg-slate-800 rounded" />
              </div>
            ))}
          </div>
        )}

        {!loading && error && (
          <div className="p-6 rounded-xl bg-slate-900/60 border border-slate-800 text-center space-y-4 max-w-2xl mx-auto">
            <div className="w-10 h-10 mx-auto rounded-full bg-slate-800/80 border border-slate-700 flex items-center justify-center text-slate-400">
              <AlertCircle className="w-5 h-5 text-amber-400" />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-medium text-slate-200">Intelligence Stream Offline</p>
              <p className="text-xs text-slate-400">{error}</p>
            </div>
            <div className="flex justify-center gap-3">
              <button
                onClick={loadData}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono rounded-lg transition-colors cursor-pointer"
              >
                Retry Connection
              </button>
              <button
                onClick={onNavigateDashboard}
                className="px-4 py-2 bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 text-xs font-mono rounded-lg border border-cyan-500/40 transition-colors cursor-pointer"
              >
                Launch Dashboard
              </button>
            </div>
          </div>
        )}

        {!loading && !error && events.length === 0 && (
          <div className="p-8 rounded-xl bg-[#141F2B]/40 border border-slate-800 text-center space-y-2">
            <Layers className="w-8 h-8 text-slate-500 mx-auto" />
            <p className="text-sm font-semibold text-slate-200">No active events in retention period</p>
            <p className="text-xs text-slate-400">
              Trigger OSINT feed ingestion in the dashboard to fetch and process the latest intelligence posts.
            </p>
            <div className="pt-2">
              <button
                onClick={onNavigateDashboard}
                className="px-4 py-2 bg-cyan-500 text-slate-950 font-bold text-xs rounded-lg hover:bg-cyan-400 cursor-pointer"
              >
                Go to Dashboard
              </button>
            </div>
          </div>
        )}

        {!loading && !error && events.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {events.map((evt) => {
              const isHigh = evt.threat_level === 'High';
              const isMed = evt.threat_level === 'Medium';
              const badgeBg = isHigh
                ? 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                : isMed
                ? 'bg-sky-500/10 text-sky-300 border-sky-500/30'
                : 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30';

              const locationDisplay = evt.location_name
                ? evt.location_name
                : evt.country_code
                ? `Region: ${evt.country_code.toUpperCase()}`
                : 'Unspecified Region';

              return (
                <div
                  key={evt.id}
                  onClick={onNavigateDashboard}
                  className="group p-5 rounded-xl bg-[#141F2B]/70 hover:bg-[#182635] border border-slate-800 hover:border-cyan-500/40 transition-all cursor-pointer shadow-md hover:shadow-[0_0_20px_rgba(66,217,245,0.1)] flex flex-col justify-between"
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') onNavigateDashboard();
                  }}
                  aria-label={`View event: ${evt.title}`}
                >
                  <div className="space-y-2.5">
                    {/* Top Row: Threat Level Badge, Score, and Primary Source */}
                    <div className="flex items-center justify-between text-xs font-mono">
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-0.5 rounded border text-[10px] font-bold uppercase tracking-wider ${badgeBg}`}>
                          {evt.threat_level} Threat
                        </span>
                        {evt.source_ids && evt.source_ids.length > 0 && (
                          <span className="hidden sm:inline-block text-[10px] text-slate-400 bg-slate-900/80 px-1.5 py-0.5 rounded border border-slate-800 truncate max-w-[140px]">
                            {evt.source_ids[0]}
                          </span>
                        )}
                      </div>
                      <span className="text-slate-400 text-[11px]">
                        Score: <span className="font-bold text-slate-200">{Math.round(evt.threat_score)}</span>/100
                      </span>
                    </div>

                    {/* Title */}
                    <h3 className="text-sm font-semibold text-slate-100 group-hover:text-cyan-300 transition-colors line-clamp-2 leading-snug">
                      {evt.title}
                    </h3>

                    {/* Summary / Snippet */}
                    {evt.summary && (
                      <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                        {evt.summary}
                      </p>
                    )}
                  </div>

                  {/* Metadata Footer */}
                  <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] font-mono text-slate-400">
                    <div className="flex items-center gap-3 truncate">
                      <span className="flex items-center gap-1 text-slate-300 truncate">
                        <MapPin className="w-3 h-3 text-cyan-400 shrink-0" />
                        <span className="truncate">{locationDisplay}</span>
                      </span>
                      <span className="flex items-center gap-1 shrink-0">
                        <Clock className="w-3 h-3 text-slate-500 shrink-0" />
                        <span>{formatTimestamp(evt.event_timestamp)}</span>
                      </span>
                    </div>

                    <span className="text-cyan-400 group-hover:translate-x-0.5 transition-transform shrink-0 ml-2">
                      <ArrowRight className="w-3.5 h-3.5" />
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
};
