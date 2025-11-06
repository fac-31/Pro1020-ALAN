import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import SignUp from '../pages/SignUp';
import SandBox from '../pages/Sandbox/SandBox';
import Chat from '../pages/Sandbox/Chat';
import Upload from '../pages/Sandbox/Upload';
import Search from '../pages/Sandbox/Search';
import Database from '../pages/Sandbox/Database';

const router = createBrowserRouter([
  {
    path: '/',
    element: <SignUp />,
  },
  {
    path: '/sandbox',
    element: <SandBox />,
  },
  {
    path: '/sandbox/chat',
    element: <Chat />,
  },
  {
    path: '/sandbox/upload',
    element: <Upload />,
  },
  {
    path: 'sandbox/search',
    element: <Search />,
  },
  {
    path: 'sandbox/db', 
    element: <Database />
  }
]);

export default function Router() {
  return <RouterProvider router={router} />;
}
