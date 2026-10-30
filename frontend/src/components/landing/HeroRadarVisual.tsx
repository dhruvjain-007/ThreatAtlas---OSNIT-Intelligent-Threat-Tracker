import React from 'react';

export const HeroRadarVisual: React.FC = () => {
  return (
    <div className="relative w-full max-w-lg lg:max-w-none aspect-square sm:aspect-[4/3] lg:aspect-square flex items-center justify-center select-none overflow-hidden rounded-2xl bg-gradient-to-b from-[#101923]/90 via-[#0c141d]/90 to-[#080D14] border border-cyan-500/20 shadow-[0_0_50px_rgba(66,217,245,0.08)]">
      {/* Background Technical Grid Pattern */}
      <div
        className="absolute inset-0 opacity-25"
        style={{
          backgroundImage:
            'radial-gradient(rgba(66, 217, 245, 0.25) 1px, transparent 1px), linear-gradient(to right, rgba(66, 217, 245, 0.05) 1px, transparent 1px), linear-gradient(to bottom, rgba(66, 217, 245, 0.05) 1px, transparent 1px)',
          backgroundSize: '32px 32px, 64px 64px, 64px 64px',
        }}
      />

      {/* SVG Geospatial Radar Projection */}
      <svg
        className="w-full h-full p-4 sm:p-6"
        viewBox="0 0 500 500"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <defs>
          {/* Radar Sweep Gradient */}
          <radialGradient id="radarSweep" cx="250" cy="250" r="220" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#42D9F5" stopOpacity="0.4" />
            <stop offset="60%" stopColor="#42D9F5" stopOpacity="0.1" />
            <stop offset="100%" stopColor="#42D9F5" stopOpacity="0" />
          </radialGradient>

          {/* Node Glow Filters */}
          <filter id="cyanGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="6" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
          <filter id="amberGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="6" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Concentric Range Rings */}
        <circle cx="250" cy="250" r="220" stroke="#1E2C3D" strokeWidth="1" strokeDasharray="3 3" />
        <circle cx="250" cy="250" r="170" stroke="#1E2C3D" strokeWidth="1" />
        <circle cx="250" cy="250" r="120" stroke="#42D9F5" strokeOpacity="0.15" strokeWidth="1.2" strokeDasharray="4 2" />
        <circle cx="250" cy="250" r="65" stroke="#42D9F5" strokeOpacity="0.25" strokeWidth="1.2" />
        <circle cx="250" cy="250" r="4" fill="#42D9F5" />

        {/* Crosshair Axes & Latitude/Longitude Lines */}
        <line x1="30" y1="250" x2="470" y2="250" stroke="#1E2C3D" strokeWidth="1" strokeDasharray="2 4" />
        <line x1="250" y1="30" x2="250" y2="470" stroke="#1E2C3D" strokeWidth="1" strokeDasharray="2 4" />

        {/* Diagonal Geodetic Bearings */}
        <line x1="95" y1="95" x2="405" y2="405" stroke="#1E2C3D" strokeWidth="0.8" strokeOpacity="0.6" />
        <line x1="95" y1="405" x2="405" y2="95" stroke="#1E2C3D" strokeWidth="0.8" strokeOpacity="0.6" />

        {/* Rotating Radar Sweep Cone */}
        <g className="origin-center" style={{ transformOrigin: '250px 250px' }}>
          <path
            d="M250 250 L470 250 A220 220 0 0 0 395 105 Z"
            fill="url(#radarSweep)"
            className="animate-spin"
            style={{ animationDuration: '8s', transformOrigin: '250px 250px' }}
          />
        </g>

        {/* Latitude Arc Curvatures (Representing Globe Projections) */}
        <path d="M 50 170 Q 250 220 450 170" stroke="#42D9F5" strokeOpacity="0.12" strokeWidth="1" fill="none" />
        <path d="M 40 250 Q 250 310 460 250" stroke="#42D9F5" strokeOpacity="0.12" strokeWidth="1" fill="none" />
        <path d="M 50 330 Q 250 400 450 330" stroke="#42D9F5" strokeOpacity="0.12" strokeWidth="1" fill="none" />

        {/* Longitude Meridians */}
        <path d="M 170 40 Q 210 250 170 460" stroke="#42D9F5" strokeOpacity="0.1" strokeWidth="1" fill="none" />
        <path d="M 330 40 Q 290 250 330 460" stroke="#42D9F5" strokeOpacity="0.1" strokeWidth="1" fill="none" />

        {/* Geodesic Connection Arcs Between Tactical Hotspot Sectors */}
        <path
          d="M 160 170 Q 210 130 330 180"
          stroke="#42D9F5"
          strokeOpacity="0.6"
          strokeWidth="1.5"
          strokeDasharray="6 4"
          fill="none"
        />
        <path
          d="M 330 180 Q 380 260 360 330"
          stroke="#F0B45A"
          strokeOpacity="0.5"
          strokeWidth="1.5"
          strokeDasharray="4 4"
          fill="none"
        />

        {/* Tactical Hotspot Illustrative Nodes */}
        {/* Node 1: Black Sea Sector (Cyan) */}
        <g transform="translate(160, 170)">
          <circle r="12" fill="#42D9F5" fillOpacity="0.1" className="animate-ping" />
          <circle r="6" fill="#42D9F5" fillOpacity="0.3" filter="url(#cyanGlow)" />
          <circle r="3.5" fill="#42D9F5" />
          <circle r="9" stroke="#42D9F5" strokeWidth="1" strokeDasharray="2 2" />
        </g>

        {/* Node 2: Levant Sector (Amber - High Threat Vector) */}
        <g transform="translate(330, 180)">
          <circle r="14" fill="#F0B45A" fillOpacity="0.12" className="animate-ping" style={{ animationDuration: '3s' }} />
          <circle r="7" fill="#F0B45A" fillOpacity="0.3" filter="url(#amberGlow)" />
          <circle r="4" fill="#F0B45A" />
          <circle r="11" stroke="#F0B45A" strokeWidth="1" strokeDasharray="2 2" />
        </g>

        {/* Node 3: Maritime Strait Sector (Cyan) */}
        <g transform="translate(360, 330)">
          <circle r="5" fill="#42D9F5" fillOpacity="0.4" />
          <circle r="2.5" fill="#42D9F5" />
          <circle r="8" stroke="#42D9F5" strokeWidth="0.8" />
        </g>

        {/* Node 4: Secondary Observation Post */}
        <g transform="translate(210, 310)">
          <circle r="3" fill="#9AA9BA" fillOpacity="0.6" />
          <circle r="7" stroke="#1E2C3D" strokeWidth="1" />
        </g>
      </svg>

      {/* Floating Tactical Overlay Cards */}
      {/* Top Left Status Telemetry - Clearly Marked as Schematic */}
      <div className="absolute top-4 left-4 font-mono text-[9px] text-cyan-400/90 tracking-widest space-y-0.5 bg-[#080D14]/85 px-2.5 py-1.5 rounded border border-cyan-500/20 backdrop-blur-sm pointer-events-none">
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
          <span>RADAR DISPLAY // SCHEMATIC</span>
        </div>
        <p className="text-slate-400 text-[8px]">PROJECTION: WGS-84 / SPHERICAL</p>
      </div>

      {/* Top Right Azimuth Readout */}
      <div className="absolute top-4 right-4 font-mono text-[9px] text-right text-slate-400 tracking-wider space-y-0.5 bg-[#080D14]/85 px-2.5 py-1.5 rounded border border-slate-800 backdrop-blur-sm pointer-events-none">
        <div className="text-cyan-400/90 font-bold">46.48° N, 30.73° E</div>
        <div className="text-[8px] text-slate-400">ILLUSTRATIVE GRID</div>
      </div>

      {/* Floating Tactical Card 1: Clearly marked as an illustrative architectural model */}
      <div className="absolute bottom-14 left-4 right-4 sm:right-auto sm:left-4 sm:max-w-xs bg-[#101923]/95 border border-cyan-500/30 rounded-xl p-3 shadow-[0_0_25px_rgba(66,217,245,0.15)] backdrop-blur-md animate-feed-in">
        <div className="flex items-center justify-between text-[10px] font-mono mb-1.5">
          <span className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30 font-bold flex items-center gap-1 text-[9px]">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
            INCIDENT PREVIEW
          </span>
          <span className="text-slate-400 text-[8px] uppercase tracking-wider bg-slate-900 px-1 py-0.5 rounded border border-slate-800">
            SIMULATED
          </span>
        </div>
        <p className="text-xs font-semibold text-slate-100 leading-snug line-clamp-1">
          Air defense interception near coastal infrastructure
        </p>
        <div className="flex items-center gap-2 mt-2 pt-2 border-t border-slate-800/80 text-[9px] font-mono text-slate-400">
          <span className="text-cyan-400">NLP: Shahed-136, S-300</span>
          <span>•</span>
          <span>Multi-Source Cluster</span>
        </div>
      </div>

      {/* Bottom Center Geospatial Legend Pill */}
      <div className="absolute bottom-3 font-mono text-[8px] tracking-widest text-slate-400 uppercase bg-[#080D14]/90 px-3 py-1 rounded-full border border-slate-800 pointer-events-none">
        GEODETIC SWEEP // ARCHITECTURAL SCHEMATIC
      </div>
    </div>
  );
};
