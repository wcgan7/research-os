import { AlertTriangle } from 'lucide-react';

export default function ErrorMessage({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700" role="alert">
      <AlertTriangle size={16} className="shrink-0" />
      <span>{message}</span>
    </div>
  );
}
