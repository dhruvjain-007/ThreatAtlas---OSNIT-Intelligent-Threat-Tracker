import React, { useEffect, useState } from 'react';
import { X, MapPin, Calendar, ExternalLink, ShieldAlert, Cpu, Award, FileText } from 'lucide-react';
import { getEventSources } from '../api/client';
import type { Event, RawPost } from '../types';

interface EventDetailDrawerProps {
  event: Event | null;
  onClose: () => void;
}

export const EventDetailDrawer: React.FC<EventDetailDrawerProps> = ({ event, onClose }) => {
  const [sources, setSources] = useState<RawPost[]>([]);
  const [loadingSources, setLoadingSources] = useState(false);

  useEffect(() => {
    if (!event) return;

    setLoadingSources(true);
    getEventSources(event.id)
      .then((data) => setSources(data))
      .catch((err) => console.error('Failed to load event sources:', err))
      .finally(() => setLoadingSources(false));
  }, [event?.id]);

  if (!event) return null;

  let threatBadgeColor = 'bg-emerald-950/80 text-emerald-300 border-emerald-800/80';
  let threatBarColor = 'bg-emerald-500';
  if (event.threat_level === 'High') {
    threatBadgeColor = 'bg-red-950/90 text-red-300 border-red-800/80 animate-pulse';
    threatBarColor = 'bg-red-500';
  } else if (event.threat_level === 'Medium') {
    threatBadgeColor = 'bg-amber-950/80 text-amber-300 border-amber-800/80';
    threatBarColor = 'bg-amber-500';
  }

  const threatBreakdown = event.score_breakdown?.threat;

  return (
    <div className="fixed right-0 top-16 bottom-0 w-[450px] max-w-[90vw] bg-slate-950/60 border-l border-slate-800/50 z-30 shadow-[-10px_0_30px_rgba(0,0,0,0.5)] flex flex-col backdrop-blur-xl animate-in slide-in-from-right duration-300 select-none">
      {/* Drawer Header */}
      <div className="p-5 border-b border-slate-800/50 flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className={`px-2.5 py-1 text-xs font-mono font-bold rounded border uppercase shadow-sm ${threatBadgeColor}`}>
              {event.threat_level} Threat
            </span>
            <span className="text-xs font-mono text-slate-400 bg-slate-900/40 border border-slate-800/60 px-2 py-1 rounded backdrop-blur-sm">
              Corroboration: {event.corroboration_count} Source(s)
            </span>
          </div>
          <h2 className="text-base font-bold text-slate-100 leading-snug tracking-wide">{event.title}</h2>
        </div>

        <button
          onClick={onClose}
          className="p-1.5 text-slate-400 hover:text-slate-100 bg-slate-900/40 hover:bg-slate-800/60 border border-slate-800/60 rounded-lg transition-all cursor-pointer backdrop-blur-sm hover:shadow-[0_0_10px_rgba(148,163,184,0.15)] focus:ring-2 focus:ring-slate-500 outline-none"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Drawer Content Body */}
      <div className="flex-1 overflow-y-auto p-5 space-y-6">
        {/* Core Metadata */}
        <div className="flex items-center justify-between text-xs font-mono text-slate-400 bg-slate-900/60 border border-slate-800/60 p-3 rounded-lg">
          <div className="flex items-center gap-1.5">
            <MapPin className="w-4 h-4 text-blue-400" />
            <span>{event.location_name || 'Location Unknown'}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Calendar className="w-4 h-4 text-blue-400" />
            <span>{new Date(event.event_timestamp).toUTCString()}</span>
          </div>
        </div>

        {/* Scores Summary */}
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-slate-900/80 border border-slate-800/80 p-3.5 rounded-lg space-y-2">
            <div className="flex items-center justify-between text-xs font-mono text-slate-400">
              <span className="flex items-center gap-1.5">
                <ShieldAlert className="w-4 h-4 text-red-400" /> Threat Score
              </span>
              <span className="font-bold text-slate-100">{event.threat_score}/100</span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
              <div className={`h-full ${threatBarColor} transition-all duration-500`} style={{ width: `${event.threat_score}%` }} />
            </div>
          </div>

          <div className="bg-slate-900/80 border border-slate-800/80 p-3.5 rounded-lg space-y-2">
            <div className="flex items-center justify-between text-xs font-mono text-slate-400">
              <span className="flex items-center gap-1.5">
                <Award className="w-4 h-4 text-blue-400" /> Credibility
              </span>
              <span className="font-bold text-slate-100">{event.credibility_score}/100</span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
              <div className="h-full bg-blue-500 transition-all duration-500" style={{ width: `${event.credibility_score}%` }} />
            </div>
          </div>
        </div>

        {/* Score Factor Breakdown */}
        {threatBreakdown && (
          <div className="bg-slate-900/50 border border-slate-800/80 p-4 rounded-lg space-y-2.5">
            <h3 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
              <Cpu className="w-4 h-4 text-blue-400" /> Transparent Score Breakdown
            </h3>

            <div className="grid grid-cols-2 gap-2 text-xs font-mono">
              <div className="bg-slate-950/60 p-2 rounded border border-slate-800/60 flex justify-between">
                <span className="text-slate-400">Action Score:</span>
                <span className="text-blue-300 font-bold">+{threatBreakdown.action_score}</span>
              </div>
              <div className="bg-slate-950/60 p-2 rounded border border-slate-800/60 flex justify-between">
                <span className="text-slate-400">Equipment Score:</span>
                <span className="text-blue-300 font-bold">+{threatBreakdown.equipment_score}</span>
              </div>
              <div className="bg-slate-950/60 p-2 rounded border border-slate-800/60 flex justify-between">
                <span className="text-slate-400">Location Score:</span>
                <span className="text-blue-300 font-bold">+{threatBreakdown.location_score}</span>
              </div>
              <div className="bg-slate-950/60 p-2 rounded border border-slate-800/60 flex justify-between">
                <span className="text-slate-400">Frequency Score:</span>
                <span className="text-blue-300 font-bold">+{threatBreakdown.frequency_score}</span>
              </div>
            </div>
          </div>
        )}

        {/* Intelligence Summary */}
        {event.summary && (
          <div className="space-y-2">
            <h3 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
              <FileText className="w-4 h-4 text-blue-400" /> Event Intelligence Summary
            </h3>
            <p className="text-xs text-slate-300 bg-slate-900/60 border border-slate-800/60 p-3.5 rounded-lg leading-relaxed font-sans">
              {event.summary}
            </p>
          </div>
        )}

        {/* Extracted Entities */}
        <div className="space-y-3">
          <h3 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider">
            Extracted Entities
          </h3>

          <div className="space-y-2 text-xs font-mono">
            {event.entities?.equipment && event.entities.equipment.length > 0 && (
              <div>
                <span className="text-slate-400 block mb-1">Equipment / Assets:</span>
                <div className="flex flex-wrap gap-1.5">
                  {event.entities.equipment.map((eq, idx) => (
                    <span key={idx} className="px-2 py-0.5 bg-amber-950/60 border border-amber-800/60 text-amber-300 rounded text-[11px]">
                      {eq}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {event.entities?.locations && event.entities.locations.length > 0 && (
              <div>
                <span className="text-slate-400 block mb-1">Locations Mentioned:</span>
                <div className="flex flex-wrap gap-1.5">
                  {event.entities.locations.map((loc, idx) => (
                    <span key={idx} className="px-2 py-0.5 bg-blue-950/60 border border-blue-800/60 text-blue-300 rounded text-[11px]">
                      {loc}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {event.entities?.organizations && event.entities.organizations.length > 0 && (
              <div>
                <span className="text-slate-400 block mb-1">Organizations / Actors:</span>
                <div className="flex flex-wrap gap-1.5">
                  {event.entities.organizations.map((org, idx) => (
                    <span key={idx} className="px-2 py-0.5 bg-purple-950/60 border border-purple-800/60 text-purple-300 rounded text-[11px]">
                      {org}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Contributing Public OSINT Sources */}
        <div className="space-y-3 pt-2">
          <h3 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider flex items-center justify-between">
            <span>Contributing OSINT Sources ({event.source_ids.length})</span>
            {loadingSources && <span className="text-[10px] text-blue-400 animate-pulse">Loading sources...</span>}
          </h3>

          <div className="space-y-2">
            {sources.map((post) => (
              <div key={post.id} className="p-3 bg-slate-900/80 border border-slate-800/80 rounded-lg text-xs space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-blue-400 uppercase">{post.source}</span>
                  <span className="font-mono text-[10px] text-slate-500">{new Date(post.original_timestamp).toLocaleDateString()}</span>
                </div>
                <p className="text-slate-300 text-[11px] line-clamp-2">{post.text}</p>
                {post.url && (
                  <a
                    href={post.url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-[10px] font-mono text-blue-400 hover:text-blue-300 underline mt-1"
                  >
                    View Original Public Source <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
