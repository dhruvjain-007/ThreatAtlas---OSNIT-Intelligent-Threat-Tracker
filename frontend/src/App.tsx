import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { Header } from './components/Header';
import { FilterPanel } from './components/FilterPanel';
import { GlobeViewer } from './components/GlobeViewer';
import { EventDetailDrawer } from './components/EventDetailDrawer';
import { PlaybackSlider } from './components/PlaybackSlider';
import { checkHealth, fetchEvents, fetchGlobalMetrics } from './api/client';
import { wsService } from './api/websocket';
import type { Event, EventFilters, EventGlobalMetrics } from './types';
import { AlertCircle, RefreshCw, Zap, X } from 'lucide-react';

export const App: React.FC = () => {
  const [isOnline, setIsOnline] = useState<boolean>(true);
  const [filters, setFilters] = useState<EventFilters>({});
  const [events, setEvents] = useState<Event[]>([]); // Normal dashboard events (default limit)
  const [playbackEvents, setPlaybackEvents] = useState<Event[]>([]); // Bounded large dataset for playback
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [showHeatmap, setShowHeatmap] = useState<boolean>(false);
  const [playbackTime, setPlaybackTime] = useState<number | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [liveToast, setLiveToast] = useState<{ message: string; threatLevel: string } | null>(null);
  const [globalMetrics, setGlobalMetrics] = useState<EventGlobalMetrics>({
    total: 0,
    high: 0,
    medium: 0,
    low: 0,
  });

  // Derived visible events based on temporal playback
  const visibleEvents = useMemo(() => {
    if (playbackTime === null) return events;
    return playbackEvents.filter(e => new Date(e.event_timestamp).getTime() <= playbackTime);
  }, [events, playbackEvents, playbackTime]);

  // When selected event becomes hidden by playback, clear selection
  useEffect(() => {
    if (selectedEvent && playbackTime !== null) {
      if (new Date(selectedEvent.event_timestamp).getTime() > playbackTime) {
        setSelectedEvent(null);
      }
    }
  }, [playbackTime, selectedEvent]);

  // Load global metrics from API
  const loadMetrics = useCallback(async () => {
    try {
      const metrics = await fetchGlobalMetrics();
      setGlobalMetrics(metrics);
    } catch (err) {
      console.error('Failed to load global metrics:', err);
    }
  }, []);

  // Load events from API
  const loadEvents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const healthy = await checkHealth();
      setIsOnline(healthy);

      // Fetch normal dashboard events
      const res = await fetchEvents(filters);
      setEvents(res.items);

      // Fetch a bounded large dataset for complete historical playback (Issue #18)
      const playbackRes = await fetchEvents(filters, 10000);
      setPlaybackEvents(playbackRes.items);
    } catch (err: any) {
      console.error('Failed to load events:', err);
      setIsOnline(false);
      setError('Unable to connect to FastAPI backend at http://localhost:8000/api/v1. Ensure the Python backend is running.');
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadEvents();
  }, [loadEvents]);

  useEffect(() => {
    loadMetrics();
  }, [loadMetrics]);

  // Subscribe to Real-Time WebSocket Events
  useEffect(() => {
    const unsubscribe = wsService.subscribe((incomingEvent: Event, action: string) => {
      console.log(`[App] Real-Time WebSocket Event (${action}):`, incomingEvent);

      setEvents((prevEvents) => {
        const index = prevEvents.findIndex((e) => e.id === incomingEvent.id);
        if (index >= 0) {
          const updated = [...prevEvents];
          updated[index] = incomingEvent;
          return updated;
        } else {
          return [incomingEvent, ...prevEvents];
        }
      });

      if (action === 'created' || action === 'updated' || action === 'merged') {
        loadMetrics();
      }

      // Trigger Live Toast Alert
      const toastMsg = `Live Event ${action.toUpperCase()}: ${incomingEvent.title}`;
      setLiveToast({ message: toastMsg, threatLevel: incomingEvent.threat_level });

      setTimeout(() => {
        setLiveToast(null);
      }, 6000);
    });

    return () => {
      unsubscribe();
    };
  }, []);

  return (
    <div className="w-screen h-screen flex flex-col bg-slate-950 text-slate-100 overflow-hidden font-sans select-none">
      {/* Header */}
      <Header
        isOnline={isOnline}
        globalMetrics={globalMetrics}
        onRefresh={() => {
          loadEvents();
          loadMetrics();
        }}
      />

      {/* Main Viewport */}
      <div className="flex-1 flex relative overflow-hidden">
        {/* Left Filter & Stream Sidebar */}
        <FilterPanel
          filters={filters}
          onFilterChange={setFilters}
          events={playbackTime === null ? events : visibleEvents.slice(0, 100)}
          selectedEvent={selectedEvent}
          onSelectEvent={setSelectedEvent}
          globalMetrics={globalMetrics}
          showHeatmap={showHeatmap}
          onHeatmapToggle={() => setShowHeatmap((prev) => !prev)}
        />

        {/* Center 3D Globe Viewer */}
        <main className="flex-1 relative">
          {/* Real-Time Toast Banner Notification */}
          {liveToast && (
            <div className="absolute top-4 left-1/2 -translate-x-1/2 z-50 bg-blue-950/95 border border-blue-500/80 text-blue-100 px-5 py-3 rounded-xl shadow-2xl backdrop-blur-md flex items-center gap-3 font-mono text-xs animate-bounce">
              <Zap className="w-4 h-4 text-blue-400 animate-pulse shrink-0" />
              <span>{liveToast.message}</span>
              <button onClick={() => setLiveToast(null)} className="text-blue-400 hover:text-white ml-2 cursor-pointer">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {/* Connection Error Banner */}
          {error && (
            <div className="absolute top-4 left-4 right-4 z-40 bg-red-950/90 border border-red-800 text-red-200 p-4 rounded-lg flex items-center justify-between shadow-2xl backdrop-blur-md font-mono text-xs">
              <div className="flex items-center gap-3">
                <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
                <span>{error}</span>
              </div>
              <button
                onClick={loadEvents}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-red-900 hover:bg-red-800 text-white rounded font-medium cursor-pointer transition-all shrink-0"
              >
                <RefreshCw className="w-3.5 h-3.5" /> Retry
              </button>
            </div>
          )}

          {/* Loading Overlay */}
          {loading && (
            <div className="absolute top-4 right-4 z-20 bg-slate-900/80 border border-slate-800 text-slate-300 px-3 py-1.5 rounded-md font-mono text-xs flex items-center gap-2 backdrop-blur-sm">
              <RefreshCw className="w-3.5 h-3.5 animate-spin text-blue-400" />
              <span>Fetching Intelligence...</span>
            </div>
          )}

          {/* Cesium Globe */}
          <GlobeViewer
            events={visibleEvents}
            selectedEvent={selectedEvent}
            onSelectEvent={setSelectedEvent}
            showHeatmap={showHeatmap}
          />
          {/* Temporal Playback Slider */}
          <PlaybackSlider
            events={playbackEvents} // Pass full filtered dataset to calculate range
            playbackTime={playbackTime}
            setPlaybackTime={setPlaybackTime}
          />
        </main>

        {/* Right Event Intelligence Detail Drawer */}
        <EventDetailDrawer
          event={selectedEvent}
          onClose={() => setSelectedEvent(null)}
        />
      </div>
    </div>
  );
};

export default App;
