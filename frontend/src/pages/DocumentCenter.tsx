import React, { useState } from 'react';
import Sidebar from '../components/Sidebar';
import Header from '../components/Header';
import MarketTicker from '../components/MarketTicker';
import { initialDocuments } from '../utils/mockData';
import type { DocumentItem } from '../utils/mockData';
import {
  Upload,
  FileText,
  Search,
  Database,
  RefreshCw,
  CheckCircle,
  XCircle,
  AlertCircle
} from 'lucide-react';

export const DocumentCenter: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentItem[]>(initialDocuments);
  const [dragActive, setDragActive] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      const newDoc: DocumentItem = {
        id: 'doc_' + Date.now(),
        name: file.name,
        type: file.name.endsWith('.pdf') ? 'PDF Document' : 'Analyst Report',
        size: (file.size / (1024 * 1024)).toFixed(1) + ' MB',
        uploadDate: new Date().toISOString().split('T')[0],
        status: 'Processing'
      };
      setDocuments([newDoc, ...documents]);

      // Mock complete indexing in 3s
      setTimeout(() => {
        setDocuments(prev => prev.map(d => d.id === newDoc.id ? { ...d, status: 'Indexed' } : d));
      }, 3000);
    }
  };

  const filteredDocs = documents.filter(doc =>
    doc.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="flex bg-[#08090C] min-h-screen text-[#F3F4F6]">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header title="RAG Document Vault" />
        <MarketTicker />

        <main className="flex-1 overflow-y-auto p-8 grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* Left Column: Upload Panel & Document List */}
          <div className="col-span-1 lg:col-span-8 space-y-8">
            
            {/* Upload Area */}
            <div
              onDragEnter={handleDrag}
              onDragOver={handleDrag}
              onDragLeave={handleDrag}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-xl p-8 text-center transition-all ${
                dragActive
                  ? 'border-[#00E5FF] bg-[#00E5FF]/5'
                  : 'border-[#242838] bg-[#0F111A] hover:border-[#242838]/80'
              }`}
            >
              <div className="max-w-md mx-auto flex flex-col items-center space-y-4">
                <div className="w-12 h-12 rounded-full bg-[#171926] border border-[#242838] flex items-center justify-center text-[#00E5FF]">
                  <Upload size={20} className={dragActive ? 'animate-bounce' : ''} />
                </div>
                <div className="space-y-1.5">
                  <h3 className="font-headline font-bold text-sm text-[#F3F4F6]">
                    Upload financial reports, filings, or spreadsheet models
                  </h3>
                  <p className="text-xs text-[#9CA3AF]">
                    Drag and drop your PDF, SEC 10-K, or annual reports here. Limits: 50MB per file.
                  </p>
                </div>
                <button className="px-4 py-2 bg-[#0F111A] hover:bg-[#171926] border border-[#242838] text-xs text-[#00E5FF] font-mono font-bold rounded-lg transition-all">
                  BROWSE LOCAL VAULT
                </button>
              </div>
            </div>

            {/* Document Library Table */}
            <div className="bg-[#0F111A] border border-[#242838] p-6 rounded-lg space-y-6">
              <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4">
                <div className="space-y-1">
                  <h3 className="font-headline font-bold text-sm text-[#F3F4F6] uppercase tracking-wider">
                    Document Library Index
                  </h3>
                  <p className="text-[11px] text-[#9CA3AF]">SEC filings and external financial assets compiled for RAG queries.</p>
                </div>

                {/* Table Search */}
                <div className="relative max-w-xs w-full">
                  <span className="absolute left-3 top-2.5 text-[#9CA3AF]">
                    <Search size={14} />
                  </span>
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search RAG vault..."
                    className="w-full bg-[#08090C] border border-[#242838] rounded-lg pl-9 pr-4 py-2 text-xs text-[#F3F4F6] placeholder-[#555] glow-focus transition-all"
                  />
                </div>
              </div>

              {/* Data Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left font-body border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-[#242838] text-[#9CA3AF] font-mono uppercase text-[9px]">
                      <th className="py-3 px-4 font-normal">Document Name</th>
                      <th className="py-3 px-4 font-normal">Doc Type</th>
                      <th className="py-3 px-4 font-normal">Size</th>
                      <th className="py-3 px-4 font-normal">Uploaded On</th>
                      <th className="py-3 px-4 font-normal text-right">RAG Index Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#242838]/60">
                    {filteredDocs.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="py-12 text-center text-xs text-[#9CA3AF] font-mono">
                          <div className="flex flex-col items-center justify-center space-y-3 max-w-sm mx-auto p-4 border border-dashed border-[#242838] rounded-xl bg-[#08090C]/50 animate-fade-in">
                            <AlertCircle size={24} className="text-[#F59E0B] animate-pulse" />
                            <div className="space-y-1 text-center">
                              <h4 className="text-[#F3F4F6] font-bold text-xs uppercase tracking-wider">NO MATCHES LOCATED</h4>
                              <p className="text-[10px] text-[#9CA3AF] leading-relaxed">
                                No RAG index chunks match your filter query "{searchQuery}". Try searching for alternative ticker symbols or upload new annual filing documents above.
                              </p>
                            </div>
                            <button
                              type="button"
                              onClick={() => setSearchQuery('')}
                              className="px-3 py-1 bg-[#171926] border border-[#242838] text-[9.5px] font-bold text-[#00E5FF] rounded hover:bg-[#242838] transition-colors cursor-pointer"
                            >
                              RESET SEARCH FILTER
                            </button>
                          </div>
                        </td>
                      </tr>
                    ) : (
                      filteredDocs.map((doc) => (
                        <tr key={doc.id} className="hover:bg-[#08090C]/50 transition-colors">
                          <td className="py-3.5 px-4 font-medium text-[#F3F4F6] flex items-center gap-2.5">
                            <FileText size={16} className="text-[#00E5FF]" />
                            <span className="truncate max-w-xs">{doc.name}</span>
                          </td>
                          <td className="py-3.5 px-4 text-[#9CA3AF] font-mono">{doc.type}</td>
                          <td className="py-3.5 px-4 text-[#9CA3AF] font-mono">{doc.size}</td>
                          <td className="py-3.5 px-4 text-[#9CA3AF] font-mono">{doc.uploadDate}</td>
                          <td className="py-3.5 px-4 text-right">
                            <span
                              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono border ${
                                doc.status === 'Indexed'
                                  ? 'bg-[#10B981]/10 text-[#10B981] border-[#10B981]/20'
                                  : doc.status === 'Processing'
                                  ? 'bg-[#00E5FF]/10 text-[#00E5FF] border-[#00E5FF]/20'
                                  : 'bg-[#EF4444]/10 text-[#EF4444] border-[#EF4444]/20'
                              }`}
                            >
                              {doc.status === 'Indexed' && <CheckCircle size={10} />}
                              {doc.status === 'Processing' && <RefreshCw size={10} className="animate-spin" />}
                              {doc.status === 'Failed' && <XCircle size={10} />}
                              {doc.status}
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

          </div>

          {/* Right Column: Database / Vector Vault Stats */}
          <div className="col-span-1 lg:col-span-4 space-y-6">
            
            {/* Vector DB card */}
            <div className="bg-[#0F111A] border border-[#242838] p-6 rounded-lg space-y-6">
              <h4 className="font-headline font-bold text-xs text-[#F3F4F6] tracking-wider uppercase flex items-center gap-2">
                <Database size={14} className="text-[#00E5FF]" />
                Vector Store Allocation
              </h4>

              <div className="space-y-4 font-mono text-xs">
                
                {/* Latency */}
                <div className="bg-[#08090C] border border-[#242838] p-4 rounded-lg space-y-2">
                  <div className="flex justify-between text-[#9CA3AF]">
                    <span>Index Nodes</span>
                    <span className="text-[#10B981]">Healthy</span>
                  </div>
                  <strong className="text-xl text-[#F3F4F6] block">Qdrant Core 1</strong>
                </div>

                {/* Storage progress */}
                <div className="bg-[#08090C] border border-[#242838] p-4 rounded-lg space-y-3">
                  <div className="flex justify-between text-[#9CA3AF]">
                    <span>Memory Allocation</span>
                    <span className="text-[#00E5FF]">48.5% Limit</span>
                  </div>
                  <div className="w-full bg-[#171926] h-2 rounded-full overflow-hidden">
                    <div className="bg-[#00E5FF] h-full w-[48.5%]" />
                  </div>
                  <div className="flex justify-between text-[10px] text-[#9CA3AF]">
                    <span>4.85 GB Used</span>
                    <span>10.00 GB Allocated</span>
                  </div>
                </div>

                <div className="flex items-center gap-2 bg-[#EF4444]/5 border border-[#EF4444]/10 p-3 rounded text-[11px] text-[#EF4444]">
                  <AlertCircle size={14} />
                  <span>Index sync requires 128MB free Redis RAM</span>
                </div>

              </div>
            </div>

          </div>

        </main>
      </div>
    </div>
  );
};
export default DocumentCenter;
