/**
 * Local API client for S&P Sentinel backend.
 */

export interface HealthResponse {
  status: string;
  project: string;
  version: string;
  mode: string;
  timestamp: string;
  datasets_ready: boolean;
  environment: {
    offline_only: boolean;
    external_apis: boolean;
    database_ready: boolean;
  };
}

export interface DatasetItem {
  file_path: string;
  format: string;
  description: string;
  is_synthetic: boolean;
  license?: string;
  sha256?: string;
  byte_size?: number;
  record_count: number;
}

export interface ManifestResponse {
  manifest_version: string;
  author: string;
  compliance: {
    synthetic_data_disclosed: boolean;
    hackathon_guidelines_section_8_compliant: boolean;
  };
  datasets: DatasetItem[];
}

const API_BASE = '/api';

export async function fetchHealth(): Promise<HealthResponse> {
  const resp = await fetch(`${API_BASE}/health`);
  if (!resp.ok) {
    throw new Error(`Health check failed: HTTP ${resp.status}`);
  }
  return resp.json();
}

export async function fetchDatasets(): Promise<ManifestResponse> {
  const resp = await fetch(`${API_BASE}/datasets`);
  if (!resp.ok) {
    throw new Error(`Dataset manifest fetch failed: HTTP ${resp.status}`);
  }
  return resp.json();
}
