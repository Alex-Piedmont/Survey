import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api, fetchRaw } from '../api/client';

interface TeamScore {
  team_id: string;
  team_name: string;
  scores: Record<string, { mean: number; median: number; std_dev: number; count: number; histogram: Record<string, number>; question_text?: string }>;
}

interface CommentEntry { question_id: string; question_text?: string; text: string; submission_id: string; withheld: boolean }
interface TeamComments { team_id: string; team_name: string; comments: CommentEntry[] }
interface ParticipationEntry { email: string; audience_submissions: Record<string, boolean>; peer_submitted: boolean; is_presenter: boolean }
interface PresentationGrade { id: string; session_id: string; team_id: string; grade: string; comments: string | null; graded_by: string }

interface Summary {
  session_id: string;
  session_date: string;
  team_scores: TeamScore[];
  team_comments: TeamComments[];
  participation_matrix: ParticipationEntry[];
  presentation_grades: PresentationGrade[];
  instructor_submissions: any[];
}

export function SessionSummaryPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [summary, setSummary] = useState<Summary | null>(null);
  const [gradeInputs, setGradeInputs] = useState<Record<string, { grade: string; comments: string }>>({});
  const [tab, setTab] = useState<'scores' | 'comments' | 'participation' | 'grades'>('scores');

  useEffect(() => {
    if (!sessionId) return;
    api.get<Summary>(`/sessions/${sessionId}/summary`).then((s) => {
      setSummary(s);
      const inputs: Record<string, { grade: string; comments: string }> = {};
      for (const g of s.presentation_grades) {
        inputs[g.team_id] = { grade: g.grade, comments: g.comments || '' };
      }
      for (const ts of s.team_scores) {
        if (!inputs[ts.team_id]) inputs[ts.team_id] = { grade: '', comments: '' };
      }
      setGradeInputs(inputs);
    }).catch(() => {});
  }, [sessionId]);

  const saveGrade = async (teamId: string) => {
    if (!sessionId) return;
    const input = gradeInputs[teamId];
    if (!input?.grade) return;
    await api.post(`/sessions/${sessionId}/teams/${teamId}/presentation-grade`, {
      grade: input.grade,
      comments: input.comments || null,
    });
    // Refresh
    const s = await api.get<Summary>(`/sessions/${sessionId}/summary`);
    setSummary(s);
  };

  const toggleWithhold = async (submissionId: string) => {
    if (!sessionId) return;
    await api.put(`/sessions/${sessionId}/comments/${submissionId}/withhold`);
    const s = await api.get<Summary>(`/sessions/${sessionId}/summary`);
    setSummary(s);
  };

  const exportData = async (format: 'csv' | 'xlsx') => {
    if (!sessionId) return;
    const res = await fetchRaw(`/sessions/${sessionId}/export?format=${format}`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `session_${sessionId}.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!summary) return <div className="text-gray-500">Loading...</div>;

  const tabs = [
    { key: 'scores' as const, label: 'Scores' },
    { key: 'comments' as const, label: 'Comments' },
    { key: 'participation' as const, label: 'Participation' },
    { key: 'grades' as const, label: 'Grades' },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <Link
            to={`/instructor/sessions/${sessionId}/dashboard`}
            className="text-sm text-blue-600 hover:underline mb-1 inline-block"
          >
            &larr; Back to dashboard
          </Link>
          <h1 className="text-xl font-bold text-gray-900">Session Summary</h1>
          <p className="text-sm text-gray-500">{summary.session_date}</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => exportData('csv')} className="px-3 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm hover:bg-gray-50">
            Export CSV
          </button>
          <button onClick={() => exportData('xlsx')} className="px-3 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm hover:bg-gray-50">
            Export XLSX
          </button>
        </div>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 mb-6 bg-gray-100 p-1 rounded-lg w-fit">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              tab === t.key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Scores */}
      {tab === 'scores' && (
        <div className="space-y-4">
          {summary.team_scores.map((t) => (
            <div key={t.team_id} className="bg-white rounded-lg border p-4">
              <h3 className="font-medium text-gray-900 mb-3">{t.team_name}</h3>
              {Object.entries(t.scores).length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-gray-500 border-b">
                        <th className="pb-2 pr-4">Question</th>
                        <th className="pb-2 pr-4">Mean</th>
                        <th className="pb-2 pr-4">Median</th>
                        <th className="pb-2 pr-4">Std Dev</th>
                        <th className="pb-2">Responses</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(t.scores).map(([qId, s]) => (
                        <tr key={qId} className="border-b last:border-0">
                          <td className="py-2 pr-4 text-gray-600">{s.question_text ?? qId.slice(0, 8)}</td>
                          <td className="py-2 pr-4 font-medium">{s.mean?.toFixed(2) ?? 'N/A'}</td>
                          <td className="py-2 pr-4">{s.median?.toFixed(1) ?? 'N/A'}</td>
                          <td className="py-2 pr-4">{s.std_dev?.toFixed(2) ?? 'N/A'}</td>
                          <td className="py-2">{s.count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-sm text-gray-400">No scores yet</div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Comments */}
      {tab === 'comments' && (
        <div className="space-y-4">
          {summary.team_comments.map((t) => {
            // Group comments by question
            const byQuestion: Record<string, { question_text: string; comments: CommentEntry[] }> = {};
            for (const c of t.comments) {
              const key = c.question_id;
              if (!byQuestion[key]) {
                byQuestion[key] = { question_text: c.question_text || key.slice(0, 8), comments: [] };
              }
              byQuestion[key].comments.push(c);
            }
            const questionGroups = Object.entries(byQuestion);

            return (
              <div key={t.team_id} className="bg-white rounded-lg border p-4">
                <h3 className="font-medium text-gray-900 mb-3">{t.team_name}</h3>
                {questionGroups.length > 0 ? (
                  <div className="space-y-4">
                    {questionGroups.map(([qId, group]) => (
                      <div key={qId}>
                        <h4 className="text-sm font-medium text-gray-600 mb-2">{group.question_text}</h4>
                        <div className="space-y-2">
                          {group.comments.map((c) => (
                            <div key={c.submission_id} className={`flex items-start justify-between p-3 rounded-lg ${c.withheld ? 'bg-red-50' : 'bg-gray-50'}`}>
                              <p className={`text-sm flex-1 ${c.withheld ? 'text-red-400 line-through' : 'text-gray-700'}`}>
                                {c.text}
                              </p>
                              <button
                                onClick={() => toggleWithhold(c.submission_id)}
                                className={`ml-3 text-xs font-medium px-2 py-1 rounded ${
                                  c.withheld
                                    ? 'text-green-600 hover:bg-green-50'
                                    : 'text-red-600 hover:bg-red-50'
                                }`}
                              >
                                {c.withheld ? 'Restore' : 'Withhold'}
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-sm text-gray-400">No comments</div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Participation */}
      {tab === 'participation' && (
        <div className="bg-white rounded-lg border overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b bg-gray-50">
                <th className="px-4 py-3">Student</th>
                <th className="px-4 py-3">Role</th>
                {summary.team_scores.map((t) => (
                  <th key={t.team_id} className="px-4 py-3 text-center">{t.team_name}</th>
                ))}
                <th className="px-4 py-3 text-center">Peer</th>
              </tr>
            </thead>
            <tbody>
              {summary.participation_matrix.map((p) => (
                <tr key={p.email} className="border-b last:border-0">
                  <td className="px-4 py-2 text-gray-700">{p.email}</td>
                  <td className="px-4 py-2">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                      p.is_presenter ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-600'
                    }`}>
                      {p.is_presenter ? 'Presenter' : 'Audience'}
                    </span>
                  </td>
                  {summary.team_scores.map((t) => (
                    <td key={t.team_id} className="px-4 py-2 text-center">
                      {p.audience_submissions[t.team_id] === true
                        ? <span className="text-green-600">&#10003;</span>
                        : p.audience_submissions[t.team_id] === false
                          ? <span className="text-red-400">&#10007;</span>
                          : <span className="text-gray-300">&mdash;</span>
                      }
                    </td>
                  ))}
                  <td className="px-4 py-2 text-center">
                    {p.is_presenter
                      ? (p.peer_submitted
                        ? <span className="text-green-600">&#10003;</span>
                        : <span className="text-red-400">&#10007;</span>)
                      : <span className="text-gray-300">&mdash;</span>
                    }
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Grades */}
      {tab === 'grades' && (
        <div className="space-y-4">
          {summary.team_scores.map((t) => {
            const input = gradeInputs[t.team_id] || { grade: '', comments: '' };
            const existing = summary.presentation_grades.find((g) => g.team_id === t.team_id);
            return (
              <div key={t.team_id} className="bg-white rounded-lg border p-4">
                <h3 className="font-medium text-gray-900 mb-3">{t.team_name}</h3>
                {existing && (
                  <div className="mb-3 text-sm text-gray-500">
                    Current grade: <span className="font-medium text-gray-900">{existing.grade}</span>
                    {existing.comments && <span> &mdash; {existing.comments}</span>}
                  </div>
                )}
                <div className="flex gap-3">
                  <input
                    value={input.grade}
                    onChange={(e) => setGradeInputs({ ...gradeInputs, [t.team_id]: { ...input, grade: e.target.value } })}
                    placeholder="Grade (e.g. A, B+)"
                    className="w-24 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <input
                    value={input.comments}
                    onChange={(e) => setGradeInputs({ ...gradeInputs, [t.team_id]: { ...input, comments: e.target.value } })}
                    placeholder="Comments (optional)"
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    onClick={() => saveGrade(t.team_id)}
                    disabled={!input.grade}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                  >
                    Save
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
