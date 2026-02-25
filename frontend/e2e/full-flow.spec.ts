import { test, expect, Page } from '@playwright/test';
import { seedTestData, authenticate, TestData } from './helpers';

/**
 * Shared test data — seeded once and cached.
 */
let _data: TestData | null = null;

async function getData(): Promise<TestData> {
  if (!_data) {
    _data = await seedTestData();
  }
  return _data;
}

/**
 * Login helper: completes the OTP flow in the browser.
 * Dev mode auto-fills the code, so we just need to click through.
 */
async function login(page: Page, email: string, redirectTo?: string) {
  const url = redirectTo
    ? `/login?redirect=${encodeURIComponent(redirectTo)}`
    : '/login';
  await page.goto(url);
  await page.getByPlaceholder('you@university.edu').fill(email);
  await page.getByRole('button', { name: 'Send verification code' }).click();

  // Wait for code step — dev mode auto-fills the code
  await expect(page.getByText('We sent a code to')).toBeVisible();
  await page.getByRole('button', { name: 'Verify & sign in' }).click();

  // Wait for navigation away from login
  await page.waitForURL((url) => !url.pathname.startsWith('/login'), { timeout: 10000 });
  await page.waitForLoadState('domcontentloaded');
}

// ─── All tests in a single describe with serial mode ───

test.describe('Full E2E Flow', () => {
  // ─── Instructor Flow ───

  test('instructor: login and see courses', async ({ page }) => {
    const data = await getData();
    await login(page, 'e2e-instructor@test.com', '/instructor');
    await expect(page).toHaveURL(/\/instructor/);
    await expect(page.getByText(data.courseName)).toBeVisible();
    await expect(page.getByText('Spring 2026').first()).toBeVisible();
  });

  test('instructor: navigate to course detail', async ({ page }) => {
    const data = await getData();
    await login(page, 'e2e-instructor@test.com', `/instructor/courses/${data.courseId}`);
    await expect(page).toHaveURL(/\/instructor\/courses\//);
    await expect(page.getByText('E2E Section')).toBeVisible();
    await expect(page.getByText('Strategic Headlines')).toBeVisible();
  });

  test('instructor: view roster after selecting section', async ({ page }) => {
    const data = await getData();
    await login(page, 'e2e-instructor@test.com', `/instructor/courses/${data.courseId}`);
    await page.getByText('E2E Section').click();
    await expect(page.getByText('enrolled')).toBeVisible();
    await expect(page.getByText('e2e-alice@test.com')).toBeVisible();
    await expect(page.getByText('e2e-dave@test.com')).toBeVisible();
  });

  test('instructor: view session list', async ({ page }) => {
    const data = await getData();
    await login(page, 'e2e-instructor@test.com', `/instructor/courses/${data.courseId}`);
    await page.getByText('E2E Section').click();
    await expect(page.getByText(data.ptypeName)).toBeVisible();
    await expect(page.getByText('2 teams')).toBeVisible();
  });

  test('instructor: open live dashboard', async ({ page }) => {
    const data = await getData();
    await login(page, 'e2e-instructor@test.com', `/instructor/sessions/${data.sessionId}/dashboard`);
    await expect(page.getByText('Live Dashboard')).toBeVisible();
    await expect(page.getByText('Submission Progress')).toBeVisible();
    await expect(page.getByText(/0 \/ \d+/)).toBeVisible();

    // QR code toggle
    await page.getByRole('button', { name: 'Show QR' }).click();
    await expect(page.getByAltText('QR Code')).toBeVisible();
    await page.getByRole('button', { name: 'Hide QR' }).click();
    await expect(page.getByAltText('QR Code')).not.toBeVisible();
  });

  test('instructor: template editor loads questions', async ({ page }) => {
    const data = await getData();
    await login(page, 'e2e-instructor@test.com', `/instructor/templates/${data.ptypeId}`);
    await expect(page.getByText('Template Editor')).toBeVisible();
    await expect(page.getByText('Version 1')).toBeVisible();
    const questionInputs = page.locator('input[placeholder="Question text"]');
    await expect(questionInputs.first()).toBeVisible();
    const count = await questionInputs.count();
    expect(count).toBeGreaterThanOrEqual(5);
  });

  // ─── Student Feedback Flow ───

  test('student: session page loads via QR link', async ({ page }) => {
    const data = await getData();
    await login(page, 'e2e-carol@test.com', `/s/${data.sessionId}`);
    await expect(page.getByText(data.courseName)).toBeVisible();
    await expect(page.getByText(data.ptypeName)).toBeVisible();
  });

  test('student: audience member sees correct targets', async ({ page }) => {
    const data = await getData();
    await login(page, 'e2e-carol@test.com', `/s/${data.sessionId}`);
    await expect(page.getByText('Audience Feedback')).toBeVisible();
    await expect(page.getByText('Team Alpha')).toBeVisible();
  });

  test('student: Carol completes feedback form', async ({ page }) => {
    const data = await getData();
    await login(page, 'e2e-carol@test.com', `/s/${data.sessionId}`);
    await expect(page.getByText('Audience Feedback')).toBeVisible();

    // Fill in all likert questions (click "4" for each)
    const likertButtons = page.locator('button:text("4")');
    const count = await likertButtons.count();
    for (let i = 0; i < count; i++) {
      await likertButtons.nth(i).click();
    }

    // Fill free text questions
    const textareas = page.locator('textarea');
    const textCount = await textareas.count();
    for (let i = 0; i < textCount; i++) {
      await textareas.nth(i).fill(`E2E test comment ${i + 1} from Carol`);
    }

    await page.getByRole('button', { name: /Save/ }).click();
    await page.waitForTimeout(500);

    const currentText = await page.textContent('body');
    if (currentText?.includes('Peer Feedback')) {
      const peerLikerts = page.locator('button:text("5")');
      const peerCount = await peerLikerts.count();
      for (let i = 0; i < peerCount; i++) {
        await peerLikerts.nth(i).click();
      }
      await page.getByRole('button', { name: /Save/ }).click();
    }

    await expect(page.getByText('All done!')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('Your feedback has been submitted')).toBeVisible();
  });

  test('student: Alice submits feedback', async ({ page }) => {
    const data = await getData();
    await login(page, 'e2e-alice@test.com', `/s/${data.sessionId}`);
    await expect(page.getByText('Audience Feedback')).toBeVisible();
    await expect(page.getByText('Team Beta')).toBeVisible();

    const likertButtons = page.locator('button:text("3")');
    const count = await likertButtons.count();
    for (let i = 0; i < count; i++) {
      await likertButtons.nth(i).click();
    }

    const textareas = page.locator('textarea');
    const textCount = await textareas.count();
    for (let i = 0; i < textCount; i++) {
      await textareas.nth(i).fill(`E2E comment from Alice`);
    }

    await page.getByRole('button', { name: /Save/ }).click();
    await page.waitForTimeout(500);

    const bodyText = await page.textContent('body');
    if (bodyText?.includes('Peer Feedback')) {
      const peerLikerts = page.locator('button:text("4")');
      const peerCount = await peerLikerts.count();
      for (let i = 0; i < peerCount; i++) {
        await peerLikerts.nth(i).click();
      }
      await page.getByRole('button', { name: /Save/ }).click();
    }

    await expect(page.getByText('All done!')).toBeVisible({ timeout: 10000 });
  });

  test('student: my submissions page shows feedback', async ({ page }) => {
    await login(page, 'e2e-carol@test.com', '/me/submissions');
    await expect(page.getByText('My Submissions')).toBeVisible();
    await expect(page.getByText(/Audience|Peer/).first()).toBeVisible();
  });

  // ─── Dashboard After Submissions ───

  test('dashboard: shows updated submission count', async ({ page }) => {
    const data = await getData();
    await login(page, 'e2e-instructor@test.com', `/instructor/sessions/${data.sessionId}/dashboard`);
    await expect(page.getByText('Live Dashboard')).toBeVisible({ timeout: 15000 });
    await expect(page.getByText('Submission Progress')).toBeVisible();
    await expect(page.getByText(/\d+ \/ \d+/)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('Team Alpha')).toBeVisible();
    await expect(page.getByText('Team Beta')).toBeVisible();
  });

  test('summary: loads with scores and comments', async ({ page }) => {
    const data = await getData();
    await login(page, 'e2e-instructor@test.com', `/instructor/sessions/${data.sessionId}/summary`);
    await expect(page.getByText('Session Summary')).toBeVisible();

    // Scores tab (default)
    await expect(page.getByText('Team Alpha')).toBeVisible();
    await expect(page.getByText('Team Beta')).toBeVisible();

    // Comments tab
    await page.getByRole('button', { name: 'Comments' }).click();
    await expect(page.getByText('E2E test comment').first()).toBeVisible({ timeout: 5000 });

    // Participation tab
    await page.getByRole('button', { name: 'Participation' }).click();
    await expect(page.getByText('e2e-carol@test.com')).toBeVisible();
    await expect(page.getByText('e2e-alice@test.com')).toBeVisible();

    // Grades tab
    await page.getByRole('button', { name: 'Grades' }).click();
    await expect(page.getByPlaceholder('Grade (e.g. A, B+)').first()).toBeVisible();
  });

  test('summary: instructor can assign grade', async ({ page }) => {
    const data = await getData();
    await login(page, 'e2e-instructor@test.com', `/instructor/sessions/${data.sessionId}/summary`);
    await page.getByRole('button', { name: 'Grades' }).click();

    const gradeInputs = page.getByPlaceholder('Grade (e.g. A, B+)');
    await gradeInputs.first().fill('A-');
    const commentInputs = page.getByPlaceholder('Comments (optional)');
    await commentInputs.first().fill('Excellent work');
    const saveButtons = page.getByRole('button', { name: 'Save' });
    await saveButtons.first().click();

    await page.waitForTimeout(1000);
    await expect(page.getByText('Current grade:')).toBeVisible();
    await expect(page.getByText('A-')).toBeVisible();
  });

  test('summary: instructor can withhold a comment', async ({ page }) => {
    const data = await getData();
    await login(page, 'e2e-instructor@test.com', `/instructor/sessions/${data.sessionId}/summary`);
    await page.getByRole('button', { name: 'Comments' }).click();

    const withholdBtn = page.getByRole('button', { name: 'Withhold' }).first();
    await withholdBtn.click();
    await expect(page.getByRole('button', { name: 'Restore' }).first()).toBeVisible();
  });

  test('summary: export CSV downloads a file', async ({ page }) => {
    const data = await getData();
    await login(page, 'e2e-instructor@test.com', `/instructor/sessions/${data.sessionId}/summary`);
    const downloadPromise = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Export CSV' }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toContain('.csv');
  });

  test('summary: export XLSX downloads a file', async ({ page }) => {
    const data = await getData();
    await login(page, 'e2e-instructor@test.com', `/instructor/sessions/${data.sessionId}/summary`);
    const downloadPromise = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Export XLSX' }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toContain('.xlsx');
  });

  // ─── Edge Cases ───

  test('edge: unauthenticated redirect from student session', async ({ page }) => {
    const data = await getData();
    await page.goto(`/s/${data.sessionId}`);
    await expect(page).toHaveURL(/\/login\?redirect=/);
  });

  test('edge: unauthenticated redirect from instructor', async ({ page }) => {
    await page.goto('/instructor');
    await expect(page).toHaveURL(/\/login/);
  });

  test('edge: form validation blocks empty required fields', async ({ page }) => {
    const data = await getData();
    await login(page, 'e2e-dave@test.com', `/s/${data.sessionId}`);
    await expect(page.getByText('Audience Feedback')).toBeVisible();
    await page.getByRole('button', { name: /Save/ }).click();
    await expect(page.getByText('Please complete all required questions')).toBeVisible();
  });

  test('edge: back navigation preserves filled answers', async ({ page }) => {
    const data = await getData();
    await login(page, 'e2e-dave@test.com', `/s/${data.sessionId}`);
    await expect(page.getByText('Audience Feedback')).toBeVisible();

    const likertButtons = page.locator('button:text("5")');
    const count = await likertButtons.count();
    for (let i = 0; i < count; i++) {
      await likertButtons.nth(i).click();
    }

    const textareas = page.locator('textarea');
    const textCount = await textareas.count();
    for (let i = 0; i < textCount; i++) {
      await textareas.nth(i).fill('Testing back nav');
    }

    await page.getByRole('button', { name: /Save & Next/ }).click();
    await page.waitForTimeout(500);

    if (await page.getByText('Peer Feedback').isVisible()) {
      await page.getByRole('button', { name: 'Back' }).click();
      const selected = page.locator('button:text("5").border-blue-600');
      await expect(selected.first()).toBeVisible();
      const textarea = page.locator('textarea').first();
      await expect(textarea).toHaveValue('Testing back nav');
    }
  });

  test('edge: previously saved submissions loaded on revisit', async ({ page }) => {
    const data = await getData();
    await login(page, 'e2e-carol@test.com', `/s/${data.sessionId}`);
    await expect(page.getByText('Audience Feedback')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('Previously saved')).toBeVisible({ timeout: 10000 });
  });

  // ─── Course Management ───

  test('management: create a new course', async ({ page }) => {
    await login(page, 'e2e-instructor@test.com', '/instructor');
    await page.getByRole('button', { name: 'New Course' }).click();
    await page.getByPlaceholder('Course name (e.g. MGMT 481)').fill('E2E New Course');
    await page.getByPlaceholder('Term (e.g. Spring 2026)').fill('Fall 2026');
    await page.getByRole('button', { name: 'Create' }).click();
    await expect(page.getByText('E2E New Course').first()).toBeVisible();
    await expect(page.getByText('Fall 2026').first()).toBeVisible();
  });

  test('management: create section and enroll students', async ({ page }) => {
    const data = await getData();
    await login(page, 'e2e-instructor@test.com', `/instructor/courses/${data.courseId}`);
    await page.getByPlaceholder('Section name').fill('Section B');
    await page.getByRole('button', { name: 'Add' }).click();
    await expect(page.getByText('Section B')).toBeVisible();

    await page.getByText('Section B').click();
    await expect(page.getByText('0 enrolled')).toBeVisible();

    await page.getByPlaceholder('Paste student emails (one per line)').fill(
      'newstudy1@test.com\nnewstudy2@test.com'
    );
    await page.getByRole('button', { name: 'Enroll students' }).click();
    await expect(page.getByText('Enrolled: 2')).toBeVisible();
  });
});
