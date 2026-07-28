import { Navigate, Route, Routes } from 'react-router';
import { RootLayout } from '@/components/layout/RootLayout';
import { ProtectedRoute } from './ProtectedRoute';
import { LoginPage } from '@/pages/LoginPage';
import { RegisterPage } from '@/pages/RegisterPage';
import { DiaryListPage } from '@/pages/DiaryListPage';
import { DiaryCreatePage } from '@/pages/DiaryCreatePage';
import { DiaryDetailPage } from '@/pages/DiaryDetailPage';
import { DiaryEditPage } from '@/pages/DiaryEditPage';
import { GenieListPage } from '@/pages/GenieListPage';
import { GenieConversationPage } from '@/pages/GenieConversationPage';
import { NotFoundPage } from '@/pages/NotFoundPage';

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<RootLayout />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/" element={<Navigate to="/diaries" replace />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/diaries" element={<DiaryListPage />} />
          <Route path="/diaries/new" element={<DiaryCreatePage />} />
          <Route path="/diaries/:id" element={<DiaryDetailPage />} />
          <Route path="/diaries/:id/edit" element={<DiaryEditPage />} />
          <Route path="/genie" element={<GenieListPage />} />
          <Route path="/genie/new" element={<GenieConversationPage />} />
          <Route path="/genie/:id" element={<GenieConversationPage />} />
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
