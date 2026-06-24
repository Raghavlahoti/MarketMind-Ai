import React from 'react';
import { Search, Bell, Cpu, Database } from 'lucide-react';

interface HeaderProps {
  title?: string;
}

export const Header: React.FC<HeaderProps> = ({ title }) => {
  return (
    <header className="h-16 bg-[#08090C]/80 backdrop-blur-md sticky top-0 z-40 border-b border-[#242838] px-8 flex items-center justify-between">
      {/* Page Title / Section name */}
      <div className="flex items-center gap-4">
        {title && (
          <h1 className="font-headline font-bold text-lg text-[#F3F4F6] tracking-wide">
            {title}
          </h1>
        )}
      </div>

      {/* Center Search Input */}
      <div className="hidden md:flex items-center max-w-md w-full relative">
        <span className="absolute left-3 text-[#9CA3AF]">
          <Search size={16} />
        </span>
        <input
          type="text"
          placeholder="Global Search (Citations, Prompts, Tickers...)"
          className="w-full bg-[#0F111A] border border-[#242838] rounded-lg pl-9 pr-4 py-1.5 text-xs text-[#F3F4F6] placeholder-[#9CA3AF] focus:outline-none focus:border-[#00E5FF] transition-all font-body"
        />
      </div>

      {/* Right Actions */}
      <div className="flex items-center gap-6">
        {/* Active NIM model info */}
        <div className="hidden xl:flex items-center gap-2 bg-[#0F111A] border border-[#242838] px-3 py-1 rounded-md">
          <Cpu size={14} className="text-[#00E5FF]" />
          <span className="font-mono text-[10px] text-[#9CA3AF]">NIM Backend:</span>
          <span className="font-mono text-[10px] text-[#00E5FF] font-bold">Llama-3-70B</span>
        </div>

        {/* Vector DB info */}
        <div className="hidden lg:flex items-center gap-2 bg-[#0F111A] border border-[#242838] px-3 py-1 rounded-md">
          <Database size={14} className="text-[#10B981]" />
          <span className="font-mono text-[10px] text-[#9CA3AF]">Vectors:</span>
          <span className="font-mono text-[10px] text-[#10B981] font-bold">485.2k</span>
        </div>

        {/* Alerts Icon */}
        <button className="relative p-1.5 rounded-lg bg-[#0F111A] hover:bg-[#171926] text-[#9CA3AF] hover:text-[#F3F4F6] border border-[#242838] transition-all">
          <Bell size={16} />
          <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-[#EF4444]" />
        </button>

        <div className="w-[1px] h-6 bg-[#242838]" />

        {/* Profile */}
        <div className="flex items-center gap-3">
          <div className="flex flex-col text-right">
            <span className="font-body text-xs font-semibold text-[#F3F4F6]">Raghav Maheshwari</span>
            <span className="font-mono text-[9px] text-[#9CA3AF]">Lead Analyst (MM)</span>
          </div>
          <div className="w-8 h-8 rounded-full bg-[#171926] border border-[#242838] flex items-center justify-center text-[#00E5FF] font-headline font-bold text-xs">
            RM
          </div>
        </div>
      </div>
    </header>
  );
};
export default Header;
