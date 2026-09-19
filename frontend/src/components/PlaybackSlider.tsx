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
  const playIntervalRef = useRef<number | null>(null);

  // Calculate timeline range
  const { minTime, maxTime } = useMemo(() => {
    if (events.length === 0) return { minTime: 0, maxTime: 0 };
    const times = events.map((e) => new Date(e.event_timestamp).getTime());
    return {
      minTime: Math.min(...times),
      maxTime: Math.max(...times),
    };
  }, [events]);

  const hasRange = minTime < maxTime;
  const isDisabled = events.length === 0;

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
          if (current === null) {
            current = minTime;
          }

          // Calculate step size (e.g., traverse the whole range in 10 seconds at 100ms ticks = 100 steps)
          // Steps: duration = 10000ms. interval = 100ms. steps = 100.
          const range = maxTime - minTime;
          const stepSize = Math.max(range / 100, 1000); // minimum step size 1 second

          let next = current + stepSize;
          if (next >= maxTime) {
            next = maxTime;
            setIsPlaying(false);
          }
          return next;
        });
      }, 100);
    }

    // Proper cleanup of interval to prevent duplicates when dependencies change
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
      // If we are at the end (or don't have a time), reset to start before playing
      if (playbackTime === null || playbackTime >= maxTime) {
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

  if (isDisabled) {
    return null; // Don't show if no events to scrub
  }

  const currentDisplayTime = playbackTime !== null ? playbackTime : maxTime;

  return (
    <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-40 bg-slate-950/70 border border-slate-800/60 text-slate-200 px-6 py-4 rounded-2xl shadow-[0_10px_30px_rgba(0,0,0,0.5)] backdrop-blur-xl flex flex-col gap-3 min-w-[500px]">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-blue-400" />
          <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-300">
            Temporal Playback
          </h3>
        </div>
        <div className="text-xs font-mono text-blue-300 font-bold bg-blue-950/50 px-2 py-1 rounded shadow-inner shadow-blue-900/20">
          {new Date(currentDisplayTime).toLocaleString()}
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 shrink-0">
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

        <div className="flex-1 flex items-center gap-3">
          <span className="text-[10px] font-mono text-slate-500 shrink-0">
            {new Date(minTime).toLocaleDateString()}
          </span>
          <input
            type="range"
            min={minTime}
            max={maxTime}
            value={currentDisplayTime}
            onChange={handleSliderChange}
            disabled={isDisabled || !hasRange}
            className="flex-1 h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-blue-500 focus:outline-none"
          />
          <span className="text-[10px] font-mono text-slate-500 shrink-0">
            {new Date(maxTime).toLocaleDateString()}
          </span>
        </div>
      </div>
    </div>
  );
};
