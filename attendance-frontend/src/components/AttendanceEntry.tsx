import { useState, useEffect } from 'react';
import { Calendar, ChevronDown, Check, X, Clock, AlertCircle } from 'lucide-react';
import { fireConfetti } from '../utils/confetti';
import { cn } from './Sidebar';
import { authFetch } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';

type AttendanceStatus = 'present' | 'absent' | 'late' | null;

interface Course {
  id: string;
  name: string;
  code: string;
}

interface Student {
  student_id: string;
  enrollment_id: string;
  first_name: string;
  last_name: string;
  email: string;
}

export default function AttendanceEntry() {
  const { user } = useAuth();
  const { toast } = useToast();

  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedCourseId, setSelectedCourseId] = useState<string>('');
  const [students, setStudents] = useState<Student[]>([]);
  const [attendance, setAttendance] = useState<Record<string, AttendanceStatus>>({});

  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [search, setSearch] = useState('');

  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const url = user?.role === 'admin' ? '/courses/' : '/teachers/me/courses';
    authFetch(url)
      .then(res => {
        if (!res.ok) throw new Error('Failed to fetch courses');
        return res.json();
      })
      .then((data: Course[]) => {
        setCourses(data);
        if (data.length > 0) setSelectedCourseId(data[0].id);
      })
      .catch(err => {
        console.error(err);
        setError('Could not load your courses. Is the backend running?');
      });
  }, []);

  // When course or date changes, load roster AND pre-fill any existing attendance for that date
  useEffect(() => {
    if (!selectedCourseId) return;

    setIsLoading(true);
    setError(null);
    setAttendance({});

    authFetch(`/courses/${selectedCourseId}/roster`)
      .then(res => {
        if (!res.ok) throw new Error('Failed to fetch roster');
        return res.json();
      })
      .then(async (data) => {
        const studentList: Student[] = data.students || [];
        setStudents(studentList);

        // Pre-fill attendance from existing records for this date
        if (studentList.length > 0) {
          try {
            // Pre-fill attendance from existing records for this date
            // Call the course attendance export filtered by date.
            const exportRes = await authFetch(
              `/courses/${selectedCourseId}/attendance/export?start_date=${date}&end_date=${date}`
            );
            if (exportRes.ok) {
              const csvText = await exportRes.text();
              const lines = csvText.split('\n').slice(1).filter(Boolean); // skip header
              const prefilledMap: Record<string, AttendanceStatus> = {};
              lines.forEach(line => {
                const parts = line.split(',');
                // CSV format: Student Name,Email,Attendance Date,Status,Remarks
                if (parts.length >= 4) {
                  const email = parts[1]?.trim();
                  const statusStr = parts[3]?.trim().toLowerCase() as AttendanceStatus;
                  const student = studentList.find(s => s.email === email);
                  if (student && ['present', 'absent', 'late'].includes(statusStr || '')) {
                    prefilledMap[student.student_id] = statusStr;
                  }
                }
              });
              if (Object.keys(prefilledMap).length > 0) {
                setAttendance(prefilledMap);
              }
            }
          } catch {
            // Pre-fill failed — silently ignore, user can mark manually
          }
        }
      })
      .catch(err => {
        console.error(err);
        setError('Failed to load class roster.');
        setStudents([]);
      })
      .finally(() => setIsLoading(false));
  }, [selectedCourseId, date]);

  const handleStatusChange = (studentId: string, status: AttendanceStatus) => {
    setAttendance(prev => ({ ...prev, [studentId]: status }));
  };

  const markAllPresent = () => {
    const all: Record<string, AttendanceStatus> = {};
    students.forEach(s => { all[s.student_id] = 'present'; });
    setAttendance(all);
  };

  const submitAttendance = async () => {
    if (totalMarked !== students.length) return;

    setIsSubmitting(true);
    setError(null);

    const payload = {
      course_id: selectedCourseId,
      attendance_date: date,
      records: students.map(s => ({
        student_id: s.student_id,
        status: attendance[s.student_id],
      })),
    };

    try {
      const res = await authFetch('/attendance/bulk', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        // FastAPI validation errors return detail as an array of objects
        let errorMsg = 'Failed to submit attendance.';
        if (typeof data.detail === 'string') {
          errorMsg = data.detail;
        } else if (Array.isArray(data.detail) && data.detail.length > 0) {
          errorMsg = data.detail.map((e: any) => e.msg || JSON.stringify(e)).join('; ');
        } else if (data.message) {
          errorMsg = data.message;
        }
        throw new Error(errorMsg);
      }
      
      fireConfetti(100);
      
      toast(`Submitted! Created: ${data.records_created}, Updated: ${data.records_updated}`, 'success');
    } catch (err: any) {
      console.error(err);
      toast(err.message || 'An error occurred during submission.', 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const filteredStudents = students.filter(s =>
    !search || s.student_id === search
  );

  const totalMarked = Object.keys(attendance).length;
  const isComplete = students.length > 0 && totalMarked === students.length;

  // Weekend check — parse the date string directly to avoid timezone shifts
  const [yyyy, mm, dd] = date.split('-').map(Number);
  const selectedDay = new Date(yyyy, mm - 1, dd).getDay(); // 0=Sun, 6=Sat
  const isWeekend = selectedDay === 0 || selectedDay === 6;
  const weekendName = selectedDay === 6 ? 'Saturday' : 'Sunday';

  const inputClass = 'w-full bg-white/10 border border-white/20 text-white placeholder-gray-400 text-sm rounded-xl focus:ring-2 focus:ring-primary/50 focus:border-primary/50 hover:border-white/30 outline-none p-2.5 transition-all';

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      {/* Header */}
      <div className="mb-6 space-y-4">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-2xl font-bold text-white">Mark Attendance</h2>
            <p className="text-gray-400 text-sm mt-1">Record daily attendance for your class.</p>
          </div>
          {students.length > 0 && (
            <button
              onClick={markAllPresent}
              className="px-3 py-1.5 text-xs font-bold rounded-lg bg-success/15 text-success border border-success/30 hover:bg-success/25 hover:-translate-y-0.5 transition-all"
            >
              Mark All Present
            </button>
          )}
        </div>

        {isWeekend && (
          <div className="bg-warn/10 border border-warn/30 text-yellow-300 px-4 py-3 rounded-xl flex items-center gap-3">
            <AlertCircle size={18} className="shrink-0 text-warn" />
            <p className="text-sm font-medium">
              🎉 It's <span className="font-bold">{weekendName}</span> — no classes today! Attendance cannot be marked on weekends.
            </p>
          </div>
        )}

        {!isWeekend && error && (
          <div className="bg-danger/10 border border-danger/30 text-red-300 px-4 py-3 rounded-xl flex items-center gap-3">
            <AlertCircle size={18} className="shrink-0 text-danger" />
            <p className="text-sm font-medium">{error}</p>
          </div>
        )}

        <div className="flex flex-wrap gap-4 glass-panel p-4">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5">Course</label>
            <div className="relative">
              <select
                value={selectedCourseId}
                onChange={e => setSelectedCourseId(e.target.value)}
                className={cn(inputClass, 'appearance-none pr-8')}
              >
                {courses.length === 0 && <option disabled value="">No courses available</option>}
                {courses.map(course => (
                  <option key={course.id} value={course.id} className="bg-surface-dark text-white">
                    {course.code} — {course.name}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-2.5 top-3 text-gray-500 pointer-events-none" size={16} />
            </div>
          </div>

          <div className="flex-1 min-w-[200px]">
            <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5">Date</label>
            <div className="relative">
              <input
                type="date"
                value={date}
                onChange={e => setDate(e.target.value)}
                className={cn(inputClass, 'pl-10')}
              />
              <Calendar className="absolute left-3 top-2.5 text-gray-500 pointer-events-none" size={18} />
            </div>
          </div>

          <div className="flex-1 min-w-[200px]">
            <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5">Search Student</label>
            <div className="relative">
              <select
                value={search}
                onChange={e => setSearch(e.target.value)}
                className={cn(inputClass, 'appearance-none pr-8')}
              >
                <option value="">All Students</option>
                {students.map(s => (
                  <option key={s.student_id} value={s.student_id} className="bg-surface-dark text-white">
                    {s.first_name} {s.last_name}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-2.5 top-3 text-gray-500 pointer-events-none" size={16} />
            </div>
          </div>
        </div>
      </div>

      {/* Student list */}
      <div className="flex-1 overflow-x-auto overflow-y-auto glass-panel mb-24 relative">
        {isLoading && (
          <div className="absolute inset-0 bg-surface-dark/60 backdrop-blur-sm flex items-center justify-center z-20">
            <p className="text-gray-400 font-medium text-sm">Loading roster...</p>
          </div>
        )}

        <table className="w-full text-sm text-left">
          <thead className="text-xs text-gray-500 uppercase bg-white/5 sticky top-0 z-10 border-b border-white/10">
            <tr>
              <th className="px-6 py-4 font-semibold">Student</th>
              <th className="px-6 py-4 font-semibold text-right">Status</th>
            </tr>
          </thead>
          <tbody>
            {filteredStudents.map(student => {
              const status = attendance[student.student_id];
              return (
                <tr key={student.student_id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                  <td className="px-6 py-4 flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-primary/15 border border-primary/25 text-primary flex items-center justify-center font-bold text-xs shrink-0">
                      {student.first_name.charAt(0)}
                    </div>
                    <div>
                      <span className="font-medium text-white block">{student.first_name} {student.last_name}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex justify-end gap-1.5">
                      {(['present', 'absent', 'late'] as const).map(s => (
                        <button
                          key={s}
                          onClick={() => handleStatusChange(student.student_id, s)}
                          className={cn(
                            'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all capitalize',
                            status === s
                              ? s === 'present'
                                ? 'bg-success/20 text-success border border-success/40 shadow-sm'
                                : s === 'absent'
                                ? 'bg-danger/20 text-danger border border-danger/40 shadow-sm'
                                : 'bg-warn/20 text-warn border border-warn/40 shadow-sm'
                              : 'bg-white/5 text-gray-500 hover:bg-white/10 hover:text-gray-300 border border-white/10'
                          )}
                        >
                          {s === 'present' ? <Check size={13} /> : s === 'absent' ? <X size={13} /> : <Clock size={13} />}
                          {s.charAt(0).toUpperCase() + s.slice(1)}
                        </button>
                      ))}
                    </div>
                  </td>
                </tr>
              );
            })}

            {!isLoading && filteredStudents.length === 0 && (
              <tr>
                <td colSpan={2} className="px-6 py-12 text-center text-gray-500">
                  {students.length === 0 ? 'No students enrolled in this course.' : 'No students match your search.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Sticky bottom submit bar */}
      <div className="fixed bottom-0 right-0 left-0 md:left-64 p-4 md:p-6 bg-surface-dark border-t border-white/8 shadow-2xl flex items-center justify-between z-20">
        <div>
          <p className="text-sm font-medium text-gray-300">
            <span className={cn('font-bold', isComplete ? 'text-success' : 'text-primary')}>
              {totalMarked} / {students.length}
            </span>{' '}
            students marked
          </p>
          {!isComplete && students.length > 0 && (
            <p className="text-xs text-gray-500 mt-0.5">Mark all students before submitting.</p>
          )}
        </div>

        <button
          disabled={!isComplete || isSubmitting || isWeekend}
          onClick={submitAttendance}
          className={cn(
            'px-6 py-2.5 rounded-xl font-semibold text-sm transition-all flex items-center gap-2',
            isComplete && !isSubmitting
              ? 'bg-primary text-white hover:bg-indigo-500 hover:-translate-y-0.5 active:translate-y-0 shadow-[0_4px_15px_rgba(99,102,241,0.35)] hover:shadow-[0_4px_20px_rgba(99,102,241,0.5)] cursor-pointer'
              : 'bg-white/8 text-gray-600 cursor-not-allowed border border-white/10'
          )}
        >
          {isSubmitting ? 'Submitting...' : 'Submit Attendance'}
        </button>
      </div>
    </div>
  );
}
