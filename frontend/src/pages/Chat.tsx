import React, { useState } from 'react';
import Sidebar from '../components/Sidebar';
import Header from '../components/Header';
import MarketTicker from '../components/MarketTicker';
import {
  mockChatHistory,
  mockChatMessages,
  mockCitations
} from '../utils/mockData';
import {
  Send,
  MessageSquare,
  Sparkles,
  BookOpen,
  ArrowUpRight,
  Loader2
} from 'lucide-react';

export const Chat: React.FC = () => {
  const [messages, setMessages] = useState(mockChatMessages);
  const [inputVal, setInputVal] = useState('');
  const [hoveredCitation, setHoveredCitation] = useState<string | null>(null);
  
  // Advanced Live Chat Polish
  const [isTyping, setIsTyping] = useState(false);
  const [typingStep, setTypingStep] = useState('');

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputVal.trim()) return;

    const userMsg = { sender: 'user', text: inputVal };
    setMessages(prev => [...prev, userMsg]);
    setInputVal('');
    setIsTyping(true);
    setTypingStep('Querying pgvector vector vault index...');

    // Phase 1: Search pgvector Database chunks
    setTimeout(() => {
      setTypingStep('Found 2 matching footnotes in TSLA Q4 filings...');
      
      // Phase 2: Nvidia NIM Completion
      setTimeout(() => {
        setTypingStep('Synthesizing report with Llama-3-70B...');
        
        // Phase 3: Complete & Push message
        setTimeout(() => {
          setIsTyping(false);
          const systemMsg = {
            sender: 'assistant',
            text: 'Based on our pgvector indexes matching your request, **Tesla\'s Q4 financial notes** show regulatory credits accounted for **$480M in revenue** [1]. The 10-Q filing cites shifts in European Union zero-emission rules as a catalyst [2].\n\nWould you like me to analyze their custom cash flows next?'
          };
          setMessages(prev => [...prev, systemMsg]);
        }, 1200);
      }, 1000);
    }, 1000);
  };

  const handleSuggestion = (prompt: string) => {
    setInputVal(prompt);
  };

  return (
    <div className="flex bg-[#08090C] min-h-screen text-[#F3F4F6]">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header title="AI Chat Assistant" />
        <MarketTicker />

        <div className="flex-1 flex overflow-hidden">
          
          {/* Conversation History Sidebar */}
          <div className="w-64 border-r border-[#242838] bg-[#0B0C10] p-4 flex flex-col justify-between hidden md:flex">
            <div className="space-y-6">
              <button className="w-full py-2 bg-[#0F111A] hover:bg-[#171926] border border-[#242838] rounded-lg text-xs font-mono font-bold text-[#00E5FF] transition-all flex items-center justify-center gap-2 group cursor-pointer">
                <Sparkles size={12} className="group-hover:rotate-12 transition-transform" />
                NEW SESSION
              </button>

              <div className="space-y-2">
                <span className="text-[9px] font-mono text-[#9CA3AF] uppercase block px-2 tracking-wider">History Logs</span>
                <div className="space-y-1">
                  {mockChatHistory.map((h) => (
                    <button
                      key={h.id}
                      className="w-full text-left px-2 py-2 rounded-lg text-xs text-[#9CA3AF] hover:bg-[#0F111A] hover:text-[#F3F4F6] transition-all truncate flex items-center gap-2 group"
                    >
                      <MessageSquare size={12} className="text-[#555] group-hover:text-[#00E5FF] transition-colors" />
                      <span>{h.title}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="bg-[#0F111A] border border-[#242838] p-3 rounded-lg flex items-center justify-between text-[10px] font-mono text-[#9CA3AF] shadow-sm">
              <span>Context Size: 16k</span>
              <span className="text-[#10B981] font-semibold">Llama-3-70b</span>
            </div>
          </div>

          {/* Main Chat Interface */}
          <div className="flex-1 flex flex-col bg-[#08090C] relative min-w-0">
            
            {/* Messages Scroll Area */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin">
              {messages.map((m, index) => (
                <div
                  key={index}
                  className={`flex ${m.sender === 'user' ? 'justify-end' : 'justify-start'} animate-fadeIn`}
                >
                  <div
                    className={`max-w-2xl rounded-xl p-4 border text-[13px] leading-relaxed space-y-2 ${
                      m.sender === 'user'
                        ? 'bg-[#171926] border-[#00E5FF]/20 text-[#F3F4F6] shadow-md shadow-[#00E5FF]/2'
                        : 'bg-[#0F111A] border-[#242838] text-[#F3F4F6] shadow-md shadow-black/10'
                    }`}
                  >
                    <span className="text-[9px] font-mono text-[#9CA3AF] block font-bold uppercase tracking-wider mb-1">
                      {m.sender === 'user' ? 'ANALYST PROMPT' : 'SYSTEM SYNTHESIS'}
                    </span>
                    
                    {/* Render messages with basic custom highlight for citation brackets */}
                    <p className="whitespace-pre-line text-[#D1D5DB]">
                      {m.text.split(/(\[\d+\])/).map((part, pIdx) => {
                        const isCitation = /^\[\d+\]$/.test(part);
                        if (isCitation) {
                          return (
                            <span
                              key={pIdx}
                              onMouseEnter={() => setHoveredCitation(part)}
                              onMouseLeave={() => setHoveredCitation(null)}
                              className="text-[#00E5FF] font-mono font-bold hover:underline cursor-pointer mx-0.5 px-0.5 rounded bg-[#00E5FF]/10 border border-[#00E5FF]/20"
                            >
                              {part}
                            </span>
                          );
                        }
                        return part;
                      })}
                    </p>
                  </div>
                </div>
              ))}

              {/* Typing Loader Indicator */}
              {isTyping && (
                <div className="flex justify-start animate-fade-in">
                  <div className="max-w-md w-full bg-[#0F111A] border border-[#242838] rounded-xl p-4 space-y-3 shadow-lg">
                    <div className="flex items-center gap-2 border-b border-[#242838]/60 pb-2">
                      <Loader2 className="animate-spin text-[#00E5FF]" size={14} />
                      <span className="font-mono text-[9px] font-bold text-[#9CA3AF] uppercase tracking-wider">AI RAG PIPELINE ACTIVE</span>
                    </div>
                    <div className="space-y-2 font-mono text-[10.5px]">
                      <div className="flex items-center gap-2">
                        <span className={`w-1.5 h-1.5 rounded-full ${typingStep.includes('Querying') || typingStep.includes('pgvector') ? 'bg-[#00E5FF] pulse-fast' : 'bg-[#10B981]'}`} />
                        <span className={typingStep.includes('Querying') || typingStep.includes('pgvector') ? 'text-[#00E5FF]' : 'text-[#9CA3AF]'}>Querying pgvector vector vault indexes</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`w-1.5 h-1.5 rounded-full ${typingStep.includes('Found') ? 'bg-[#00E5FF] pulse-fast' : typingStep.includes('Synthesizing') ? 'bg-[#10B981]' : typingStep.includes('Querying') || typingStep.includes('pgvector') ? 'bg-[#242838]' : 'bg-[#242838]'}`} />
                        <span className={typingStep.includes('Found') ? 'text-[#00E5FF]' : typingStep.includes('Synthesizing') ? 'text-[#9CA3AF]' : 'text-[#555]'}>Extracting footnote reference contexts</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`w-1.5 h-1.5 rounded-full ${typingStep.includes('Synthesizing') ? 'bg-[#00E5FF] pulse-fast' : 'bg-[#242838]'}`} />
                        <span className={typingStep.includes('Synthesizing') ? 'text-[#00E5FF]' : 'text-[#555]'}>Synthesizing analysis via Llama-3-70B NIM</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Quick Suggestions & Input Footer */}
            <div className="p-6 border-t border-[#242838] bg-[#0B0C10]/95 space-y-4">
              
              {/* Suggestion Chips */}
              <div className="flex gap-2 overflow-x-auto whitespace-nowrap scrollbar-none pb-1">
                <button
                  onClick={() => handleSuggestion('Analyze risk beta targets for Tesla following Q3 SEC report.')}
                  className="bg-[#0F111A] hover:bg-[#171926] border border-[#242838] hover:border-[#00E5FF]/30 px-3 py-1.5 rounded-full text-[10px] font-mono text-[#9CA3AF] hover:text-[#F3F4F6] transition-all cursor-pointer"
                >
                  Tesla Q3 Risk Beta
                </button>
                <button
                  onClick={() => handleSuggestion('What are NVIDIA\'s custom cap expenditure budgets for advanced packaging?')}
                  className="bg-[#0F111A] hover:bg-[#171926] border border-[#242838] hover:border-[#00E5FF]/30 px-3 py-1.5 rounded-full text-[10px] font-mono text-[#9CA3AF] hover:text-[#F3F4F6] transition-all cursor-pointer"
                >
                  NVIDIA CapEx Packaging
                </button>
                <button
                  onClick={() => handleSuggestion('Generate net income comparisons for JPM and Goldman Sachs.')}
                  className="bg-[#0F111A] hover:bg-[#171926] border border-[#242838] hover:border-[#00E5FF]/30 px-3 py-1.5 rounded-full text-[10px] font-mono text-[#9CA3AF] hover:text-[#F3F4F6] transition-all cursor-pointer"
                >
                  Goldman vs JPM Revenues
                </button>
              </div>

              {/* Chat Input form */}
              <form onSubmit={handleSend} className="flex gap-4">
                <input
                  type="text"
                  value={inputVal}
                  onChange={(e) => setInputVal(e.target.value)}
                  placeholder="Ask assistant to process vector vault files..."
                  className="flex-1 bg-[#0F111A] border border-[#242838] rounded-lg px-4 py-2.5 text-xs text-[#F3F4F6] placeholder-[#555] glow-focus transition-all"
                />
                <button
                  type="submit"
                  disabled={!inputVal.trim() || isTyping}
                  className="px-4 py-2 bg-[#00E5FF] hover:bg-[#0099ff] disabled:bg-[#171926] disabled:text-[#555] text-black rounded-lg font-headline font-bold text-xs transition-all flex items-center justify-center cursor-pointer"
                >
                  <Send size={14} />
                </button>
              </form>
            </div>

          </div>

          {/* Column 3: Citations Overlay Sidebar (Right Side) */}
          <div className="w-80 border-l border-[#242838] bg-[#0B0C10] p-6 space-y-4 overflow-y-auto hidden lg:flex scrollbar-thin">
            <h4 className="font-headline font-bold text-xs text-[#F3F4F6] tracking-wider uppercase flex items-center gap-2">
              <BookOpen size={14} className="text-[#00E5FF]" />
              Footnote References
            </h4>
            
            <div className="space-y-4 pt-2">
              {mockCitations.map((c) => {
                const isHighlighted = hoveredCitation === c.id;
                return (
                  <div
                    key={c.id}
                    className={`p-4 rounded-lg border transition-all ${
                      isHighlighted
                        ? 'bg-[#00E5FF]/5 border-[#00E5FF] shadow-lg shadow-[#00E5FF]/5 scale-[1.02]'
                        : 'bg-[#0F111A] border-[#242838] hover:border-[#242838]/80'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-[10px] font-mono font-bold text-[#00E5FF]">{c.id} Citation Details</span>
                      <ArrowUpRight size={12} className="text-[#9CA3AF]" />
                    </div>
                    <h5 className="font-headline font-bold text-xs text-[#F3F4F6]">{c.title}</h5>
                    <p className="text-[10px] text-[#9CA3AF] mt-2 leading-relaxed">"{c.excerpt}"</p>
                  </div>
                );
              })}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};
export default Chat;
