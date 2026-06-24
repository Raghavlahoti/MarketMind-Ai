import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Cpu, ShieldCheck, Database, KeyRound, UserPlus, Lock, Loader2 } from 'lucide-react';
import { api } from '../../utils/api';

export const Login: React.FC = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'login' | 'register' | 'forgot'>('login');
  
  // Form States
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMsg('');
    
    if (activeTab === 'login') {
      try {
        const response = await api.post('/auth/login', { email, password });
        localStorage.setItem('token', response.data.access_token);
        navigate('/dashboard');
      } catch (err: any) {
        setErrorMsg(err.response?.data?.message || err.response?.data?.error || 'Authentication failed. Please verify credentials.');
      } finally {
        setIsLoading(false);
      }
    } else if (activeTab === 'register') {
      if (password !== confirmPassword) {
        setErrorMsg('Passwords do not match.');
        setIsLoading(false);
        return;
      }
      try {
        const nameParts = name.trim().split(/\s+/);
        const first_name = nameParts[0] || '';
        const last_name = nameParts.slice(1).join(' ') || '';
        await api.post('/auth/register', { email, password, first_name, last_name });
        setSuccessMsg('Account registered successfully! Please log in.');
        setActiveTab('login');
      } catch (err: any) {
        setErrorMsg(err.response?.data?.message || err.response?.data?.error || 'Registration failed.');
      } finally {
        setIsLoading(false);
      }
    } else {
      // Mock Forgot Password
      setSuccessMsg('Reset password link sent to your registered email.');
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#08090C] text-[#F3F4F6] flex flex-col justify-between font-body relative overflow-hidden">
      {/* Background Decorative Grid */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-[#00E5FF]/5 via-transparent to-transparent opacity-40 pointer-events-none" />
      <div className="absolute inset-y-0 right-0 w-1/3 bg-[radial-gradient(circle_at_right,_var(--tw-gradient-stops))] from-[#10B981]/2 via-transparent to-transparent opacity-20 pointer-events-none" />

      {/* Top Header */}
      <div className="h-16 flex items-center justify-between px-8 border-b border-[#242838] z-10 bg-[#08090C]/80 backdrop-blur-md">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded bg-gradient-to-br from-[#00E5FF] to-[#005580] flex items-center justify-center">
            <span className="font-mono font-bold text-black text-sm">MM</span>
          </div>
          <span className="font-headline font-bold text-lg tracking-wider">
            MARKET<span className="text-[#00E5FF]">MIND</span>
          </span>
        </div>
        <div className="flex items-center gap-1.5 bg-[#0F111A] border border-[#242838] px-3 py-1 rounded-md">
          <span className="w-2 h-2 rounded-full bg-[#10B981] pulse-indicator" />
          <span className="font-mono text-[10px] text-[#9CA3AF]">PRODUCTION SYNC ACTIVE</span>
        </div>
      </div>

      {/* Main Container */}
      <div className="max-w-[1440px] mx-auto w-full px-8 py-12 flex-1 grid grid-cols-1 lg:grid-cols-12 gap-8 items-center z-10">
        
        {/* Left Side: System Telemetry Stats */}
        <div className="col-span-1 lg:col-span-5 space-y-6">
          <div className="space-y-2">
            <span className="text-[10px] font-mono font-bold text-[#00E5FF] tracking-widest uppercase">Institutional Research Portal</span>
            <h2 className="font-headline font-bold text-3xl xl:text-4xl text-[#F3F4F6] leading-tight">
              Real-time Market Insights powered by <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#00E5FF] to-[#0099ff] glow-text-cyan">NVIDIA NIM</span>
            </h2>
            <p className="text-sm text-[#9CA3AF] max-w-md font-body leading-relaxed pt-2">
              Access institutional-grade financial analysis, vector RAG indexers, and autonomous risk reporting engines under absolute security standards.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Stat Card 1 */}
            <div className="bg-[#0F111A] border border-[#242838] p-4 rounded-lg hover-glow hover:border-[#00E5FF]/30 transition-all duration-300 relative overflow-hidden group">
              <div className="absolute top-2 right-2 w-1.5 h-1.5 rounded-full bg-[#10B981] pulse-indicator" />
              <div className="flex items-center gap-2 text-[#00E5FF] mb-2">
                <Cpu size={16} />
                <span className="font-mono text-[10px] font-bold tracking-wider uppercase">NIM Inference</span>
              </div>
              <span className="font-headline font-bold text-2xl text-[#F3F4F6]">82 ms</span>
              <p className="text-[10px] text-[#9CA3AF] mt-1">Average pipeline processing latency</p>
            </div>

            {/* Stat Card 2 */}
            <div className="bg-[#0F111A] border border-[#242838] p-4 rounded-lg hover-glow hover:border-[#10B981]/30 transition-all duration-300 relative overflow-hidden group">
              <div className="absolute top-2 right-2 w-1.5 h-1.5 rounded-full bg-[#10B981] pulse-indicator" />
              <div className="flex items-center gap-2 text-[#10B981] mb-2">
                <ShieldCheck size={16} />
                <span className="font-mono text-[10px] font-bold tracking-wider uppercase">pgvector RAG</span>
              </div>
              <span className="font-headline font-bold text-2xl text-[#F3F4F6]">98.8%</span>
              <p className="text-[10px] text-[#9CA3AF] mt-1">Contextual prompt citation accuracy</p>
            </div>

            {/* Stat Card 3 */}
            <div className="bg-[#0F111A] border border-[#242838] p-4 rounded-lg hover-glow hover:border-[#F3F4F6]/30 transition-all duration-300 relative overflow-hidden group">
              <div className="absolute top-2 right-2 w-1.5 h-1.5 rounded-full bg-[#10B981] pulse-indicator" />
              <div className="flex items-center gap-2 text-[#F3F4F6] mb-2">
                <Database size={16} />
                <span className="font-mono text-[10px] font-bold tracking-wider uppercase">Active Workers</span>
              </div>
              <span className="font-headline font-bold text-2xl text-[#F3F4F6]">128 / 128</span>
              <p className="text-[10px] text-[#9CA3AF] mt-1">ARQ processing workers operational</p>
            </div>

            {/* Stat Card 4 */}
            <div className="bg-[#0F111A] border border-[#242838] p-4 rounded-lg hover-glow hover:border-[#00E5FF]/30 transition-all duration-300 relative overflow-hidden group">
              <div className="absolute top-2 right-2 w-1.5 h-1.5 rounded-full bg-[#10B981] pulse-indicator" />
              <div className="flex items-center gap-2 text-[#00E5FF] mb-2">
                <KeyRound size={16} />
                <span className="font-mono text-[10px] font-bold tracking-wider uppercase">Auth Standard</span>
              </div>
              <span className="font-headline font-bold text-xl text-[#F3F4F6]">HS256 JWT</span>
              <p className="text-[10px] text-[#9CA3AF] mt-1">Encrypted institutional sessions</p>
            </div>
          </div>
        </div>

        {/* Right Side: Glassmorphism Login Card */}
        <div className="col-span-1 lg:col-span-7 flex justify-center lg:justify-end">
          <div className="glass-panel max-w-md w-full p-8 rounded-xl shadow-2xl shadow-[#00E5FF]/5 relative">
            
            {/* Success Message Banner */}
            {successMsg && (
              <div className="mb-6 bg-[#10B981]/10 border border-[#10B981] p-3 rounded-lg text-xs text-[#10B981] flex items-center justify-between">
                <span>{successMsg}</span>
                <button onClick={() => setSuccessMsg('')} className="font-bold hover:opacity-80">×</button>
              </div>
            )}

            {/* Error Message Banner */}
            {errorMsg && (
              <div className="mb-6 bg-[#EF4444]/10 border border-[#EF4444] p-3 rounded-lg text-xs text-[#EF4444] flex items-center justify-between">
                <span>{errorMsg}</span>
                <button onClick={() => setErrorMsg('')} className="font-bold hover:opacity-80">×</button>
              </div>
            )}

            {/* Header / Tabs */}
            <div className="flex border-b border-[#242838] mb-6">
              <button
                disabled={isLoading}
                onClick={() => { setActiveTab('login'); setSuccessMsg(''); setErrorMsg(''); }}
                className={`flex-1 pb-3 text-xs font-mono font-bold tracking-wider uppercase border-b-2 transition-all ${
                  activeTab === 'login'
                    ? 'border-[#00E5FF] text-[#00E5FF]'
                    : 'border-transparent text-[#9CA3AF] hover:text-[#F3F4F6] disabled:opacity-50'
                }`}
              >
                Sign In
              </button>
              <button
                disabled={isLoading}
                onClick={() => { setActiveTab('register'); setSuccessMsg(''); setErrorMsg(''); }}
                className={`flex-1 pb-3 text-xs font-mono font-bold tracking-wider uppercase border-b-2 transition-all ${
                  activeTab === 'register'
                    ? 'border-[#00E5FF] text-[#00E5FF]'
                    : 'border-transparent text-[#9CA3AF] hover:text-[#F3F4F6] disabled:opacity-50'
                }`}
              >
                Register
              </button>
              <button
                disabled={isLoading}
                onClick={() => { setActiveTab('forgot'); setSuccessMsg(''); setErrorMsg(''); }}
                className={`flex-1 pb-3 text-xs font-mono font-bold tracking-wider uppercase border-b-2 transition-all ${
                  activeTab === 'forgot'
                    ? 'border-[#00E5FF] text-[#00E5FF]'
                    : 'border-transparent text-[#9CA3AF] hover:text-[#F3F4F6] disabled:opacity-50'
                }`}
              >
                Recover
              </button>
            </div>

            {/* Forms */}
            <form onSubmit={handleSubmit} className="space-y-4">
              {activeTab === 'register' && (
                <div>
                  <label className="block text-[10px] font-mono font-bold text-[#9CA3AF] uppercase tracking-wider mb-1.5">
                    User Full Name
                  </label>
                  <input
                    type="text"
                    required
                    disabled={isLoading}
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Enter your name"
                    className="w-full bg-[#0F111A] border border-[#242838] rounded-lg px-4 py-2.5 text-xs text-[#F3F4F6] placeholder-[#555] glow-focus hover:border-[#242838]/80 transition-all disabled:opacity-50"
                  />
                </div>
              )}

              <div>
                <label className="block text-[10px] font-mono font-bold text-[#9CA3AF] uppercase tracking-wider mb-1.5">
                  Institutional Email Address
                </label>
                <input
                  type="email"
                  required
                  disabled={isLoading}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="analyst@firm.com"
                  className="w-full bg-[#0F111A] border border-[#242838] rounded-lg px-4 py-2.5 text-xs text-[#F3F4F6] placeholder-[#555] glow-focus hover:border-[#242838]/80 transition-all disabled:opacity-50"
                />
              </div>

              {activeTab !== 'forgot' && (
                <div>
                  <label className="block text-[10px] font-mono font-bold text-[#9CA3AF] uppercase tracking-wider mb-1.5">
                    Account Security Password
                  </label>
                  <input
                    type="password"
                    required
                    disabled={isLoading}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full bg-[#0F111A] border border-[#242838] rounded-lg px-4 py-2.5 text-xs text-[#F3F4F6] placeholder-[#555] glow-focus hover:border-[#242838]/80 transition-all disabled:opacity-50"
                  />
                </div>
              )}

              {activeTab === 'register' && (
                <div>
                  <label className="block text-[10px] font-mono font-bold text-[#9CA3AF] uppercase tracking-wider mb-1.5">
                    Confirm Security Password
                  </label>
                  <input
                    type="password"
                    required
                    disabled={isLoading}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full bg-[#0F111A] border border-[#242838] rounded-lg px-4 py-2.5 text-xs text-[#F3F4F6] placeholder-[#555] glow-focus hover:border-[#242838]/80 transition-all disabled:opacity-50"
                  />
                </div>
              )}

              {activeTab === 'login' && (
                <div className="flex items-center justify-between text-[11px] text-[#9CA3AF] pt-1">
                  <label className="flex items-center gap-1.5 cursor-pointer">
                    <input type="checkbox" disabled={isLoading} className="rounded bg-[#0F111A] border-[#242838] text-[#00E5FF] focus:ring-0 focus:ring-offset-0 disabled:opacity-50" />
                    <span>Remember terminal session</span>
                  </label>
                  <button type="button" disabled={isLoading} onClick={() => setActiveTab('forgot')} className="text-[#00E5FF] hover:underline disabled:opacity-50">
                    Forgot keys?
                  </button>
                </div>
              )}

              <button
                type="submit"
                disabled={isLoading}
                className="w-full bg-gradient-to-r from-[#00E5FF] to-[#0099ff] hover:opacity-90 disabled:opacity-50 text-black font-headline font-bold text-xs py-3 rounded-lg shadow-lg shadow-[#00E5FF]/10 transition-all flex items-center justify-center gap-2 mt-4 cursor-pointer"
              >
                {isLoading ? (
                  <Loader2 className="animate-spin" size={14} />
                ) : (
                  <>
                    {activeTab === 'login' && (
                      <>
                        <Lock size={14} />
                        <span>AUTHENTICATE SECURE SESSION</span>
                      </>
                    )}
                    {activeTab === 'register' && (
                      <>
                        <UserPlus size={14} />
                        <span>CREATE ANALYST ACCOUNT</span>
                      </>
                    )}
                    {activeTab === 'forgot' && (
                      <span>REQUEST TEMPORARY ACCESS KEYS</span>
                    )}
                  </>
                )}
              </button>
            </form>

            {/* Footer notice */}
            <div className="mt-6 pt-4 border-t border-[#242838] text-center">
              <span className="text-[10px] font-mono text-[#9CA3AF]">
                AUTHORIZED USE ONLY. ALL COMMUNICATIONS ENCRYPTED & LOGGED.
              </span>
            </div>

          </div>
        </div>

      </div>

      {/* Footer */}
      <footer className="h-12 border-t border-[#242838] flex items-center justify-between px-8 text-[10px] font-mono text-[#9CA3AF] z-10 bg-[#08090C]/80">
        <span>© 2026 MARKETMIND AI CO.</span>
        <div className="flex gap-4">
          <a href="#" className="hover:text-[#F3F4F6] transition-colors">SECURITY AUDIT (SOC2)</a>
          <a href="#" className="hover:text-[#F3F4F6] transition-colors">TERMS OF SERVICE</a>
        </div>
      </footer>
    </div>
  );
};
export default Login;
