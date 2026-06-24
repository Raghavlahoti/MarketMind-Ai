export interface QueryItem {
  id: string;
  timestamp: string;
  query: string;
  sourceCount: number;
  status: 'Completed' | 'Processing' | 'Failed';
  inferenceTime: string;
}

export interface ReportItem {
  id: string;
  ticker: string;
  companyName: string;
  reportType: string;
  date: string;
  sentiment: 'Bullish' | 'Neutral' | 'Bearish';
  author: string;
  riskRating: 'High' | 'Medium' | 'Low';
}

export interface SystemStatus {
  nvidiaNim: {
    status: 'Operational' | 'Degraded' | 'Offline';
    latencyMs: number;
    throughput: number;
  };
  arqWorkers: {
    active: number;
    queued: number;
    failed24h: number;
  };
  redis: {
    status: 'Operational' | 'Degraded';
    memoryUsageMB: number;
    connectedClients: number;
  };
  postgres: {
    status: 'Operational';
    activeConnections: number;
    dbSizeGB: number;
  };
  qdrant: {
    status: 'Operational';
    indexedVectors: number;
    searchLatencyMs: number;
  };
}

export interface DocumentItem {
  id: string;
  name: string;
  type: string;
  size: string;
  uploadDate: string;
  status: 'Indexed' | 'Processing' | 'Failed';
}

export interface UserItem {
  id: string;
  name: string;
  email: string;
  role: 'Admin' | 'Analyst';
  activeKeys: number;
  status: 'Active' | 'Suspended';
}

export const initialQueries: QueryItem[] = [
  { id: 'q1', timestamp: '2026-06-24 15:34', query: 'Compare Q3 SEC Filings for NVIDIA & AMD regarding AI accelerator supply chains', sourceCount: 12, status: 'Completed', inferenceTime: '82ms' },
  { id: 'q2', timestamp: '2026-06-24 14:15', query: 'Tesla Q4 risk factors analysis following European regulatory updates', sourceCount: 8, status: 'Completed', inferenceTime: '94ms' },
  { id: 'q3', timestamp: '2026-06-24 12:02', query: 'Microsoft annual cloud capital expenditure projections and NIM LLM integration costs', sourceCount: 15, status: 'Completed', inferenceTime: '105ms' },
  { id: 'q4', timestamp: '2026-06-24 10:45', query: 'Apple AR/VR headset supply chain bottlenecks and gross margin predictions', sourceCount: 5, status: 'Failed', inferenceTime: '—' },
  { id: 'q5', timestamp: '2026-06-24 09:30', query: 'Analyzing JPMorgan Chase Q1 net interest income growth targets', sourceCount: 9, status: 'Completed', inferenceTime: '76ms' }
];

export const initialReports: ReportItem[] = [
  { id: 'rep1', ticker: 'NVDA', companyName: 'NVIDIA Corporation', reportType: 'Full Deep Dive', date: '2026-06-24', sentiment: 'Bullish', author: 'MarketMind AI NIM', riskRating: 'Medium' },
  { id: 'rep2', ticker: 'TSLA', companyName: 'Tesla Inc', reportType: 'Risk Assessment', date: '2026-06-23', sentiment: 'Neutral', author: 'MarketMind AI NIM', riskRating: 'High' },
  { id: 'rep3', ticker: 'MSFT', companyName: 'Microsoft Corporation', reportType: 'Financial Summary', date: '2026-06-22', sentiment: 'Bullish', author: 'MarketMind AI NIM', riskRating: 'Low' },
  { id: 'rep4', ticker: 'AMZN', companyName: 'Amazon.com Inc', reportType: 'Annual Report Parse', date: '2026-06-21', sentiment: 'Bullish', author: 'MarketMind AI NIM', riskRating: 'Low' }
];

export const initialSystemStatus: SystemStatus = {
  nvidiaNim: {
    status: 'Operational',
    latencyMs: 82,
    throughput: 1240
  },
  arqWorkers: {
    active: 12,
    queued: 0,
    failed24h: 2
  },
  redis: {
    status: 'Operational',
    memoryUsageMB: 284.5,
    connectedClients: 32
  },
  postgres: {
    status: 'Operational',
    activeConnections: 45,
    dbSizeGB: 18.4
  },
  qdrant: {
    status: 'Operational',
    indexedVectors: 485230,
    searchLatencyMs: 4.2
  }
};

export const initialDocuments: DocumentItem[] = [
  { id: 'doc1', name: 'NVIDIA-10K-2025.pdf', type: 'SEC 10-K', size: '4.8 MB', uploadDate: '2026-06-24', status: 'Indexed' },
  { id: 'doc2', name: 'Tesla-Sustainability-Report-2025.pdf', type: 'Annual Report', size: '12.4 MB', uploadDate: '2026-06-23', status: 'Indexed' },
  { id: 'doc3', name: 'JPM-Q1-2026-Earnings-Release.pdf', type: 'Earnings Release', size: '2.1 MB', uploadDate: '2026-06-24', status: 'Processing' },
  { id: 'doc4', name: 'AMD-Supply-Chain-Risks-External.pdf', type: 'Analyst Report', size: '1.5 MB', uploadDate: '2026-06-22', status: 'Indexed' },
  { id: 'doc5', name: 'Apple-Vision-Pro-Sales-Data.csv', type: 'Spreadsheet', size: '0.9 MB', uploadDate: '2026-06-20', status: 'Failed' }
];

export const initialUsers: UserItem[] = [
  { id: 'u1', name: 'Sarah Connor', email: 's.connor@cyberdyne.com', role: 'Admin', activeKeys: 3, status: 'Active' },
  { id: 'u2', name: 'Raghav Maheshwari', email: 'raghav@marketmind.ai', role: 'Admin', activeKeys: 2, status: 'Active' },
  { id: 'u3', name: 'John Doe', email: 'john.doe@goldman.com', role: 'Analyst', activeKeys: 1, status: 'Active' },
  { id: 'u4', name: 'Alice Smith', email: 'alice.s@blackrock.com', role: 'Analyst', activeKeys: 1, status: 'Suspended' }
];

export const mockChatHistory = [
  { id: 'c1', title: 'NVIDIA Q3 AI Capacity Analysis' },
  { id: 'c2', title: 'Tesla regulatory headwind assessment' },
  { id: 'c3', title: 'JPMorgan net interest income targets' },
  { id: 'c4', title: 'Microsoft NIM integration cost models' }
];

export const mockChatMessages = [
  {
    sender: 'user',
    text: 'Show me NVIDIA\'s AI capacity expansion plans and reference your sources.'
  },
  {
    sender: 'assistant',
    text: 'According to **NVIDIA\'s Q3 SEC 10-Q filing** [1], NVIDIA is expanding its advanced chip manufacturing and packaging capacity through key partnerships. They project a capital expenditure increase of **28% year-over-year** to support packaging expansions [2]. Here is a summary of the insights:\n\n*   **H100 & Blackwell packaging bottlenecks:** CoWoS supply constraints are expected to ease by Q1 2027.\n*   **RAG Document Reference:** Document *NVIDIA-10K-2025.pdf* lists capital expansion budget as $8.4B.\n*   **NIM Integration latency:** 82ms response using Llama 3 70B NIM backend.\n\nWhat other metrics would you like me to look up?'
  }
];

export const mockCitations = [
  { id: '[1]', title: 'NVIDIA Q3 10-Q SEC Filing, Section 4 (Page 45)', excerpt: 'Manufacturing capacity expansions are ongoing with primary partner TSMC under joint CoWoS optimization plans...' },
  { id: '[2]', title: 'NVIDIA annual capital allocation report 2025', excerpt: 'Capital expenditures for packaging and testing facilities will grow by 28% to support high volume production of Blackwell...' }
];
