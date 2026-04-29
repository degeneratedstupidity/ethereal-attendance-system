import { useState, useEffect } from 'react';
import { LogOut, CalendarCheck, AlertCircle, TrendingUp, Download, GraduationCap } from 'lucide-react';
import { authFetch } from '../api/client';
import { useAuth } from '../context/AuthContext';
import AvatarUpload from '../components/AvatarUpload';
import { cn } from '../components/Sidebar';

interface CourseAttendanceSummary {
  course_id: string;
  course_name: string;
  course_code: string;
  total_classes: number;
  present_count: number;
  absent_count: number;
  late_count: number;
  attendance_percentage: number;
  teacher_name?: string;
}

interface AttendanceReport {
  student_id: string;
  student_name: string;
  courses: CourseAttendanceSummary[];
  overall_percentage: number;
}

interface BunkResult {
  overall_percentage: number;
  total_classes: number;
  attended_classes: number;
  status: 'safe' | 'critical' | 'no_data';
  safe_to_bunk: number | null;
  must_attend: number | null;
  message: string;
}

function CircularProgress({ pct, size = 160 }: { pct: number; size?: number }) {
  const radius = (size - 20) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (Math.min(pct, 100) / 100) * circumference;
  const isSafe = pct >= 75;

  return (
    <svg width={size} height={size} className="rotate-[-90deg]">
      <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="#1E2538" strokeWidth={12} />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke={isSafe ? '#22C55E' : '#EF4444'}
        strokeWidth={12}
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        style={{
          transition: 'stroke-dashoffset 1.4s cubic-bezier(0.4,0,0.2,1)',
          filter: `drop-shadow(0 0 8px ${isSafe ? '#22C55E88' : '#EF444488'})`,
        }}
      />
      <text
        x={size / 2}
        y={size / 2}
        textAnchor="middle"
        dominantBaseline="middle"
        style={{ transform: `rotate(90deg)`, transformOrigin: `${size / 2}px ${size / 2}px` }}
        fontSize="22"
        fontWeight="700"
        fill={isSafe ? '#22C55E' : '#EF4444'}
      >
        {Math.round(pct)}%
      </text>
    </svg>
  );
}

export default function StudentDashboard() {
  const { user, logout } = useAuth();
  const [report, setReport] = useState<AttendanceReport | null>(null);
  const [bunk, setBunk] = useState<BunkResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    const id = user.id;
    Promise.all([
      authFetch(`/students/${id}/attendance`).then(r => r.json()),
      authFetch(`/students/${id}/bunk-calculator`).then(r => r.json()),
    ])
      .then(([reportData, bunkData]) => {
        setReport(reportData);
        setBunk(bunkData);
      })
      .catch(err => {
        console.error(err);
        setError('Failed to load your attendance data.');
      })
      .finally(() => setIsLoading(false));
  }, [user]);

  const handleExport = async () => {
    if (!user) return;
    const res = await authFetch(`/students/${user.id}/attendance/export`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'my_attendance.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="w-10 h-10 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-gray-500">Loading your dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Top nav */}
      <header className="bg-surface-dark border-b border-white/8 shadow-lg sticky top-0 z-20">
        <div className="max-w-4xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <GraduationCap size={18} className="text-primary animate-bounce-icon" />
            <div>
              <h1 className="text-sm font-bold text-white leading-tight">Ethereal Paranatellon University</h1>
              <p className="text-[10px] text-primary font-bold uppercase tracking-widest">Student Portal</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleExport}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-white/8 text-gray-300 border border-white/10 hover:bg-white/15 hover:text-white hover:-translate-y-0.5 transition-all"
            >
              <Download size={13} />
              Export CSV
            </button>
            <button
              onClick={logout}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg text-gray-400 hover:bg-danger/10 hover:text-danger border border-transparent transition-all"
            >
              <LogOut size={13} />
              Sign Out
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 md:px-6 py-8 space-y-6">
        {error && (
          <div className="flex items-center gap-2 bg-danger/10 border border-danger/30 text-red-300 px-4 py-3 rounded-xl text-sm">
            <AlertCircle size={16} className="text-danger" />
            {error}
          </div>
        )}

        {/* Profile header */}
        <div className="bg-surface rounded-2xl border border-white/10 shadow-xl p-6 flex flex-col sm:flex-row items-center sm:items-start gap-6">
          <AvatarUpload />
          <div className="flex-1 text-center sm:text-left">
            <h2 className="text-2xl font-bold text-white">{user?.full_name}</h2>
            <p className="text-sm text-gray-500 mt-0.5">{user?.email}</p>
            {report && (
              <div className={cn(
                'inline-block mt-3 px-3 py-1 rounded-full text-xs font-bold border',
                report.overall_percentage >= 75
                  ? 'bg-success/15 text-success border-success/30'
                  : 'bg-danger/15 text-danger border-danger/30'
              )}>
                {report.overall_percentage >= 75 ? 'Good Standing' : 'Attendance Critical'}
                {' · '}{report.overall_percentage.toFixed(1)}% overall
              </div>
            )}
          </div>
        </div>

        {/* Bunk Calculator hero */}
        {bunk && bunk.status !== 'no_data' && (
          <div className={cn(
            'rounded-2xl border shadow-2xl p-6 md:p-8 relative overflow-hidden',
            bunk.status === 'safe'
              ? 'bg-success/5 border-success/25'
              : 'bg-danger/5 border-danger/25'
          )}>
            {/* Subtle glow */}
            <div className={cn(
              'absolute -top-20 -right-20 w-60 h-60 rounded-full blur-3xl pointer-events-none opacity-30',
              bunk.status === 'safe' ? 'bg-success' : 'bg-danger'
            )} />

            <div className="flex flex-col sm:flex-row items-center gap-8 relative z-10">
              <div className="shrink-0">
                <CircularProgress pct={bunk.overall_percentage} size={160} />
              </div>
              <div className="flex-1 text-center sm:text-left">
                <div className={cn(
                  'inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wider px-3 py-1 rounded-full mb-4',
                  bunk.status === 'safe'
                    ? 'bg-success/15 text-success border border-success/30'
                    : 'bg-danger/15 text-danger border border-danger/30'
                )}>
                  <TrendingUp size={12} />
                  Bunk Calculator
                </div>

                {bunk.status === 'safe' ? (
                  <>
                    <p className="text-3xl font-bold text-white leading-tight">
                      You can miss{' '}
                      <span className="text-5xl font-black text-success">{bunk.safe_to_bunk}</span>{' '}
                      more class{bunk.safe_to_bunk !== 1 ? 'es' : ''}
                    </p>
                    <p className="text-sm text-gray-400 mt-2">and still stay above the 75% threshold.</p>
                  </>
                ) : (
                  <>
                    <p className="text-3xl font-bold text-white leading-tight">
                      Attend{' '}
                      <span className="text-5xl font-black text-danger">{bunk.must_attend}</span>{' '}
                      consecutive class{bunk.must_attend !== 1 ? 'es' : ''}
                    </p>
                    <p className="text-sm text-gray-400 mt-2">to recover to 75% attendance.</p>
                  </>
                )}

                <div className="mt-5 grid grid-cols-3 gap-3 text-center">
                  {[
                    { label: 'Attended', value: bunk.attended_classes },
                    { label: 'Missed',   value: bunk.total_classes - bunk.attended_classes },
                    { label: 'Total',    value: bunk.total_classes },
                  ].map(stat => (
                    <div key={stat.label} className="bg-white/5 border border-white/8 rounded-xl p-3">
                      <p className="text-2xl font-bold text-white">{stat.value}</p>
                      <p className="text-xs text-gray-500 mt-0.5">{stat.label}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {bunk?.status === 'no_data' && (
          <div className="bg-surface border border-white/10 rounded-2xl p-8 text-center text-gray-500">
            No attendance records yet — check back after your first class.
          </div>
        )}

        {/* Per-course breakdown */}
        {report && report.courses.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-lg font-bold text-white">Course Breakdown</h3>
            {report.courses.map(course => (
              <div
                key={course.course_id}
                className="bg-surface rounded-xl border border-white/10 shadow-lg p-5 hover:border-white/20 hover:-translate-y-0.5 transition-all"
              >
                <div className="flex justify-between items-center mb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
                      <CalendarCheck size={18} />
                    </div>
                    <div>
                      <p className="font-semibold text-white text-sm">{course.course_name}</p>
                      <p className="text-xs text-gray-500">
                        {course.course_code}
                        {course.teacher_name && (
                          <span className="text-warn"> · Prof. {course.teacher_name}</span>
                        )}
                      </p>
                    </div>
                  </div>
                  <span className={cn(
                    'text-lg font-bold',
                    course.attendance_percentage >= 75 ? 'text-success' : 'text-danger'
                  )}>
                    {course.attendance_percentage}%
                  </span>
                </div>

                {/* Progress bar */}
                <div className="w-full bg-white/8 rounded-full h-2 mb-3 overflow-hidden">
                  <div
                    className="h-2 rounded-full transition-all duration-1000"
                    style={{
                      width: `${course.attendance_percentage}%`,
                      background: course.attendance_percentage >= 75
                        ? '#22C55E'
                        : course.attendance_percentage >= 60
                        ? '#F59E0B'
                        : '#EF4444',
                    }}
                  />
                </div>

                <div className="flex justify-between text-xs mt-1">
                  <div className="flex gap-3">
                    <span className="text-success">P: {course.present_count}</span>
                    <span className="text-warn">L: {course.late_count}</span>
                    <span className="text-danger">A: {course.absent_count}</span>
                  </div>
                  <span className="text-gray-500">{course.total_classes} total</span>
                </div>

                {course.attendance_percentage < 75 && course.total_classes > 0 && (
                  <div className="mt-2 text-xs flex items-center gap-1.5 text-danger bg-danger/10 border border-danger/20 px-3 py-1.5 rounded-lg">
                    <AlertCircle size={12} />
                    Below 75% — attendance critical in this course.
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
