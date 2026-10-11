import { useEffect, useState } from 'react';
import { fetchLiveStatus, LiveStatusResponse } from '../api/client';

export function useLiveStatus(pollIntervalMs = 15000) {
  const [liveStatus, setLiveStatus] = useState<LiveStatusResponse | null>(null);

  useEffect(() => {
    let active = true;
    const pollLive = async () => {
      try {
        const s = await fetchLiveStatus();
        if (active) setLiveStatus(s);
      } catch {
        // ignore error
      }
    };
    pollLive();
    const interval = setInterval(pollLive, pollIntervalMs);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [pollIntervalMs]);

  return { liveStatus, setLiveStatus };
}
