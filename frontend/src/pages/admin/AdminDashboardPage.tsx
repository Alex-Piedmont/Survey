import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api } from '../../api/client';

interface DashboardStats {
  total_users: number;
  total_instructors: number;
  total_admins: number;
  total_courses: number;
  total_active_sessions: number;
  total_submissions: number;
  recent_courses: {
    id: string;
    name: string;
    term: string | null;
    instructor_email: string;
    section_count: number;
    student_count: number;
  }[];
}

export function AdminDashboardPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['admin', 'dashboard'],
    queryFn: () => api.get<DashboardStats>('/admin/dashboard'),
  });

  if (isLoading) return <p className="text-gray-500">Loading...</p>;
  if (error) return <p className="text-red-600">Failed to load dashboard</p>;
  if (!data) return null;

  const stats = [
    { label: 'Users', value: data.total_users },
    { label: 'Instructors', value: data.total_instructors },
    { label: 'Admins', value: data.total_admins },
    { label: 'Courses', value: data.total_courses },
    { label: 'Active Sessions', value: data.total_active_sessions },
    { label: 'Submissions', value: data.total_submissions },
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Admin Dashboard</h1>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {stats.map((s) => (
          <div key={s.label} className="bg-white rounded-lg border p-4">
            <p className="text-sm text-gray-500">{s.label}</p>
            <p className="text-2xl font-bold">{s.value}</p>
          </div>
        ))}
      </div>

      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold">Recent Courses</h2>
          <Link to="/admin/courses" className="text-sm text-blue-600 hover:underline">
            View all
          </Link>
        </div>
        <div className="bg-white rounded-lg border divide-y">
          {data.recent_courses.length === 0 && (
            <p className="p-4 text-gray-500 text-sm">No courses yet</p>
          )}
          {data.recent_courses.map((c) => (
            <div key={c.id} className="p-4 flex items-center justify-between">
              <div>
                <p className="font-medium">{c.name}</p>
                <p className="text-sm text-gray-500">
                  {c.instructor_email} {c.term && `· ${c.term}`}
                </p>
              </div>
              <div className="text-sm text-gray-500">
                {c.section_count} sections · {c.student_count} students
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
