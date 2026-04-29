import React, { useState } from 'react';
import { ClipboardList, BarChart2, User, LogOut, Menu, X, Download, GraduationCap } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export function cn(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(' ');
}

export type TeacherView = 'attendance' | 'report' | 'course_export' | 'profile';

interface SidebarProps {
  currentView: TeacherView;
  onViewChange: (view: TeacherView) => void;
}

const NAV_ITEMS: { id: TeacherView; label: string; icon: React.ElementType }[] = [
  { id: 'attendance',    label: 'Mark Attendance', icon: ClipboardList },
  { id: 'report',        label: 'View Reports',    icon: BarChart2 },
  { id: 'course_export', label: 'Course Export',   icon: Download },
  { id: 'profile',       label: 'My Profile',      icon: User },
];

export default function Sidebar({ currentView, onViewChange }: SidebarProps) {
  const { user, logout } = useAuth();
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  const initials = user?.full_name
    ?.split(' ')
    .map(n => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2) ?? '?';

  const handleNavChange = (view: TeacherView) => {
    onViewChange(view);
    setIsMobileOpen(false);
  };

  const isAdmin = user?.role === 'admin';
  const roleColor = isAdmin ? 'text-warn' : 'text-primary';
  const roleBadge = isAdmin
    ? 'bg-warn/15 text-warn border border-warn/30'
    : 'bg-primary/15 text-primary border border-primary/30';

  return (
    <>
      {/* Mobile hamburger trigger */}
      <button
        onClick={() => setIsMobileOpen(true)}
        className="md:hidden fixed top-4 left-4 z-50 w-10 h-10 bg-surface-dark border border-white/10 rounded-lg flex items-center justify-center text-gray-300 shadow-xl hover:border-primary/40 hover:text-white transition-all"
        aria-label="Open menu"
      >
        <Menu size={20} />
      </button>

      {/* Mobile backdrop */}
      {isMobileOpen && (
        <div
          className="md:hidden fixed inset-0 bg-black/70 z-40 backdrop-blur-sm"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* Sidebar panel */}
      <aside
        className={cn(
          'fixed top-0 left-0 h-full w-64 bg-surface-dark border-r border-white/8 flex flex-col z-50 transition-transform duration-300 ease-out',
          isMobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        )}
      >
        {/* Brand */}
        <div className="px-5 py-5 border-b border-white/8 flex items-start justify-between gap-3">
          <div className="flex items-start gap-2.5">
            <GraduationCap
              size={20}
              className={cn('mt-0.5 shrink-0 animate-bounce-icon', roleColor)}
            />
            <div>
              <h1 className="text-sm font-bold text-white leading-snug tracking-tight">
                Ethereal Paranatellon<br />University
              </h1>
              <p className={cn('text-[10px] font-bold uppercase tracking-widest mt-1', roleColor)}>
                {isAdmin ? 'Admin Portal' : 'Teacher Portal'}
              </p>
            </div>
          </div>
          <button
            onClick={() => setIsMobileOpen(false)}
            className="md:hidden text-gray-500 hover:text-white transition-colors mt-0.5 shrink-0"
            aria-label="Close menu"
          >
            <X size={18} />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
          {NAV_ITEMS.map(({ id, label, icon: Icon }) => {
            const active = currentView === id;
            return (
              <button
                key={id}
                onClick={() => handleNavChange(id)}
                className={cn(
                  'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all text-left group relative',
                  active
                    ? 'bg-primary/15 text-primary'
                    : 'text-gray-400 hover:bg-white/5 hover:text-gray-100'
                )}
              >
                <span
                  className={cn(
                    'absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-r-full transition-all duration-200',
                    active ? 'bg-primary opacity-100' : 'opacity-0'
                  )}
                />
                <Icon
                  size={17}
                  strokeWidth={active ? 2.5 : 2}
                  className={cn(
                    'transition-all duration-200',
                    active ? 'text-primary' : 'group-hover:-translate-y-0.5 group-hover:scale-110'
                  )}
                />
                {label}
              </button>
            );
          })}
        </nav>

        {/* User footer */}
        <div className="px-3 py-4 border-t border-white/8 space-y-1">
          <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-white/5 border border-white/8">
            {user?.profile_picture_url ? (
              <img
                src={`http://127.0.0.1:8000${user.profile_picture_url}`}
                alt="Avatar"
                className="w-8 h-8 rounded-full object-cover shrink-0 ring-2 ring-success/50"
              />
            ) : (
              <div className="w-8 h-8 rounded-full bg-primary/20 border border-primary/30 text-primary flex items-center justify-center text-xs font-bold shrink-0">
                {initials}
              </div>
            )}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-white truncate">{user?.full_name}</p>
              <span className={cn('inline-block text-[10px] px-1.5 py-0.5 rounded font-bold capitalize mt-0.5', roleBadge)}>
                {user?.role}
              </span>
            </div>
          </div>

          <button
            onClick={logout}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-400 hover:bg-danger/10 hover:text-danger transition-all group"
          >
            <LogOut size={16} className="transition-transform group-hover:translate-x-0.5" />
            Sign Out
          </button>
        </div>
      </aside>
    </>
  );
}
