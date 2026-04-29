import { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { X, CheckCircle2, AlertCircle, AlertTriangle } from 'lucide-react';

type ToastType = 'success' | 'error' | 'warning';

interface Toast {
  id: string;
  message: string;
  type: ToastType;
}

interface ToastContextValue {
  toast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}

const STYLES: Record<ToastType, { border: string; icon: string; bar: string; bg: string }> = {
  success: { bg: 'bg-surface',   border: 'border-success/30', icon: 'text-success', bar: 'bg-success' },
  error:   { bg: 'bg-surface',   border: 'border-danger/30',  icon: 'text-danger',  bar: 'bg-danger' },
  warning: { bg: 'bg-surface',   border: 'border-warn/30',    icon: 'text-warn',    bar: 'bg-warn' },
};

const ICONS: Record<ToastType, typeof CheckCircle2> = {
  success: CheckCircle2,
  error:   AlertCircle,
  warning: AlertTriangle,
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const toast = useCallback((message: string, type: ToastType = 'success') => {
    const id = Math.random().toString(36).slice(2);
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000);
  }, []);

  const dismiss = (id: string) => setToasts(prev => prev.filter(t => t.id !== id));

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-[200] flex flex-col gap-2 pointer-events-none max-w-sm w-full px-4">
        {toasts.map(t => {
          const Icon = ICONS[t.type];
          const s = STYLES[t.type];
          return (
            <div
              key={t.id}
              className={`relative flex items-start gap-3 px-4 py-3 rounded-xl border shadow-2xl pointer-events-auto overflow-hidden ${s.bg} ${s.border}`}
              style={{ animation: 'fadeSlideUp 0.25s ease-out' }}
            >
              {/* Coloured left accent bar */}
              <div className={`absolute left-0 top-0 bottom-0 w-1 ${s.bar} rounded-l-xl`} />
              <Icon size={17} className={`shrink-0 mt-0.5 ml-1 ${s.icon}`} />
              <p className="text-sm text-gray-200 flex-1">{t.message}</p>
              <button
                onClick={() => dismiss(t.id)}
                className="text-gray-500 hover:text-white transition-colors shrink-0"
              >
                <X size={14} />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}
