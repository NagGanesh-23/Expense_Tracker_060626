import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import { Calendar, ArrowUp, ArrowDown } from 'lucide-react';

interface RadialGaugeProps {
  amount: number;
  change: number;
  data: { name: string; value: number; color: string }[];
}

export function RadialGauge({ amount, change, data }: RadialGaugeProps) {
  const isPositive = change > 0;

  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm flex flex-col items-center">
      <div className="w-full flex justify-between items-center mb-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-brand-slate text-white flex items-center justify-center">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4">
              <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
            </svg>
          </div>
          <span className="font-semibold text-gray-700">Category breakdown</span>
        </div>
        <button className="p-1.5 border border-gray-200 text-gray-500 rounded-lg hover:bg-gray-50 transition-colors">
          <Calendar size={18} />
        </button>
      </div>

      <div className="relative w-full h-[200px] flex items-center justify-center mt-4">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="100%"
              startAngle={180}
              endAngle={0}
              innerRadius={75}
              outerRadius={95}
              paddingAngle={2}
              dataKey="value"
              stroke="none"
              cornerRadius={4}
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        
        <div className="absolute bottom-4 flex flex-col items-center">
          <span className="text-3xl font-bold text-gray-800">
            ${amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
          <div className="flex items-center gap-1 mt-2">
            <span className={`flex items-center px-2 py-1 rounded-full font-medium text-xs ${
              isPositive ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
            }`}>
              {isPositive ? <ArrowUp size={12} className="mr-0.5" /> : <ArrowDown size={12} className="mr-0.5" />}
              {Math.abs(change)}%
            </span>
          </div>
          <span className="text-xs text-gray-400 mt-1">vs last month</span>
        </div>
      </div>

      <div className="w-full mt-6 grid grid-cols-3 gap-y-3 gap-x-2 text-xs">
        {data.map((item, i) => (
          <div key={i} className="flex items-center gap-1.5">
            <div className="w-1.5 h-3 rounded-full" style={{ backgroundColor: item.color }}></div>
            <span className="text-gray-500 truncate" title={item.name}>{item.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
