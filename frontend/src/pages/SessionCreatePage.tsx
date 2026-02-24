import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { api } from '../api/client';

interface PresentationType { id: string; name: string }
interface Team { id: string; name: string; members: string[] }

export function SessionCreatePage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const sectionId = searchParams.get('section') || '';
  const courseId = searchParams.get('course') || '';

  const [ptypes, setPtypes] = useState<PresentationType[]>([]);
  const [selectedPtype, setSelectedPtype] = useState('');
  const [teams, setTeams] = useState<Team[]>([]);
  const [selectedTeams, setSelectedTeams] = useState<Set<string>>(new Set());
  const [sessionDate, setSessionDate] = useState(new Date().toISOString().split('T')[0]);
  const [creating, setCreating] = useState(false);

  // Team creation
  const [newTeamName, setNewTeamName] = useState('');
  const [newTeamMembers, setNewTeamMembers] = useState('');
  const [creatingTeam, setCreatingTeam] = useState(false);

  useEffect(() => {
    if (!courseId) return;
    api.get<PresentationType[]>(`/courses/${courseId}/presentation-types`).then(setPtypes).catch(() => {});
  }, [courseId]);

  useEffect(() => {
    if (!sectionId || !selectedPtype) { setTeams([]); return; }
    api.get<Team[]>(`/sections/${sectionId}/teams?presentation_type_id=${selectedPtype}`).then(setTeams).catch(() => {});
  }, [sectionId, selectedPtype]);

  const toggleTeam = (id: string) => {
    const next = new Set(selectedTeams);
    if (next.has(id)) next.delete(id); else next.add(id);
    setSelectedTeams(next);
  };

  const createTeam = async () => {
    if (!newTeamName || !sectionId || !selectedPtype) return;
    setCreatingTeam(true);
    try {
      const emails = newTeamMembers.split('\n').map(e => e.trim()).filter(Boolean);
      const team = await api.post<Team>(`/sections/${sectionId}/teams`, {
        name: newTeamName,
        presentation_type_id: selectedPtype,
        member_emails: emails,
      });
      setTeams([...teams, team]);
      setNewTeamName('');
      setNewTeamMembers('');
    } finally {
      setCreatingTeam(false);
    }
  };

  const createSession = async () => {
    if (!sectionId || !selectedPtype || selectedTeams.size === 0) return;
    setCreating(true);
    try {
      const session = await api.post<{ id: string }>('/sessions', {
        section_id: sectionId,
        presentation_type_id: selectedPtype,
        presenting_team_ids: Array.from(selectedTeams),
        session_date: sessionDate,
      });
      navigate(`/instructor/sessions/${session.id}/dashboard`);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div>
      <Link to={`/instructor/courses/${courseId}`} className="text-sm text-blue-600 hover:underline mb-4 inline-block">
        &larr; Back to course
      </Link>
      <h1 className="text-xl font-bold text-gray-900 mb-6">New Session</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4">
          {/* Presentation Type */}
          <div>
            <label className="text-sm font-medium text-gray-700 mb-1 block">Presentation Type</label>
            <select
              value={selectedPtype}
              onChange={(e) => { setSelectedPtype(e.target.value); setSelectedTeams(new Set()); }}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select...</option>
              {ptypes.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>

          {/* Date */}
          <div>
            <label className="text-sm font-medium text-gray-700 mb-1 block">Session Date</label>
            <input
              type="date"
              value={sessionDate}
              onChange={(e) => setSessionDate(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Teams selection */}
          {selectedPtype && (
            <div>
              <label className="text-sm font-medium text-gray-700 mb-2 block">
                Presenting Teams ({selectedTeams.size} selected)
              </label>
              <div className="bg-white rounded-lg border divide-y max-h-64 overflow-y-auto">
                {teams.map((t) => (
                  <label key={t.id} className="flex items-center gap-3 px-4 py-3 hover:bg-gray-50 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedTeams.has(t.id)}
                      onChange={() => toggleTeam(t.id)}
                      className="rounded"
                    />
                    <div>
                      <div className="text-sm font-medium text-gray-900">{t.name}</div>
                      <div className="text-xs text-gray-500">{t.members.join(', ')}</div>
                    </div>
                  </label>
                ))}
                {teams.length === 0 && (
                  <div className="px-4 py-3 text-sm text-gray-400">No teams for this presentation type yet.</div>
                )}
              </div>
            </div>
          )}

          <button
            onClick={createSession}
            disabled={creating || !selectedPtype || selectedTeams.size === 0}
            className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {creating ? 'Creating...' : 'Create Session'}
          </button>
        </div>

        {/* Create team panel */}
        {selectedPtype && (
          <div>
            <h2 className="text-sm font-medium text-gray-700 mb-3">Create a Team</h2>
            <div className="bg-white rounded-lg border p-4 space-y-3">
              <input
                value={newTeamName}
                onChange={(e) => setNewTeamName(e.target.value)}
                placeholder="Team name"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <textarea
                value={newTeamMembers}
                onChange={(e) => setNewTeamMembers(e.target.value)}
                placeholder="Member emails (one per line)"
                rows={4}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={createTeam}
                disabled={creatingTeam || !newTeamName}
                className="px-4 py-2 bg-gray-800 text-white rounded-lg text-sm font-medium hover:bg-gray-900 disabled:opacity-50"
              >
                {creatingTeam ? 'Creating...' : 'Create Team'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
