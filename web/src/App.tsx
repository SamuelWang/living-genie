import { BrowserRouter } from 'react-router';
import { AuthProvider } from '@/context/AuthProvider';
import { AppRoutes } from '@/routes/AppRoutes';

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
