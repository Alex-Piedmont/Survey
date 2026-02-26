import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../api/client';
import { TAManagementModal } from '../../components/admin/TAManagementModal';

interface InstructorItem {
  email: string;
  display_name: string | null;
  course_count: number;
  ta_count: number;
}

export function AdminInstructorsPage() {
  const [newEmail, setNewEmail] = useState('');
  const [error, setError] = useState('');
  const [taModalEmail, setTaModalEmail] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: instructors = [], isLoading } = useQuery({
    queryKey: ['admin', 'instructors'],
    queryFn: () => api.get<InstructorItem[]>('/admin/instructors'),
  });

  const addMutation = useMutation({
    mutationFn: (email: string) => api.post('/admin/instructors', { email }),
    onSuccess: () => {
      setNewEmail('');
      setError('');
      queryClient.invalidateQueries({ queryKey: ['admin'] });
    },
    onError: (err: any) => setError(err.message || 'Failed to add instructor'),
  });

  const revokeMutation = useMutation({
    mutationFn: (email: string) => api.delete(`/admin/instructors/${encodeURIComponent(email)}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin'] }),
    onError: (err: any) => setError(err.message || 'Failed to revoke'),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Instructors</h1>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (newEmail.trim()) addMutation.mutate(newEmail.trim().toLowerCase());
        }}
        className="flex gap-2"
      >
        <input
          type="email"
          placeholder="Email address"
          value={newEmail}
          onChange={(e) => setNewEmail(e.target.value)}
          className="border rounded px-3 py-2 text-sm w-80"
        />
        <button
          type="submit"
          disabled={addMutation.isPending}
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700 disabled:opacity-50"
        >
          + Add Instructor
        </button>
      </form>
      {error && <p className="text-sm text-red-600">{error}</p>}

      {isLoading ? (
        <p className="text-gray-500">Loading...</p>
      ) : (
        <div className="bg-white rounded-lg border divide-y">
          {instructors.length === 0 && (
            <p className="p-4 text-gray-500 text-sm">No instructors</p>
          )}
          {instructors.map((inst) => (
            <div key={inst.email} className="p-4 flex items-center justify-between">
              <div>
                <p className="font-medium">
                  {inst.display_name || inst.email}
                </p>
                {inst.display_name && (
                  <p className="text-sm text-gray-500">{inst.email}</p>
                )}
                <p className="text-sm text-gray-500">
                  {inst.course_count} courses · {inst.ta_count} TAs
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setTaModalEmail(inst.email)}
                  className="text-sm text-blue-600 hover:underline"
                >
                  Manage TAs
                </button>
                <button
                  onClick={() => {
                    if (confirm(`Revoke instructor privileges for ${inst.email}?`)) {
                      revokeMutation.mutate(inst.email);
                    }
                  }}
                  className="text-sm text-red-600 hover:underline"
                >
                  Revoke
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {taModalEmail && (
        <TAManagementModal
          instructorEmail={taModalEmail}
          onClose={() => setTaModalEmail(null)}
        />
      )}
    </div>
  );
}
