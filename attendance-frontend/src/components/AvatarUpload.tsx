import { useRef, useState } from 'react';
import { Camera, Loader2 } from 'lucide-react';
import { authFetch } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';

export default function AvatarUpload() {
  const { user, updateUser } = useAuth();
  const { toast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);

  const initials = user?.full_name
    ?.split(' ')
    .map(n => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2) ?? '?';

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await authFetch('/profile/avatar', { method: 'POST', body: formData });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Upload failed.');
      updateUser({ profile_picture_url: data.profile_picture_url });
      toast('Photo updated!', 'success');
    } catch (err: any) {
      toast(err.message || 'Upload failed.', 'error');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const avatarUrl = user?.profile_picture_url
    ? `http://127.0.0.1:8000${user.profile_picture_url}`
    : null;

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="relative group cursor-pointer" onClick={() => fileInputRef.current?.click()}>
        <div className="w-28 h-28 rounded-full overflow-hidden border-2 border-white/15 shadow-xl ring-4 ring-primary/20 transition-all group-hover:ring-primary/40">
          {avatarUrl ? (
            <img src={avatarUrl} alt="Profile" className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full bg-primary/15 text-primary flex items-center justify-center text-3xl font-bold">
              {initials}
            </div>
          )}
        </div>
        <div className="absolute inset-0 rounded-full bg-black/60 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity backdrop-blur-sm">
          {isUploading ? (
            <Loader2 className="text-white animate-spin" size={24} />
          ) : (
            <Camera className="text-white" size={24} />
          )}
        </div>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/gif,image/webp"
        className="hidden"
        onChange={handleFileChange}
      />

      <div className="text-center">
        <p className="text-sm font-semibold text-white">{user?.full_name}</p>
        <p className="text-xs text-gray-500 capitalize mt-0.5">{user?.role}</p>
        <p className="text-xs text-gray-500 mt-0.5">{user?.email}</p>
      </div>

      <button
        onClick={() => fileInputRef.current?.click()}
        disabled={isUploading}
        className="px-4 py-2 text-sm font-semibold rounded-lg bg-white/10 text-gray-300 border border-white/20 hover:bg-white/15 hover:text-white hover:-translate-y-0.5 transition-all disabled:opacity-50 disabled:translate-y-0"
      >
        {isUploading ? 'Uploading...' : 'Change Photo'}
      </button>
    </div>
  );
}
