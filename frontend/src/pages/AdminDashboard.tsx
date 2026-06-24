import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Sidebar from '../components/Sidebar';
import Header from '../components/Header';
import MarketTicker from '../components/MarketTicker';
import { api } from '../utils/api';
import { initialUsers, initialSystemStatus } from '../utils/mockData';
import {
  UserCheck,
  Activity,
  Server,
  RefreshCcw,
  Database,
  Cpu
} from 'lucide-react';

export const AdminDashboard: React.FC = () => {
  const [users, setUsers] = useState(initialUsers);

  // Load real telemetry from backend
  const { data: telemetry } = useQuery({
    queryKey: ['systemTelemetry'],
    queryFn: async () => {
      const res = await api.get('/system/telemetry');
      return res.data;
    },
    refetchInterval: 5000
  });

  const status = telemetry || initialSystemStatus;

  const toggleUserStatus = (userId: string) => {
    setUsers(prev => prev.map(u => 
      u.id === userId 
        ? { ...u, status: u.status === 'Active' ? 'Suspended' : 'Active' } 
        : u
    ));
  };

  return (
    <div className="flex bg-[#08090C] min-h-screen text-[#F3F4F6]">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header title="Institutional Admin Console" />
        <MarketTicker />

        <main className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin">
          
          {/* Top Status Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            
            {/* NIM Model Status */}
            <div className="bg-[#0F111A] border border-[#242838] p-4 rounded-lg space-y-2 hover-glow hover:border-[#00E5FF]/30 transition-all duration-300 relative overflow-hidden group">
              <div className="flex items-center justify-between text-[10px] text-[#9CA3AF] font-mono">
                <span className="flex items-center gap-1.5 uppercase font-bold tracking-wider">
                  <Cpu size={13} className="text-[#00E5FF]" />
                  NIM API Node
                </span>
                <span className="w-1.5 h-1.5 rounded-full bg-[#10B981] pulse-indicator shadow-[0_0_8px_#10B981]" />
              </div>
              <div className="flex justify-between items-end">
                <span className="font-headline font-bold text-2xl text-[#F3F4F6]">99.8%</span>
                <span className="font-mono text-[9px] text-[#10B981] bg-[#10B981]/10 px-1.5 py-0.5 rounded">{status.nvidiaNim.throughput} req/s</span>
              </div>
            </div>

            {/* Workers status */}
            <div className="bg-[#0F111A] border border-[#242838] p-4 rounded-lg space-y-2 hover-glow hover:border-[#00E5FF]/30 transition-all duration-300 relative overflow-hidden group">
              <div className="flex items-center justify-between text-[10px] text-[#9CA3AF] font-mono">
                <span className="flex items-center gap-1.5 uppercase font-bold tracking-wider">
                  <Activity size={13} className="text-[#10B981]" />
                  ARQ Queue
                </span>
                <span className="w-1.5 h-1.5 rounded-full bg-[#10B981] pulse-indicator shadow-[0_0_8px_#10B981]" />
              </div>
              <div className="flex justify-between items-end">
                <span className="font-headline font-bold text-2xl text-[#F3F4F6]">
                  {status.arqWorkers.active} Threads
                </span>
                <span className="font-mono text-[9px] text-[#9CA3AF]">Queued: {status.arqWorkers.queued}</span>
              </div>
            </div>

            {/* Redis Cache */}
            <div className="bg-[#0F111A] border border-[#242838] p-4 rounded-lg space-y-2 hover-glow hover:border-[#00E5FF]/30 transition-all duration-300 relative overflow-hidden group">
              <div className="flex items-center justify-between text-[10px] text-[#9CA3AF] font-mono">
                <span className="flex items-center gap-1.5 uppercase font-bold tracking-wider">
                  <Server size={13} className="text-[#F3F4F6]" />
                  Redis Cache
                </span>
                <span className="w-1.5 h-1.5 rounded-full bg-[#10B981] pulse-indicator shadow-[0_0_8px_#10B981]" />
              </div>
              <div className="flex justify-between items-end">
                <span className="font-headline font-bold text-2xl text-[#F3F4F6]">{status.redis.memoryUsageMB} MB</span>
                <span className="font-mono text-[9px] text-[#9CA3AF]">{status.redis.connectedClients} connected</span>
              </div>
            </div>

            {/* Vector index */}
            <div className="bg-[#0F111A] border border-[#242838] p-4 rounded-lg space-y-2 hover-glow hover:border-[#00E5FF]/30 transition-all duration-300 relative overflow-hidden group">
              <div className="flex items-center justify-between text-[10px] text-[#9CA3AF] font-mono">
                <span className="flex items-center gap-1.5 uppercase font-bold tracking-wider">
                  <Database size={13} className="text-[#00E5FF]" />
                  pgvector Store
                </span>
                <span className="w-1.5 h-1.5 rounded-full bg-[#10B981] pulse-indicator shadow-[0_0_8px_#10B981]" />
              </div>
              <div className="flex justify-between items-end">
                <span className="font-headline font-bold text-2xl text-[#F3F4F6]">
                  {status.qdrant.indexedVectors.toLocaleString()}
                </span>
                <span className="font-mono text-[9px] text-[#00E5FF]">{status.qdrant.searchLatencyMs} ms queries</span>
              </div>
            </div>
          </div>

          {/* User Management & Worker Backlog Layout */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            
            {/* User administration list */}
            <div className="col-span-1 lg:col-span-8 bg-[#0F111A] border border-[#242838] p-5 rounded-lg space-y-4">
              <div className="flex items-center justify-between border-b border-[#242838] pb-3">
                <h3 className="font-headline font-bold text-xs text-[#F3F4F6] uppercase tracking-wider flex items-center gap-2">
                  <UserCheck size={14} className="text-[#00E5FF]" />
                  Analyst Accounts & Access Control
                </h3>
                <span className="text-[10px] font-mono text-[#9CA3AF]">{users.length} total users registered</span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left font-body border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-[#242838] text-[#9CA3AF] font-mono uppercase text-[9px]">
                      <th className="py-2.5 px-4 font-normal">Name</th>
                      <th className="py-2.5 px-4 font-normal">Email Address</th>
                      <th className="py-2.5 px-4 font-normal">Security Role</th>
                      <th className="py-2.5 px-4 font-normal text-center">NIM Keys</th>
                      <th className="py-2.5 px-4 font-normal text-right">Access Status</th>
                      <th className="py-2.5 px-4 font-normal text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#242838]/60">
                    {users.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="py-8 text-center text-xs text-[#9CA3AF] font-mono">
                          NO ANALYST ACCOUNTS REGISTERED IN DATABASE
                        </td>
                      </tr>
                    ) : (
                      users.map((u) => (
                        <tr key={u.id} className="hover:bg-[#08090C]/50 transition-colors">
                          <td className="py-2.5 px-4 font-medium text-[#F3F4F6]">{u.name}</td>
                          <td className="py-2.5 px-4 text-[#9CA3AF] font-mono">{u.email}</td>
                          <td className="py-2.5 px-4 font-mono text-[#00E5FF]">{u.role}</td>
                          <td className="py-2.5 px-4 font-mono text-center text-[#9CA3AF]">{u.activeKeys} keys</td>
                          <td className="py-2.5 px-4 text-right">
                            <span
                              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono border ${
                                u.status === 'Active'
                                  ? 'bg-[#10B981]/10 text-[#10B981] border-[#10B981]/20'
                                  : 'bg-[#EF4444]/10 text-[#EF4444] border-[#EF4444]/20'
                              }`}
                            >
                              {u.status}
                            </span>
                          </td>
                          <td className="py-2.5 px-4 text-right">
                            <button
                              onClick={() => toggleUserStatus(u.id)}
                              className="font-mono text-[9px] font-bold text-[#00E5FF] hover:underline hover:text-[#0099ff] transition-all cursor-pointer"
                            >
                              {u.status === 'Active' ? 'SUSPEND' : 'ACTIVATE'}
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Server logs & Error rates */}
            <div className="col-span-1 lg:col-span-4 bg-[#0F111A] border border-[#242838] p-5 rounded-lg space-y-4">
              <h3 className="font-headline font-bold text-xs text-[#F3F4F6] uppercase tracking-wider border-b border-[#242838] pb-3">
                Telemetry Log stream
              </h3>
              
              <div className="space-y-4 font-mono text-[10px]">
                
                {/* Console Logs */}
                <div className="bg-[#08090C] border border-[#242838] p-4 rounded-lg h-48 overflow-y-auto space-y-2 text-[#9CA3AF] scrollbar-thin shadow-inner font-mono leading-relaxed">
                  <div><span className="text-[#555]">[15:44:02]</span> <span className="bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/25 px-1 rounded text-[9px] font-bold">INFO</span> NIM LLM Llama3 token completion: 82ms</div>
                  <div><span className="text-[#555]">[15:43:55]</span> <span className="bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/25 px-1 rounded text-[9px] font-bold">INFO</span> pgvector cosine similarity search: 4.2ms</div>
                  <div><span className="text-[#555]">[15:43:50]</span> <span className="bg-[#00E5FF]/10 text-[#00E5FF] border border-[#00E5FF]/25 px-1 rounded text-[9px] font-bold">DEBUG</span> Redis connection pool synced (32 clients)</div>
                  <div><span className="text-[#555]">[15:43:12]</span> <span className="bg-[#EF4444]/10 text-[#EF4444] border border-[#EF4444]/25 px-1 rounded text-[9px] font-bold pulse-fast">ERROR</span> ARQ task job_98b50e failed: connection close</div>
                  <div><span className="text-[#555]">[15:42:01]</span> <span className="bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/25 px-1 rounded text-[9px] font-bold">INFO</span> Qdrant memory flush completed successfully</div>
                </div>

                <div className="flex items-center gap-2 bg-[#171926] p-3 rounded-lg border border-[#242838] text-xs">
                  <RefreshCcw size={14} className="text-[#00E5FF] animate-spin" />
                  <span className="text-[#F3F4F6] font-mono text-[11px]">LIVE LOG STREAM ACTIVE</span>
                </div>

              </div>
            </div>

          </div>

        </main>
      </div>
    </div>
  );
};

export default AdminDashboard;
