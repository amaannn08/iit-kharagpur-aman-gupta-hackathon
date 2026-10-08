/**
 * Local API client for S&P Sentinel backend.
 * Conforms to 100% offline localhost runtime policy.
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

export interface ReplayStatus {
  run_id: string;
  state: 'idle' | 'running' | 'paused' | 'draining' | 'completed' | 'failed';
  speed: number;
  simulated_at: string | null;
  total_records: number;
  processed_count: number;
  pending_count: number;
  duplicate_count: number;
  error_count: number;
  is_paused: boolean;
  is_completed: boolean;
}

export interface EntityReference {
  name: string;
  ticker: string | null;
  scope: string;
  resolved: boolean;
}

export interface SentimentProbabilities {
  positive: number;
  negative: number;
  neutral: number;
}

export interface SentimentOutput {
  score: number;
  label: 'positive' | 'negative' | 'neutral';
  probabilities: SentimentProbabilities;
}

export interface EventOutput {
  label: string;
  confidence: number;
  abstained: boolean;
}

export interface ImpactComponents {
  event_base: number;
  scope: number;
  explicit_severity: number;
}

export interface ImpactOutput {
  score: number;
  rubric_version: string;
  components: ImpactComponents;
}

export interface EvidenceSpan {
  start: number;
  end: number;
  text: string;
}

export interface RiskSignal {
  schema_version: string;
  signal_id: string;
  run_id: string;
  record_id: string;
  source_id: string;
  source_type: string;
  is_synthetic: boolean;
  published_at?: string;
  simulated_at?: string;
  processed_at: string;
  entity: EntityReference;
  sentiment: SentimentOutput;
  event: EventOutput;
  impact: ImpactOutput;
  evidence: EvidenceSpan[];
  duplicate_group_id?: string;
  eligible_for_action: boolean;
  action_block_reasons: string[];
}

export interface PositionStressDelta {
  position_id: string;
  asset_class: 'loan' | 'bond' | 'swap' | 'cash';
  entity_id: string;
  counterparty_name: string;
  sector: string;
  baseline_value_usd: number;
  stressed_value_usd: number;
  pnl_usd: number;
  pct_change: number;
  ecl_baseline_usd: number;
  ecl_stressed_usd: number;
  incremental_ecl_usd: number;
  market_risk_pnl_usd: number;
  applied_shock_summary: string;
}

export interface AssetClassStressSummary {
  asset_class: 'loan' | 'bond' | 'swap' | 'cash';
  baseline_value_usd: number;
  stressed_value_usd: number;
  total_pnl_usd: number;
  pct_change: number;
  credit_ecl_delta_usd: number;
  mark_to_market_pnl_usd: number;
  derivative_gross_notional_usd: number;
}

export interface SectorStressSummary {
  sector: string;
  baseline_value_usd: number;
  stressed_value_usd: number;
  total_pnl_usd: number;
  pct_change: number;
}

export interface StressRunResult {
  stress_id: string;
  run_id: string;
  executed_at: string;
  trigger_type: string;
  trigger_signal_id?: string;
  event_class: string;
  impact_score: number;
  target_entity?: string;
  target_scope: string;
  shock_parameters: Record<string, any>;
  model_version: string;
  baseline_total_book_value_usd: number;
  stressed_total_book_value_usd: number;
  total_pnl_usd: number;
  total_pnl_pct: number;
  credit_ecl_change_usd: number;
  market_mtm_change_usd: number;
  asset_class_breakdown: AssetClassStressSummary[];
  sector_breakdown: SectorStressSummary[];
  position_deltas: PositionStressDelta[];
  reconciliation_passed: boolean;
}

export interface WholesalePortfolio {
  portfolio_name: string;
  base_currency: string;
  valuation_date: string;
  summary: {
    total_book_value_usd: number;
    corporate_loans_value_usd: number;
    corporate_bonds_value_usd: number;
    cash_reserves_usd: number;
    interest_rate_swaps_mtm_usd: number;
    interest_rate_swaps_gross_notional_usd: number;
  };
  loans: any[];
  bonds: any[];
  swaps: any[];
  cash: any[];
}

export interface AnalyzeResponse {
  record: any;
  signal: RiskSignal;
  stress_run?: StressRunResult;
  is_duplicate: boolean;
  duplicate_group_id?: string;
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

export async function fetchReplayStatus(): Promise<ReplayStatus> {
  const resp = await fetch(`${API_BASE}/replay/status`);
  if (!resp.ok) {
    throw new Error(`Replay status failed: HTTP ${resp.status}`);
  }
  return resp.json();
}

export async function loadReplayScenario(scenarioId: string, sources = ['news_demo', 'social_demo']): Promise<ReplayStatus> {
  const resp = await fetch(`${API_BASE}/replay/load`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario_id: scenarioId, sources }),
  });
  if (!resp.ok) {
    throw new Error(`Load scenario failed: HTTP ${resp.status}`);
  }
  return resp.json();
}

export async function stepReplay(): Promise<any> {
  const resp = await fetch(`${API_BASE}/replay/step`, { method: 'POST' });
  if (!resp.ok) {
    throw new Error(`Replay step failed: HTTP ${resp.status}`);
  }
  return resp.json();
}

export async function pauseReplay(): Promise<ReplayStatus> {
  const resp = await fetch(`${API_BASE}/replay/pause`, { method: 'POST' });
  if (!resp.ok) {
    throw new Error(`Pause replay failed: HTTP ${resp.status}`);
  }
  return resp.json();
}

export async function resumeReplay(): Promise<ReplayStatus> {
  const resp = await fetch(`${API_BASE}/replay/resume`, { method: 'POST' });
  if (!resp.ok) {
    throw new Error(`Resume replay failed: HTTP ${resp.status}`);
  }
  return resp.json();
}

export async function resetReplay(): Promise<ReplayStatus> {
  const resp = await fetch(`${API_BASE}/replay/reset`, { method: 'POST' });
  if (!resp.ok) {
    throw new Error(`Reset replay failed: HTTP ${resp.status}`);
  }
  return resp.json();
}

export async function setReplaySpeed(speed: number): Promise<ReplayStatus> {
  const resp = await fetch(`${API_BASE}/replay/speed`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ speed }),
  });
  if (!resp.ok) {
    throw new Error(`Set speed failed: HTTP ${resp.status}`);
  }
  return resp.json();
}

export async function fetchSignals(limit = 50): Promise<RiskSignal[]> {
  const resp = await fetch(`${API_BASE}/signals?limit=${limit}`);
  if (!resp.ok) {
    throw new Error(`Fetch signals failed: HTTP ${resp.status}`);
  }
  return resp.json();
}

export async function fetchSignal(signalId: string): Promise<RiskSignal> {
  const resp = await fetch(`${API_BASE}/signals/${signalId}`);
  if (!resp.ok) {
    throw new Error(`Fetch signal detail failed: HTTP ${resp.status}`);
  }
  return resp.json();
}

export async function analyzeText(text: string, sourceType = 'news'): Promise<AnalyzeResponse> {
  const resp = await fetch(`${API_BASE}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, source_type: sourceType }),
  });
  if (!resp.ok) {
    throw new Error(`Analyze text failed: HTTP ${resp.status}`);
  }
  return resp.json();
}

export async function fetchPortfolio(): Promise<WholesalePortfolio> {
  const resp = await fetch(`${API_BASE}/portfolio`);
  if (!resp.ok) {
    throw new Error(`Fetch portfolio failed: HTTP ${resp.status}`);
  }
  return resp.json();
}

export interface SimulateStressParams {
  event_class: string;
  impact_score: number;
  target_entity?: string;
  target_scope?: string;
  is_easing?: boolean;
}

export async function simulateStress(params: SimulateStressParams): Promise<StressRunResult> {
  const resp = await fetch(`${API_BASE}/stress`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      event_class: params.event_class,
      impact_score: params.impact_score,
      target_entity: params.target_entity || null,
      target_scope: params.target_scope || 'entity',
      is_easing: params.is_easing || false,
    }),
  });
  if (!resp.ok) {
    throw new Error(`Stress simulation failed: HTTP ${resp.status}`);
  }
  return resp.json();
}

export async function fetchStressRuns(limit = 20): Promise<any[]> {
  const resp = await fetch(`${API_BASE}/stress/runs?limit=${limit}`);
  if (!resp.ok) {
    throw new Error(`Fetch stress runs failed: HTTP ${resp.status}`);
  }
  return resp.json();
}

export async function fetchStressRun(stressId: string): Promise<StressRunResult> {
  const resp = await fetch(`${API_BASE}/stress/${stressId}`);
  if (!resp.ok) {
    throw new Error(`Fetch stress run detail failed: HTTP ${resp.status}`);
  }
  return resp.json();
}
