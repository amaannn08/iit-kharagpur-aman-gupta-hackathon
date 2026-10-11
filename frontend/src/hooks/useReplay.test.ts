import { describe, expect, it, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { matchPresetFromStatus, useReplay } from './useReplay';
import type { ReplayStatus } from '../api/client';

describe('matchPresetFromStatus', () => {
  it('matches preset by exact sources (e.g. polygon_2023)', () => {
    const status: ReplayStatus = {
      run_id: 'test-run',
      scenario_id: 'polygon_2023',
      state: 'idle',
      speed: 1.0,
      current_simulated_at: null,
      total_records: 5548,
      processed_count: 301,
      pending_records: 5247,
      duplicate_count: 0,
      error_count: 0,
      sources: ['polygon_2023'],
    };
    expect(matchPresetFromStatus(status)).toBe('polygon_2023');
  });

  it('matches preset by sources when scenario_id is preset alias (polygon_news)', () => {
    const status: ReplayStatus = {
      run_id: 'test-run',
      scenario_id: 'polygon_news',
      state: 'idle',
      speed: 1.0,
      current_simulated_at: null,
      total_records: 5548,
      processed_count: 301,
      pending_records: 5247,
      duplicate_count: 0,
      error_count: 0,
      sources: ['polygon_2023'],
    };
    expect(matchPresetFromStatus(status)).toBe('polygon_2023');
  });

  it('matches multi-source preset (demo)', () => {
    const status: ReplayStatus = {
      run_id: 'test-run',
      scenario_id: 'demo',
      state: 'idle',
      speed: 1.0,
      current_simulated_at: null,
      total_records: 100,
      processed_count: 20,
      pending_records: 80,
      duplicate_count: 0,
      error_count: 0,
      sources: ['social_demo', 'news_demo'],
    };
    expect(matchPresetFromStatus(status)).toBe('demo');
  });

  it('returns real source list when sources do not match any preset', () => {
    const status: ReplayStatus = {
      run_id: 'test-run',
      scenario_id: 'custom_source_stream',
      state: 'running',
      speed: 1.0,
      current_simulated_at: null,
      total_records: 50,
      processed_count: 10,
      pending_records: 40,
      duplicate_count: 0,
      error_count: 0,
      sources: ['custom_rss_1', 'custom_twitter_2'],
    };
    expect(matchPresetFromStatus(status)).toBe('custom_rss_1, custom_twitter_2');
  });

  it('falls back to demo when status is null', () => {
    expect(matchPresetFromStatus(null)).toBe('demo');
  });
});

describe('useReplay on-load scenario sync', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url.includes('/api/replay/status')) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                run_id: 'run-poly-2023',
                scenario_id: 'polygon_news',
                state: 'idle',
                current_simulated_at: '2023-01-23T13:30:00Z',
                speed: 1.0,
                total_records: 5548,
                pending_records: 5247,
                processed_count: 301,
                duplicate_count: 0,
                error_count: 0,
                sources: ['polygon_2023'],
                source_badges: ['HISTORICAL REPLAY'],
              }),
          } as Response);
        }
        if (url.includes('/api/replay/presets')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ presets: [] }),
          } as Response);
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) } as Response);
      })
    );
  });

  it('sets selectedScenario to matching preset on load instead of defaulting to demo', async () => {
    const { result } = renderHook(() => useReplay());

    await waitFor(() => {
      expect(result.current.selectedScenario).toBe('polygon_2023');
    });
    expect(result.current.replayStatus?.run_id).toBe('run-poly-2023');
  });
});
