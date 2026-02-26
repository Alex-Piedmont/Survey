import { test, expect, Page } from '@playwright/test';
import {
  authenticate,
  apiPost,
  apiGet,
  apiDelete,
  seedTestData,
  TestData,
} from './helpers';

// ─── Admin E2E email constants ───
const ADMIN_EMAIL = 'alex@aptuslearning.ai';
const NEW_INSTRUCTOR_EMAIL = 'e2e-new-instructor@test.com';
const TA_EMAIL = 'e2e-admin-ta@test.com';
const REGULAR_EMAIL = 'e2e-regular-user@test.com';

// Unique course name per test run to avoid strict mode violations
const RUN_ID = Date.now().toString(36);
const ADMIN_COURSE_NAME = `Admin E2E ${RUN_ID}`;

// ─── Shared state ───
let adminToken: string;
let _mainData: TestData | null = null;

async function getMainData(): Promise<TestData> {
  if (!_mainData) _mainData = await seedTestData();
  return _mainData;
}

/**
 * Login helper: completes the OTP flow in the browser.
 */
async function login(page: Page, email: string, redirectTo?: string) {
  const url = redirectTo
    ? `/login?redirect=${encodeURIComponent(redirectTo)}`
    : '/login';
  await page.goto(url);
  await page.getByPlaceholder('you@university.edu').fill(email);
  await page.getByRole('button', { name: 'Send verification code' }).click();
  await expect(page.getByText('We sent a code to')).toBeVisible();
  await page.getByRole('button', { name: 'Verify & sign in' }).click();
  await page.waitForURL((url) => !url.pathname.startsWith('/login'), { timeout: 10000 });
  await page.waitForLoadState('domcontentloaded');
}

/**
 * Helper to find an instructor row by email on the instructors page.
 * Waits for data to load first, then finds the row containing the email.
 */
async function findInstructorRow(page: Page, email: string) {
  // Wait for loading to finish
  await expect(page.getByText('Loading...')).not.toBeVisible({ timeout: 15000 });
  // Each instructor row is a direct child of the divide-y container
  const row = page.locator('.divide-y > div').filter({ hasText: email });
  await expect(row).toBeVisible();
  return row;
}

// ─── Tests ───

test.describe('Admin E2E Flow', () => {
  // ─── Setup: ensure admin token and base data exist ───

  test.beforeAll(async () => {
    adminToken = await authenticate(ADMIN_EMAIL);
    await getMainData();

    // Clean up from previous runs (ignore errors)
    try { await apiDelete(`/admin/instructors/${NEW_INSTRUCTOR_EMAIL}`, adminToken); } catch {}
    try { await apiDelete(`/admin/instructors/e2e-instructor@test.com/tas/${TA_EMAIL}`, adminToken); } catch {}
  });

  // ─── Navigation & Access Control ───

  test('admin sees Admin link in instructor nav', async ({ page }) => {
    await login(page, ADMIN_EMAIL, '/instructor');
    await expect(page.getByRole('link', { name: 'Admin' })).toBeVisible();
  });

  test('non-admin does NOT see Admin link', async ({ page }) => {
    await authenticate(REGULAR_EMAIL);
    await login(page, REGULAR_EMAIL, '/instructor');
    await expect(page.getByRole('link', { name: 'Admin' })).not.toBeVisible();
  });

  test('admin navigates to admin dashboard', async ({ page }) => {
    await login(page, ADMIN_EMAIL, '/admin');
    await expect(page.getByText('Admin Dashboard')).toBeVisible();
  });

  // ─── Dashboard Stats ───

  test('admin dashboard shows stats cards', async ({ page }) => {
    await login(page, ADMIN_EMAIL, '/admin');
    // Use the grid container for stat cards to avoid matching nav links
    const statsGrid = page.locator('.grid');
    await expect(statsGrid.getByText('Users')).toBeVisible();
    await expect(statsGrid.getByText('Instructors')).toBeVisible();
    await expect(statsGrid.getByText('Admins')).toBeVisible();
    await expect(statsGrid.getByText('Courses')).toBeVisible();
    await expect(statsGrid.getByText('Active Sessions')).toBeVisible();
    await expect(statsGrid.getByText('Submissions')).toBeVisible();
  });

  test('admin dashboard shows recent courses', async ({ page }) => {
    const data = await getMainData();
    await login(page, ADMIN_EMAIL, '/admin');
    await expect(page.getByText('Recent Courses')).toBeVisible();
    await expect(page.getByText(data.courseName)).toBeVisible();
  });

  // ─── Instructor Management ───

  test('admin navigates to instructors page', async ({ page }) => {
    await login(page, ADMIN_EMAIL, '/admin/instructors');
    await expect(page.getByRole('heading', { name: 'Instructors' })).toBeVisible();
    await expect(page.getByText('Loading...')).not.toBeVisible({ timeout: 15000 });
    await expect(page.getByText('e2e-instructor@test.com')).toBeVisible();
  });

  test('admin adds a new instructor', async ({ page }) => {
    await login(page, ADMIN_EMAIL, '/admin/instructors');
    await expect(page.getByText('Loading...')).not.toBeVisible({ timeout: 15000 });

    await page.getByPlaceholder('Email address').fill(NEW_INSTRUCTOR_EMAIL);
    await page.getByRole('button', { name: '+ Add Instructor' }).click();

    await expect(page.getByText(NEW_INSTRUCTOR_EMAIL)).toBeVisible({ timeout: 10000 });
  });

  test('adding duplicate instructor shows error', async ({ page }) => {
    await login(page, ADMIN_EMAIL, '/admin/instructors');
    await expect(page.getByText('Loading...')).not.toBeVisible({ timeout: 15000 });

    await page.getByPlaceholder('Email address').fill(NEW_INSTRUCTOR_EMAIL);
    await page.getByRole('button', { name: '+ Add Instructor' }).click();

    await expect(page.getByText(/already has instructor/i)).toBeVisible({ timeout: 10000 });
  });

  test('new instructor can create a course', async ({ page }) => {
    await login(page, NEW_INSTRUCTOR_EMAIL, '/instructor');

    await page.getByRole('button', { name: 'New Course' }).click();
    await page.getByPlaceholder('Course name (e.g. MGMT 481)').fill(ADMIN_COURSE_NAME);
    await page.getByPlaceholder('Term (e.g. Spring 2026)').fill('Fall 2026');
    await page.getByRole('button', { name: 'Create' }).click();

    // Use unique name to avoid strict mode violations from previous runs
    await expect(page.getByText(ADMIN_COURSE_NAME)).toBeVisible({ timeout: 10000 });
  });

  test('admin revokes instructor privileges', async ({ page }) => {
    await login(page, ADMIN_EMAIL, '/admin/instructors');

    const row = await findInstructorRow(page, NEW_INSTRUCTOR_EMAIL);
    page.on('dialog', (dialog) => dialog.accept());
    await row.getByRole('button', { name: 'Revoke' }).click();

    await expect(page.getByText(NEW_INSTRUCTOR_EMAIL)).not.toBeVisible({ timeout: 10000 });
  });

  test('revoked instructor cannot create a course', async ({ page }) => {
    await login(page, NEW_INSTRUCTOR_EMAIL, '/instructor');

    await page.getByRole('button', { name: 'New Course' }).click();
    await page.getByPlaceholder('Course name (e.g. MGMT 481)').fill('Should Fail');
    await page.getByPlaceholder('Term (e.g. Spring 2026)').fill('Fall 2026');
    await page.getByRole('button', { name: 'Create' }).click();

    // Should see an error (403 from backend)
    await expect(page.getByText(/instructor privileges|error|failed/i)).toBeVisible({
      timeout: 10000,
    });
  });

  // ─── TA Management ───

  test('admin opens TA management modal', async ({ page }) => {
    await login(page, ADMIN_EMAIL, '/admin/instructors');

    const row = await findInstructorRow(page, 'e2e-instructor@test.com');
    await row.getByRole('button', { name: 'Manage TAs' }).click();

    await expect(page.getByText('TAs for e2e-instructor@test.com')).toBeVisible();
  });

  test('admin assigns a TA to instructor', async ({ page }) => {
    await login(page, ADMIN_EMAIL, '/admin/instructors');

    const row = await findInstructorRow(page, 'e2e-instructor@test.com');
    await row.getByRole('button', { name: 'Manage TAs' }).click();
    await expect(page.getByText('TAs for e2e-instructor@test.com')).toBeVisible();
    await expect(page.getByText('Loading...')).not.toBeVisible({ timeout: 15000 });

    // Scope Add button to the modal to avoid matching "+ Add Instructor"
    const modal = page.locator('.fixed');
    await modal.getByPlaceholder('TA email').fill(TA_EMAIL);
    await modal.getByRole('button', { name: 'Add' }).click();

    await expect(modal.getByText(TA_EMAIL)).toBeVisible({ timeout: 10000 });
  });

  test('duplicate TA assignment shows error', async ({ page }) => {
    await login(page, ADMIN_EMAIL, '/admin/instructors');

    const row = await findInstructorRow(page, 'e2e-instructor@test.com');
    await row.getByRole('button', { name: 'Manage TAs' }).click();
    await expect(page.getByText('TAs for e2e-instructor@test.com')).toBeVisible();
    await expect(page.getByText('Loading...')).not.toBeVisible({ timeout: 15000 });
    await expect(page.getByText(TA_EMAIL)).toBeVisible();

    const modal = page.locator('.fixed');
    await modal.getByPlaceholder('TA email').fill(TA_EMAIL);
    await modal.getByRole('button', { name: 'Add' }).click();

    await expect(modal.getByText(/already assigned/i)).toBeVisible({ timeout: 10000 });
  });

  test('admin removes a TA from instructor', async ({ page }) => {
    await login(page, ADMIN_EMAIL, '/admin/instructors');

    const row = await findInstructorRow(page, 'e2e-instructor@test.com');
    await row.getByRole('button', { name: 'Manage TAs' }).click();
    await expect(page.getByText('TAs for e2e-instructor@test.com')).toBeVisible();
    await expect(page.getByText('Loading...')).not.toBeVisible({ timeout: 15000 });
    await expect(page.getByText(TA_EMAIL)).toBeVisible();

    page.on('dialog', (dialog) => dialog.accept());
    const modal = page.locator('.fixed');
    await modal.getByRole('button', { name: 'Remove' }).click();

    await expect(page.getByText(TA_EMAIL)).not.toBeVisible({ timeout: 10000 });
  });

  // ─── Courses Page ───

  test('admin navigates to all courses page', async ({ page }) => {
    const data = await getMainData();
    await login(page, ADMIN_EMAIL, '/admin/courses');
    await expect(page.getByText('All Courses')).toBeVisible();
    await expect(page.getByText(data.courseName)).toBeVisible();
  });

  test('admin clicks through to course detail', async ({ page }) => {
    const data = await getMainData();
    await login(page, ADMIN_EMAIL, '/admin/courses');

    await page.getByRole('link', { name: data.courseName }).click();
    await expect(page).toHaveURL(/\/instructor\/courses\//);
    await expect(page.getByText('E2E Section')).toBeVisible();
  });

  // ─── Admin Read Bypass ───

  test('admin can view any course without enrollment', async ({ page }) => {
    const data = await getMainData();
    await login(page, ADMIN_EMAIL, `/instructor/courses/${data.courseId}`);
    await expect(page.getByText('E2E Section')).toBeVisible();
    await expect(page.getByText('Sections')).toBeVisible();
  });

  test('admin can view any session dashboard', async ({ page }) => {
    const data = await getMainData();
    await login(page, ADMIN_EMAIL, `/instructor/sessions/${data.sessionId}/dashboard`);
    await expect(page.getByText('Live Dashboard')).toBeVisible();
    await expect(page.getByText('Team Alpha')).toBeVisible();
  });

  test('admin can view any session summary', async ({ page }) => {
    const data = await getMainData();
    await login(page, ADMIN_EMAIL, `/instructor/sessions/${data.sessionId}/summary`);
    await expect(page.getByText('Session Summary')).toBeVisible();
    await expect(page.getByText('Team Alpha')).toBeVisible();
  });

  // ─── Layout Navigation ───

  test('admin layout has correct nav links', async ({ page }) => {
    await login(page, ADMIN_EMAIL, '/admin');
    await expect(page.getByRole('link', { name: 'Dashboard' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Instructors' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Courses' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Instructor View' })).toBeVisible();
  });

  test('admin can navigate back to instructor view', async ({ page }) => {
    await login(page, ADMIN_EMAIL, '/admin');
    await page.getByRole('link', { name: 'Instructor View' }).click();
    await expect(page).toHaveURL(/\/instructor/);
  });
});
