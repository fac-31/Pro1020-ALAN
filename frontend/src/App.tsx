import { RouterProvider, createBrowserRouter } from 'react-router';
import Signup from './pages/Signup';
import { AdminPortal } from './pages/AdminPortal';
import { NotFound } from './pages/NotFound';

// Define routes
const router = createBrowserRouter([
  { path: '/', element: <Signup /> },
  { path: '/admin', element: <AdminPortal /> },
  { path: '*', element: <NotFound /> },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
