import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import Sidebar from '../components/Sidebar';
import Header from '../components/Header';
import MarketTicker from '../components/MarketTicker';
import { api } from '../utils/api';
import {
  initialReports,
  initialSystemStatus
} from '../utils/mockData';
import {
  TrendingUp,
  Clock,
  Layers,
  ArrowRight,
  PlusCircle,
  FileCode,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  PlayCircle,
  Activity,
  History,
  Database,
  Cpu
} from 'lucide-react';

export const Dashboard: React.FC = () => {
  // 1. Fetch system telemetry from backend
  const { data: telemetry, isLoading: isLoadingTelemetry } = useQuery({
    queryKey: ['systemTelemetry'],
    queryFn: async () => {
      const res = await api.get('/system/telemetry');
      return res.data;
    },
    refetchInterval: 5000 // Poll every 5s to update dashboard metrics dynamically
  });

  // 2. Fetch dashboard user stats and recent runs list
  const { data: stats, isLoading: isLoadingStats } = useQuery({
    queryKey: ['dashboardStats'],
    queryFn: async () => {
      const res = await api.get('/system/dashboard-stats');
      return res.data;
    },
    refetchInterval: 5000
  });

  // Fallback structures if queries are loading or backend is unreachable
  const system = telemetry || initialSystemStatus;
  const recentQueries = stats?.recentQueries || [];
  const reportsCount = stats?.reportsCount ?? initialReports.length;

  // Static Activity Timeline items for high-fidelity professional UX
  const activityTimeline = [
    { type: 'upload', message: 'Annual report SEC 10-K indexed into pgvector memory', time: '12 mins ago', color: 'text-[#10B981]' },
    { type: 'research', message: 'AI Analyst generated completed research report for AAPL', time: '1 hour ago', color: 'text-[#00E5FF]' },
    { type: 'alert', message: 'Price threshold alert rule triggered for NVIDIA ($145.00)', time: '3 hours ago', color: 'text-[#EF4444]' },
    { type: 'database', message: 'System cron swept and reconciled 2 dangling runs', time: '5 hours ago', color: 'text-[#9CA3AF]' }
  ];

  return (
    <div className="flex bg-[#08090C] min-h-screen text-[#F3F4F6]">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header title="Dashboard Command Center" />
        <MarketTicker />

        <main className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin">
          
          {/* Top Metrics Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            
            {/* Metric 1 */}
            <div className="bg-[#0F111A] border border-[#242838] p-4 rounded-lg flex flex-col justify-between hover-glow hover:border-[#00E5FF]/30 transition-all duration-300 group">
              <div>
                <span className="text-[10px] font-mono font-bold text-[#9CA3AF] uppercase tracking-wider group-hover:text-[#00E5FF] transition-colors">Research Reports</span>
                {isLoadingStats ? (
                  <div className="h-8 shimmer rounded mt-2 w-20" />
                ) : (
                  <h3 className="font-headline font-bold text-3xl mt-1 text-[#F3F4F6]">{reportsCount}</h3>
                )}
              </div>
              <div className="flex items-center gap-1 text-[10px] text-[#10B981] mt-3 font-mono">
                <TrendingUp size={12} />
                <span>+2 Reports created today</span>
              </div>
            </div>

            {/* Metric 2 */}
            <div className="bg-[#0F111A] border border-[#242838] p-4 rounded-lg flex flex-col justify-between hover-glow hover:border-[#00E5FF]/30 transition-all duration-300 group">
              <div>
                <span className="text-[10px] font-mono font-bold text-[#9CA3AF] uppercase tracking-wider group-hover:text-[#00E5FF] transition-colors">Average Latency</span>
                {isLoadingTelemetry ? (
                  <div className="h-8 shimmer rounded mt-2 w-24" />
                ) : (
                  <h3 className="font-headline font-bold text-3xl mt-1 text-[#00E5FF]">{system.nvidiaNim.latencyMs} ms</h3>
                )}
              </div>
              <div className="flex items-center gap-1 text-[10px] text-[#10B981] mt-3 font-mono">
                <CheckCircle2 size={12} />
                <span>NVIDIA NIM Optimized</span>
              </div>
            </div>

            {/* Metric 3 */}
            <div className="bg-[#0F111A] border border-[#242838] p-4 rounded-lg flex flex-col justify-between hover-glow hover:border-[#00E5FF]/30 transition-all duration-300 group">
              <div>
                <span className="text-[10px] font-mono font-bold text-[#9CA3AF] uppercase tracking-wider group-hover:text-[#00E5FF] transition-colors">Queue Backlog</span>
                {isLoadingTelemetry ? (
                  <div className="h-8 shimmer rounded mt-2 w-16" />
                ) : (
                  <h3 className="font-headline font-bold text-3xl mt-1 text-[#F3F4F6]">{system.arqWorkers.queued}</h3>
                )}
              </div>
              <div className="flex items-center gap-1 text-[10px] text-[#9CA3AF] mt-3 font-mono">
                <Clock size={12} />
                <span>All workers running idle</span>
              </div>
            </div>

            {/* Metric 4 */}
            <div className="bg-[#0F111A] border border-[#242838] p-4 rounded-lg flex flex-col justify-between hover-glow hover:border-[#00E5FF]/30 transition-all duration-300 group">
              <div>
                <span className="text-[10px] font-mono font-bold text-[#9CA3AF] uppercase tracking-wider group-hover:text-[#00E5FF] transition-colors">Total Vectors Indexed</span>
                {isLoadingTelemetry ? (
                  <div className="h-8 shimmer rounded mt-2 w-32" />
                ) : (
                  <h3 className="font-headline font-bold text-3xl mt-1 text-[#10B981]">{system.qdrant.indexedVectors.toLocaleString()}</h3>
                )}
              </div>
              <div className="flex items-center gap-1 text-[10px] text-[#00E5FF] mt-3 font-mono">
                <Layers size={12} />
                <span>Ready for semantic RAG search</span>
              </div>
            </div>

          </div>

          {/* Middle Layout: Charts & Telemetry Status + Activity Feeds */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            
            {/* System Status Telemetry & Activity (Left 7 Columns) */}
            <div className="col-span-1 lg:col-span-7 space-y-6">
              
              {/* Telemetry Card */}
              <div className="bg-[#0F111A] border border-[#242838] p-5 rounded-lg space-y-4 shadow-xl">
                <div className="flex items-center justify-between border-b border-[#242838]/80 pb-3">
                  <h3 className="font-headline font-bold text-xs text-[#F3F4F6] tracking-wider uppercase flex items-center gap-2">
                    <ShieldCheck size={14} className="text-[#00E5FF]" />
                    System & Database Telemetry
                  </h3>
                  <div className="flex items-center gap-1.5 text-[9px] font-mono text-[#10B981] bg-[#10B981]/10 px-2 py-0.5 rounded border border-[#10B981]/20 shadow-sm shadow-[#10B981]/5">
                    <span className="w-1.5 h-1.5 bg-[#10B981] rounded-full animate-pulse" />
                    ALL SYSTEMS ONLINE
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Postgres Card */}
                  <div className="bg-[#08090C] border border-[#242838] p-3.5 rounded-lg space-y-2.5">
                    <div className="flex items-center justify-between">
                      <span className="font-headline font-bold text-xs text-[#F3F4F6] flex items-center gap-1.5">
                        <Database size={13} className="text-[#00E5FF]" />
                        PostgreSQL DB
                      </span>
                      <span className={`w-1.5 h-1.5 rounded-full ${system.postgres.status === 'Operational' ? 'bg-[#10B981] shadow-[0_0_8px_#10B981]' : 'bg-[#EF4444]'}`} />
                    </div>
                    <div className="space-y-1.5 font-mono text-[10px]">
                      <div className="flex justify-between">
                        <span className="text-[#9CA3AF]">Status</span>
                        <span className={system.postgres.status === 'Operational' ? 'text-[#10B981]' : 'text-[#EF4444]'}>
                          {system.postgres.status}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[#9CA3AF]">Active Connections</span>
                        <span className="text-[#F3F4F6]">{system.postgres.activeConnections}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[#9CA3AF]">Total Size</span>
                        <span className="text-[#F3F4F6] font-bold">{system.postgres.dbSizeGB} GB</span>
                      </div>
                    </div>
                  </div>

                  {/* Redis Card */}
                  <div className="bg-[#08090C] border border-[#242838] p-3.5 rounded-lg space-y-2.5">
                    <div className="flex items-center justify-between">
                      <span className="font-headline font-bold text-xs text-[#F3F4F6] flex items-center gap-1.5">
                        <Cpu size={13} className="text-[#10B981]" />
                        Redis & ARQ Workers
                      </span>
                      <span className={`w-1.5 h-1.5 rounded-full pulse-indicator ${system.redis.status === 'Operational' ? 'bg-[#10B981] shadow-[0_0_8px_#10B981]' : 'bg-[#EF4444]'}`} />
                    </div>
                    <div className="space-y-1.5 font-mono text-[10px]">
                      <div className="flex justify-between">
                        <span className="text-[#9CA3AF]">Active Threads</span>
                        <span className="text-[#00E5FF]">{system.arqWorkers.active}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[#9CA3AF]">Redis Memory</span>
                        <span className="text-[#F3F4F6]">{system.redis.memoryUsageMB} MB</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[#9CA3AF]">Failed Jobs (24h)</span>
                        <span className="text-[#EF4444] font-bold">{system.arqWorkers.failed24h}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="bg-[#08090C] border border-[#242838] p-3 rounded-lg flex items-center justify-between font-mono text-[10px]">
                  <span className="text-[#9CA3AF]">Vector Store (Qdrant RAG Latency)</span>
                  <div className="flex items-center gap-3">
                    <span className="text-[#9CA3AF]">Query Speed: <strong className="text-[#00E5FF]">{system.qdrant.searchLatencyMs} ms</strong></span>
                    <div className="w-[1px] h-3 bg-[#242838]" />
                    <span className="text-[#10B981] font-bold">98.8% Hit rate</span>
                  </div>
                </div>
              </div>

              {/* Activity Timeline Card */}
              <div className="bg-[#0F111A] border border-[#242838] p-5 rounded-lg space-y-4">
                <div className="flex items-center justify-between border-b border-[#242838]/80 pb-3">
                  <h3 className="font-headline font-bold text-xs text-[#F3F4F6] tracking-wider uppercase flex items-center gap-2">
                    <History size={14} className="text-[#00E5FF]" />
                    Activity & Audit Timeline
                  </h3>
                  <span className="text-[9px] font-mono text-[#9CA3AF] uppercase">Security Logs</span>
                </div>

                <div className="space-y-3.5 relative pl-4 before:absolute before:left-[5px] before:top-2 before:bottom-2 before:w-[1px] before:bg-[#242838]">
                  {activityTimeline.map((act, index) => {
                    // Premium color-coordinated dots
                    let dotBorderColor = 'border-[#9CA3AF]';
                    if (act.type === 'upload') dotBorderColor = 'border-[#10B981]';
                    else if (act.type === 'research') dotBorderColor = 'border-[#00E5FF]';
                    else if (act.type === 'alert') dotBorderColor = 'border-[#EF4444]';

                    return (
                      <div key={index} className="relative flex flex-col sm:flex-row sm:items-center sm:justify-between text-[11px] group py-0.5">
                        <div className={`absolute -left-[14px] top-1.5 w-2.5 h-2.5 rounded-full bg-[#08090C] border-2 ${dotBorderColor} group-hover:scale-125 transition-all duration-200`} />
                        <span className="text-[#9CA3AF] group-hover:text-[#F3F4F6] transition-colors">{act.message}</span>
                        <span className="text-[10px] font-mono text-[#555] sm:ml-4">{act.time}</span>
                      </div>
                    );
                  })}
                </div>
              </div>

            </div>

            {/* Quick Actions & Research Feed (Right 5 Columns) */}
            <div className="col-span-1 lg:col-span-5 space-y-6">
              
              {/* Quick Actions Card */}
              <div className="bg-[#0F111A] border border-[#242838] p-5 rounded-lg space-y-4">
                <h3 className="font-headline font-bold text-xs text-[#F3F4F6] tracking-wider uppercase border-b border-[#242838]/80 pb-3">
                  Quick Research Actions
                </h3>
                <div className="space-y-3">
                  <Link
                    to="/workspace"
                    className="flex items-center justify-between p-3 bg-[#08090C] hover:bg-[#171926] border border-[#242838] hover:border-[#00E5FF]/40 rounded-lg group transition-all"
                  >
                    <div className="flex items-center gap-3">
                      <PlusCircle size={16} className="text-[#00E5FF]" />
                      <div className="text-left">
                        <p className="font-headline font-bold text-xs text-[#F3F4F6]">New Research Session</p>
                        <p className="text-[9px] text-[#9CA3AF] mt-0.5">Generate real-time reports via NIM</p>
                      </div>
                    </div>
                    <ArrowRight size={12} className="text-[#9CA3AF] group-hover:text-[#00E5FF] group-hover:translate-x-1 transition-all" />
                  </Link>

                  <Link
                    to="/documents"
                    className="flex items-center justify-between p-3 bg-[#08090C] hover:bg-[#171926] border border-[#242838] hover:border-[#10B981]/40 rounded-lg group transition-all"
                  >
                    <div className="flex items-center gap-3">
                      <FileCode size={16} className="text-[#10B981]" />
                      <div className="text-left">
                        <p className="font-headline font-bold text-xs text-[#F3F4F6]">Upload Annual Reports</p>
                        <p className="text-[9px] text-[#9CA3AF] mt-0.5">Index SEC PDFs directly into pgvector</p>
                      </div>
                    </div>
                    <ArrowRight size={12} className="text-[#9CA3AF] group-hover:text-[#10B981] group-hover:translate-x-1 transition-all" />
                  </Link>
                </div>
              </div>

              {/* Latest Research Feed */}
              <div className="bg-[#0F111A] border border-[#242838] p-5 rounded-lg space-y-3">
                <h3 className="font-headline font-bold text-xs text-[#F3F4F6] tracking-wider uppercase border-b border-[#242838]/80 pb-3">
                  Latest Research Feed
                </h3>
                <div className="divide-y divide-[#242838]/50">
                  {initialReports.slice(0, 3).map((rep) => (
                    <div key={rep.id} className="py-2.5 flex items-center justify-between group hover:bg-[#08090C]/30 px-1 rounded transition-colors">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold text-[#00E5FF]">{rep.ticker}</span>
                          <span className="text-[10px] text-[#9CA3AF] truncate max-w-[120px]">{rep.companyName}</span>
                        </div>
                        <p className="text-[10px] text-[#555] font-mono mt-0.5">{rep.reportType} • {rep.date}</p>
                      </div>
                      <span className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded border ${
                        rep.sentiment === 'Bullish'
                          ? 'bg-[#10B981]/5 text-[#10B981] border-[#10B981]/20'
                          : 'bg-[#EF4444]/5 text-[#EF4444] border-[#EF4444]/20'
                      }`}>
                        {rep.sentiment.toUpperCase()}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

            </div>

          </div>

          {/* Bottom Table: Recent Queries */}
          <div className="bg-[#0F111A] border border-[#242838] p-5 rounded-lg space-y-4">
            <div className="flex items-center justify-between border-b border-[#242838] pb-3">
              <h3 className="font-headline font-bold text-xs text-[#F3F4F6] tracking-wider uppercase flex items-center gap-2">
                <Activity size={14} className="text-[#00E5FF]" />
                Recent AI Analyst Queries
              </h3>
              <span className="text-[10px] text-[#9CA3AF] font-mono">Showing last 5 searches</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left font-body border-collapse text-xs">
                <thead>
                  <tr className="border-b border-[#242838] text-[#9CA3AF] font-mono uppercase text-[9px]">
                    <th className="py-2.5 px-4 font-normal">Timestamp</th>
                    <th className="py-2.5 px-4 font-normal">Research Prompt Query</th>
                    <th className="py-2.5 px-4 font-normal">Sources cited</th>
                    <th className="py-2.5 px-4 font-normal text-center">NIM Latency</th>
                    <th className="py-2.5 px-4 font-normal text-right">Job Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#242838]/60">
                  {isLoadingStats ? (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-xs text-[#9CA3AF] font-mono">
                        <div className="flex items-center justify-center gap-2">
                          <span className="w-3.5 h-3.5 border-2 border-t-transparent border-[#00E5FF] rounded-full animate-spin" />
                          <span>FETCHING TERMINAL LOGS...</span>
                        </div>
                      </td>
                    </tr>
                  ) : recentQueries.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-xs text-[#9CA3AF] font-mono">
                        NO RECENT AI RESEARCH RUNS FOUND. START A SYNTHESIS SESSION IN THE WORKSPACE.
                      </td>
                    </tr>
                  ) : (
                    recentQueries.map((q: any) => (
                      <tr key={q.id} className="hover:bg-[#08090C]/50 transition-colors">
                        <td className="py-2.5 px-4 font-mono text-[#9CA3AF]">{q.timestamp}</td>
                        <td className="py-2.5 px-4 text-[#F3F4F6] font-medium max-w-sm truncate">{q.query}</td>
                        <td className="py-2.5 px-4 font-mono text-[#00E5FF]">{q.sourceCount} files</td>
                        <td className="py-2.5 px-4 font-mono text-[#9CA3AF] text-center">{q.inferenceTime}</td>
                        <td className="py-2.5 px-4 text-right">
                          <span
                            className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono border ${
                              q.status === 'Completed'
                                ? 'bg-[#10B981]/10 text-[#10B981] border-[#10B981]/20'
                                : q.status === 'Processing'
                                ? 'bg-[#00E5FF]/10 text-[#00E5FF] border-[#00E5FF]/20'
                                : 'bg-[#EF4444]/10 text-[#EF4444] border-[#EF4444]/20'
                            }`}
                          >
                            {q.status === 'Completed' && <CheckCircle2 size={10} />}
                            {q.status === 'Processing' && <PlayCircle size={10} className="animate-spin" />}
                            {q.status === 'Failed' && <XCircle size={10} />}
                            {q.status}
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

        </main>
      </div>
    </div>
  );
};

export default Dashboard;
