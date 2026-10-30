import React from 'react';
import { Shield, ExternalLink, ArrowRight } from 'lucide-react';

interface LandingFooterProps {
  onNavigateDashboard: () => void;
  onScrollToSection: (id: string) => void;
}

export const LandingFooter: React.FC<LandingFooterProps> = ({
  onNavigateDashboard,
  onScrollToSection,
}) => {
  return (
    <footer className="border-t border-slate-800/80 bg-[#06090F] py-12 text-slate-400 font-sans">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-8 items-start justify-between">
          {/* Brand & Mission Statement */}
          <div className="md:col-span-6 space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
                <Shield className="w-5 h-5" />
              </div>
              <span className="text-base font-bold tracking-wider text-slate-100 uppercase">
                Threat<span className="text-cyan-400 font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 to-sky-300">Atlas</span>
              </span>
              <span className="px-1.5 py-0.5 text-[9px] font-mono tracking-widest bg-cyan-950/60 text-cyan-300 border border-cyan-800/60 rounded uppercase">
                OSINT v1.0
              </span>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed max-w-md">
              ThreatAtlas is an open-source intelligence platform engineered for defensive threat tracking,
              multimodal event extraction, and 3D geospatial situational awareness. Built with React, CesiumJS,
              FastAPI, spaCy, and MongoDB.
            </p>
          </div>

          {/* Navigation Links */}
          <div className="md:col-span-3 space-y-3">
            <p className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">Navigation</p>
            <ul className="space-y-2 text-xs font-mono">
              <li>
                <button
                  onClick={() => onScrollToSection('overview')}
                  className="hover:text-cyan-400 transition-colors cursor-pointer"
                >
                  Overview
                </button>
              </li>
              <li>
                <button
                  onClick={() => onScrollToSection('preview')}
                  className="hover:text-cyan-400 transition-colors cursor-pointer"
                >
                  Live Intelligence Preview
                </button>
              </li>
              <li>
                <button
                  onClick={() => onScrollToSection('capabilities')}
                  className="hover:text-cyan-400 transition-colors cursor-pointer"
                >
                  Core Capabilities
                </button>
              </li>
              <li>
                <button
                  onClick={() => onScrollToSection('how-it-works')}
                  className="hover:text-cyan-400 transition-colors cursor-pointer"
                >
                  Pipeline Workflow
                </button>
              </li>
              <li>
                <button
                  onClick={onNavigateDashboard}
                  className="text-cyan-400 hover:text-cyan-300 transition-colors cursor-pointer font-bold flex items-center gap-1"
                >
                  <span>Launch 3D Dashboard</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </li>
            </ul>
          </div>

          {/* Project Context & Links */}
          <div className="md:col-span-3 space-y-3">
            <p className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">Repository & Docs</p>
            <div className="space-y-2 text-xs font-mono">
              <a
                href="https://github.com/dhruvjain-007/ThreatAtlas---OSNIT-Intelligent-Threat-Tracker"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-slate-300 hover:text-cyan-400 transition-colors"
              >
                <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    fillRule="evenodd"
                    clipRule="evenodd"
                    d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
                  />
                </svg>
                <span>GitHub Repository</span>
                <ExternalLink className="w-3.5 h-3.5 opacity-70" />
              </a>
              <p className="text-[11px] text-slate-400 leading-normal">
                Open-source defense threat tracker capstone demonstration project.
              </p>
            </div>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="mt-10 pt-6 border-t border-slate-800/80 flex flex-col sm:flex-row items-center justify-between gap-4 text-[11px] font-mono text-slate-400">
          <p>© {new Date().getFullYear()} ThreatAtlas. Open-source defensive intelligence tracker.</p>
          <div className="flex items-center gap-4">
            <span>FastAPI • CesiumJS • React 19 • Tailwind CSS</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
