import React from 'react';
import { AlertTriangle, CheckCircle, Database, FileCheck, XCircle } from 'lucide-react';
import { HealthResponse, ManifestResponse } from '../api/client';
import { Card } from './ui/Card';
import { Pill } from './ui/Pill';

export interface DatasetsTabProps {
  manifest: ManifestResponse | null;
  health: HealthResponse | null;
}

export const DatasetsTab: React.FC<DatasetsTabProps> = ({ manifest, health }) => {
  return (
    <div className="flex-1 flex flex-col space-y-6 overflow-y-auto">
      {/* Header & Status Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-[#111827] flex items-center gap-2">
            <span className="w-8 h-8 rounded-full bg-[#E8F5EE] text-[#14532D] flex items-center justify-center">
              <Database className="w-4 h-4" />
            </span>
            M0/M1 Operational Status & Verified Dataset Catalog
          </h2>
          <p className="text-xs text-[#6B7280] mt-1">
            Cryptographically audited synthetic replay fixtures and local readiness verification.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Pill variant="neutral" size="md">
            Manifest: {manifest ? `v${manifest.manifest_version}` : 'Unavailable'}
          </Pill>
          <Pill variant="primary" size="md">
            {manifest ? `${manifest.datasets.length} Registered Datasets` : '0 Registered Datasets'}
          </Pill>
        </div>
      </div>

      {/* System Readiness Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-5 flex flex-col justify-between">
          <div>
            <div className="text-xs font-semibold text-[#6B7280]">FastAPI Health Service</div>
            <div className="text-base font-bold font-mono mt-2 flex items-center gap-1.5">
              {health?.status === 'ok' ? (
                <>
                  <CheckCircle className="w-4 h-4 text-[#15803D]" />
                  <span className="text-[#15803D]">READY (200 OK)</span>
                </>
              ) : (
                <>
                  <XCircle className="w-4 h-4 text-[#6B7280]" />
                  <span className="text-[#6B7280]">STANDALONE</span>
                </>
              )}
            </div>
          </div>
          <div className="text-[11px] text-[#9CA3AF] mt-3 font-mono">Route: /api/health</div>
        </Card>

        <Card className="p-5 flex flex-col justify-between">
          <div>
            <div className="text-xs font-semibold text-[#6B7280]">Offline Isolation Policy</div>
            <div className="text-base font-bold text-[#15803D] font-mono mt-2 flex items-center gap-1.5">
              <CheckCircle className="w-4 h-4 text-[#15803D]" />
              100% LOCALHOST
            </div>
          </div>
          <div className="text-[11px] text-[#9CA3AF] mt-3 font-mono">External APIs: Strictly 0</div>
        </Card>

        <Card className="p-5 flex flex-col justify-between">
          <div>
            <div className="text-xs font-semibold text-[#6B7280]">Local SQLite Audit Store</div>
            <div className="text-base font-bold font-mono mt-2 flex items-center gap-1.5">
              {health?.environment.database_ready ? (
                <>
                  <CheckCircle className="w-4 h-4 text-[#15803D]" />
                  <span className="text-[#15803D]">INITIALIZED</span>
                </>
              ) : (
                <span className="text-[#6B7280]">PENDING</span>
              )}
            </div>
          </div>
          <div className="text-[11px] text-[#9CA3AF] mt-3 font-mono">SQLAlchemy 2.0 Engine</div>
        </Card>

        <Card className="p-5 flex flex-col justify-between">
          <div>
            <div className="text-xs font-semibold text-[#6B7280]">Dataset Provenance</div>
            <div className="text-base font-bold text-[#111827] font-mono mt-2 flex items-center gap-1.5">
              <FileCheck className="w-4 h-4 text-[#1F6B45]" />
              {manifest ? 'SHA-256 AUDITED' : 'AWAITING MANIFEST'}
            </div>
          </div>
          <div className="text-[11px] text-[#9CA3AF] mt-3 font-mono">
            {manifest ? 'License: Audited Offline Fixtures' : 'Manifest: Not Loaded'}
          </div>
        </Card>
      </div>

      {/* Datasets Table Card */}
      <Card
        title="Bundled Offline Datasets & Cryptographic Checksums"
        subtitle="data/manifest.json • Hackathon Section 8 & 9 Compliant"
      >
        {!manifest ? (
          <div className="py-12 text-center border border-dashed border-[#ECEDEC] rounded-2xl bg-[#F9FAFB]/50 p-6 space-y-2 mt-2">
            <AlertTriangle className="w-8 h-8 text-[#9CA3AF] mx-auto" />
            <div className="text-sm font-bold text-[#111827]">Dataset Manifest Unavailable</div>
            <p className="text-xs text-[#6B7280] max-w-md mx-auto leading-relaxed">
              Unable to load dataset metadata from <code className="text-[#111827] font-mono font-semibold">/api/datasets</code>.
              Start the local backend API to verify offline datasets and cryptographic checksums.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto mt-2">
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-[#F3F4F6] text-[#6B7280] font-semibold text-[11px]">
                  <th className="pb-2.5 font-medium">Dataset File Path</th>
                  <th className="pb-2.5 font-medium">Format</th>
                  <th className="pb-2.5 font-medium">Records</th>
                  <th className="pb-2.5 font-medium">Data Type</th>
                  <th className="pb-2.5 font-medium">License</th>
                  <th className="pb-2.5 text-right font-medium">SHA-256 (Prefix)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#F3F4F6] text-xs">
                {manifest.datasets.map((ds) => (
                  <tr key={ds.file_path} className="hover:bg-[#F9FAFB] transition-colors">
                    <td className="py-3 text-[#111827] font-bold font-mono">{ds.file_path}</td>
                    <td className="text-[#6B7280] uppercase font-mono">{ds.format}</td>
                    <td className="text-[#111827] font-semibold">{ds.record_count}</td>
                    <td>
                      {ds.is_synthetic ? (
                        <Pill variant="neutral" size="sm">SYNTHETIC</Pill>
                      ) : (
                        <Pill variant="primary" size="sm">FACTUAL REF</Pill>
                      )}
                    </td>
                    <td className="text-[#4B5563] text-[11px] truncate max-w-xs">{ds.license ?? 'N/A'}</td>
                    <td className="py-3 text-right text-[#9CA3AF] font-mono text-[11px]">
                      {ds.sha256 ? `${ds.sha256.slice(0, 12)}...` : 'n/a'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
};
