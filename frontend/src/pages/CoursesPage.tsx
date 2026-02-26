import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';

interface Course {
  id: string;
  name: string;
  term: string;
  created_at: string;
}

export function CoursesPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState('');
  const [term, setTerm] = useState('');
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState('');

  const load = () => {
    api.get<Course[]>('/courses')
      .then(setCourses)
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const create = async () => {
    if (!name || !term) return;
    setCreating(true);
    setCreateError('');
    try {
      await api.post('/courses', { name, term });
      setName('');
      setTerm('');
      setShowCreate(false);
      load();
    } catch (err: any) {
      setCreateError(err.message || 'Failed to create course');
    } finally {
      setCreating(false);
    }
  };

  if (loading) return <div className="text-gray-500">Loading...</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Courses</h1>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
        >
          New Course
        </button>
      </div>

      {showCreate && (
        <div className="bg-white rounded-lg border p-4 mb-6">
          <div className="grid grid-cols-2 gap-4 mb-3">
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Course name (e.g. MGMT 481)"
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <input
              value={term}
              onChange={(e) => setTerm(e.target.value)}
              placeholder="Term (e.g. Spring 2026)"
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="flex gap-2">
            <button
              onClick={create}
              disabled={creating || !name || !term}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {creating ? 'Creating...' : 'Create'}
            </button>
            <button
              onClick={() => setShowCreate(false)}
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm hover:bg-gray-50"
            >
              Cancel
            </button>
          </div>
          {createError && <p className="text-sm text-red-600 mt-2">{createError}</p>}
        </div>
      )}

      {courses.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          No courses yet. Create one to get started.
        </div>
      ) : (
        <div className="grid gap-4">
          {courses.map((c) => (
            <Link
              key={c.id}
              to={`/instructor/courses/${c.id}`}
              className="bg-white rounded-lg border p-4 hover:border-blue-300 transition-colors"
            >
              <div className="font-semibold text-gray-900">{c.name}</div>
              <div className="text-sm text-gray-500">{c.term}</div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
