import React from 'react';
import { MoreVertical, ArrowUp, ArrowDown } from 'lucide-react';

export interface BreakdownItem {
  id: string;
  name: string;
  icon?: React.ReactNode;
  color: string;
  amount: number;
  savingsRate: number;
  currentValue: number;
  targetValue: number;
  optimizedCost: number;
}

interface BreakdownGridProps {
  items: BreakdownItem[];
}

export function BreakdownGrid({ items }: BreakdownGridProps) {
  return (
    <div className="grid grid-cols-3 gap-6 mt-6">
      {items.map((item) => (
        <div key={item.id} className="bg-white rounded-2xl p-6 shadow-sm flex flex-col">
          <div className="flex justify-between items-center mb-6">
            <div className="flex items-center gap-2">
              {item.icon ? (
                <div className="text-xl">{item.icon}</div>
              ) : (
                <div className="w-5 h-5 rounded flex items-center justify-center font-bold text-white text-xs" style={{ backgroundColor: item.color }}>
                  {item.name.charAt(0)}
                </div>
              )}
              <span className="font-semibold text-gray-800">{item.name}</span>
            </div>
            <button className="text-gray-400 hover:text-gray-600">
              <MoreVertical size={20} />
            </button>
          </div>
          
          <div className="flex justify-between items-end mb-6">
            <div className="flex flex-col">
              <span className="text-2xl font-bold text-gray-800">${item.amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
              <span className="text-xs text-gray-400 mt-1">Est. Monthly missed savings</span>
            </div>
            <div className="flex flex-col items-end">
              <span className="text-2xl font-bold text-gray-800">{item.savingsRate}%</span>
              <span className="text-xs text-gray-400 mt-1">Savings rate</span>
            </div>
          </div>
          
          <div className="flex justify-between text-sm font-semibold mb-2">
            <span>${item.currentValue.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
            <span>${item.targetValue.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
          </div>
          
          <div className="w-full h-2.5 bg-brand-light rounded-full mb-6 overflow-hidden flex">
            <div 
              className="h-full rounded-full" 
              style={{ width: `${(item.currentValue / item.targetValue) * 100}%`, backgroundColor: item.color }}
            ></div>
          </div>
          
          <div className="flex justify-between items-center mb-6">
            <span className="flex items-center px-2 py-1 rounded-full font-medium text-xs bg-green-100 text-green-700">
              <ArrowUp size={12} className="mr-0.5" />
              {item.optimizedCost}%
            </span>
            <span className="text-xs text-gray-500">Potential optimized cost</span>
          </div>
          
          <button className="w-full py-3 bg-brand-navy hover:bg-gray-800 text-white rounded-xl font-medium transition-colors mt-auto">
            Start optimizing
          </button>
        </div>
      ))}
    </div>
  );
}
