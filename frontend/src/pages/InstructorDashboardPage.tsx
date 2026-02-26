import { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client';

interface TeamScore {
  team_id: string;
  team_name: string;
  scores: Record<string, { mean: number; count: number; question_text?: string }>;
}

interface Dashboard {
  session_id: string;
  enrolled_count: number;
  submitted_count: number;
  submitted_emails: string[];
  not_submitted_emails: string[];
  team_averages: TeamScore[];
}

interface QRCode {
  session_id: string;
  qr_url: string;
  qr_base64: string;
}

export function InstructorDashboardPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [qr, setQr] = useState<QRCode | null>(null);
  const [showQr, setShowQr] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const fetchDashboard = () => {
    if (!sessionId) return;
    api.get<Dashboard>(`/sessions/${sessionId}/dashboard`).then(setDashboard).catch(() => {});
  };

  useEffect(() => {
    fetchDashboard();
    if (!sessionId) return;
    api.get<QRCode>(`/sessions/${sessionId}/qr`).then(setQr).catch(() => {});
  }, [sessionId]);

  // WebSocket for live updates
  useEffect(() => {
    if (!sessionId) return;
    const apiUrl = import.meta.env.VITE_API_URL || '';
    let wsUrl: string;
    if (apiUrl) {
      wsUrl = apiUrl.replace(/^http/, 'ws') + `/ws/sessions/${sessionId}`;
    } else {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      wsUrl = `${protocol}//${window.location.host}/ws/sessions/${sessionId}`;
    }
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = () => {
      fetchDashboard();
    };

    ws.onclose = () => {
      // Reconnect after 3s
      setTimeout(() => {
        if (wsRef.current === ws) {
          wsRef.current = null;
        }
      }, 3000);
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [sessionId]);

  if (!dashboard) return <div className="text-gray-500">Loading...</div>;

  const pct = dashboard.enrolled_count > 0
    ? Math.round((dashboard.submitted_count / dashboard.enrolled_count) * 100)
    : 0;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-bold text-gray-900">Live Dashboard</h1>
          <span className="inline-flex items-center gap-1 text-xs font-medium text-green-600 bg-green-50 px-2 py-1 rounded-full">
            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            Live
          </span>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowQr(!showQr)}
            className="px-3 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm hover:bg-gray-50"
          >
            {showQr ? 'Hide QR' : 'Show QR'}
          </button>
          <Link
            to={`/instructor/sessions/${sessionId}/summary`}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
          >
            Full Summary
          </Link>
        </div>
      </div>

      {/* QR Code */}
      {showQr && qr && (
        <div className="bg-white rounded-lg border p-6 mb-6 flex flex-col items-center">
          <img src={`data:image/png;base64,${qr.qr_base64}`} alt="QR Code" className="w-64 h-64" />
          <p className="mt-2 text-sm text-gray-500">{qr.qr_url}</p>
        </div>
      )}

      {/* Progress */}
      <div className="bg-white rounded-lg border p-6 mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">Submission Progress</span>
          <span className="text-sm font-medium text-gray-900">
            {dashboard.submitted_count} / {dashboard.enrolled_count} ({pct}%)
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div
            className="bg-blue-600 rounded-full h-3 transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Team Averages */}
        <div>
          <h2 className="text-lg font-bold text-gray-900 mb-3">Team Averages</h2>
          {dashboard.team_averages.map((t) => {
            const entries = Object.entries(t.scores);
            const validEntries = entries.filter(([, s]) => s.mean != null);
            const overallMean = validEntries.length > 0
              ? (validEntries.reduce((sum, [, s]) => sum + s.mean, 0) / validEntries.length).toFixed(2)
              : 'N/A';
            return (
              <div key={t.team_id} className="bg-white rounded-lg border p-4 mb-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-gray-900">{t.team_name}</span>
                  <span className="text-sm font-bold text-blue-600">{overallMean}</span>
                </div>
                {entries.length > 0 ? (
                  <div className="space-y-1">
                    {entries.map(([qId, s]) => (
                      <div key={qId} className="flex justify-between text-xs text-gray-500">
                        <span className="truncate mr-2">{s.question_text ?? qId.slice(0, 8)}</span>
                        <span>{s.mean != null ? s.mean.toFixed(2) : 'N/A'} ({s.count} responses)</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-xs text-gray-400">No responses yet</div>
                )}
              </div>
            );
          })}
        </div>

        {/* Not Submitted */}
        <div>
          <h2 className="text-lg font-bold text-gray-900 mb-3">
            Not Yet Submitted ({dashboard.not_submitted_emails.length})
          </h2>
          <div className="bg-white rounded-lg border divide-y max-h-96 overflow-y-auto">
            {dashboard.not_submitted_emails.map((email) => (
              <div key={email} className="px-4 py-2 text-sm text-gray-700">{email}</div>
            ))}
            {dashboard.not_submitted_emails.length === 0 && (
              <div className="px-4 py-3 text-sm text-green-600">Everyone has submitted!</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
