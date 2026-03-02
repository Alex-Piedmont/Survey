import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../api/client';
import { TAManagementModal } from '../../components/admin/TAManagementModal';

interface SectionItem {
  id: string;
  name: string;
  student_count: number;
}

interface CourseItem {
  id: string;
  name: string;
  term: string | null;
  section_count: number;
  student_count: number;
  sections: SectionItem[];
}

interface InstructorDetail {
  email: string;
  display_name: string | null;
  is_instructor: boolean;
  is_admin: boolean;
  course_count: number;
  ta_count: number;
  courses: CourseItem[];
}

export function AdminInstructorDetailPage() {
  const { email: rawEmail } = useParams<{ email: string }>();
  const email = decodeURIComponent(rawEmail || '');
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [taModalOpen, setTaModalOpen] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ['admin', 'instructors', email, 'detail'],
    queryFn: () =>
      api.get<InstructorDetail>(
        `/admin/instructors/${encodeURIComponent(email)}/courses`
      ),
    enabled: !!email,
  });

  const revokeMutation = useMutation({
    mutationFn: () =>
      api.delete(`/admin/instructors/${encodeURIComponent(email)}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin'] });
      navigate('/admin/instructors');
    },
  });

  if (isLoading) return <p className="text-gray-500">Loading...</p>;
  if (error)
    return <p className="text-red-600">Failed to load instructor detail.</p>;
  if (!data) return null;

  return (
    <div className="space-y-6">
      <Link
        to="/admin/instructors"
        className="text-sm text-blue-600 hover:underline"
      >
        &larr; Back to Instructors
      </Link>

      {/* Profile header */}
      <div className="bg-white rounded-lg border p-6">
        <h1 className="text-2xl font-bold">
          {data.display_name || data.email}
        </h1>
        {data.display_name && (
          <p className="text-gray-500">{data.email}</p>
        )}
        <p className="text-sm text-gray-500 mt-1">
          {data.course_count} courses · {data.ta_count} TAs
        </p>

        {!data.is_instructor && (
          <div className="mt-3 bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-2 rounded text-sm">
            This user no longer has instructor privileges.
          </div>
        )}

        <div className="mt-4 flex gap-2">
          <button
            onClick={() => setTaModalOpen(true)}
            className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700"
          >
            Manage TAs
          </button>
          <button
            onClick={() => {
              if (
                confirm(
                  `Revoke instructor privileges for ${data.email}?`
                )
              ) {
                revokeMutation.mutate();
              }
            }}
            className="bg-red-600 text-white px-4 py-2 rounded text-sm hover:bg-red-700"
          >
            Revoke
          </button>
        </div>
      </div>

      {/* Courses */}
      <div>
        <h2 className="text-lg font-semibold mb-3">Courses</h2>
        {data.courses.length === 0 ? (
          <p className="text-gray-500 text-sm">No courses created.</p>
        ) : (
          <div className="space-y-4">
            {data.courses.map((course) => (
              <div
                key={course.id}
                className="bg-white rounded-lg border p-4"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">{course.name}</p>
                    {course.term && (
                      <p className="text-sm text-gray-500">
                        {course.term}
                      </p>
                    )}
                  </div>
                  <p className="text-sm text-gray-500">
                    {course.section_count} sections ·{' '}
                    {course.student_count} students
                  </p>
                </div>
                {course.sections.length > 0 && (
                  <ul className="mt-3 divide-y border-t">
                    {course.sections.map((section) => (
                      <li
                        key={section.id}
                        className="py-2 flex items-center justify-between text-sm"
                      >
                        <span>{section.name}</span>
                        <span className="text-gray-500">
                          {section.student_count} students
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {taModalOpen && (
        <TAManagementModal
          instructorEmail={email}
          onClose={() => setTaModalOpen(false)}
        />
      )}
    </div>
  );
}
