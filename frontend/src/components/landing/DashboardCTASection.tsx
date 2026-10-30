import React from 'react';
import { ArrowRight, Globe, Zap, ExternalLink } from 'lucide-react';

interface DashboardCTASectionProps {
  onNavigateDashboard: () => void;
}

export const DashboardCTASection: React.FC<DashboardCTASectionProps> = ({ onNavigateDashboard }) => {
  return (
    <section className="relative py-20 lg:py-28 overflow-hidden">
      {/* Background Radial Glow */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div className="w-[600px] h-[300px] bg-gradient-to-r from-cyan-500/10 via-blue-600/10 to-transparent blur-3xl opacity-75" />
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="relative rounded-3xl bg-gradient-to-b from-[#101923] to-[#080D14] border border-cyan-500/30 p-8 sm:p-12 lg:p-16 shadow-[0_0_60px_rgba(66,217,245,0.12)] overflow-hidden text-center max-w-4xl mx-auto space-y-8">
          {/* Subtle Grid Accent */}
          <div
            className="absolute inset-0 opacity-15 pointer-events-none"
            style={{
              backgroundImage: 'radial-gradient(rgba(66, 217, 245, 0.4) 1px, transparent 1px)',
              backgroundSize: '24px 24px',
            }}
          />

          {/* Eyebrow Badge */}
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-cyan-950/60 border border-cyan-500/30 text-cyan-300 font-mono text-xs tracking-widest uppercase">
            <Globe className="w-3.5 h-3.5 text-cyan-400" />
            <span>INTERACTIVE COMMAND INTERFACE</span>
          </div>

          {/* Heading */}
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-slate-100 uppercase leading-tight">
            See the world through{' '}
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 via-sky-300 to-blue-500">
              connected intelligence.
            </span>
          </h2>

          {/* Supporting Copy */}
          <p className="text-sm sm:text-base text-slate-300 max-w-2xl mx-auto leading-relaxed font-normal">
            Transition from the architectural overview to the live ThreatAtlas command center. Explore clustered
            defense incidents, inspect weapon system classifications, and scrub chronological event progression.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-wrap items-center justify-center gap-4 pt-2">
            <button
              onClick={onNavigateDashboard}
              className="flex items-center gap-3 px-8 py-4 bg-gradient-to-r from-cyan-500 via-sky-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold text-sm rounded-xl shadow-[0_0_30px_rgba(66,217,245,0.4)] hover:shadow-[0_0_40px_rgba(66,217,245,0.6)] transition-all cursor-pointer transform hover:-translate-y-0.5 focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none"
            >
              <Zap className="w-4 h-4 text-slate-950 fill-slate-950" />
              <span>Open ThreatAtlas Dashboard</span>
              <ArrowRight className="w-4 h-4" />
            </button>

            <a
              href="https://github.com/dhruvjain-007/ThreatAtlas---OSNIT-Intelligent-Threat-Tracker"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-6 py-4 bg-slate-900/80 hover:bg-slate-800 text-slate-200 hover:text-cyan-400 font-mono text-xs uppercase tracking-wider rounded-xl border border-slate-700/80 hover:border-cyan-500/40 transition-all cursor-pointer backdrop-blur-sm focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none"
            >
              <span>Repository & Docs</span>
              <ExternalLink className="w-3.5 h-3.5 opacity-70" />
            </a>
          </div>

          {/* Technical Telemetry Footer */}
          <div className="pt-6 border-t border-slate-800/80 flex flex-wrap items-center justify-center gap-6 font-mono text-[11px] text-slate-400">
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span>Production FastAPI Backend</span>
            </div>
            <span>•</span>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-cyan-400" />
              <span>Hardware-Accelerated CesiumJS</span>
            </div>
            <span>•</span>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-blue-400" />
              <span>Sub-Second Redis Pub/Sub</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
