import React from 'react';
import { Radio, Cpu, MapPin, Activity, Zap, Globe2, Layers } from 'lucide-react';

export const CapabilitiesSection: React.FC = () => {
  const capabilities = [
    {
      icon: Radio,
      title: 'Multi-Source OSINT Ingestion',
      category: 'DATA PIPELINE',
      description:
        'Continuous collection from configured international news wires and defense feeds including BBC, Al Jazeera, UN News, CrisisWatch, and Defense Blog with resilient header handling and sanitization.',
    },
    {
      icon: Cpu,
      title: 'NLP-Assisted Entity Extraction',
      category: 'NATURAL LANGUAGE PROCESSING',
      description:
        'Custom spaCy pipeline with tailored EntityRuler detecting weapon systems, military formations, defense assets, and kinetic engagement verbs to evaluate incident context.',
    },
    {
      icon: MapPin,
      title: 'Geocoding & Centroid Fallback',
      category: 'GEOLOCATION ENGINE',
      description:
        'Rapid sub-second coordinates resolution via local SQLite GeoNames database cache, equipped with automatic country-centroid fallback when regional or city-level NER is ambiguous.',
    },
    {
      icon: Activity,
      title: 'Explainable Multi-Factor Scoring',
      category: 'ANALYSIS & INDEXING',
      description:
        'Transparent threat and credibility metrics calculated from kinetic severity, military equipment grade, location frequency, and independent cross-source corroboration.',
    },
    {
      icon: Zap,
      title: 'Real-Time WebSocket Streaming',
      category: 'LIVE TELEMETRY',
      description:
        'Immediate live event broadcast powered by Redis Pub/Sub, automatic camera focus alerts, and 48-hour automated stale-threat database purging to maintain clean tactical awareness.',
    },
    {
      icon: Globe2,
      title: '3D Globe & Temporal Playback',
      category: 'INTERACTIVE VISUALIZATION',
      description:
        'Hardware-accelerated CesiumJS 3D geospatial environment featuring customizable entity pins, density heatmaps, and a temporal timeline scrubber to analyze conflict progression.',
    },
  ];

  return (
    <section id="capabilities" className="scroll-mt-20 relative py-20 lg:py-28 overflow-hidden">
      {/* Background Subtle Gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[#101923]/30 to-transparent pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Section Heading */}
        <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded bg-cyan-950/40 border border-cyan-800/40 text-cyan-400 font-mono text-[10px] tracking-widest uppercase">
            <Layers className="w-3 h-3" />
            <span>CORE ARCHITECTURE</span>
          </div>

          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-slate-100 uppercase">
            From raw signals to{' '}
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 to-sky-300">
              geographic insight.
            </span>
          </h2>

          <p className="text-sm sm:text-base text-slate-400 leading-relaxed font-normal">
            Explore the capabilities that turn incoming open-source intelligence into a verifiable, structured
            understanding of global defense and security developments.
          </p>
        </div>

        {/* 6 Capabilities Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {capabilities.map((cap, idx) => {
            const Icon = cap.icon;
            return (
              <div
                key={idx}
                className="group p-6 rounded-2xl bg-[#101923]/80 hover:bg-[#141F2B] border border-slate-800/80 hover:border-cyan-500/40 transition-all duration-300 shadow-sm hover:shadow-[0_0_25px_rgba(66,217,245,0.08)] flex flex-col justify-between"
              >
                <div className="space-y-4">
                  {/* Category Pill and Icon */}
                  <div className="flex items-center justify-between">
                    <div className="p-3 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 group-hover:scale-105 group-hover:border-cyan-400/40 transition-all">
                      <Icon className="w-5 h-5" />
                    </div>
                    <span className="text-[9px] font-mono tracking-widest text-slate-400 uppercase">
                      {cap.category}
                    </span>
                  </div>

                  {/* Title */}
                  <h3 className="text-lg font-bold text-slate-100 group-hover:text-cyan-300 transition-colors">
                    {cap.title}
                  </h3>

                  {/* Description */}
                  <p className="text-xs sm:text-sm text-slate-400 leading-relaxed">
                    {cap.description}
                  </p>
                </div>

                {/* Technical Index Footnote */}
                <div className="mt-6 pt-4 border-t border-slate-800/80 flex items-center justify-between text-[10px] font-mono text-slate-400">
                  <span>MODULE // 0{idx + 1}</span>
                  <span className="text-cyan-400/80 group-hover:text-cyan-300">VERIFIED CAPABILITY</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
