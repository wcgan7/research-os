import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import ReviewWorkspace from './pages/ReviewWorkspace';
import EmptyState from './components/EmptyState';
import { FileQuestion } from 'lucide-react';

function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <EmptyState icon={FileQuestion} title="Page not found" description="The page you're looking for doesn't exist." />
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/review/:reviewId/*" element={<ReviewWorkspace />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  );
}
