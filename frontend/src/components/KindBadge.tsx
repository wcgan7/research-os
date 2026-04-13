const styles: Record<string, string> = {
  observation: 'bg-blue-50 text-blue-700',
  question: 'bg-purple-50 text-purple-700',
  gap: 'bg-red-50 text-red-700',
  contradiction: 'bg-orange-50 text-orange-700',
  baseline_candidate: 'bg-teal-50 text-teal-700',
  strategy_note: 'bg-gray-100 text-gray-700',
  assumption: 'bg-yellow-50 text-yellow-700',
  next_step: 'bg-green-50 text-green-700',
  tool_wish: 'bg-pink-50 text-pink-700',
};

export default function KindBadge({ kind }: { kind: string }) {
  const cls = styles[kind] || 'bg-gray-100 text-gray-600';
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${cls}`}>
      {kind.replace(/_/g, ' ')}
    </span>
  );
}
