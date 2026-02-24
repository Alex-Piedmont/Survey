import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client';

interface Question {
  id?: string;
  question_text: string;
  question_type: string;
  category: string;
  options: string[] | null;
  is_required: boolean;
  sort_order: number;
  is_active: boolean;
}

interface Template {
  id: string;
  presentation_type_id: string;
  version: number;
  questions: Question[];
}

const QUESTION_TYPES = ['likert_5', 'likert_7', 'free_text', 'multiple_choice'];
const CATEGORIES = ['audience', 'peer', 'instructor'];

export function TemplateEditorPage() {
  const { ptypeId } = useParams<{ ptypeId: string }>();
  const [template, setTemplate] = useState<Template | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!ptypeId) return;
    api.get<Template>(`/presentation-types/${ptypeId}/template`).then((t) => {
      setTemplate(t);
      setQuestions(t.questions.length > 0 ? t.questions : []);
    }).catch(() => {});
  }, [ptypeId]);

  const addQuestion = () => {
    setQuestions([
      ...questions,
      {
        question_text: '',
        question_type: 'likert_5',
        category: 'audience',
        options: null,
        is_required: true,
        sort_order: questions.length + 1,
        is_active: true,
      },
    ]);
  };

  const updateQuestion = (index: number, updates: Partial<Question>) => {
    setQuestions(questions.map((q, i) => (i === index ? { ...q, ...updates } : q)));
  };

  const removeQuestion = (index: number) => {
    setQuestions(questions.filter((_, i) => i !== index).map((q, i) => ({ ...q, sort_order: i + 1 })));
  };

  const moveQuestion = (index: number, direction: -1 | 1) => {
    const target = index + direction;
    if (target < 0 || target >= questions.length) return;
    const updated = [...questions];
    [updated[index], updated[target]] = [updated[target], updated[index]];
    setQuestions(updated.map((q, i) => ({ ...q, sort_order: i + 1 })));
  };

  const save = async () => {
    if (!ptypeId) return;
    setSaving(true);
    setSaved(false);
    try {
      const result = await api.put<Template>(`/presentation-types/${ptypeId}/template`, { questions });
      setTemplate(result);
      setQuestions(result.questions);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  };

  if (!template) return <div className="text-gray-500">Loading...</div>;

  return (
    <div>
      <Link to="/instructor" className="text-sm text-blue-600 hover:underline mb-4 inline-block">
        &larr; Back to courses
      </Link>

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Template Editor</h1>
          <p className="text-sm text-gray-500">Version {template.version}</p>
        </div>
        <div className="flex items-center gap-3">
          {saved && <span className="text-sm text-green-600">Saved!</span>}
          <button
            onClick={save}
            disabled={saving}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save (new version)'}
          </button>
        </div>
      </div>

      <div className="space-y-4">
        {questions.map((q, i) => (
          <div key={i} className="bg-white rounded-lg border p-4">
            <div className="flex items-start justify-between mb-3">
              <span className="text-xs font-medium text-gray-400">Q{i + 1}</span>
              <div className="flex gap-1">
                <button onClick={() => moveQuestion(i, -1)} disabled={i === 0} className="px-2 py-1 text-xs text-gray-500 hover:bg-gray-100 rounded disabled:opacity-30">&uarr;</button>
                <button onClick={() => moveQuestion(i, 1)} disabled={i === questions.length - 1} className="px-2 py-1 text-xs text-gray-500 hover:bg-gray-100 rounded disabled:opacity-30">&darr;</button>
                <button onClick={() => removeQuestion(i)} className="px-2 py-1 text-xs text-red-500 hover:bg-red-50 rounded">Remove</button>
              </div>
            </div>

            <input
              value={q.question_text}
              onChange={(e) => updateQuestion(i, { question_text: e.target.value })}
              placeholder="Question text"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />

            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="text-xs text-gray-500 mb-1 block">Type</label>
                <select
                  value={q.question_type}
                  onChange={(e) => updateQuestion(i, { question_type: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {QUESTION_TYPES.map((t) => (
                    <option key={t} value={t}>{t.replace('_', ' ')}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">Category</label>
                <select
                  value={q.category}
                  onChange={(e) => updateQuestion(i, { category: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {CATEGORIES.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>
              <div className="flex items-end">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={q.is_required}
                    onChange={(e) => updateQuestion(i, { is_required: e.target.checked })}
                    className="rounded"
                  />
                  Required
                </label>
              </div>
            </div>
          </div>
        ))}
      </div>

      <button
        onClick={addQuestion}
        className="mt-4 w-full py-3 border-2 border-dashed border-gray-300 rounded-lg text-sm text-gray-500 hover:border-blue-400 hover:text-blue-600"
      >
        + Add Question
      </button>
    </div>
  );
}
