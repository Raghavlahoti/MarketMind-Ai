import React, { useState } from 'react';
import Sidebar from '../components/Sidebar';
import Header from '../components/Header';
import MarketTicker from '../components/MarketTicker';
import {
  KeyRound,
  User,
  Sliders,
  Plus,
  Trash2,
  Cpu,
  Check
} from 'lucide-react';

interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  created: string;
}

export const Settings: React.FC = () => {
  const [activeSubTab, setActiveSubTab] = useState<'profile' | 'keys' | 'model'>('profile');
  
  // Profile States
  const [name, setName] = useState('Raghav Maheshwari');
  const [email, setEmail] = useState('raghav@marketmind.ai');
  const [company, setCompany] = useState('MarketMind AI Co.');
  const [isSaved, setIsSaved] = useState(false);

  // API Key States
  const [keys, setKeys] = useState<ApiKey[]>([
    { id: 'k1', name: 'NIM Production Llama3', prefix: 'nv-nim_••••••••••••W1az', created: '2026-06-24' },
    { id: 'k2', name: 'RAG Qdrant ReadOnly', prefix: 'qd-key_••••••••••••3aB8', created: '2026-06-22' }
  ]);
  const [newKeyName, setNewKeyName] = useState('');

  // Model Parameter States
  const [selectedModel, setSelectedModel] = useState('Llama-3-70B-NIM');
  const [temperature, setTemperature] = useState(0.2);
  const [maxTokens, setMaxTokens] = useState(4096);

  const handleProfileSave = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 2000);
  };

  const handleCreateKey = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKeyName.trim()) return;

    const newKey: ApiKey = {
      id: 'k_' + Date.now(),
      name: newKeyName,
      prefix: 'nv-nim_••••••••••••' + Math.random().toString(36).substring(2, 6).toUpperCase(),
      created: new Date().toISOString().split('T')[0]
    };
    setKeys([...keys, newKey]);
    setNewKeyName('');
  };

  const handleDeleteKey = (id: string) => {
    setKeys(prev => prev.filter(k => k.id !== id));
  };

  return (
    <div className="flex bg-[#08090C] min-h-screen text-[#F3F4F6]">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header title="Developer & Profile Settings" />
        <MarketTicker />

        <main className="flex-1 overflow-y-auto p-8 max-w-5xl w-full mx-auto space-y-8">
          
          <div className="flex flex-col md:flex-row gap-8">
            
            {/* Left Nav Pane */}
            <div className="w-full md:w-56 flex flex-col space-y-1">
              <button
                onClick={() => setActiveSubTab('profile')}
                className={`flex items-center gap-3 px-4 py-2.5 rounded-lg text-xs font-mono font-bold tracking-wider uppercase transition-all text-left ${
                  activeSubTab === 'profile'
                    ? 'bg-[#171926] text-[#00E5FF] border border-[#00E5FF]/20'
                    : 'text-[#9CA3AF] hover:bg-[#0F111A] hover:text-[#F3F4F6]'
                }`}
              >
                <User size={14} />
                Analyst Profile
              </button>
              <button
                onClick={() => setActiveSubTab('keys')}
                className={`flex items-center gap-3 px-4 py-2.5 rounded-lg text-xs font-mono font-bold tracking-wider uppercase transition-all text-left ${
                  activeSubTab === 'keys'
                    ? 'bg-[#171926] text-[#00E5FF] border border-[#00E5FF]/20'
                    : 'text-[#9CA3AF] hover:bg-[#0F111A] hover:text-[#F3F4F6]'
                }`}
              >
                <KeyRound size={14} />
                NIM API Credentials
              </button>
              <button
                onClick={() => setActiveSubTab('model')}
                className={`flex items-center gap-3 px-4 py-2.5 rounded-lg text-xs font-mono font-bold tracking-wider uppercase transition-all text-left ${
                  activeSubTab === 'model'
                    ? 'bg-[#171926] text-[#00E5FF] border border-[#00E5FF]/20'
                    : 'text-[#9CA3AF] hover:bg-[#0F111A] hover:text-[#F3F4F6]'
                }`}
              >
                <Sliders size={14} />
                NIM Model Config
              </button>
            </div>

            {/* Right Pane Contents */}
            <div className="flex-1 bg-[#0F111A] border border-[#242838] p-8 rounded-xl shadow-xl">
              
              {/* Profile subtab */}
              {activeSubTab === 'profile' && (
                <form onSubmit={handleProfileSave} className="space-y-6">
                  <div className="border-b border-[#242838] pb-4">
                    <h3 className="font-headline font-bold text-sm text-[#F3F4F6] uppercase tracking-wider">Analyst Profile Configuration</h3>
                    <p className="text-[11px] text-[#9CA3AF] mt-1">Manage institutional email parameters and identity settings.</p>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                    <div>
                      <label className="block text-[10px] font-mono font-bold text-[#9CA3AF] uppercase tracking-wider mb-2">Full Name</label>
                      <input
                        type="text"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        className="w-full bg-[#08090C] border border-[#242838] rounded-lg px-4 py-2.5 text-xs text-[#F3F4F6] glow-focus transition-all"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-mono font-bold text-[#9CA3AF] uppercase tracking-wider mb-2">Email Address</label>
                      <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="w-full bg-[#08090C] border border-[#242838] rounded-lg px-4 py-2.5 text-xs text-[#F3F4F6] glow-focus transition-all"
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <label className="block text-[10px] font-mono font-bold text-[#9CA3AF] uppercase tracking-wider mb-2">Organization</label>
                      <input
                        type="text"
                        value={company}
                        onChange={(e) => setCompany(e.target.value)}
                        className="w-full bg-[#08090C] border border-[#242838] rounded-lg px-4 py-2.5 text-xs text-[#F3F4F6] glow-focus transition-all"
                      />
                    </div>
                  </div>

                  <div className="pt-4 flex items-center gap-4">
                    <button
                      type="submit"
                      className="px-5 py-2.5 bg-[#00E5FF] hover:bg-[#0099ff] text-black font-headline font-bold text-xs rounded-lg transition-all"
                    >
                      SAVE PROFILE SETTINGS
                    </button>
                    {isSaved && (
                      <span className="text-xs text-[#10B981] flex items-center gap-1 font-mono">
                        <Check size={14} /> Profile updated
                      </span>
                    )}
                  </div>
                </form>
              )}

              {/* API Keys Subtab */}
              {activeSubTab === 'keys' && (
                <div className="space-y-6">
                  <div className="border-b border-[#242838] pb-4">
                    <h3 className="font-headline font-bold text-sm text-[#F3F4F6] uppercase tracking-wider">NVIDIA NIM API Access Keys</h3>
                    <p className="text-[11px] text-[#9CA3AF] mt-1">Configure credentials for autonomous worker indexers.</p>
                  </div>

                  {/* Create Key form */}
                  <form onSubmit={handleCreateKey} className="flex gap-4 relative">
                    <input
                      type="text"
                      required
                      value={newKeyName}
                      onChange={(e) => setNewKeyName(e.target.value)}
                      placeholder="e.g. Test Key Node 2"
                      className="flex-1 bg-[#08090C] border border-[#242838] rounded-lg px-4 py-2.5 text-xs text-[#F3F4F6] placeholder-[#555] glow-focus transition-all"
                    />
                    <button
                      type="submit"
                      className="px-4 py-2 bg-[#171926] hover:bg-[#242838] border border-[#242838] text-[#00E5FF] rounded-lg font-headline font-bold text-xs transition-all flex items-center gap-1.5"
                    >
                      <Plus size={14} />
                      CREATE KEY
                    </button>
                  </form>

                  {/* Keys list table */}
                  <div className="overflow-x-auto pt-4">
                    <table className="w-full text-left font-body border-collapse text-xs">
                      <thead>
                        <tr className="border-b border-[#242838] text-[#9CA3AF] font-mono uppercase text-[9px]">
                          <th className="pb-3 px-2 font-normal">Key Name</th>
                          <th className="pb-3 px-2 font-normal">Token Hash</th>
                          <th className="pb-3 px-2 font-normal">Created On</th>
                          <th className="pb-3 px-2 font-normal text-right">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#242838]/60">
                        {keys.map((k) => (
                          <tr key={k.id} className="hover:bg-[#08090C]/30 transition-colors">
                            <td className="py-3 px-2 font-medium text-[#F3F4F6]">{k.name}</td>
                            <td className="py-3 px-2 font-mono text-[#9CA3AF]">{k.prefix}</td>
                            <td className="py-3 px-2 text-[#9CA3AF] font-mono">{k.created}</td>
                            <td className="py-3 px-2 text-right">
                              <button
                                onClick={() => handleDeleteKey(k.id)}
                                className="text-[#EF4444] hover:text-red-400 p-1 rounded hover:bg-[#EF4444]/10 transition-all"
                              >
                                <Trash2 size={14} />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Model config subtab */}
              {activeSubTab === 'model' && (
                <div className="space-y-6">
                  <div className="border-b border-[#242838] pb-4">
                    <h3 className="font-headline font-bold text-sm text-[#F3F4F6] uppercase tracking-wider">Model Inference Settings</h3>
                    <p className="text-[11px] text-[#9CA3AF] mt-1">Configure weights and hyper-parameters for NIM text completion.</p>
                  </div>

                  <div className="space-y-6">
                    {/* Model Choice */}
                    <div>
                      <label className="block text-[10px] font-mono font-bold text-[#9CA3AF] uppercase tracking-wider mb-2">Default NIM LLM Engine</label>
                      <select
                        value={selectedModel}
                        onChange={(e) => setSelectedModel(e.target.value)}
                        className="w-full bg-[#08090C] border border-[#242838] rounded-lg px-4 py-2.5 text-xs text-[#F3F4F6] glow-focus transition-all"
                      >
                        <option value="Llama-3-70B-NIM">NVIDIA Llama-3-70B NIM (Recomended)</option>
                        <option value="Mistral-Large-NIM">NVIDIA Mistral-Large NIM</option>
                        <option value="Llama-3-8B-NIM">NVIDIA Llama-3-8B NIM (Fast)</option>
                      </select>
                    </div>

                    {/* Temperature Slider */}
                    <div className="space-y-2">
                      <div className="flex justify-between text-[10px] font-mono font-bold uppercase tracking-wider">
                        <span className="text-[#9CA3AF]">Temperature (Creativity)</span>
                        <span className="text-[#00E5FF] font-bold">{temperature}</span>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.05"
                        value={temperature}
                        onChange={(e) => setTemperature(parseFloat(e.target.value))}
                        className="w-full h-1 bg-[#171926] rounded-lg appearance-none cursor-pointer accent-[#00E5FF]"
                      />
                    </div>

                    {/* Max token limits */}
                    <div>
                      <label className="block text-[10px] font-mono font-bold text-[#9CA3AF] uppercase tracking-wider mb-2">Token limit cap (Max Output)</label>
                      <input
                        type="number"
                        value={maxTokens}
                        onChange={(e) => setMaxTokens(parseInt(e.target.value))}
                        className="w-full bg-[#08090C] border border-[#242838] rounded-lg px-4 py-2.5 text-xs text-[#F3F4F6] glow-focus transition-all"
                      />
                    </div>

                    <div className="flex items-center gap-2 bg-[#08090C] border border-[#242838] p-4 rounded-lg text-xs">
                      <Cpu size={16} className="text-[#00E5FF] animate-pulse" />
                      <span className="text-[#9CA3AF]">
                        Adjusting temperature settings modifies direct API JSON parameters on the backend query engines.
                      </span>
                    </div>

                  </div>
                </div>
              )}

            </div>

          </div>

        </main>
      </div>
    </div>
  );
};
export default Settings;
