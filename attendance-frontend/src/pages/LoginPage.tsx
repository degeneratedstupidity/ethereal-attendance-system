import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertCircle, Loader2, GraduationCap } from 'lucide-react';
import { fireConfetti } from '../utils/confetti';
import { useAuth } from '../context/AuthContext';

export default function LoginPage() {
  const navigate = useNavigate();
  const { login, isAuthenticated, user } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  if (isAuthenticated && user) {
    if (user.role === 'student') navigate('/student', { replace: true });
    else navigate('/teacher', { replace: true });
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Please enter your email and password.');
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      await login(email, password);
      
      fireConfetti(150);
      
      const stored = localStorage.getItem('user');
      const u = stored ? JSON.parse(stored) : null;
      if (u?.role === 'student') navigate('/student', { replace: true });
      else navigate('/teacher', { replace: true });
    } catch (err: any) {
      setError(err.message || 'Login failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="aurora-bg min-h-screen flex items-center justify-center relative overflow-hidden p-4">

      {/* Animated floating orbs */}
      <div className="absolute top-[-15%] left-[-10%] w-[700px] h-[700px] rounded-full bg-primary/25 blur-[130px] animate-float-1 pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[600px] h-[600px] rounded-full bg-accent/20 blur-[110px] animate-float-2 pointer-events-none" />
      <div className="absolute top-[35%] left-[55%] w-[450px] h-[450px] rounded-full bg-info/15 blur-[100px] animate-float-3 pointer-events-none" />
      <div
        className="absolute top-[5%] right-[15%] w-[350px] h-[350px] rounded-full bg-danger/10 blur-[90px] animate-float-1 pointer-events-none"
        style={{ animationDelay: '6s' }}
      />
      <div
        className="absolute bottom-[15%] left-[25%] w-[300px] h-[300px] rounded-full bg-success/10 blur-[80px] animate-float-2 pointer-events-none"
        style={{ animationDelay: '10s' }}
      />

      {/* Subtle grid overlay */}
      <div
        className="absolute inset-0 pointer-events-none opacity-[0.025]"
        style={{
          backgroundImage: 'linear-gradient(white 1px, transparent 1px), linear-gradient(90deg, white 1px, transparent 1px)',
          backgroundSize: '60px 60px',
        }}
      />

      <div className="relative w-full max-w-md animate-fade-slide-up">
        {/* Card */}
        <div className="bg-surface/80 backdrop-blur-2xl border border-white/15 rounded-2xl shadow-[0_25px_80px_rgba(0,0,0,0.6)] p-8">

          {/* Logo */}
          <div className="flex flex-col items-center mb-8">
            <div className="w-16 h-16 rounded-2xl bg-primary/20 border border-primary/40 flex items-center justify-center shadow-[0_0_30px_rgba(99,102,241,0.35)] mb-4 animate-pulse-glow">
              <GraduationCap className="text-primary animate-bounce-icon" size={30} strokeWidth={2} />
            </div>
            <h1 className="text-2xl font-bold text-white tracking-tight text-center">
              Ethereal Paranatellon University
            </h1>
            <p className="text-sm text-white/50 mt-1.5">Sign in to your account</p>
          </div>

          {/* Error */}
          {error && (
            <div className="mb-5 flex items-center gap-2.5 bg-danger/15 border border-danger/30 text-red-300 px-4 py-3 rounded-xl text-sm">
              <AlertCircle size={16} className="shrink-0 text-danger" />
              <span>{error}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-white/60 uppercase tracking-wider mb-1.5">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@college.edu"
                autoComplete="email"
                className="w-full bg-white/10 border border-white/20 text-white placeholder-gray-400 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/50 hover:border-white/30 transition-all"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-white/60 uppercase tracking-wider mb-1.5">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete="current-password"
                className="w-full bg-white/10 border border-white/20 text-white placeholder-gray-400 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/50 hover:border-white/30 transition-all"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full mt-2 py-3 px-4 bg-primary hover:bg-indigo-500 text-white font-semibold rounded-xl text-sm transition-all shadow-[0_4px_20px_rgba(99,102,241,0.4)] hover:shadow-[0_4px_30px_rgba(99,102,241,0.6)] hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-60 disabled:cursor-not-allowed disabled:translate-y-0 flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Signing in...
                </>
              ) : (
                'Sign In'
              )}
            </button>
          </form>

          <p className="text-center text-xs text-white/25 mt-6">
            Contact your administrator if you need access.
          </p>
        </div>
      </div>
    </div>
  );
}
