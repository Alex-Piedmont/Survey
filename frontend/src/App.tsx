import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { AdminLayout } from './components/AdminLayout';
import { InstructorLayout } from './components/InstructorLayout';
import { LoginPage } from './pages/LoginPage';
import { AdminDashboardPage } from './pages/admin/AdminDashboardPage';
import { AdminInstructorsPage } from './pages/admin/AdminInstructorsPage';
import { AdminCoursesPage } from './pages/admin/AdminCoursesPage';
import { StudentSession } from './pages/StudentSession';
import { MySubmissions } from './pages/MySubmissions';
import { CoursesPage } from './pages/CoursesPage';
import { CourseDetailPage } from './pages/CourseDetailPage';
import { TemplateEditorPage } from './pages/TemplateEditorPage';
import { SessionCreatePage } from './pages/SessionCreatePage';
import { InstructorDashboardPage } from './pages/InstructorDashboardPage';
import { SessionSummaryPage } from './pages/SessionSummaryPage';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/s/:sessionId" element={<StudentSession />} />

            {/* Admin routes */}
            <Route
              path="/admin"
              element={
                <ProtectedRoute>
                  <AdminLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<AdminDashboardPage />} />
              <Route path="instructors" element={<AdminInstructorsPage />} />
              <Route path="courses" element={<AdminCoursesPage />} />
            </Route>

            {/* Instructor routes */}
            <Route
              path="/instructor"
              element={
                <ProtectedRoute>
                  <InstructorLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<CoursesPage />} />
              <Route path="courses/:courseId" element={<CourseDetailPage />} />
              <Route path="templates/:ptypeId" element={<TemplateEditorPage />} />
              <Route path="sessions/new" element={<SessionCreatePage />} />
              <Route path="sessions/:sessionId/dashboard" element={<InstructorDashboardPage />} />
              <Route path="sessions/:sessionId/summary" element={<SessionSummaryPage />} />
            </Route>

            <Route
              path="/me/submissions"
              element={
                <ProtectedRoute>
                  <MySubmissions />
                </ProtectedRoute>
              }
            />
            <Route path="/" element={<Navigate to="/instructor" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
