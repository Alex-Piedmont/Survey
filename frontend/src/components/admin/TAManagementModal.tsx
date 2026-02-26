import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../api/client';

interface TAItem {
  ta_email: string;
  display_name: string | null;
  created_at: string;
  created_by: string;
}

interface Props {
  instructorEmail: string;
  onClose: () => void;
}

export function TAManagementModal({ instructorEmail, onClose }: Props) {
  const [taEmail, setTaEmail] = useState('');
  const [error, setError] = useState('');
  const queryClient = useQueryClient();

  const { data: tas = [], isLoading } = useQuery({
    queryKey: ['admin', 'instructors', instructorEmail, 'tas'],
    queryFn: () => api.get<TAItem[]>(`/admin/instructors/${encodeURIComponent(instructorEmail)}/tas`),
  });

  const addMutation = useMutation({
    mutationFn: (email: string) =>
      api.post(`/admin/instructors/${encodeURIComponent(instructorEmail)}/tas`, { ta_email: email }),
    onSuccess: () => {
      setTaEmail('');
      setError('');
      queryClient.invalidateQueries({ queryKey: ['admin', 'instructors', instructorEmail, 'tas'] });
      queryClient.invalidateQueries({ queryKey: ['admin', 'instructors'] });
    },
    onError: (err: any) => setError(err.message || 'Failed to add TA'),
  });

  const removeMutation = useMutation({
    mutationFn: (email: string) =>
      api.delete(`/admin/instructors/${encodeURIComponent(instructorEmail)}/tas/${encodeURIComponent(email)}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'instructors', instructorEmail, 'tas'] });
      queryClient.invalidateQueries({ queryKey: ['admin', 'instructors'] });
    },
  });

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-lg w-full max-w-md mx-4">
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="font-semibold">TAs for {instructorEmail}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">
            &times;
          </button>
        </div>
        <div className="p-4 space-y-4">
          {isLoading ? (
            <p className="text-sm text-gray-500">Loading...</p>
          ) : tas.length === 0 ? (
            <p className="text-sm text-gray-500">No TAs assigned</p>
          ) : (
            <ul className="divide-y">
              {tas.map((ta) => (
                <li key={ta.ta_email} className="py-2 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">{ta.ta_email}</p>
                    {ta.display_name && (
                      <p className="text-xs text-gray-500">{ta.display_name}</p>
                    )}
                  </div>
                  <button
                    onClick={() => {
                      if (confirm(`Remove ${ta.ta_email} as TA?`)) {
                        removeMutation.mutate(ta.ta_email);
                      }
                    }}
                    className="text-xs text-red-600 hover:underline"
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          )}

          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (taEmail.trim()) addMutation.mutate(taEmail.trim().toLowerCase());
            }}
            className="flex gap-2"
          >
            <input
              type="email"
              placeholder="TA email"
              value={taEmail}
              onChange={(e) => setTaEmail(e.target.value)}
              className="flex-1 border rounded px-3 py-1.5 text-sm"
            />
            <button
              type="submit"
              disabled={addMutation.isPending}
              className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              Add
            </button>
          </form>
          {error && <p className="text-sm text-red-600">{error}</p>}
        </div>
      </div>
    </div>
  );
}
