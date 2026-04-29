import { useState, useEffect } from 'react';
import { User, CalendarCheck, AlertCircle, ChevronDown, Loader2 } from 'lucide-react';
import { cn } from './Sidebar';
import { authFetch } from '../api/client';
import { useAuth } from '../context/AuthContext';

interface Course {
  id: string;
  name: string;
  code: string;
}

interface Student {
  student_id: string;
  first_name: string;
  last_name: string;
  email: string;
}

interface CourseAttendanceSummary {
  course_id: string;
  course_name: string;
  course_code: string;
  total_classes: number;
  present_count: number;
  absent_count: number;
  late_count: number;
  attendance_percentage: number;
}

interface StudentAttendanceReport {
  student_id: string;
  student_name: string;
  courses: CourseAttendanceSummary[];
  overall_percentage: number;
}

export default function StudentReport() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedCourseId, setSelectedCourseId] = useState<string>('');
  const [students, setStudents] = useState<Student[]>([]);
  const [selectedStudentId, setSelectedStudentId] = useState<string>('');
  const [report, setReport] = useState<StudentAttendanceReport | null>(null);
  const [isLoadingReport, setIsLoadingReport] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { user } = useAuth();

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
        setError('Could not load courses.');
      });
  }, []);

  useEffect(() => {
    if (!selectedCourseId) return;
    setStudents([]);
    setSelectedStudentId('');
    setReport(null);
    setError(null);
    authFetch(`/courses/${selectedCourseId}/roster`)
      .then(res => {
        if (!res.ok) throw new Error('Failed to fetch roster');
        return res.json();
      })
      .then(data => {
        const roster = data.students || [];
        setStudents(roster);
        if (roster.length > 0) setSelectedStudentId(roster[0].student_id);
      })
      .catch(err => {
        console.error(err);
        setError('Failed to load class roster.');
      });
  }, [selectedCourseId]);

  useEffect(() => {
    if (!selectedStudentId) { setReport(null); return; }
    setIsLoadingReport(true);
    setError(null);
    authFetch(`/students/${selectedStudentId}/attendance`)
      .then(res => {
        if (!res.ok) throw new Error('Failed to fetch attendance report');
        return res.json();
      })
      .then(data => setReport(data))
      .catch(err => {
        console.error(err);
        setError('Failed to load student report.');
      })
      .finally(() => setIsLoadingReport(false));
  }, [selectedStudentId]);

  const studentDetails = students.find(s => s.student_id === selectedStudentId);

  const handleExport = async () => {
    if (!selectedStudentId) return;
    const res = await authFetch(`/students/${selectedStudentId}/attendance/export`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `attendance_${selectedStudentId}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const selectClass = 'w-full appearance-none bg-white/10 border border-white/20 text-white text-sm rounded-xl focus:ring-2 focus:ring-primary/50 focus:border-primary/50 hover:border-white/30 outline-none p-2.5 pr-8 transition-all disabled:opacity-40';

  return (
    <div className="space-y-6 pb-12">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Student Report</h2>
          <p className="text-gray-400 text-sm mt-1">Detailed attendance breakdown for individual students.</p>
        </div>
        {report && (
          <button
            onClick={handleExport}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-white/8 text-gray-300 border border-white/10 hover:bg-white/15 hover:text-white transition-all"
          >
            Export CSV
          </button>
        )}
      </div>

      {error && (
        <div className="bg-danger/10 border border-danger/30 text-red-300 px-4 py-3 rounded-xl flex items-center gap-3">
          <AlertCircle size={18} className="shrink-0 text-danger" />
          <p className="text-sm font-medium">{error}</p>
        </div>
      )}

      {/* Selectors */}
      <div className="flex flex-wrap gap-4 glass-panel p-4">
        <div className="flex-1 min-w-[200px]">
          <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5">Select Course</label>
          <div className="relative">
            <select
              value={selectedCourseId}
              onChange={e => setSelectedCourseId(e.target.value)}
              className={selectClass}
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
          <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5">Select Student</label>
          <div className="relative">
            <select
              value={selectedStudentId}
              onChange={e => setSelectedStudentId(e.target.value)}
              disabled={students.length === 0}
              className={selectClass}
            >
              {students.length === 0 && <option disabled value="">No students in course</option>}
              {students.map(student => (
                <option key={student.student_id} value={student.student_id} className="bg-surface-dark text-white">
                  {student.first_name} {student.last_name}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-2.5 top-3 text-gray-500 pointer-events-none" size={16} />
          </div>
        </div>
      </div>

      {isLoadingReport && (
        <div className="h-64 flex flex-col items-center justify-center text-primary">
          <Loader2 className="animate-spin mb-4" size={32} />
          <p className="text-sm font-medium text-gray-400">Generating report...</p>
        </div>
      )}

      {!isLoadingReport && report && studentDetails && (
        <div className="space-y-6">
          {/* Student header card */}
          <div className="glass-panel p-6 flex items-start gap-6 relative overflow-hidden">
            <div className="absolute -right-10 -top-10 w-40 h-40 bg-primary/5 rounded-full blur-3xl pointer-events-none" />
            <div className="w-20 h-20 rounded-2xl bg-primary/15 border border-primary/25 text-primary flex items-center justify-center shrink-0 z-10">
              <User size={36} strokeWidth={2} />
            </div>
            <div className="flex-1 z-10">
              <div className="flex justify-between items-start gap-4">
                <div>
                  <h3 className="text-xl font-bold text-white">{report.student_name}</h3>
                  <p className="text-primary font-medium text-sm mt-0.5">Enrolled Student</p>
                </div>
                <div className={cn(
                  'px-3 py-1.5 rounded-full text-xs font-bold border shrink-0',
                  report.overall_percentage >= 75
                    ? 'bg-success/15 text-success border-success/30'
                    : 'bg-danger/15 text-danger border-danger/30'
                )}>
                  {report.overall_percentage >= 75 ? 'Good Standing' : 'Needs Attention'}
                </div>
              </div>
              <span className="text-sm text-gray-500 mt-2 block">{studentDetails.email}</span>
            </div>
          </div>

          {/* Quick stats */}
          {(() => {
            const overallTotal = report.courses.reduce((acc, c) => acc + c.total_classes, 0);
            const overallPresent = report.courses.reduce((acc, c) => acc + c.present_count + c.late_count, 0);
            return (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {[
                  { label: 'Total Classes', value: overallTotal, unit: 'sessions', accent: 'border-primary' },
                  { label: 'Attended',      value: overallPresent, unit: 'sessions', accent: 'border-success' },
                  { label: 'Overall',       value: `${report.overall_percentage}%`, unit: null, accent: report.overall_percentage >= 75 ? 'border-success' : 'border-danger' },
                ].map(stat => (
                  <div key={stat.label} className={cn('glass-panel p-5 border-l-4', stat.accent)}>
                    <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">{stat.label}</p>
                    <div className="flex items-end gap-2">
                      <h4 className="text-3xl font-bold text-white">{stat.value}</h4>
                      {stat.unit && <span className="text-sm text-gray-500 mb-1">{stat.unit}</span>}
                    </div>
                  </div>
                ))}
              </div>
            );
          })()}

          {/* Per-course breakdown */}
          <h3 className="text-lg font-bold text-white">Course Breakdown</h3>
          <div className="grid grid-cols-1 gap-4">
            {report.courses.map(course => (
              <div key={course.course_id} className="glass-panel p-5 hover:border-white/20 transition-all">
                <div className="flex justify-between items-center mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center text-gray-400">
                      <CalendarCheck size={20} />
                    </div>
                    <div>
                      <h4 className="font-bold text-white">{course.course_name}</h4>
                      <p className="text-xs text-gray-500">{course.course_code}</p>
                    </div>
                  </div>
                  <span className={cn(
                    'text-xl font-bold',
                    course.attendance_percentage >= 75 ? 'text-success' : 'text-danger'
                  )}>
                    {course.attendance_percentage}%
                  </span>
                </div>

                <div className="w-full bg-white/8 rounded-full h-2.5 mb-3 overflow-hidden">
                  <div
                    className="h-2.5 rounded-full transition-all duration-1000"
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

                <div className="flex justify-between text-xs font-semibold">
                  <div className="flex gap-2">
                    <span className="text-success bg-success/10 px-2 py-0.5 rounded border border-success/20">Present: {course.present_count}</span>
                    <span className="text-warn bg-warn/10 px-2 py-0.5 rounded border border-warn/20">Late: {course.late_count}</span>
                    <span className="text-danger bg-danger/10 px-2 py-0.5 rounded border border-danger/20">Absent: {course.absent_count}</span>
                  </div>
                  <span className="text-gray-500">Total: {course.total_classes}</span>
                </div>

                {course.attendance_percentage < 75 && course.total_classes > 0 && (
                  <div className="mt-3 text-xs flex items-center gap-1.5 text-danger bg-danger/10 border border-danger/20 px-3 py-2 rounded-lg">
                    <AlertCircle size={14} />
                    Below the required 75% threshold.
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {!isLoadingReport && !report && students.length === 0 && selectedCourseId && (
        <div className="glass-panel p-12 text-center text-gray-500">No students found in this course.</div>
      )}
    </div>
  );
}
