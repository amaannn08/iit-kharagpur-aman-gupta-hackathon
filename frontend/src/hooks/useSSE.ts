import { useEffect, useRef, useState } from 'react';
import { ReplayStatus, RiskSignal, StressRunResult } from '../api/client';

export interface UseSSEOptions {
  onSignal?: (signal: RiskSignal) => void;
  onStressRun?: (stressRun: StressRunResult) => void;
  onReplayStatus?: (status: ReplayStatus) => void;
}

export function useSSE(options: UseSSEOptions = {}) {
  const [sseConnected, setSseConnected] = useState<boolean>(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  const onSignalRef = useRef(options.onSignal);
  const onStressRunRef = useRef(options.onStressRun);
  const onReplayStatusRef = useRef(options.onReplayStatus);

  useEffect(() => {
    onSignalRef.current = options.onSignal;
    onStressRunRef.current = options.onStressRun;
    onReplayStatusRef.current = options.onReplayStatus;
  });

  useEffect(() => {
    try {
      const es = new EventSource('/api/events/stream');
      eventSourceRef.current = es;

      es.addEventListener('open', () => {
        setSseConnected(true);
      });

      es.addEventListener('signal', (event) => {
        try {
          const sig: RiskSignal = JSON.parse(event.data);
          onSignalRef.current?.(sig);
        } catch {
          // ignore parse error
        }
      });

      es.addEventListener('signal_emitted', (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.signal) onSignalRef.current?.(payload.signal);
          if (payload.stress_run) onStressRunRef.current?.(payload.stress_run);
        } catch {
          // ignore parse error
        }
      });

      es.addEventListener('stress_run', (event) => {
        try {
          const sRun: StressRunResult = JSON.parse(event.data);
          onStressRunRef.current?.(sRun);
        } catch {
          // ignore parse error
        }
      });

      es.addEventListener('replay_status', (event) => {
        try {
          const st: ReplayStatus = JSON.parse(event.data);
          onReplayStatusRef.current?.(st);
        } catch {
          // ignore parse error
        }
      });

      es.onerror = () => {
        setSseConnected(false);
      };

      return () => {
        es.close();
      };
    } catch {
      setSseConnected(false);
    }
  }, []);

  return { sseConnected, eventSourceRef };
}
