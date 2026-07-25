import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { Settings2, Calendar } from 'lucide-react';

interface ChartData {
  name: string;
  current: number;
  previous: number;
}

interface MainChartProps {
  data: ChartData[];
  totalAmount: number;
}

export function MainChart({ data, totalAmount }: MainChartProps) {
  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm col-span-2">
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-brand-slate text-white flex items-center justify-center">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
              <line x1="12" y1="8" x2="12" y2="16"></line>
              <line x1="8" y1="12" x2="16" y2="12"></line>
            </svg>
          </div>
          <span className="font-semibold text-gray-700">Total cost, $</span>
        </div>
        
        <div className="flex items-center gap-3">
          <button className="flex items-center gap-2 px-3 py-1.5 border border-brand-slate text-brand-slate rounded-lg text-sm font-medium hover:bg-blue-50 transition-colors">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4">
              <rect x="3" y="3" width="7" height="18" rx="1" ry="1"></rect>
              <rect x="14" y="3" width="7" height="18" rx="1" ry="1"></rect>
            </svg>
            Columns
          </button>
          <button className="flex items-center gap-2 px-3 py-1.5 border border-gray-200 text-gray-500 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors">
            <Settings2 size={16} />
            Liner
          </button>
          <button className="p-1.5 border border-gray-200 text-gray-500 rounded-lg hover:bg-gray-50 transition-colors">
            <Calendar size={18} />
          </button>
        </div>
      </div>

      <div className="h-[250px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }} barGap={2} barSize={20}>
            <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#9CA3AF', fontSize: 12 }} dy={10} />
            <YAxis axisLine={false} tickLine={false} tick={{ fill: '#9CA3AF', fontSize: 12 }} tickFormatter={(val) => val >= 1000 ? `${val/1000}k` : val} />
            <Tooltip 
              cursor={{ fill: '#F1F5F9', radius: 4 }}
              content={({ active, payload, label }) => {
                if (active && payload && payload.length) {
                  return (
                    <div className="bg-white p-4 shadow-lg rounded-xl border border-gray-100">
                      <p className="font-semibold text-gray-700 mb-2">{label}</p>
                      <div className="flex flex-col gap-2">
                        <div className="flex items-center gap-2 text-sm">
                          <div className="w-3 h-3 rounded-full bg-brand-blue"></div>
                          <span className="text-gray-500">Current month</span>
                          <span className="font-bold text-gray-800 ml-auto">${payload[0].value?.toLocaleString()}</span>
                        </div>
                        <div className="flex items-center gap-2 text-sm">
                          <div className="w-3 h-3 rounded-full bg-brand-light"></div>
                          <span className="text-gray-500">Previous month</span>
                          <span className="font-bold text-gray-800 ml-auto">${payload[1]?.value?.toLocaleString() || 0}</span>
                        </div>
                      </div>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Bar dataKey="current" radius={[4, 4, 4, 4]}>
              {data.map((entry, index) => (
                <Cell key={`cell-curr-${index}`} fill="#1E3A8A" /> // brand-blue
              ))}
            </Bar>
            <Bar dataKey="previous" radius={[4, 4, 4, 4]}>
              {data.map((entry, index) => (
                <Cell key={`cell-prev-${index}`} fill="#93C5FD" /> // brand-light
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
