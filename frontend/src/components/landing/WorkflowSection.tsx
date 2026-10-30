import React from 'react';
import { DownloadCloud, Cpu, Compass, Eye, CheckCircle2 } from 'lucide-react';

export const WorkflowSection: React.FC = () => {
  const steps = [
    {
      num: '01',
      title: 'Collect',
      subtitle: 'MULTI-SOURCE HARVESTING',
      icon: DownloadCloud,
      description:
        'Automated background workers poll diverse international RSS news wires and defense bulletins, normalizing article payloads and deduplicating raw entries in MongoDB.',
      tag: 'Sanitized Payloads',
    },
    {
      num: '02',
      title: 'Analyze',
      subtitle: 'NLP & THREAT SCORING',
      icon: Cpu,
      description:
        'A memory-optimized spaCy NLP engine evaluates text against defense keywords, extracts equipment and unit entities, and generates explainable threat and credibility scores.',
      tag: 'EntityRuler + Scorer',
    },
    {
      num: '03',
      title: 'Geolocate',
      subtitle: 'GAZETTEER & SPATIAL CLUSTERING',
      icon: Compass,
      description:
        'Locations resolve via an offline SQLite GeoNames gazetteer. If specific city data is missing, the engine gracefully falls back to country centroids before clustering related reports.',
      tag: 'Haversine Locality Bound',
    },
    {
      num: '04',
      title: 'Visualize',
      subtitle: 'LIVE 3D GLOBE & DISPATCH',
      icon: Eye,
      description:
        'Classified incidents broadcast via Redis Pub/Sub to active client WebSockets, dropping live tactical pins on the Cesium 3D globe and delivering geofenced webhook alerts.',
      tag: 'Real-Time Pub/Sub',
    },
  ];

  return (
    <section id="how-it-works" className="scroll-mt-20 relative py-20 lg:py-28 bg-[#101923]/30 border-t border-slate-800/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded bg-cyan-950/40 border border-cyan-800/40 text-cyan-400 font-mono text-[10px] tracking-widest uppercase">
            <Compass className="w-3 h-3" />
            <span>OPERATIONAL PIPELINE</span>
          </div>

          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-slate-100 uppercase">
            From signal to{' '}
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 to-sky-300">
              situational awareness.
            </span>
          </h2>

          <p className="text-sm sm:text-base text-slate-400 leading-relaxed font-normal">
            A deterministic, four-stage processing pipeline that converts unstructured public articles into verified,
            geospatially mapped threat intelligence.
          </p>
        </div>

        {/* 4 Steps: Horizontal Timeline on lg, Vertical on mobile */}
        <div className="relative">
          {/* Subtle Horizontal Connecting Line for Desktop */}
          <div className="hidden lg:block absolute top-1/2 left-0 right-0 h-0.5 bg-gradient-to-r from-cyan-500/20 via-cyan-500/40 to-cyan-500/20 -translate-y-8 z-0 pointer-events-none" />

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 relative z-10">
            {steps.map((st, idx) => {
              const Icon = st.icon;
              return (
                <div
                  key={idx}
                  className="group relative p-6 rounded-2xl bg-[#080D14]/90 hover:bg-[#141F2B] border border-slate-800 hover:border-cyan-500/40 transition-all duration-300 shadow-md flex flex-col justify-between"
                >
                  <div className="space-y-4">
                    {/* Header Row: Step Number & Icon */}
                    <div className="flex items-center justify-between">
                      <span className="text-2xl font-mono font-extrabold text-cyan-400/90 tracking-tight">
                        {st.num}
                      </span>
                      <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-cyan-400 group-hover:border-cyan-500/30 transition-colors">
                        <Icon className="w-4 h-4" />
                      </div>
                    </div>

                    {/* Step Subtitle Eyebrow */}
                    <p className="text-[9px] font-mono tracking-widest text-slate-400 uppercase">
                      {st.subtitle}
                    </p>

                    {/* Title */}
                    <h3 className="text-lg font-bold text-slate-100 group-hover:text-cyan-300 transition-colors">
                      {st.title}
                    </h3>

                    {/* Description */}
                    <p className="text-xs text-slate-400 leading-relaxed">
                      {st.description}
                    </p>
                  </div>

                  {/* Tag Footnote */}
                  <div className="mt-6 pt-4 border-t border-slate-800/80 flex items-center gap-1.5 text-[10px] font-mono text-cyan-300/80">
                    <CheckCircle2 className="w-3 h-3 text-cyan-400" />
                    <span>{st.tag}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
};
