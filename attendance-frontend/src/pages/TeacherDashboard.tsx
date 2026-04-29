import React, { useState } from 'react';
import Sidebar, { TeacherView } from '../components/Sidebar';
import AttendanceEntry from '../components/AttendanceEntry';
import StudentReport from '../components/StudentReport';
import CourseExport from '../components/CourseExport';
import AvatarUpload from '../components/AvatarUpload';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { KeyRound, ShieldCheck } from 'lucide-react';
import { authFetch } from '../api/client';

function ProfileTab() {
  const { user } = useAuth();
  const { toast } = useToast();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword.length < 8) {
      toast('New password must be at least 8 characters.', 'error');
      return;
    }
    setIsSaving(true);
    try {
      const res = await authFetch('/auth/change-password', {
        method: 'POST',
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to change password.');
      toast('Password changed successfully.', 'success');
      setCurrentPassword('');
      setNewPassword('');
    } catch (err: any) {
      toast(err.message, 'error');
    } finally {
      setIsSaving(false);
    }
  };

  const isAdmin = user?.role === 'admin';
  const inputClass = 'w-full bg-white/10 border border-white/20 text-white placeholder-gray-400 text-sm rounded-xl p-2.5 focus:ring-2 focus:ring-primary/50 focus:border-primary/50 hover:border-white/30 outline-none transition-all';

  return (
    <div className="max-w-lg space-y-8 animate-fade-slide-up">
      <div>
        <h2 className="text-2xl font-bold text-white">My Profile</h2>
        <p className="text-gray-400 text-sm mt-1">Manage your account settings and photo.</p>
      </div>

      <div className="glass-panel p-8 flex flex-col items-center gap-4">
        <AvatarUpload />
        <p className="text-xs text-gray-500 mt-1">Click the photo to upload a new one (JPEG, PNG, max 5 MB)</p>
      </div>

      {isAdmin && (
        <div className="flex items-center gap-2 px-4 py-3 rounded-xl bg-warn/10 border border-warn/30 text-warn text-sm font-semibold">
          <ShieldCheck size={16} />
          You are logged in as an Administrator.
        </div>
      )}

      <div className="glass-panel p-6">
        <h3 className="text-base font-bold text-white mb-5 flex items-center gap-2">
          <KeyRound size={16} className="text-primary" />
          Change Password
        </h3>
        <form onSubmit={handleChangePassword} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5">
              Current Password
            </label>
            <input
              type="password"
              value={currentPassword}
              onChange={e => setCurrentPassword(e.target.value)}
              className={inputClass}
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5">
              New Password
            </label>
            <input
              type="password"
              value={newPassword}
              onChange={e => setNewPassword(e.target.value)}
              placeholder="Minimum 8 characters"
              className={inputClass}
            />
          </div>
          <button
            type="submit"
            disabled={isSaving || !currentPassword || !newPassword}
            className="px-5 py-2.5 text-sm font-semibold rounded-xl bg-primary text-white hover:bg-indigo-500 hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-40 disabled:cursor-not-allowed disabled:translate-y-0 transition-all shadow-[0_4px_15px_rgba(99,102,241,0.3)]"
          >
            {isSaving ? 'Saving...' : 'Update Password'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default function TeacherDashboard() {
  const [currentView, setCurrentView] = useState<TeacherView>('attendance');
  const { user } = useAuth();

  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
  const isAdmin = user?.role === 'admin';

  return (
    <div className="min-h-screen bg-background">
      <Sidebar currentView={currentView} onViewChange={setCurrentView} />
      <main className="md:ml-64 p-4 md:p-8 pt-16 md:pt-8">
        <div className="max-w-6xl mx-auto">

          {/* Quick stats greeting header */}
          <div className="mb-6 pb-6 border-b border-white/8 flex items-center justify-between">
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-widest font-semibold">{greeting}</p>
              <h2 className="text-xl font-bold text-white mt-0.5">{user?.full_name}</h2>
            </div>
            <span className={
              isAdmin
                ? 'px-3 py-1 rounded-full text-xs font-bold bg-warn/15 text-warn border border-warn/30'
                : 'px-3 py-1 rounded-full text-xs font-bold bg-primary/15 text-primary border border-primary/30'
            }>
              {isAdmin ? 'Administrator' : 'Teacher'}
            </span>
          </div>

          {/* Tab content — keyed so each switch re-triggers the fade animation */}
          <div key={currentView} className="animate-fade-slide-up">
            {currentView === 'attendance'    && <AttendanceEntry />}
            {currentView === 'report'        && <StudentReport />}
            {currentView === 'course_export' && <CourseExport />}
            {currentView === 'profile'       && <ProfileTab />}
          </div>
        </div>
      </main>
    </div>
  );
}
