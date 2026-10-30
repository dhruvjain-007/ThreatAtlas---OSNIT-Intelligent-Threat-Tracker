import React from 'react';
import { ArrowRight, ChevronDown, Radio, Globe2, Cpu, Zap } from 'lucide-react';
import { HeroRadarVisual } from './HeroRadarVisual';

interface HeroSectionProps {
  onNavigateDashboard: () => void;
  onScrollToSection: (id: string) => void;
}

export const HeroSection: React.FC<HeroSectionProps> = ({
  onNavigateDashboard,
  onScrollToSection,
}) => {
  return (
    <section id="overview" className="scroll-mt-20 relative pt-12 pb-20 lg:pt-20 lg:pb-28 overflow-hidden">
      {/* Background Radial Glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-gradient-to-b from-cyan-500/10 via-blue-500/5 to-transparent blur-3xl pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center">
          {/* Left Column: Typography & CTAs */}
          <div className="lg:col-span-7 space-y-6 text-left">
            {/* Status Eyebrow Badge */}
            <div className="inline-flex items-center gap-2.5 px-3 py-1.5 rounded-full bg-slate-900/90 border border-cyan-500/30 backdrop-blur-md shadow-[0_0_15px_rgba(66,217,245,0.15)] animate-feed-in">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
              <span className="text-[11px] font-mono tracking-widest text-cyan-300 font-semibold uppercase">
                OPEN-SOURCE INTELLIGENCE PLATFORM
              </span>
              <span className="text-slate-400 text-[10px] font-mono">v1.0</span>
            </div>

            {/* Main Headline */}
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-slate-100 leading-[1.1] uppercase">
              Global Intelligence.{' '}
              <span className="block mt-1 bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 via-sky-300 to-blue-500">
                Connected.
              </span>
            </h1>

            {/* Subtitle / Description */}
            <p className="text-base sm:text-lg text-slate-300 leading-relaxed max-w-2xl font-normal">
              ThreatAtlas transforms incoming intelligence from multiple public news feeds into a unified
              geospatial view—extracting military entities, evaluating kinetic actions with NLP, and mapping
              emerging threats onto an interactive 3D command globe.
            </p>

            {/* Call to Actions */}
            <div className="flex flex-wrap items-center gap-4 pt-2">
              <button
                onClick={onNavigateDashboard}
                className="flex items-center gap-2.5 px-6 py-3.5 bg-gradient-to-r from-cyan-500 via-sky-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold text-sm rounded-xl shadow-[0_0_25px_rgba(66,217,245,0.35)] hover:shadow-[0_0_35px_rgba(66,217,245,0.55)] transition-all cursor-pointer transform hover:-translate-y-0.5 focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none"
              >
                <Zap className="w-4 h-4 text-slate-950 fill-slate-950" />
                <span>Explore Live Intelligence</span>
                <ArrowRight className="w-4 h-4" />
              </button>

              <button
                onClick={() => onScrollToSection('capabilities')}
                className="flex items-center gap-2 px-5 py-3.5 bg-slate-900/70 hover:bg-slate-800 text-slate-200 hover:text-cyan-400 font-mono text-xs uppercase tracking-wider rounded-xl border border-slate-700/70 hover:border-cyan-500/40 transition-all cursor-pointer backdrop-blur-sm focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none"
              >
                <span>Discover Capabilities</span>
                <ChevronDown className="w-4 h-4 text-slate-400" />
              </button>
            </div>

            {/* Compact Value Proposition Pillars */}
            <div className="pt-6 grid grid-cols-1 sm:grid-cols-3 gap-3 border-t border-slate-800/80">
              <div className="p-3 rounded-lg bg-slate-900/40 border border-slate-800/80 space-y-1">
                <div className="flex items-center gap-2 text-cyan-400 font-mono text-xs font-semibold">
                  <Radio className="w-3.5 h-3.5" />
                  <span>Multi-Source Ingestion</span>
                </div>
                <p className="text-[11px] text-slate-400 leading-snug">
                  Automated scraping across BBC, Al Jazeera, UN News, & Defense Feeds.
                </p>
              </div>

              <div className="p-3 rounded-lg bg-slate-900/40 border border-slate-800/80 space-y-1">
                <div className="flex items-center gap-2 text-cyan-400 font-mono text-xs font-semibold">
                  <Globe2 className="w-3.5 h-3.5" />
                  <span>Geospatial Mapping</span>
                </div>
                <p className="text-[11px] text-slate-400 leading-snug">
                  Offline GeoNames cache with country-level centroid fallbacks.
                </p>
              </div>

              <div className="p-3 rounded-lg bg-slate-900/40 border border-slate-800/80 space-y-1">
                <div className="flex items-center gap-2 text-cyan-400 font-mono text-xs font-semibold">
                  <Cpu className="w-3.5 h-3.5" />
                  <span>NLP Threat Scoring</span>
                </div>
                <p className="text-[11px] text-slate-400 leading-snug">
                  spaCy entity ruler identifying weapon systems & multi-factor scores.
                </p>
              </div>
            </div>
          </div>

          {/* Right Column: Geospatial Radar Visual */}
          <div className="lg:col-span-5 flex justify-center">
            <HeroRadarVisual />
          </div>
        </div>
      </div>
    </section>
  );
};
