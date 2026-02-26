import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api } from '../../api/client';

interface AdminCourseItem {
  id: string;
  name: string;
  term: string | null;
  instructor_email: string;
  section_count: number;
  student_count: number;
}

export function AdminCoursesPage() {
  const [page, setPage] = useState(1);

  const { data: courses = [], isLoading } = useQuery({
    queryKey: ['admin', 'courses', page],
    queryFn: () => api.get<AdminCourseItem[]>(`/admin/courses?page=${page}&per_page=50`),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">All Courses</h1>

      {isLoading ? (
        <p className="text-gray-500">Loading...</p>
      ) : (
        <>
          <div className="bg-white rounded-lg border divide-y">
            {courses.length === 0 && (
              <p className="p-4 text-gray-500 text-sm">No courses</p>
            )}
            {courses.map((c) => (
              <div key={c.id} className="p-4 flex items-center justify-between">
                <div>
                  <Link
                    to={`/instructor/courses/${c.id}`}
                    className="font-medium text-blue-600 hover:underline"
                  >
                    {c.name}
                  </Link>
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

          <div className="flex gap-2 justify-center">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1 text-sm border rounded disabled:opacity-50"
            >
              Previous
            </button>
            <span className="px-3 py-1 text-sm">Page {page}</span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={courses.length < 50}
              className="px-3 py-1 text-sm border rounded disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}
