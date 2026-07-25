import React from 'react';
import { MoreVertical, ArrowUp, ArrowDown } from 'lucide-react';

interface KpiCardProps {
  title: string;
  amount: number | string;
  change: number;
  icon?: React.ReactNode;
}

export function KpiCard({ title, amount, change, icon }: KpiCardProps) {
  const isPositive = change > 0;
  
  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm flex flex-col gap-4">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-2">
          {icon && (
            <div className="w-8 h-8 rounded-full bg-brand-slate text-white flex items-center justify-center">
              {icon}
            </div>
          )}
          <span className="font-semibold text-gray-700">{title}</span>
        </div>
        <button className="text-gray-400 hover:text-gray-600">
          <MoreVertical size={20} />
        </button>
      </div>
      
      <div className="text-4xl font-bold text-gray-800">
        {typeof amount === 'number' ? `$${amount.toLocaleString(undefined, { minimumFractionDigits: 0 })}` : amount}
      </div>
      
      <div className="flex items-center gap-2 text-sm">
        <span className={`flex items-center px-2 py-1 rounded-full font-medium ${
          isPositive ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
        }`}>
          {isPositive ? <ArrowUp size={14} className="mr-1" /> : <ArrowDown size={14} className="mr-1" />}
          {Math.abs(change)}%
        </span>
        <span className="text-gray-400">vs last month</span>
      </div>
    </div>
  );
}
