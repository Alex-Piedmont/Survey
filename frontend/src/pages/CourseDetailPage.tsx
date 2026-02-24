import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client';

interface Section { id: string; name: string }
interface PresentationType { id: string; name: string }
interface RosterEntry { email: string; role: string }

export function CourseDetailPage() {
  const { courseId } = useParams<{ courseId: string }>();
  const [sections, setSections] = useState<Section[]>([]);
  const [ptypes, setPtypes] = useState<PresentationType[]>([]);
  const [selectedSection, setSelectedSection] = useState<string | null>(null);
  const [roster, setRoster] = useState<RosterEntry[]>([]);
  const [newSectionName, setNewSectionName] = useState('');
  const [enrollEmails, setEnrollEmails] = useState('');
  const [enrollResult, setEnrollResult] = useState<any>(null);
  const [seeding, setSeeding] = useState(false);

  useEffect(() => {
    if (!courseId) return;
    api.get<Section[]>(`/courses/${courseId}/sections`).then(setSections).catch(() => {});
    api.get<PresentationType[]>(`/courses/${courseId}/presentation-types`).then(setPtypes).catch(() => {});
  }, [courseId]);

  useEffect(() => {
    if (!selectedSection) return;
    api.get<RosterEntry[]>(`/sections/${selectedSection}/roster`).then(setRoster).catch(() => {});
  }, [selectedSection]);

  const createSection = async () => {
    if (!newSectionName || !courseId) return;
    await api.post(`/courses/${courseId}/sections`, { name: newSectionName });
    setNewSectionName('');
    api.get<Section[]>(`/courses/${courseId}/sections`).then(setSections);
  };

  const enroll = async () => {
    if (!selectedSection || !enrollEmails) return;
    const result = await api.post(`/sections/${selectedSection}/enroll`, { emails: enrollEmails });
    setEnrollResult(result);
    setEnrollEmails('');
    api.get<RosterEntry[]>(`/sections/${selectedSection}/roster`).then(setRoster);
  };

  const seedDefaults = async () => {
    if (!courseId) return;
    setSeeding(true);
    try {
      await api.post(`/courses/${courseId}/seed-defaults`);
      api.get<PresentationType[]>(`/courses/${courseId}/presentation-types`).then(setPtypes);
    } finally {
      setSeeding(false);
    }
  };

  return (
    <div>
      <Link to="/instructor" className="text-sm text-blue-600 hover:underline mb-4 inline-block">
        &larr; Back to courses
      </Link>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Sections */}
        <div>
          <h2 className="text-lg font-bold text-gray-900 mb-3">Sections</h2>
          <div className="bg-white rounded-lg border divide-y">
            {sections.map((s) => (
              <button
                key={s.id}
                onClick={() => setSelectedSection(s.id)}
                className={`w-full text-left px-4 py-3 text-sm hover:bg-gray-50 ${
                  selectedSection === s.id ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-700'
                }`}
              >
                {s.name}
              </button>
            ))}
            {sections.length === 0 && (
              <div className="px-4 py-3 text-sm text-gray-400">No sections yet</div>
            )}
          </div>
          <div className="flex gap-2 mt-3">
            <input
              value={newSectionName}
              onChange={(e) => setNewSectionName(e.target.value)}
              placeholder="Section name"
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              onKeyDown={(e) => e.key === 'Enter' && createSection()}
            />
            <button
              onClick={createSection}
              disabled={!newSectionName}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              Add
            </button>
          </div>

          {/* Enrollment */}
          {selectedSection && (
            <div className="mt-6">
              <h3 className="text-sm font-semibold text-gray-700 mb-2">
                Roster ({roster.length} enrolled)
              </h3>
              <div className="bg-white rounded-lg border max-h-48 overflow-y-auto divide-y mb-3">
                {roster.map((r) => (
                  <div key={r.email} className="px-4 py-2 text-sm flex justify-between">
                    <span className="text-gray-700">{r.email}</span>
                    <span className={`text-xs font-medium ${
                      r.role === 'instructor' ? 'text-purple-600' : r.role === 'ta' ? 'text-blue-600' : 'text-gray-400'
                    }`}>{r.role}</span>
                  </div>
                ))}
              </div>
              <textarea
                value={enrollEmails}
                onChange={(e) => setEnrollEmails(e.target.value)}
                placeholder="Paste student emails (one per line)"
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm mb-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={enroll}
                disabled={!enrollEmails}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                Enroll students
              </button>
              {enrollResult && (
                <div className="mt-2 text-xs text-gray-500">
                  Enrolled: {enrollResult.enrolled?.length || 0},
                  Duplicates: {enrollResult.duplicates?.length || 0},
                  Invalid: {enrollResult.invalid?.length || 0}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Presentation Types */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-bold text-gray-900">Presentation Types</h2>
            <button
              onClick={seedDefaults}
              disabled={seeding}
              className="px-3 py-1 border border-gray-300 text-gray-700 rounded-lg text-xs font-medium hover:bg-gray-50 disabled:opacity-50"
            >
              {seeding ? 'Seeding...' : 'Seed defaults'}
            </button>
          </div>
          <div className="bg-white rounded-lg border divide-y">
            {ptypes.map((p) => (
              <Link
                key={p.id}
                to={`/instructor/templates/${p.id}`}
                className="block px-4 py-3 text-sm text-gray-700 hover:bg-gray-50"
              >
                {p.name}
                <span className="text-gray-400 ml-2">&rarr;</span>
              </Link>
            ))}
            {ptypes.length === 0 && (
              <div className="px-4 py-3 text-sm text-gray-400">
                No presentation types. Seed defaults or create one.
              </div>
            )}
          </div>

          {/* Sessions */}
          {selectedSection && (
            <div className="mt-6">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-lg font-bold text-gray-900">Sessions</h2>
                <Link
                  to={`/instructor/sessions/new?section=${selectedSection}&course=${courseId}`}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
                >
                  New Session
                </Link>
              </div>
              <SessionList sectionId={selectedSection} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function SessionList({ sectionId }: { sectionId: string }) {
  const [sessions, setSessions] = useState<any[]>([]);

  useEffect(() => {
    api.get<any[]>(`/sections/${sectionId}/sessions`).then(setSessions).catch(() => {});
  }, [sectionId]);

  if (sessions.length === 0) {
    return <div className="text-sm text-gray-400">No sessions yet.</div>;
  }

  return (
    <div className="bg-white rounded-lg border divide-y">
      {sessions.map((s) => (
        <Link
          key={s.id}
          to={`/instructor/sessions/${s.id}/dashboard`}
          className="block px-4 py-3 hover:bg-gray-50"
        >
          <div className="text-sm font-medium text-gray-900">
            {s.presentation_type_name} &middot; {s.session_date}
          </div>
          <div className="text-xs text-gray-500">
            {s.presenting_team_count} teams &middot; {s.submission_count} submissions
          </div>
        </Link>
      ))}
    </div>
  );
}
