import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  SearchCode,
  FolderGit2,
  MessageSquareCode,
  ShieldCheck,
  Settings,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';

interface SidebarProps {
  onCollapseChange?: (collapsed: boolean) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ onCollapseChange }) => {
  const [isCollapsed, setIsCollapsed] = useState(false);

  const toggleSidebar = () => {
    setIsCollapsed(!isCollapsed);
    if (onCollapseChange) {
      onCollapseChange(!isCollapsed);
    }
  };

  const navItems = [
    { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
    { name: 'Workspace', path: '/workspace', icon: SearchCode },
    { name: 'Document Center', path: '/documents', icon: FolderGit2 },
    { name: 'AI Chat', path: '/chat', icon: MessageSquareCode },
    { name: 'Admin Console', path: '/admin', icon: ShieldCheck },
    { name: 'Settings', path: '/settings', icon: Settings },
  ];

  return (
    <div
      className={`h-screen sticky top-0 bg-[#0B0C10] border-r border-[#242838] transition-all duration-300 flex flex-col justify-between ${
        isCollapsed ? 'w-20' : 'w-64'
      }`}
    >
      {/* Top Section */}
      <div>
        <div className="h-16 flex items-center justify-between px-6 border-b border-[#242838]">
          {!isCollapsed && (
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded bg-gradient-to-br from-[#00E5FF] to-[#005580] flex items-center justify-center shadow-lg shadow-[#00E5FF]/20">
                <span className="font-mono font-bold text-black text-sm">MM</span>
              </div>
              <span className="font-headline font-bold text-lg tracking-wider text-[#F3F4F6]">
                MARKET<span className="text-[#00E5FF]">MIND</span>
              </span>
            </div>
          )}
          {isCollapsed && (
            <div className="w-8 h-8 mx-auto rounded bg-gradient-to-br from-[#00E5FF] to-[#005580] flex items-center justify-center shadow-lg shadow-[#00E5FF]/20">
              <span className="font-mono font-bold text-black text-xs">MM</span>
            </div>
          )}
          <button
            onClick={toggleSidebar}
            className="p-1 rounded-md hover:bg-[#171926] text-[#9CA3AF] hover:text-[#F3F4F6] transition-colors"
          >
            {isCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          </button>
        </div>

        {/* Navigation Links */}
        <nav className="mt-6 px-3 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.name}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg font-body text-sm font-medium transition-all group relative ${
                  isActive
                    ? 'bg-[#171926] text-[#00E5FF] border border-[#00E5FF]/30 shadow-md shadow-[#00E5FF]/5'
                    : 'text-[#9CA3AF] hover:bg-[#0F111A] hover:text-[#F3F4F6]'
                }`
              }
            >
              <item.icon
                size={18}
                className="transition-colors group-hover:text-[#00E5FF]"
              />
              {!isCollapsed && <span>{item.name}</span>}
              {isCollapsed && (
                <div className="absolute left-16 bg-[#171926] border border-[#242838] text-[#F3F4F6] px-2 py-1 rounded text-xs opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto transition-opacity whitespace-nowrap z-50 shadow-xl">
                  {item.name}
                </div>
              )}
            </NavLink>
          ))}
        </nav>
      </div>

      {/* Bottom Section - Active System Indicators */}
      <div className="p-4 border-t border-[#242838]">
        {!isCollapsed ? (
          <div className="bg-[#0F111A] p-3 rounded-lg border border-[#242838] space-y-2.5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-[#9CA3AF]">NIM LLM Status</span>
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#10B981] pulse-indicator"></span>
                <span className="text-[#10B981] font-mono">Active</span>
              </div>
            </div>
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-[#9CA3AF]">Latency</span>
              <span className="text-[#00E5FF] font-bold">82ms</span>
            </div>
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-[#9CA3AF]">Workers</span>
              <span className="text-[#F3F4F6]">12/12</span>
            </div>
          </div>
        ) : (
          <div className="flex justify-center">
            <div className="w-2.5 h-2.5 rounded-full bg-[#10B981] pulse-indicator" />
          </div>
        )}
      </div>
    </div>
  );
};
export default Sidebar;
