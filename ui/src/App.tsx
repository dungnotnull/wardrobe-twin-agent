import React from 'react';
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAppStore } from './stores/appStore';
import { healthCheck } from './api';
import BodyScanPage from './pages/BodyScanPage';
import WardrobePage from './pages/WardrobePage';
import TryOnPage from './pages/TryOnPage';
import AdvisorPage from './pages/AdvisorPage';
import SettingsPage from './pages/SettingsPage';

const navItems = [
  { path: '/scan', label: '🧍 Body Scan', page: 'scan' as const },
  { path: '/wardrobe', label: '👔 Wardrobe', page: 'wardrobe' as const },
  { path: '/tryon', label: '👗 Try-On', page: 'tryon' as const },
  { path: '/advisor', label: '💡 Advisor', page: 'advisor' as const },
  { path: '/settings', label: '⚙️ Settings', page: 'settings' as const },
];

export default function App() {
  const { backendConnected, setBackendConnected, setCurrentPage } = useAppStore();

  // Check backend connection
  useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const res = await healthCheck();
      setBackendConnected(res.data?.status === 'ok');
      return res.data;
    },
    refetchInterval: 10000,
  });

  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col">
        {/* Header */}
        <header className="bg-primary-700 text-white px-6 py-3 flex items-center justify-between shadow-md">
          <h1 className="text-xl font-bold tracking-tight">👗 Wardrobe Twin Agent</h1>
          <span className={	ext-xs px-2 py-1 rounded-full }>
            {backendConnected ? '● Connected' : '○ Disconnected'}
          </span>
        </header>

        {/* Navigation */}
        <nav className="bg-gray-100 border-b border-gray-200 px-4 py-2 flex gap-1">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              onClick={() => setCurrentPage(item.page)}
              className={({ isActive }) =>
                px-4 py-2 rounded-lg text-sm font-medium transition-colors 
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* Main content */}
        <main className="flex-1 p-6 overflow-auto">
          {!backendConnected && (
            <div className="mb-4 p-3 bg-yellow-50 border border-yellow-300 rounded-lg text-yellow-800 text-sm">
              ⚠️ Backend not connected. Make sure the Python server is running on localhost:7331
            </div>
          )}
          <Routes>
            <Route path="/" element={<BodyScanPage />} />
            <Route path="/scan" element={<BodyScanPage />} />
            <Route path="/wardrobe" element={<WardrobePage />} />
            <Route path="/tryon" element={<TryOnPage />} />
            <Route path="/advisor" element={<AdvisorPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>

        {/* Footer */}
        <footer className="bg-gray-50 border-t border-gray-200 px-6 py-2 text-center text-xs text-gray-400">
          wardrobe-twin-agent v0.1.0 — Your data stays local
        </footer>
      </div>
    </BrowserRouter>
  );
}
