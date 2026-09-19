import React, { useEffect, useState, useMemo, useRef } from 'react';
import { Play, Pause, RotateCcw, Clock } from 'lucide-react';
import type { Event } from '../types';

interface PlaybackSliderProps {
  events: Event[];
  playbackTime: number | null;
  setPlaybackTime: React.Dispatch<React.SetStateAction<number | null>>;
}

export const PlaybackSlider: React.FC<PlaybackSliderProps> = ({ events, playbackTime, setPlaybackTime }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [presetTimeWindow, setPresetTimeWindow] = useState<{ start: number; end: number } | null>(null);
  const playIntervalRef = useRef<number | null>(null);

  // Calculate full timeline range based on data
  const fullRange = useMemo(() => {
    if (events.length === 0) return { minTime: 0, maxTime: 0 };
    const times = events.map((e) => new Date(e.event_timestamp).getTime());
    return {
      minTime: Math.min(...times),
      maxTime: Math.max(...times),
    };
  }, [events]);

  // Apply active preset bounds
  const minTime = presetTimeWindow ? presetTimeWindow.start : fullRange.minTime;
  const maxTime = presetTimeWindow ? presetTimeWindow.end : fullRange.maxTime;

  const hasRange = minTime < maxTime;
  const isDisabled = events.length === 0;

  // Histogram calculation
  const BUCKETS = 60;
  const histogram = useMemo(() => {
    if (events.length === 0 || !hasRange) return Array(BUCKETS).fill(0);
    const buckets = Array(BUCKETS).fill(0);
    const range = maxTime - minTime;

    events.forEach(e => {
      const ts = new Date(e.event_timestamp).getTime();
      if (ts >= minTime && ts <= maxTime) {
        let index = Math.floor(((ts - minTime) / range) * BUCKETS);
        if (index >= BUCKETS) index = BUCKETS - 1;
        if (index < 0) index = 0;
        buckets[index]++;
      }
    });

    const maxCount = Math.max(...buckets, 1);
    return buckets.map(count => count / maxCount);
  }, [events, minTime, maxTime, hasRange]);

  // Cleanup on unmount or when pausing
  useEffect(() => {
    if (!isPlaying && playIntervalRef.current) {
      window.clearInterval(playIntervalRef.current);
      playIntervalRef.current = null;
    }
    return () => {
      if (playIntervalRef.current) {
        window.clearInterval(playIntervalRef.current);
        playIntervalRef.current = null;
      }
    };
  }, [isPlaying]);

  // Playback timer tick
  useEffect(() => {
    if (isPlaying && hasRange) {
      playIntervalRef.current = window.setInterval(() => {
        setPlaybackTime((prevTime) => {
          let current = prevTime;
          if (current === null || current < minTime) {
            current = minTime;
          }

          const range = maxTime - minTime;
          const stepSize = Math.max(range / 100, 1000);

          let next = current + stepSize;
          if (next >= maxTime) {
            next = maxTime;
            setIsPlaying(false);
          }
          return next;
        });
      }, 100);
    }

    return () => {
      if (playIntervalRef.current) {
        window.clearInterval(playIntervalRef.current);
        playIntervalRef.current = null;
      }
    };
  }, [isPlaying, hasRange, minTime, maxTime, setPlaybackTime]);

  const handlePlayPause = () => {
    if (isDisabled) return;

    if (!isPlaying) {
      if (playbackTime === null || playbackTime >= maxTime || playbackTime < minTime) {
        setPlaybackTime(minTime);
      }
      setIsPlaying(true);
    } else {
      setIsPlaying(false);
    }
  };

  const handleReset = () => {
    setIsPlaying(false);
    setPlaybackTime(null);
  };

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (isDisabled) return;
    setIsPlaying(false);
    const value = parseInt(e.target.value, 10);
    setPlaybackTime(value >= maxTime ? null : value);
  };

  const [isCustomRange, setIsCustomRange] = useState(false);

  const applyPreset = (hours: number | 'custom' | null) => {
    if (hours === 'custom') {
      setIsCustomRange(true);
      if (!presetTimeWindow) {
        setPresetTimeWindow({ start: fullRange.minTime, end: fullRange.maxTime });
      }
    } else {
      setIsCustomRange(false);
      if (hours === null) {
        setPresetTimeWindow(null);
      } else {
        const end = fullRange.maxTime;
        const start = Math.max(fullRange.minTime, end - (hours * 60 * 60 * 1000));
        setPresetTimeWindow({ start, end });
        if (playbackTime !== null && (playbackTime < start || playbackTime > end)) {
          setPlaybackTime(null); // Reset visibility to the new current time context
        }
      }
    }
  };

  if (isDisabled) {
    return null;
  }

  const currentDisplayTime = playbackTime !== null ? playbackTime : maxTime;

  return (
    <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-40 bg-slate-950/70 border border-slate-800/60 text-slate-200 px-6 py-4 rounded-2xl shadow-[0_10px_30px_rgba(0,0,0,0.5)] backdrop-blur-xl flex flex-col gap-4 min-w-[550px] max-w-[90vw]">

      {/* Header & Presets */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Clock className="w-4 h-4 text-blue-400" />
          <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-300">
            Temporal Timeline
          </h3>
          <div className="flex bg-slate-900/50 rounded-lg p-0.5 border border-slate-800/50">
            <button onClick={() => applyPreset(24)} className={`px-2 py-1 text-[10px] font-mono rounded ${!isCustomRange && presetTimeWindow && presetTimeWindow.start === fullRange.maxTime - (24*3600000) ? 'bg-blue-900/60 text-blue-300' : 'text-slate-400 hover:text-slate-200'}`}>24H</button>
            <button onClick={() => applyPreset(24*7)} className={`px-2 py-1 text-[10px] font-mono rounded ${!isCustomRange && presetTimeWindow && presetTimeWindow.start === fullRange.maxTime - (24*7*3600000) ? 'bg-blue-900/60 text-blue-300' : 'text-slate-400 hover:text-slate-200'}`}>7D</button>
            <button onClick={() => applyPreset(24*30)} className={`px-2 py-1 text-[10px] font-mono rounded ${!isCustomRange && presetTimeWindow && presetTimeWindow.start === fullRange.maxTime - (24*30*3600000) ? 'bg-blue-900/60 text-blue-300' : 'text-slate-400 hover:text-slate-200'}`}>30D</button>
            <button onClick={() => applyPreset('custom')} className={`px-2 py-1 text-[10px] font-mono rounded ${isCustomRange ? 'bg-blue-900/60 text-blue-300' : 'text-slate-400 hover:text-slate-200'}`}>CUSTOM</button>
            <button onClick={() => applyPreset(null)} className={`px-2 py-1 text-[10px] font-mono rounded ${!isCustomRange && presetTimeWindow === null ? 'bg-blue-900/60 text-blue-300' : 'text-slate-400 hover:text-slate-200'}`}>ALL</button>
          </div>

          {isCustomRange && presetTimeWindow && (
            <div className="flex items-center gap-2 text-[10px] font-mono text-slate-400 ml-2">
              <input
                type="datetime-local"
                className="bg-slate-900/80 border border-slate-700 rounded px-1.5 py-1 focus:ring-1 focus:ring-blue-500 outline-none"
                value={new Date(presetTimeWindow.start - new Date().getTimezoneOffset() * 60000).toISOString().slice(0,16)}
                onChange={(e) => {
                  const ts = new Date(e.target.value).getTime();
                  if (!isNaN(ts)) setPresetTimeWindow(prev => ({ start: ts, end: prev?.end || fullRange.maxTime }));
                }}
              />
              <span>TO</span>
              <input
                type="datetime-local"
                className="bg-slate-900/80 border border-slate-700 rounded px-1.5 py-1 focus:ring-1 focus:ring-blue-500 outline-none"
                value={new Date(presetTimeWindow.end - new Date().getTimezoneOffset() * 60000).toISOString().slice(0,16)}
                onChange={(e) => {
                  const ts = new Date(e.target.value).getTime();
                  if (!isNaN(ts)) setPresetTimeWindow(prev => ({ start: prev?.start || fullRange.minTime, end: ts }));
                }}
              />
            </div>
          )}
        </div>
        <div className="text-xs font-mono text-blue-300 font-bold bg-blue-950/50 px-2 py-1 rounded shadow-inner shadow-blue-900/20">
          {new Date(currentDisplayTime).toLocaleString()}
        </div>
      </div>

      {/* Playback Controls & Histogram Slider */}
      <div className="flex items-end gap-4">
        <div className="flex items-center gap-2 shrink-0 mb-1">
          <button
            onClick={handlePlayPause}
            disabled={isDisabled || !hasRange}
            className={`p-2 rounded-lg border transition-all focus:ring-2 focus:ring-blue-500/50 outline-none ${
              isPlaying
                ? 'bg-amber-900/50 border-amber-800/60 text-amber-400 hover:bg-amber-900/70 hover:shadow-[0_0_10px_rgba(217,119,6,0.2)]'
                : 'bg-blue-900/40 border-blue-800/60 text-blue-400 hover:bg-blue-900/60 hover:shadow-[0_0_10px_rgba(59,130,246,0.2)]'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
            title={isPlaying ? 'Pause' : 'Play'}
          >
            {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
          </button>

          <button
            onClick={handleReset}
            disabled={isDisabled || playbackTime === null}
            className="p-2 rounded-lg border border-slate-700/60 bg-slate-800/40 text-slate-400 hover:bg-slate-800/60 hover:text-slate-200 transition-all disabled:opacity-50 disabled:cursor-not-allowed focus:ring-2 focus:ring-slate-500/50 outline-none hover:shadow-[0_0_10px_rgba(148,163,184,0.1)]"
            title="Reset"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 flex flex-col gap-1 relative">
          <div className="flex items-end justify-between px-1 h-8 gap-[1px]">
            {histogram.map((val, idx) => (
              <div
                key={idx}
                className={`flex-1 rounded-t-sm transition-all duration-300 ${val > 0 ? 'bg-blue-500/40' : 'bg-transparent'}`}
                style={{ height: `${Math.max(val * 100, 5)}%`, opacity: val > 0 ? 1 : 0.2 }}
              />
            ))}
          </div>
          <div className="flex items-center gap-3">
            <span className="text-[10px] font-mono text-slate-500 shrink-0 w-16 text-right">
              {new Date(minTime).toLocaleDateString()}
            </span>
            <input
              type="range"
              min={minTime}
              max={maxTime}
              value={currentDisplayTime}
              onChange={handleSliderChange}
              disabled={isDisabled || !hasRange}
              className="flex-1 h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 relative z-10"
            />
            <span className="text-[10px] font-mono text-slate-500 shrink-0 w-16">
              {new Date(maxTime).toLocaleDateString()}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
