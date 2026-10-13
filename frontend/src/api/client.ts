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
  scenario_id?: string | null;
  state: 'idle' | 'running' | 'paused' | 'draining' | 'completed' | 'failed';
  speed: number;
  current_simulated_at: string | null;
  total_records: number;
  processed_count: number;
  pending_records: number;
  duplicate_count: number;
  error_count: number;
  step_count?: number;
  sources?: string[];
  source_badges?: string[];
}

export interface ReplaySource {
  source: string;
  kind: 'news' | 'social';
  badge: 'SYNTHETIC SCENARIO' | 'HISTORICAL REPLAY' | 'LIVE CAPTURE';
  path: string;
  available: boolean;
}

export interface EntityReference {
  name: string;
  ticker: string | null;
  scope: string;
  resolved: boolean;
  sector?: string | null;
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
  method?: 'rubric' | 'market_calibrated' | 'floor';
  market_calibration?: { model: string; predicted_abs_abnormal_z: number; decile: number; rubric_score: number } | null;
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
  text_excerpt?: string | null;
  model_versions?: Record<string, string>;
}

export interface LossAttribution {
  rates_usd: number;
  spread_usd: number;
  pd_usd: number;
  lgd_usd: number;
  equity_usd: number;
  operational_usd: number;
  clamp_usd: number;
}

export interface PositionStressDelta {
  position_id: string;
  asset_class: 'loan' | 'bond' | 'swap' | 'cash' | 'equity';
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
  operational_loss_usd?: number;
  applied_shock_summary: string;
  sleeve?: string;
  attribution?: LossAttribution;
  driver?: string;
}

export interface SleeveStressSummary {
  sleeve: string;
  baseline_value_usd: number;
  stressed_value_usd: number;
  total_pnl_usd: number;
  pct_change: number;
}

export interface AssetClassStressSummary {
  asset_class: 'loan' | 'bond' | 'swap' | 'cash' | 'equity';
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

export interface TopPositionLoss {
  position_id: string;
  entity_id: string;
  counterparty_name: string;
  asset_class: string;
  pnl_usd: number;
  dominant_component: string;
  driver: string;
  attribution?: Record<string, number>;
}

export interface StressAttributionSummary {
  by_component: Record<string, number>;
  by_driver: Record<string, number>;
  top_positions: TopPositionLoss[];
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
  sleeve_breakdown?: SleeveStressSummary[];
  funded_baseline_value_usd?: number;
  funded_stressed_value_usd?: number;
  derivative_mtm_change_usd?: number;
  status?: 'COMPLETED' | 'NO_EXPOSURE';
  attribution?: StressAttributionSummary;
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
  equities?: any[];
  funded_value_by_sleeve_usd?: Record<string, number>;
}

export interface AnalyzeResponse {
  record: any;
  signal: RiskSignal;
  signals?: RiskSignal[];
  stress_run?: StressRunResult;
  stress_runs?: StressRunResult[];
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

export interface ReplayPresetItem {
  id: string;
  label: string;
  sources: string[];
  badge: string;
}

export async function fetchReplayPresets(): Promise<ReplayPresetItem[]> {
  const resp = await fetch(`${API_BASE}/replay/presets`);
  if (!resp.ok) {
    throw new Error(`Fetch presets failed: HTTP ${resp.status}`);
  }
  const data = await resp.json();
  return data.presets || [];
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

export interface SignalStats {
  total_signals: number;
  actionable_count: number;
  duplicate_count: number;
  blocked_count: number;
  high_impact_count: number;
  by_event: Record<string, { eligible: number; blocked: number; total: number }>;
}

export async function fetchSignalStats(runId?: string): Promise<SignalStats> {
  const url = runId ? `${API_BASE}/signals/stats?run_id=${encodeURIComponent(runId)}` : `${API_BASE}/signals/stats`;
  const resp = await fetch(url);
  if (!resp.ok) {
    throw new Error(`Fetch signal stats failed: HTTP ${resp.status}`);
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

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, init);
  if (!resp.ok) throw new Error(`${path} failed: HTTP ${resp.status}`);
  return resp.json();
}

const postJson = <T,>(path: string, body?: unknown) =>
  getJson<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

export const fetchReplaySources = () => getJson<ReplaySource[]>('/replay/sources');
export const appendReplaySource = (source: string) => postJson<ReplayStatus>('/replay/append', { source });

export interface IndexRecord {
  timestamp: string;
  weights: Record<string, number>;
  sentiment_ema: Record<string, number>;
  turnover: number;
  reasons: Record<string, string>;
  trigger_ticker?: string | null;
}

export interface IndexCurrent {
  label: string;
  weights: Record<string, number>;
  base_weights: Record<string, number>;
  sentiment_ema: Record<string, number>;
  sectors: Record<string, string>;
  reasons: Record<string, string>;
  constraints: { name_cap: number; sector_cap: number; k: number; halflife_days: number };
  rebalances: number;
}

export const fetchIndexCurrent = () => getJson<IndexCurrent>('/index/current');
export const fetchIndexHistory = (limit = 500) => getJson<IndexRecord[]>(`/index/history?limit=${limit}`);
export const resetIndex = () => postJson<IndexCurrent>('/index/reset');

export interface StressScenario {
  scenario_id: string;
  name: string;
  description: string;
  event_class: string;
  is_synthetic?: boolean;
}

export const fetchStressScenarios = () =>
  getJson<{ scenarios: StressScenario[] }>('/stress/scenarios').then((r) => r.scenarios);
export const runStressScenario = (id: string) => postJson<StressRunResult>(`/stress/scenario/${id}`);
export const runCustomStress = (params: {
  equity_shock_pct?: number;
  benchmark_yield_shift_bps?: number;
  bond_spread_shift_bps?: number;
  loan_pd_increment?: number;
}) => postJson<StressRunResult>('/stress/custom', params);

export const fetchMetrics = () => getJson<Record<string, any>>('/datasets/metrics');

export interface LiveStatusResponse {
  mode: 'LIVE' | 'STALE' | 'REPLAY' | 'SYNTHETIC' | 'IDLE';
  last_record_at: string | null;
  last_fetch_at: string | null;
  lag_seconds: number | null;
  recorder_alive: boolean;
}

export const fetchLiveStatus = () => getJson<LiveStatusResponse>('/replay/live_status');

// --- Crisis Time Machine Types & API ---
export interface CrisisVersionComparison {
  version: 'v1' | 'v2';
  lead_time_hours: number | null;
  lead_time_display: string;
  triggered: boolean;
  status_label: string;
}

export interface CrisisSummary {
  crisis_id: string;
  name: string;
  event_class: string;
  primary_entity: string;
  entity_name: string;
  benchmark_ticker: string;
  benchmark_name: string;
  lead_time_hours: number | null;
  lead_time_display: string;
  window_start: string;
  window_end: string;
  description: string;
  triggered?: boolean;
  test_type?: 're_run_after_diagnosis' | 'blind_test';
  diagnosis_note?: string;
  v1?: CrisisVersionComparison;
  v2?: CrisisVersionComparison;
}

export interface CrisisMilestone {
  id: string;
  label: string;
  timestamp: string;
  description: string;
  source: string;
  icon?: string;
}

export interface CrisisTimelinePoint {
  timestamp: string;
  article_volume: number;
  story_intensity: number;
  benchmark_return: number;
  sample_headlines: string[];
}

export interface CrisisDetail {
  crisis_id: string;
  name: string;
  event_class: string;
  primary_entity: string;
  entity_name: string;
  benchmark_ticker: string;
  benchmark_name: string;
  lead_time_hours: number | null;
  lead_time_display: string;
  window_start: string;
  window_end: string;
  triggered?: boolean;
  trigger_time?: string | null;
  first_signal_time?: string | null;
  peak_story_intensity?: number;
  test_type?: 're_run_after_diagnosis' | 'blind_test';
  diagnosis_note?: string;
  v1?: CrisisVersionComparison;
  v2?: CrisisVersionComparison;
  naive_alert_performance: {
    naive_rule: string;
    naive_triggers: number;
    naive_first_trigger: string;
    naive_false_positives: number;
    verdict: string;
  };
  sentinel_performance: {
    sentinel_rule: string;
    sentinel_triggers: number;
    sentinel_trigger_time: string;
    sentinel_false_positives: number;
    verdict: string;
  };
  portfolio_impact: {
    portfolio_loss_usd: number;
    cet1_impact_bps: number;
    loans_migrated_stage2: number;
    staging_cliff_provision_jump_usd: number;
  };
  milestones: CrisisMilestone[];
  price_trajectory: Record<string, any>[];
  timeline_series: CrisisTimelinePoint[];
  total_articles: number;
}

export const fetchCrises = () => getJson<CrisisSummary[]>('/time-machine/crises');
export const fetchCrisisDetail = (crisisId: string) => getJson<CrisisDetail>(`/time-machine/crisis/${crisisId}`);
export const replayCrisis = (crisisId: string) => postJson<any>(`/time-machine/crisis/${crisisId}/replay`);

// --- Credit Domain Depth: EWS, IFRS 9 Staging & Reverse Stress ---
export interface EWSWatchlistItem {
  obligor_id: string;
  name: string;
  sector: string;
  rating: string;
  baseline_pd: number;
  active_story_count: number;
  peak_story_intensity: number;
  composite_score: number;
  status: 'GREEN' | 'AMBER' | 'RED';
  trigger_reasons: string[];
  recommended_action: string;
}

export interface IFRS9StageBreakdown {
  exposure_usd: number;
  ecl_usd: number;
  count: number;
}

export interface IFRS9StagingReport {
  summary: {
    total_loans: number;
    stage1_count: number;
    stage2_count: number;
    stage3_count: number;
    stage1_exposure_usd?: number;
    stage1_ecl_usd?: number;
    stage2_exposure_usd?: number;
    stage2_ecl_usd?: number;
    stage3_exposure_usd?: number;
    stage3_ecl_usd?: number;
    total_exposure_usd?: number;
    total_baseline_ecl_usd: number;
    total_stressed_ecl_usd: number;
    total_incremental_ecl_usd: number;
  };
  stage_1?: IFRS9StageBreakdown;
  stage_2?: IFRS9StageBreakdown;
  stage_3?: IFRS9StageBreakdown;
  stage_migrations?: {
    stage1_to_stage2_count: number;
    stage1_to_stage3_count: number;
    stage2_to_stage3_count: number;
  };
  staging_cliff_jump_usd: number;
  staging_cliff_total_jump_usd?: number;
  positions?: Array<{
    position_id: string;
    counterparty: string;
    sector: string;
    ead_usd: number;
    baseline_pd: number;
    stressed_pd: number;
    stage_baseline: number;
    stage_stressed: number;
    lifetime_ecl_active: boolean;
    ecl_delta_usd: number;
    sicr_triggered: boolean;
  }>;
}

export interface CapitalImpactReport {
  capital_base_tier1_usd: number;
  standardized_rwa_usd: number;
  baseline_cet1_ratio_pct: number;
  stressed_cet1_ratio_pct: number;
  cet1_ratio_impact_bps: number;
  regulatory_minimum_pct: number;
  internal_target_floor_pct: number;
  capital_breach: boolean;
}

export interface ReverseStressResponse {
  scenario_id: string;
  target_cet1_floor_pct: number;
  critical_shock_multiplier: number;
  required_loss_usd: number;
  total_loss_at_break_usd: number;
  final_cet1_ratio_pct: number;
  iterations: number;
  converged: boolean;
}

export const fetchEWSWatchlist = () => getJson<EWSWatchlistItem[]>('/stress/ews');
export const fetchIFRS9Staging = (scenarioId?: string) =>
  getJson<IFRS9StagingReport>(scenarioId ? `/stress/staging?scenario_id=${scenarioId}` : '/stress/staging');
export const fetchCapitalImpact = (totalPnlUsd = 0.0) =>
  getJson<CapitalImpactReport>(`/stress/capital?total_pnl_usd=${totalPnlUsd}`);
export const runReverseStress = (req: { scenario_id: string; target_cet1_floor?: number; max_loss_usd?: number }) =>
  postJson<ReverseStressResponse>('/stress/reverse-stress', req);
export const fetchStressMemo = (runId: string) =>
  getJson<{ run_id: string; executed_at: string; event_class: string; target_entity: string; total_pnl_usd: number; markdown: string }>(`/stress/memo/${runId}`);

// --- NLP Cascade Tiering ---
export interface CascadeResponse {
  text: string;
  label: string;
  confidence: number;
  tier_used: 'fast_tier_1' | 'deep_tier_2';
  routing_reason: string;
  latency_ms: number;
  stats: {
    total_calls: number;
    tier1_resolved: number;
    tier2_routed: number;
    routing_rate_pct: number;
    avg_latency_ms: number;
  };
}

export const analyzeCascade = (text: string) => postJson<CascadeResponse>('/analyze/cascade', { text });
export const fetchCascadeStats = () => getJson<any>('/analyze/cascade/stats');
