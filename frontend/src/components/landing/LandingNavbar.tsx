import React, { useState } from 'react';
import { Shield, ArrowRight, Menu, X, ExternalLink } from 'lucide-react';

interface LandingNavbarProps {
  onNavigateDashboard: () => void;
  onScrollToSection: (id: string) => void;
}

export const LandingNavbar: React.FC<LandingNavbarProps> = ({
  onNavigateDashboard,
  onScrollToSection,
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navLinks = [
    { label: 'Overview', id: 'overview' },
    { label: 'Live Stream', id: 'preview' },
    { label: 'Capabilities', id: 'capabilities' },
    { label: 'How It Works', id: 'how-it-works' },
  ];

  const handleNavClick = (id: string) => {
    setMobileMenuOpen(false);
    onScrollToSection(id);
  };

  return (
    <header className="sticky top-0 z-50 w-full bg-[#080D14]/85 backdrop-blur-md border-b border-slate-800/80 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div
          onClick={() => handleNavClick('overview')}
          className="flex items-center gap-3 cursor-pointer select-none group"
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') handleNavClick('overview');
          }}
          aria-label="ThreatAtlas Home"
        >
          <div className="relative p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 shadow-[0_0_15px_rgba(66,217,245,0.2)] group-hover:border-cyan-400 group-hover:shadow-[0_0_20px_rgba(66,217,245,0.4)] transition-all">
            <Shield className="w-5 h-5" />
            <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-cyan-400 animate-ping opacity-75" />
            <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-cyan-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-base font-bold tracking-wider text-slate-100 uppercase">
                Threat<span className="text-cyan-400 font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 to-sky-300">Atlas</span>
              </span>
              <span className="px-1.5 py-0.5 text-[9px] font-mono tracking-widest bg-cyan-950/60 text-cyan-300 border border-cyan-800/60 rounded uppercase">
                OSINT
              </span>
            </div>
            <p className="text-[9px] text-slate-400 font-mono tracking-widest uppercase opacity-75 -mt-0.5">
              INTELLIGENCE PLATFORM
            </p>
          </div>
        </div>

        {/* Desktop Nav Items */}
        <nav className="hidden md:flex items-center gap-8" aria-label="Main Navigation">
          {navLinks.map((item) => (
            <button
              key={item.id}
              onClick={() => handleNavClick(item.id)}
              className="text-xs font-mono uppercase tracking-wider text-slate-300 hover:text-cyan-400 transition-colors cursor-pointer focus-visible:ring-2 focus-visible:ring-cyan-400 rounded px-1 py-0.5 outline-none"
            >
              {item.label}
            </button>
          ))}
          <a
            href="https://github.com/dhruvjain-007/ThreatAtlas---OSNIT-Intelligent-Threat-Tracker"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-xs font-mono uppercase tracking-wider text-slate-400 hover:text-slate-200 transition-colors focus-visible:ring-2 focus-visible:ring-cyan-400 rounded px-1 py-0.5 outline-none"
            title="View ThreatAtlas on GitHub"
          >
            <span>GitHub</span>
            <ExternalLink className="w-3 h-3 opacity-70" />
          </a>
        </nav>

        {/* Action Button */}
        <div className="hidden sm:flex items-center gap-3">
          <button
            onClick={onNavigateDashboard}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold text-xs rounded-lg shadow-[0_0_20px_rgba(66,217,245,0.3)] hover:shadow-[0_0_25px_rgba(66,217,245,0.5)] transition-all cursor-pointer transform hover:-translate-y-0.5 focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none"
          >
            <span>Launch Dashboard</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Mobile Menu Toggle Button */}
        <div className="flex md:hidden items-center gap-2">
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 rounded-lg bg-slate-900/60 border border-slate-800 text-slate-300 hover:text-cyan-400 focus-visible:ring-2 focus-visible:ring-cyan-400 outline-none cursor-pointer"
            aria-expanded={mobileMenuOpen}
            aria-label={mobileMenuOpen ? 'Close Navigation Menu' : 'Open Navigation Menu'}
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden border-b border-slate-800 bg-[#080D14]/95 backdrop-blur-xl px-4 pt-3 pb-6 space-y-3 animate-feed-in">
          {navLinks.map((item) => (
            <button
              key={item.id}
              onClick={() => handleNavClick(item.id)}
              className="w-full text-left py-2 px-3 rounded-md text-xs font-mono uppercase tracking-wider text-slate-300 hover:bg-slate-900/60 hover:text-cyan-400 transition-colors"
            >
              {item.label}
            </button>
          ))}
          <a
            href="https://github.com/dhruvjain-007/ThreatAtlas---OSNIT-Intelligent-Threat-Tracker"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-between py-2 px-3 rounded-md text-xs font-mono uppercase tracking-wider text-slate-400 hover:bg-slate-900/60 hover:text-slate-200"
          >
            <span>GitHub Repository</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
          <div className="pt-2">
            <button
              onClick={() => {
                setMobileMenuOpen(false);
                onNavigateDashboard();
              }}
              className="w-full flex items-center justify-center gap-2 py-2.5 bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 font-bold text-xs rounded-lg shadow-lg cursor-pointer"
            >
              <span>Launch Dashboard</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </header>
  );
};
