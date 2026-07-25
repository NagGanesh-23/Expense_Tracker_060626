import React, { useEffect, useState } from 'react';
import { TopNav } from './components/TopNav';
import { KpiCard } from './components/KpiCard';
import { MainChart } from './components/MainChart';
import { RadialGauge } from './components/RadialGauge';
import { BreakdownGrid } from './components/BreakdownGrid';
import { fetchDashboardData } from './utils/dataIngestion';
import type { DashboardData } from './utils/dataIngestion';

function App() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData().then(d => {
      setData(d);
      setLoading(false);
    });
  }, []);

  if (loading || !data) {
    return <div className="min-h-screen bg-brand-bg flex items-center justify-center font-semibold text-gray-500">Loading Dashboard...</div>;
  }

  return (
    <div className="min-h-screen bg-[#E5E7EB] p-4 lg:p-8">
      <div className="max-w-7xl mx-auto bg-brand-bg rounded-[2rem] shadow-xl overflow-hidden border border-gray-200">
        <TopNav />
        
        <div className="p-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* Left Column (KPI + Gauge) */}
            <div className="flex flex-col gap-6">
              <KpiCard 
                title="Total Expense" 
                amount={data.totalSpend} 
                change={data.spendChangePct}
                icon={
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4">
                    <path d="M12 1v22M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
                  </svg>
                }
              />
              <RadialGauge 
                amount={data.totalSpend} 
                change={6} // Example change specifically for hybrid cost comparison
                data={data.categoryBreakdown}
              />
            </div>
            
            {/* Right Column (Main Chart) */}
            <MainChart data={data.chartData} totalAmount={data.totalSpend} />
            
          </div>

          {/* Bottom Grid */}
          <BreakdownGrid items={data.breakdownItems} />
        </div>
      </div>
    </div>
  );
}

export default App;
