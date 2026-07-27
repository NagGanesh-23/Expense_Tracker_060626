import { useState, useRef, useEffect } from 'react';
import { Settings, Terminal, Database, ShieldCheck } from 'lucide-react';

interface HeaderSettingsMenuProps {
  isDevMode: boolean;
  onToggleDevMode: () => void;
  dataSource?: string;
}

export function HeaderSettingsMenu({
  isDevMode,
  onToggleDevMode,
  dataSource = 'Google Sheets (Live)',
}: HeaderSettingsMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="relative inline-block text-left ml-2" ref={menuRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`p-2 rounded-lg border transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-brand-primary ${
          isOpen
            ? 'bg-brand-surface border-brand-primary text-white shadow-sm'
            : 'bg-transparent border-brand-border text-brand-neutral hover:text-white hover:bg-brand-surface/50'
        }`}
        title="Settings & Preferences"
        aria-label="Settings"
      >
        <Settings className={`w-4 h-4 transition-transform duration-300 ${isOpen ? 'rotate-90 text-brand-primary' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-64 rounded-xl bg-[#0F172A] border border-brand-border shadow-2xl z-50 py-2 animate-fadeIn backdrop-blur-xl">
          <div className="px-4 py-2 border-b border-brand-border/60">
            <span className="text-[11px] font-semibold tracking-wider text-brand-neutral uppercase">
              System Settings
            </span>
          </div>

          <div className="px-4 py-3 border-b border-brand-border/60">
            <label className="flex items-center justify-between cursor-pointer group">
              <div className="flex items-center gap-2.5">
                <div className={`p-1.5 rounded-lg ${isDevMode ? 'bg-brand-primary/20 text-brand-primary' : 'bg-slate-800 text-slate-400'}`}>
                  <Terminal className="w-3.5 h-3.5" />
                </div>
                <div>
                  <div className="text-xs font-semibold text-slate-200 group-hover:text-white transition-colors">
                    Developer Mode
                  </div>
                  <div className="text-[10px] text-brand-neutral">
                    Show System Health view
                  </div>
                </div>
              </div>
              <input
                type="checkbox"
                checked={isDevMode}
                onChange={onToggleDevMode}
                className="sr-only peer"
              />
              <div className="w-8 h-4 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[12px] after:right-[18px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-brand-primary relative"></div>
            </label>
          </div>

          <div className="px-4 py-2.5 space-y-1.5">
            <div className="flex items-center justify-between text-xs text-brand-neutral">
              <span className="flex items-center gap-1.5">
                <Database className="w-3.5 h-3.5" /> Storage:
              </span>
              <span className="text-slate-300 font-mono text-[11px]">{dataSource}</span>
            </div>
            <div className="flex items-center justify-between text-xs text-brand-neutral">
              <span className="flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" /> Security:
              </span>
              <span className="text-emerald-400 font-mono text-[11px]">Enforced</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
