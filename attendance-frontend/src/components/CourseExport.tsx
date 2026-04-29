import { useState, useEffect } from 'react';
import { Calendar, ChevronDown, Download, AlertCircle, FileDown } from 'lucide-react';
import { authFetch } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';

interface Course {
  id: string;
  name: string;
  code: string;
}

export default function CourseExport() {
  const { user } = useAuth();
  const { toast } = useToast();
  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedCourseId, setSelectedCourseId] = useState<string>('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isExporting, setIsExporting] = useState(false);

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
        setLoadError('Could not load courses. Is the backend running?');
      });
  }, [user]);

  const handleExport = async () => {
    if (!selectedCourseId) return;
    setIsExporting(true);

    let url = `/courses/${selectedCourseId}/attendance/export`;
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    if (params.toString()) url += `?${params.toString()}`;

    try {
      const res = await authFetch(url);
      if (!res.ok) throw new Error('Export failed. Check the selected course and date range.');
      const blob = await res.blob();
      const objUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = objUrl;
      a.download = `course_attendance${startDate ? `_${startDate}` : ''}${endDate ? `_to_${endDate}` : ''}.csv`;
      a.click();
      URL.revokeObjectURL(objUrl);
      toast('CSV exported successfully.', 'success');
    } catch (err: any) {
      toast(err.message || 'Export failed.', 'error');
    } finally {
      setIsExporting(false);
    }
  };

  const inputClass = 'w-full bg-white/10 border border-white/20 text-white text-sm rounded-xl focus:ring-2 focus:ring-primary/50 focus:border-primary/50 hover:border-white/30 outline-none p-2.5 transition-all';

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h2 className="text-2xl font-bold text-white">Course Export</h2>
        <p className="text-gray-400 text-sm mt-1">Export attendance for an entire course across any date range.</p>
      </div>

      {loadError && (
        <div className="bg-danger/10 border border-danger/30 text-red-300 px-4 py-3 rounded-xl flex items-center gap-3">
          <AlertCircle size={18} className="shrink-0 text-danger" />
          <p className="text-sm font-medium">{loadError}</p>
        </div>
      )}

      <div className="glass-panel p-6 space-y-5">
        <div>
          <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5">Select Course</label>
          <div className="relative">
            <select
              value={selectedCourseId}
              onChange={e => setSelectedCourseId(e.target.value)}
              className={`${inputClass} appearance-none pr-8`}
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

        <div className="flex gap-4 flex-wrap">
          <div className="flex-1 min-w-[180px]">
            <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5">Start Date (Optional)</label>
            <div className="relative">
              <input
                type="date"
                value={startDate}
                onChange={e => setStartDate(e.target.value)}
                className={`${inputClass} pl-10`}
              />
              <Calendar className="absolute left-3 top-2.5 text-gray-500 pointer-events-none" size={18} />
            </div>
          </div>
          <div className="flex-1 min-w-[180px]">
            <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5">End Date (Optional)</label>
            <div className="relative">
              <input
                type="date"
                value={endDate}
                onChange={e => setEndDate(e.target.value)}
                className={`${inputClass} pl-10`}
              />
              <Calendar className="absolute left-3 top-2.5 text-gray-500 pointer-events-none" size={18} />
            </div>
          </div>
        </div>

        <div className="pt-1">
          <p className="text-xs text-gray-500 mb-3 flex items-center gap-1.5">
            <FileDown size={13} />
            Leave dates blank to export all records for this course.
          </p>
          <button
            onClick={handleExport}
            disabled={!selectedCourseId || isExporting}
            className="w-full px-6 py-3 rounded-xl font-bold text-sm transition-all flex items-center justify-center gap-2 bg-primary text-white hover:bg-indigo-500 hover:-translate-y-0.5 active:translate-y-0 shadow-[0_4px_20px_rgba(99,102,241,0.35)] hover:shadow-[0_4px_30px_rgba(99,102,241,0.5)] disabled:opacity-40 disabled:cursor-not-allowed disabled:translate-y-0"
          >
            <Download size={16} className={isExporting ? 'animate-bounce' : ''} />
            {isExporting ? 'Exporting...' : 'Export CSV'}
          </button>
        </div>
      </div>
    </div>
  );
}
