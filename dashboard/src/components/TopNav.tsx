import React from 'react';
import { LayoutDashboard, SlidersHorizontal, DollarSign, Bell } from 'lucide-react';

export function TopNav() {
  return (
    <nav className="bg-brand-navy text-white py-4 px-6 rounded-t-2xl flex items-center justify-between">
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 bg-white text-brand-navy flex items-center justify-center font-bold text-xl rounded">
          <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
            <path d="M12 2L2 22h20L12 2z" />
          </svg>
        </div>
        <span className="font-bold text-xl tracking-wider">CCMO</span>
      </div>

      <div className="flex gap-4">
        <button className="flex items-center gap-2 px-4 py-2 bg-gray-800 rounded-full text-sm font-medium">
          <LayoutDashboard size={16} /> Dashboard
        </button>
        <button className="flex items-center gap-2 px-4 py-2 hover:bg-gray-800 rounded-full text-sm font-medium text-gray-400 transition-colors">
          <SlidersHorizontal size={16} /> Optimisation
        </button>
        <button className="flex items-center gap-2 px-4 py-2 hover:bg-gray-800 rounded-full text-sm font-medium text-gray-400 transition-colors">
          <DollarSign size={16} /> Cost analysis
        </button>
      </div>

      <div className="flex items-center gap-4">
        <button className="p-2 hover:bg-gray-800 rounded-full transition-colors relative">
          <Bell size={20} />
          <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
        </button>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gray-600 rounded-full overflow-hidden">
            {/* Placeholder avatar */}
            <img src="https://i.pravatar.cc/150?img=11" alt="David Wilium" className="w-full h-full object-cover" />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-semibold">David Wilium</span>
            <span className="text-xs text-gray-400">DevOps</span>
          </div>
        </div>
      </div>
    </nav>
  );
}
