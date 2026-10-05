import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { App } from './App';

describe('S&P Sentinel Risk Terminal', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url.includes('/api/health')) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                status: 'ok',
                project: 'S&P Sentinel',
                version: '0.1.0',
                mode: 'offline-replay',
                timestamp: '2026-03-01T12:00:00Z',
                datasets_ready: true,
                environment: {
                  offline_only: true,
                  external_apis: false,
                  database_ready: true,
                },
              }),
          } as Response);
        }
        if (url.includes('/api/datasets')) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                manifest_version: '1.0',
                author: 'Aman Gupta (IIT Kharagpur)',
                compliance: {
                  synthetic_data_disclosed: true,
                  hackathon_guidelines_section_8_compliant: true,
                },
                datasets: [
                  {
                    file_path: 'data/news_demo.csv',
                    format: 'csv',
                    record_count: 25,
                    is_synthetic: true,
                    license: 'MIT License (Project-Authored Synthetic Data)',
                    sha256: '0f4ec4ae71089cf953abf953ecd888746f56e0cba487d703220ad2d4369b32fb',
                    byte_size: 8906,
                    description: 'Curated synthetic financial news headlines',
                  },
                ],
              }),
          } as Response);
        }
        return Promise.reject(new Error(`Unhandled URL: ${url}`));
      })
    );
  });

  it('renders the header and mandatory historical replay honesty badge', async () => {
    render(<App />);

    // Assert mandatory honesty badge is present
    expect(
      screen.getByText(/HISTORICAL REPLAY \/ SYNTHETIC SCENARIO/i)
    ).toBeInTheDocument();

    // Assert candidate and app identity
    expect(screen.getByText('S&P Sentinel')).toBeInTheDocument();
    expect(screen.getByText(/Candidate: Aman Gupta \(IIT Kharagpur\)/i)).toBeInTheDocument();

    // Assert disabled replay controls badge
    expect(screen.getByText(/\[PLANNED M2: CONTROLS DISABLED\]/i)).toBeInTheDocument();

    // Wait for manifest data to load
    await waitFor(() => {
      expect(screen.getByText('data/news_demo.csv')).toBeInTheDocument();
    });
  });

  it('allows switching between terminal workspace tabs', async () => {
    render(<App />);

    // Wait for initial render and data fetch to settle
    await waitFor(() => {
      expect(screen.getByText('data/news_demo.csv')).toBeInTheDocument();
    });

    // Switch to Wholesale Stress tab
    const stressTabButton = screen.getByRole('button', { name: /Wholesale Stress \(Planned M4\)/i });
    fireEvent.click(stressTabButton);

    expect(
      screen.getByText(/Module B: Wholesale Banking Portfolio Specification/i)
    ).toBeInTheDocument();
    expect(screen.getByText('$500,000,000 USD')).toBeInTheDocument();

    // Switch to Evaluation & Governance tab
    const evalTabButton = screen.getByRole('button', { name: /Evaluation & Governance/i });
    fireEvent.click(evalTabButton);

    expect(
      screen.getByText(/Evaluation Framework & Release Gates/i)
    ).toBeInTheDocument();
  });
});
