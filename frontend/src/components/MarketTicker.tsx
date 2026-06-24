import React, { useEffect, useState } from 'react';
import { ArrowUpRight, ArrowDownRight, Activity } from 'lucide-react';

interface IndexItem {
  name: string;
  baseValue: number;
  value: string;
  change: string;
  changePercent: number;
  positive: boolean;
  isCustom?: boolean;
}

export const MarketTicker: React.FC = () => {
  const [items, setItems] = useState<IndexItem[]>([
    { name: 'S&P 500', baseValue: 5422.30, value: '5,422.30', change: '+0.45%', changePercent: 0.45, positive: true },
    { name: 'NASDAQ', baseValue: 17830.55, value: '17,830.55', change: '+0.88%', changePercent: 0.88, positive: true },
    { name: 'DOW JONES', baseValue: 39127.14, value: '39,127.14', change: '-0.12%', changePercent: -0.12, positive: false },
    { name: 'NIM LATENCY', baseValue: 82, value: '82 ms', change: '-4 ms', changePercent: -4.6, positive: true, isCustom: true },
    { name: 'ARQ WORKERS', baseValue: 12, value: '12 ACTIVE', change: '100% OK', changePercent: 0, positive: true, isCustom: true },
    { name: 'QDRANT RAG', baseValue: 4.2, value: '4.2 ms', change: '98.8% HIT', changePercent: 0.5, positive: true, isCustom: true }
  ]);

  useEffect(() => {
    const interval = setInterval(() => {
      setItems((prevItems) =>
        prevItems.map((item) => {
          if (item.isCustom) return item; // Keep system latency/status stable
          const pct = (Math.random() - 0.5) * 0.04; // small fluctuation up to +/-0.02%
          const newPct = parseFloat((item.changePercent + pct).toFixed(2));
          const newValue = parseFloat((item.baseValue * (1 + newPct / 100)).toFixed(2));
          const isPositive = newPct >= 0;
          return {
            ...item,
            changePercent: newPct,
            value: newValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
            change: `${isPositive ? '+' : ''}${newPct}%`,
            positive: isPositive,
          };
        })
      );
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="bg-[#0A0B0E] border-b border-[#1E2235] h-9 px-6 flex items-center justify-between overflow-x-auto whitespace-nowrap scrollbar-none gap-6 select-none relative shadow-inner">
      <div className="flex items-center gap-2 border-r border-[#1E2235] pr-4">
        <Activity size={12} className="text-[#00E5FF] animate-pulse" />
        <span className="font-mono text-[9px] font-bold text-[#00E5FF] tracking-wider uppercase">Live Feed</span>
      </div>

      <div className="flex items-center gap-8 text-xs font-mono flex-1 px-4">
        {items.map((index) => (
          <div key={index.name} className="flex items-center gap-2 hover:bg-[#171926]/30 px-2 py-0.5 rounded transition-all cursor-pointer">
            <span className="text-[#9CA3AF] text-[9px] font-semibold">{index.name}</span>
            <span className="text-[#F3F4F6] font-medium text-[11px]">{index.value}</span>
            <span
              className={`flex items-center text-[9px] font-bold transition-colors ${
                index.positive ? 'text-[#10B981]' : 'text-[#EF4444]'
              }`}
            >
              {index.change}
              {index.positive ? <ArrowUpRight size={10} className="ml-0.5" /> : <ArrowDownRight size={10} className="ml-0.5" />}
            </span>
          </div>
        ))}
      </div>

      <div className="flex items-center gap-2 border-l border-[#1E2235] pl-4">
        <span className="w-1.5 h-1.5 rounded-full bg-[#10B981] animate-pulse" />
        <span className="font-mono text-[9px] text-[#9CA3AF] tracking-wider uppercase font-semibold">SYNCED</span>
      </div>
    </div>
  );
};
export default MarketTicker;
