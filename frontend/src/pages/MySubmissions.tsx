import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';

interface Submission {
  id: string;
  session_id: string;
  target_team_id: string | null;
  target_student_email: string | null;
  feedback_type: string;
  responses: Record<string, any>;
  version: number;
  submitted_at: string;
  is_late: boolean;
  penalty_pct: number;
}

export function MySubmissions() {
  const { email } = useAuth();
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<Submission[]>('/me/submissions')
      .then(setSubmissions)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b px-4 py-4">
        <div className="max-w-2xl mx-auto">
          <h1 className="text-xl font-bold text-gray-900">My Submissions</h1>
          <p className="text-sm text-gray-500">{email}</p>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 py-6">
        {submissions.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            No submissions yet.
          </div>
        ) : (
          <div className="space-y-3">
            {submissions.map((sub) => (
              <div
                key={sub.id}
                className="bg-white rounded-lg border p-4 flex items-center justify-between"
              >
                <div>
                  <div className="font-medium text-gray-900">
                    {sub.feedback_type === 'audience'
                      ? `Audience → ${sub.target_team_id?.slice(0, 8)}...`
                      : `Peer → ${sub.target_student_email}`}
                  </div>
                  <div className="text-sm text-gray-500">
                    v{sub.version} &middot;{' '}
                    {new Date(sub.submitted_at).toLocaleString()}
                    {sub.is_late && (
                      <span className="ml-2 text-orange-600 font-medium">
                        Late ({sub.penalty_pct}% penalty)
                      </span>
                    )}
                  </div>
                </div>
                <Link
                  to={`/s/${sub.session_id}`}
                  className="text-blue-600 text-sm font-medium hover:underline"
                >
                  Edit
                </Link>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
