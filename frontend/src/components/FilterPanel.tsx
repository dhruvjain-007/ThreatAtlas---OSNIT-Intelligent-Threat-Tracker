import React, { useState, useEffect } from 'react';
import { Search, AlertTriangle, ShieldAlert, ShieldCheck, MapPin, Calendar, Globe, X, ChevronDown } from 'lucide-react';
import type { Event, EventFilters, EventGlobalMetrics } from '../types';
import { fetchAvailableCountries, exportEvents } from '../api/client';

interface FilterPanelProps {
  filters: EventFilters;
  onFilterChange: (filters: EventFilters) => void;
  events: Event[];
  selectedEvent: Event | null;
  onSelectEvent: (event: Event) => void;
  globalMetrics: EventGlobalMetrics;
  showHeatmap: boolean;
  onHeatmapToggle: () => void;
}

export const FilterPanel: React.FC<FilterPanelProps> = ({
  filters,
  onFilterChange,
  events,
  selectedEvent,
  onSelectEvent,
  globalMetrics,
  showHeatmap,
  onHeatmapToggle,
}) => {
  const [availableCountries, setAvailableCountries] = useState<string[]>([]);
  const [isLoadingCountries, setIsLoadingCountries] = useState(false);
  const [isCountryDropdownOpen, setIsCountryDropdownOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  const handleExport = async (format: 'pdf' | 'stix') => {
    setIsExporting(true);
    try {
      await exportEvents(filters, format);
    } catch (err) {
      console.error('Failed to export events:', err);
      alert('Failed to export events. Please try again.');
    } finally {
      setIsExporting(false);
    }
  };

  useEffect(() => {
    const loadCountries = async () => {
      setIsLoadingCountries(true);
      try {
        const countries = await fetchAvailableCountries();
        setAvailableCountries(countries);
      } catch (err) {
        console.error('Failed to load available countries', err);
      } finally {
        setIsLoadingCountries(false);
      }
    };
    loadCountries();
  }, []);

  const getCountryName = (code: string) => {
    try {
      const regionNames = new Intl.DisplayNames(['en'], { type: 'region' });
      return regionNames.of(code.toUpperCase()) || code.toUpperCase();
    } catch {
      return code.toUpperCase();
    }
  };

  const highCount = globalMetrics.high;
  const medCount = globalMetrics.medium;
  const lowCount = globalMetrics.low;
  const totalCount = globalMetrics.total;

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({ ...filters, search: e.target.value });
  };

  const handleThreatLevelSelect = (level?: string) => {
    onFilterChange({ ...filters, threat_level: level });
  };

  const handleMinThreatScoreChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({ ...filters, min_threat_score: Number(e.target.value) });
  };

  const handleToggleHideLowThreat = () => {
    const isHidden = filters.min_threat_score === 40;
    onFilterChange({ ...filters, min_threat_score: isHidden ? undefined : 40 });
  };

  const handleCountryToggle = (code: string) => {
    const current = filters.countries || [];
    const updated = current.includes(code)
      ? current.filter(c => c !== code)
      : [...current, code];

    onFilterChange({ ...filters, countries: updated });
  };

  const handleClearCountries = (e: React.MouseEvent) => {
    e.stopPropagation();
    onFilterChange({ ...filters, countries: [] });
  };

  return (
    <aside className="w-96 bg-slate-950/95 border-r border-slate-800/80 flex flex-col h-[calc(100vh-4rem)] z-20 backdrop-blur-md select-none">
      {/* Search & Filter Header */}
      <div className="p-4 border-b border-slate-800/80 space-y-3">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-3 text-slate-500" />
          <input
            type="text"
            placeholder="Search events, keywords..."
            value={filters.search || ''}
            onChange={handleSearchChange}
            className="w-full pl-9 pr-4 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-all font-mono"
          />
        </div>

        {/* Threat Level Filter Tabs */}
        <div className="flex items-center gap-1 p-1 bg-slate-900/80 border border-slate-800/60 rounded-lg text-xs font-mono">
          <button
            onClick={() => handleThreatLevelSelect(undefined)}
            className={`flex-1 py-1.5 rounded text-center transition-all cursor-pointer ${
              !filters.threat_level
                ? 'bg-slate-800 text-slate-100 font-bold shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            All ({totalCount})
          </button>
          <button
            onClick={() => handleThreatLevelSelect('High')}
            className={`flex-1 py-1.5 rounded text-center transition-all cursor-pointer ${
              filters.threat_level === 'High'
                ? 'bg-red-950/80 text-red-300 font-bold border border-red-800/60'
                : 'text-slate-400 hover:text-red-400'
            }`}
          >
            High ({highCount})
          </button>
          <button
            onClick={() => handleThreatLevelSelect('Medium')}
            className={`flex-1 py-1.5 rounded text-center transition-all cursor-pointer ${
              filters.threat_level === 'Medium'
                ? 'bg-amber-950/80 text-amber-300 font-bold border border-amber-800/60'
                : 'text-slate-400 hover:text-amber-400'
            }`}
          >
            Med ({medCount})
          </button>
          <button
            onClick={() => handleThreatLevelSelect('Low')}
            className={`flex-1 py-1.5 rounded text-center transition-all cursor-pointer ${
              filters.threat_level === 'Low'
                ? 'bg-emerald-950/80 text-emerald-300 font-bold border border-emerald-800/60'
                : 'text-slate-400 hover:text-emerald-400'
            }`}
          >
            Low ({lowCount})
          </button>
        </div>

        {/* Minimum Threat Score Slider */}
        <div className="pt-2 space-y-2">
          <div className="flex items-center justify-between text-xs font-mono text-slate-300">
            <label htmlFor="minThreatScoreSlider" className="font-semibold">
              Min Threat Score: {filters.min_threat_score ?? 0}
            </label>
            <button
              onClick={handleToggleHideLowThreat}
              aria-pressed={filters.min_threat_score === 40}
              className={`px-2 py-1 rounded transition-colors ${
                filters.min_threat_score === 40
                  ? 'bg-blue-600 hover:bg-blue-500 text-white'
                  : 'bg-slate-800 hover:bg-slate-700 text-slate-300'
              }`}
            >
              Hide Low Threat (&lt;40)
            </button>
          </div>
          <input
            id="minThreatScoreSlider"
            type="range"
            min="0"
            max="100"
            step="5"
            value={filters.min_threat_score ?? 0}
            onChange={handleMinThreatScoreChange}
            aria-label="Minimum Threat Score"
            className="w-full accent-blue-500 h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer"
          />
        </div>

        {/* Country Filter */}
        <div className="pt-2 space-y-2 relative">
          <div className="flex items-center justify-between text-xs font-mono text-slate-300">
            <label className="font-semibold flex items-center gap-1">
              <Globe className="w-3.5 h-3.5 text-slate-400" /> Countries
            </label>
            {(filters.countries?.length || 0) > 0 && (
              <button
                onClick={handleClearCountries}
                className="text-[10px] bg-slate-800 hover:bg-slate-700 text-slate-300 px-1.5 py-0.5 rounded transition-colors flex items-center gap-0.5"
              >
                <X className="w-3 h-3" /> Clear
              </button>
            )}
          </div>

          <button
            onClick={() => setIsCountryDropdownOpen(!isCountryDropdownOpen)}
            className="w-full flex items-center justify-between px-3 py-2 bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-lg text-xs text-slate-300 transition-colors font-mono"
          >
            <span className="truncate">
              {isLoadingCountries ? 'Loading...' :
                (filters.countries?.length || 0) > 0
                  ? `${filters.countries!.length} selected`
                  : 'All Countries'}
            </span>
            <ChevronDown className={`w-4 h-4 text-slate-500 transition-transform ${isCountryDropdownOpen ? 'rotate-180' : ''}`} />
          </button>

          {isCountryDropdownOpen && (
            <div className="absolute top-full left-0 right-0 mt-1 max-h-48 overflow-y-auto bg-slate-900 border border-slate-700 rounded-lg shadow-xl z-50 p-1 font-mono text-xs scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent">
              {availableCountries.length === 0 && !isLoadingCountries ? (
                <div className="p-2 text-slate-500 text-center">No countries available</div>
              ) : (
                availableCountries.map(code => (
                  <label key={code} className="flex items-center gap-2 p-2 hover:bg-slate-800 rounded cursor-pointer transition-colors group">
                    <input
                      type="checkbox"
                      checked={(filters.countries || []).includes(code)}
                      onChange={() => handleCountryToggle(code)}
                      className="w-3.5 h-3.5 rounded border-slate-700 text-blue-500 bg-slate-950 focus:ring-blue-500/20 focus:ring-offset-slate-900"
                    />
                    <span className="text-slate-300 group-hover:text-slate-100 flex-1 truncate">
                      {getCountryName(code)}
                    </span>
                    <span className="text-slate-600 uppercase text-[9px]">{code}</span>
                  </label>
                ))
              )}
            </div>
          )}
        </div>

        {/* Export Controls & View Mode */}
        <div className="pt-2 flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-mono font-semibold text-slate-300">View Mode</label>
            <button
              onClick={onHeatmapToggle}
              className={`px-3 py-1 rounded text-[10px] font-mono font-bold uppercase transition-colors ${
                showHeatmap
                  ? 'bg-amber-600 hover:bg-amber-500 text-white shadow-[0_0_10px_rgba(217,119,6,0.4)]'
                  : 'bg-slate-800 hover:bg-slate-700 text-slate-400'
              }`}
            >
              {showHeatmap ? 'Heatmap ON' : 'Heatmap OFF'}
            </button>
          </div>
          {showHeatmap && (
            <div className="flex flex-col gap-1 mt-1 p-2 bg-slate-900 rounded border border-slate-800/80">
              <span className="text-[10px] font-mono text-slate-400 text-center">Threat Density</span>
              <div className="h-1.5 w-full bg-gradient-to-r from-yellow-500/20 via-orange-500/60 to-red-600 rounded"></div>
              <div className="flex justify-between text-[9px] font-mono text-slate-500">
                <span>Low</span>
                <span>Medium</span>
                <span>High</span>
              </div>
            </div>
          )}

          <div className="flex gap-2 mt-2">
            <button
              onClick={() => handleExport('pdf')}
              disabled={isExporting}
              className="flex-1 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:bg-slate-900 disabled:text-slate-600 border border-slate-700 rounded text-xs text-slate-200 font-mono transition-colors"
            >
              {isExporting ? 'Exporting...' : 'Export PDF'}
            </button>
            <button
              onClick={() => handleExport('stix')}
              disabled={isExporting}
              className="flex-1 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:bg-slate-900 disabled:text-slate-600 border border-slate-700 rounded text-xs text-slate-200 font-mono transition-colors"
            >
              {isExporting ? 'Exporting...' : 'Export STIX'}
            </button>
          </div>
        </div>
      </div>

      {/* Quick Metrics Summary */}
      <div className="grid grid-cols-3 gap-2 p-4 border-b border-slate-800/60 font-mono text-center">
        <div className="bg-red-950/20 border border-red-900/30 p-2 rounded-md">
          <div className="flex items-center justify-center gap-1 text-red-400 text-[10px] uppercase">
            <ShieldAlert className="w-3 h-3" /> High
          </div>
          <div className="text-base font-bold text-red-400">{highCount}</div>
        </div>

        <div className="bg-amber-950/20 border border-amber-900/30 p-2 rounded-md">
          <div className="flex items-center justify-center gap-1 text-amber-400 text-[10px] uppercase">
            <AlertTriangle className="w-3 h-3" /> Medium
          </div>
          <div className="text-base font-bold text-amber-400">{medCount}</div>
        </div>

        <div className="bg-emerald-950/20 border border-emerald-900/30 p-2 rounded-md">
          <div className="flex items-center justify-center gap-1 text-emerald-400 text-[10px] uppercase">
            <ShieldCheck className="w-3 h-3" /> Low
          </div>
          <div className="text-base font-bold text-emerald-400">{lowCount}</div>
        </div>
      </div>

      {/* Event List Stream */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2.5">
        <div className="flex items-center justify-between text-xs font-mono text-slate-400 px-1 mb-1">
          <span>INTELLIGENCE STREAM</span>
          <span>{events.length} DISPLAYED</span>
        </div>

        {events.length === 0 ? (
          <div className="text-center py-12 px-4 border border-dashed border-slate-800 rounded-lg text-slate-500 font-mono text-xs">
            No threat intelligence events match the current filter criteria.
          </div>
        ) : (
          events.map((evt) => {
            const isSelected = selectedEvent?.id === evt.id;
            let badgeStyle = 'bg-emerald-950/60 text-emerald-400 border-emerald-800/60';
            if (evt.threat_level === 'High') {
              badgeStyle = 'bg-red-950/80 text-red-400 border-red-800/80 animate-pulse';
            } else if (evt.threat_level === 'Medium') {
              badgeStyle = 'bg-amber-950/60 text-amber-400 border-amber-800/60';
            }

            return (
              <div
                key={evt.id}
                onClick={() => onSelectEvent(evt)}
                className={`p-3 rounded-lg border transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-slate-900 border-blue-500 shadow-md shadow-blue-950/40'
                    : 'bg-slate-900/50 border-slate-800/80 hover:bg-slate-900 hover:border-slate-700'
                }`}
              >
                <div className="flex items-start justify-between gap-2 mb-1.5">
                  <h3 className="text-xs font-semibold text-slate-200 line-clamp-1 leading-snug">
                    {evt.title}
                  </h3>
                  <span className={`px-2 py-0.5 text-[10px] font-mono font-bold rounded border uppercase ${badgeStyle}`}>
                    {evt.threat_level} ({evt.threat_score})
                  </span>
                </div>

                <div className="flex items-center gap-3 text-[11px] font-mono text-slate-400">
                  {evt.location_name && (
                    <span className="flex items-center gap-1">
                      <MapPin className="w-3 h-3 text-slate-500" />
                      {evt.location_name}
                    </span>
                  )}
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3 h-3 text-slate-500" />
                    {new Date(evt.event_timestamp).toLocaleDateString()}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
};
