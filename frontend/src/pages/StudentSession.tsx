import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { LikertScale } from '../components/LikertScale';
import { FreeTextInput } from '../components/FreeTextInput';
import { ProgressBar } from '../components/ProgressBar';

interface Question {
  id: string;
  question_text: string;
  question_type: string;
  category: string;
  options: any;
  is_required: boolean;
  sort_order: number;
}

interface Team {
  id: string;
  name: string;
  members: string[];
}

interface SessionData {
  session_id: string;
  course_name: string;
  section_name: string;
  presentation_type_name: string;
  session_date: string;
  deadline: string;
  status: string;
  presenting_teams: Team[];
  questions: Question[];
  student_role: string;
  student_team_id: string | null;
}

interface FeedbackTarget {
  type: 'audience' | 'peer';
  label: string;
  teamId?: string;
  studentEmail?: string;
}

export function StudentSession() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const { isAuthenticated, email } = useAuth();
  const navigate = useNavigate();

  const [session, setSession] = useState<SessionData | null>(null);
  const [targets, setTargets] = useState<FeedbackTarget[]>([]);
  const [currentPage, setCurrentPage] = useState(0);
  const [responses, setResponses] = useState<Record<string, Record<string, any>>>({});
  const [savedPages, setSavedPages] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [loadingSubmissions, setLoadingSubmissions] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [finished, setFinished] = useState(false);

  // Load session data
  useEffect(() => {
    if (!sessionId) return;
    api.get<SessionData>(`/s/${sessionId}`)
      .then((data) => {
        setSession(data);
        buildTargets(data);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [sessionId]);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!loading && !isAuthenticated) {
      navigate(`/login?redirect=/s/${sessionId}`, { replace: true });
    }
  }, [loading, isAuthenticated, sessionId, navigate]);

  function buildTargets(data: SessionData) {
    const t: FeedbackTarget[] = [];

    // Audience targets: all presenting teams except student's own team
    for (const team of data.presenting_teams) {
      if (team.id !== data.student_team_id) {
        t.push({ type: 'audience', label: team.name, teamId: team.id });
      }
    }

    // Peer targets: if presenter, all teammates except self
    if (data.student_role === 'presenter' && data.student_team_id) {
      const myTeam = data.presenting_teams.find((tm) => tm.id === data.student_team_id);
      if (myTeam) {
        for (const member of myTeam.members) {
          if (member !== email) {
            t.push({ type: 'peer', label: member, studentEmail: member });
          }
        }
      }
    }

    setTargets(t);
    if (t.length > 0) setLoadingSubmissions(true);

    // Initialize responses for each target
    const init: Record<string, Record<string, any>> = {};
    t.forEach((target, i) => {
      init[i] = {};
    });
    setResponses(init);
  }

  // Load existing submissions
  useEffect(() => {
    if (!sessionId || !isAuthenticated || targets.length === 0) return;
    setLoadingSubmissions(true);
    api.get<any[]>(`/s/${sessionId}/submissions`)
      .then((subs) => {
        const saved = new Set<number>();
        for (const sub of subs) {
          const idx = targets.findIndex((t) =>
            t.type === 'audience'
              ? t.teamId === sub.target_team_id && sub.feedback_type === 'audience'
              : t.studentEmail === sub.target_student_email && sub.feedback_type === 'peer'
          );
          if (idx >= 0) {
            setResponses((prev) => ({ ...prev, [idx]: sub.responses }));
            saved.add(idx);
          }
        }
        setSavedPages(saved);
      })
      .catch(() => {}) // Silently fail — user might not have prior submissions
      .finally(() => setLoadingSubmissions(false));
  }, [sessionId, isAuthenticated, targets]);

  const questionsForTarget = (target: FeedbackTarget): Question[] => {
    if (!session) return [];
    const category = target.type === 'audience' ? 'audience' : 'peer';
    return session.questions.filter((q) => q.category === category);
  };

  const updateResponse = (questionId: string, value: any) => {
    setResponses((prev) => ({
      ...prev,
      [currentPage]: { ...prev[currentPage], [questionId]: value },
    }));
  };

  const validatePage = (): boolean => {
    const target = targets[currentPage];
    const qs = questionsForTarget(target);
    const pageResponses = responses[currentPage] || {};

    for (const q of qs) {
      if (q.is_required) {
        const val = pageResponses[q.id];
        if (val === undefined || val === null || val === '') return false;
      }
    }
    return true;
  };

  const savePage = async () => {
    const target = targets[currentPage];
    setSaving(true);
    setError('');

    try {
      const body: any = {
        feedback_type: target.type,
        responses: responses[currentPage] || {},
      };

      if (target.type === 'audience') {
        body.target_team_id = target.teamId;
      } else {
        body.target_student_email = target.studentEmail;
      }

      await api.post(`/s/${sessionId}/submit`, body);
      setSavedPages((prev) => new Set(prev).add(currentPage));
      return true;
    } catch (e: any) {
      setError(e.message);
      return false;
    } finally {
      setSaving(false);
    }
  };

  const handleNext = async () => {
    if (!validatePage()) {
      setError('Please complete all required questions before continuing.');
      return;
    }
    const ok = await savePage();
    if (ok) {
      if (currentPage < targets.length - 1) {
        setCurrentPage((p) => p + 1);
        setError('');
      } else {
        setFinished(true);
      }
    }
  };

  const handleBack = () => {
    if (currentPage > 0) {
      setCurrentPage((p) => p - 1);
      setError('');
    }
  };

  if (loading || loadingSubmissions) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-gray-500">Loading session...</div>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-red-600">Session not found</div>
      </div>
    );
  }

  if (targets.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">No feedback to submit</h2>
          <p className="text-gray-600">There are no targets available for your feedback.</p>
        </div>
      </div>
    );
  }

  if (finished) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="max-w-md w-full bg-white rounded-xl shadow-md p-8 text-center">
          <div className="text-5xl mb-4">&#10003;</div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">All done!</h2>
          <p className="text-gray-600 mb-4">
            Your feedback has been submitted successfully.
            You can edit your responses within 7 days.
          </p>
          <p className="text-sm text-gray-400">
            Submitted at {new Date().toLocaleString()}
          </p>
          <button
            onClick={() => navigate('/me/submissions')}
            className="mt-6 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            View my submissions
          </button>
        </div>
      </div>
    );
  }

  const target = targets[currentPage];
  const questions = questionsForTarget(target);
  const pageResponses = responses[currentPage] || {};
  const isLastPage = currentPage === targets.length - 1;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b px-4 py-3">
        <div className="max-w-lg mx-auto">
          <div className="text-sm text-gray-500">
            {session.course_name} &middot; {session.section_name}
          </div>
          <div className="text-sm text-gray-400">
            {session.presentation_type_name} &middot; {session.session_date}
          </div>
        </div>
      </div>

      <div className="max-w-lg mx-auto px-4 py-6">
        <ProgressBar current={currentPage + 1} total={targets.length} />

        {/* Target header */}
        <div className="mb-6">
          <span className="text-xs font-semibold uppercase tracking-wide text-blue-600">
            {target.type === 'audience' ? 'Audience Feedback' : 'Peer Feedback'}
          </span>
          <h2 className="text-xl font-bold text-gray-900">{target.label}</h2>
          {savedPages.has(currentPage) && (
            <span className="text-xs text-green-600 font-medium">Previously saved</span>
          )}
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
            {error}
          </div>
        )}

        {/* Questions */}
        {questions.map((q) => {
          if (q.question_type.startsWith('likert')) {
            return (
              <LikertScale
                key={q.id}
                label={q.question_text}
                value={pageResponses[q.id] ?? null}
                onChange={(v) => updateResponse(q.id, v)}
                required={q.is_required}
              />
            );
          }
          if (q.question_type === 'free_text') {
            return (
              <FreeTextInput
                key={q.id}
                label={q.question_text}
                value={pageResponses[q.id] ?? ''}
                onChange={(v) => updateResponse(q.id, v)}
                required={q.is_required}
              />
            );
          }
          return null;
        })}

        {/* Navigation */}
        <div className="flex gap-3 mt-8">
          {currentPage > 0 && (
            <button
              onClick={handleBack}
              className="flex-1 py-3 border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50"
            >
              Back
            </button>
          )}
          <button
            onClick={handleNext}
            disabled={saving}
            className="flex-1 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {saving
              ? 'Saving...'
              : isLastPage
                ? 'Save & Finish'
                : 'Save & Next'}
          </button>
        </div>
      </div>
    </div>
  );
}
