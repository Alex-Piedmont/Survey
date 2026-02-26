/**
 * API helpers for E2E test setup.
 * Calls the backend directly to seed data before browser tests run.
 */

export const API = (process.env.DEPLOYED_API_URL || 'http://localhost:8001') + '/api/v1';

export async function apiDelete(path: string, token?: string) {
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(`${API}${path}`, { method: 'DELETE', headers });
  if (!res.ok && res.status !== 204) {
    const text = await res.text();
    throw new Error(`DELETE ${path} → ${res.status}: ${text}`);
  }
  return res.status === 204 ? null : res.json();
}

export async function apiPatch(path: string, body: unknown, token?: string) {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(`${API}${path}`, {
    method: 'PATCH',
    headers,
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`PATCH ${path} → ${res.status}: ${text}`);
  }
  return res.json();
}

export async function apiPost(path: string, body: unknown, token?: string) {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(`${API}${path}`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`POST ${path} → ${res.status}: ${text}`);
  }
  return res.json();
}

export async function apiGet(path: string, token?: string) {
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(`${API}${path}`, { headers });
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`);
  return res.json();
}

export async function authenticate(email: string): Promise<string> {
  const otp = await apiPost('/auth/otp/request', { email });
  const verify = await apiPost('/auth/otp/verify', { email, code: otp._dev_code });
  return verify.access_token;
}

export interface TestData {
  instructorToken: string;
  courseId: string;
  courseName: string;
  sectionId: string;
  ptypeId: string;
  ptypeName: string;
  teamAId: string;
  teamBId: string;
  sessionId: string;
  questionIds: { likert: string[]; freeText: string[]; peer: string[] };
}

/**
 * Seeds a full course/section/teams/session via API.
 * Returns all IDs needed for browser tests.
 */
export async function seedTestData(): Promise<TestData> {
  // Admin grants instructor privileges first (required since admin system)
  const adminToken = await authenticate('alex@aptuslearning.ai');
  try {
    await apiPost('/admin/instructors', { email: 'e2e-instructor@test.com' }, adminToken);
  } catch {
    // 409 = already an instructor, that's fine
  }

  // Instructor auth (re-authenticate to get fresh token with is_instructor claim)
  const instructorToken = await authenticate('e2e-instructor@test.com');

  // Create course with unique name to avoid stale-data collisions
  const runId = Date.now().toString(36);
  const courseName = `E2E Course ${runId}`;
  const course = await apiPost('/courses', { name: courseName, term: 'Spring 2026' }, instructorToken);

  // Create section
  const section = await apiPost(`/courses/${course.id}/sections`, { name: 'E2E Section' }, instructorToken);

  // Seed default templates
  await apiPost(`/courses/${course.id}/seed-defaults`, {}, instructorToken);

  // Get first ptype
  const ptypes = await apiGet(`/courses/${course.id}/presentation-types`, instructorToken);
  const ptype = ptypes[0];

  // Enroll students
  const students = [
    'e2e-alice@test.com',
    'e2e-bob@test.com',
    'e2e-carol@test.com',
    'e2e-dave@test.com',
  ];
  await apiPost(`/sections/${section.id}/enroll`, { emails: students.join('\n') }, instructorToken);

  // Create teams
  const teamA = await apiPost(`/sections/${section.id}/teams`, {
    name: 'Team Alpha',
    presentation_type_id: ptype.id,
    member_emails: ['e2e-alice@test.com', 'e2e-bob@test.com'],
  }, instructorToken);

  const teamB = await apiPost(`/sections/${section.id}/teams`, {
    name: 'Team Beta',
    presentation_type_id: ptype.id,
    member_emails: ['e2e-carol@test.com', 'e2e-dave@test.com'],
  }, instructorToken);

  // Create session (today's date)
  const today = new Date().toISOString().split('T')[0];
  const session = await apiPost('/sessions', {
    section_id: section.id,
    presentation_type_id: ptype.id,
    presenting_team_ids: [teamA.id, teamB.id],
    session_date: today,
  }, instructorToken);

  // Get question IDs from student session view
  const studentView = await apiGet(`/s/${session.id}`);
  const likert: string[] = [];
  const freeText: string[] = [];
  const peer: string[] = [];
  for (const q of studentView.questions) {
    if (q.category === 'peer') peer.push(q.id);
    else if (q.question_type === 'free_text') freeText.push(q.id);
    else likert.push(q.id);
  }

  return {
    instructorToken,
    courseId: course.id,
    courseName,
    sectionId: section.id,
    ptypeId: ptype.id,
    ptypeName: ptype.name,
    teamAId: teamA.id,
    teamBId: teamB.id,
    sessionId: session.id,
    questionIds: { likert, freeText, peer },
  };
}
