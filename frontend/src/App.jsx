import React, { useState, useEffect, useRef } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import { CaseEventProvider } from './context/CaseEventContext';
import Dashboard from './pages/Dashboard';
import CaseAnalysis from './pages/CaseAnalysis';
import CaseList from './pages/CaseList';
import FollowUp from './pages/FollowUp';
import FollowUpAttempts from './pages/FollowUpAttempts';
import Explainability from './pages/Explainability';
import Signals from './pages/Signals';
import Login from './components/Login';
import FollowUpAgent from './pages/FollowUpAgent';
import LifecycleTracking from './pages/LifecycleTracking';
import CiomsUploadPage from './pages/CiomsUploadPage';
import ReviewerDashboard from './pages/ReviewerDashboard';
import AuditTrail from './pages/AuditTrail';

/* ── Tab definitions ── */
const mainTabs = [
  { to: '/cioms-upload',            label: 'CIOMS Upload' },
  { to: '/case-analysis',           label: 'Case Repository' },
  { to: '/followup-attempts',       label: 'Follow-Up Tracker' },
  { to: '/reviewer',                label: 'Reviewer' },
  { to: '/lifecycle',               label: 'Lifecycle (F4)' },
  { to: '/signals',                 label: 'Severity Monitor (F6)' },
  { to: '/dashboard',               label: 'Dashboard' },
];
const adminTabs = [
  { to: '/audit-trail',             label: 'Audit Trail' },
  { to: '/explainability/185573372', label: 'Explainability (F5)' },
];

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

function AppContent() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [adminOpen, setAdminOpen] = useState(false);
  const adminRef = useRef(null);
  const navigate = useNavigate();
  const location = useLocation();

  // Close admin dropdown on outside click
  useEffect(() => {
    const handleClick = (e) => {
      if (adminRef.current && !adminRef.current.contains(e.target)) setAdminOpen(false);
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  useEffect(() => {
    if (location.pathname.startsWith('/followup-agent')) return;
    const token = localStorage.getItem('access_token');
    setIsAuthenticated(!!token);
    if (!token && location.pathname !== '/login') navigate('/login');
  }, [navigate, location]);

  const handleLoginSuccess = () => { setIsAuthenticated(true); navigate('/cioms-upload'); };
  const handleLogout = () => { localStorage.removeItem('access_token'); setIsAuthenticated(false); navigate('/login'); };

  const showNav = isAuthenticated && location.pathname !== '/login' && !location.pathname.startsWith('/followup-agent');

  const isTabActive = (to) =>
    location.pathname === to ||
    (to === '/case-analysis' && location.pathname === '/cases') ||
    (to === '/lifecycle' && location.pathname.startsWith('/lifecycle'));

  return (
    <CaseEventProvider>
      <div className="min-h-screen bg-[#f8f9fb]">
        {showNav && (
          <header className="sticky top-0 z-50 bg-white border-b border-[#E5E7EB]">
            <div className="max-w-[1440px] mx-auto flex items-center h-14 px-5">

              {/* ── Logo + Product ── */}
              <button onClick={() => navigate('/cioms-upload')} className="flex items-center gap-2.5 mr-8 shrink-0">
                <span className="flex items-center justify-center w-8 h-8 rounded-md bg-[#2563EB]/10">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <path d="M12 2L2 7l10 5 10-5-10-5z" fill="#2563EB" opacity=".85"/>
                    <path d="M2 17l10 5 10-5" stroke="#2563EB" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M2 12l10 5 10-5" stroke="#2563EB" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" opacity=".5"/>
                  </svg>
                </span>
                <div className="flex flex-col leading-none">
                  <span className="text-[13px] font-semibold text-[#111827]">SmartFU</span>
                  <span className="text-[10px] text-[#9CA3AF] mt-[1px]">Pharmacovigilance</span>
                </div>
              </button>

              {/* ── Separator ── */}
              <div className="w-px h-6 bg-[#E5E7EB] mr-6 shrink-0" />

              {/* ── Navigation tabs ── */}
              <nav className="flex items-center gap-1 flex-1 h-full">
                {mainTabs.map(({ to, label }) => {
                  const active = isTabActive(to);
                  return (
                    <button
                      key={to}
                      onClick={() => navigate(to)}
                      className={`
                        relative h-full flex items-center px-2.5 text-[13px] transition-colors duration-100
                        ${active
                          ? 'font-semibold text-[#111827]'
                          : 'font-medium text-[#6B7280] hover:text-[#111827]'
                        }
                      `}
                    >
                      {label}
                      {active && (
                        <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-[#2563EB] rounded-t-sm" />
                      )}
                    </button>
                  );
                })}

                <div className="flex-1" />

                {/* Admin dropdown — right-aligned */}
                <div className="relative h-full flex items-center" ref={adminRef}>
                  <button
                    onClick={() => setAdminOpen(v => !v)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium transition-colors ${
                      adminOpen || adminTabs.some(t => isTabActive(t.to))
                        ? 'bg-gray-100 text-[#111827]'
                        : 'text-[#9CA3AF] hover:text-[#6B7280] hover:bg-gray-50'
                    }`}
                  >
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
                    Admin
                    <svg className={`w-3 h-3 transition-transform ${adminOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
                  </button>

                  {adminOpen && (
                    <div className="absolute right-0 top-full mt-1 w-52 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50">
                      <p className="px-3 py-1.5 text-[9px] text-gray-400 uppercase tracking-wider font-semibold">Admin Tools</p>
                      {adminTabs.map(({ to, label }) => {
                        const active = isTabActive(to);
                        return (
                          <button
                            key={to}
                            onClick={() => { navigate(to); setAdminOpen(false); }}
                            className={`w-full text-left px-3 py-2 text-[13px] flex items-center gap-2.5 transition-colors ${
                              active
                                ? 'bg-blue-50 text-blue-700 font-semibold'
                                : 'text-gray-700 hover:bg-gray-50'
                            }`}
                          >
                            {label === 'Audit Trail' ? (
                              <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" /></svg>
                            ) : (
                              <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>
                            )}
                            {label}
                            {active && <span className="ml-auto w-1.5 h-1.5 rounded-full bg-blue-600" />}
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              </nav>

              {/* ── Right utilities ── */}
              <div className="flex items-center gap-4 ml-4 shrink-0">

                {/* Live indicator */}
                <span className="flex items-center gap-1.5">
                  <span className="w-[7px] h-[7px] rounded-full bg-emerald-500" />
                  <span className="text-xs text-[#6B7280]">Live</span>
                </span>

                <div className="w-px h-5 bg-[#E5E7EB]" />

                {/* User */}
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-full bg-[#2563EB] flex items-center justify-center">
                    <span className="text-[11px] font-semibold text-white leading-none">SC</span>
                  </div>
                  <div className="flex flex-col leading-none">
                    <span className="text-[12px] font-medium text-[#111827]">Swapnil C.</span>
                    <span className="text-[10px] text-[#9CA3AF] mt-[1px]">PV Analyst</span>
                  </div>
                </div>

                {/* Logout */}
                <button
                  onClick={handleLogout}
                  className="text-[12px] font-medium text-[#6B7280] hover:text-[#111827] transition-colors"
                >
                  Logout
                </button>
              </div>
            </div>
          </header>
        )}

        {/* Routes */}
        <Routes>
          <Route path="/followup-agent" element={<FollowUpAgent />} />
          <Route path="/login" element={<Login onLoginSuccess={handleLoginSuccess} />} />
          <Route path="/" element={<Navigate to="/cioms-upload" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/case-analysis" element={<CaseList />} />
          <Route path="/cioms-upload" element={<CiomsUploadPage />} />
          <Route path="/cases" element={<CaseList />} />
          <Route path="/cases/:caseId" element={<CaseAnalysis />} />
          <Route path="/followup-attempts" element={<FollowUpAttempts />} />
          <Route path="/follow-up/:caseId" element={<FollowUp />} />
          <Route path="/signals" element={<Signals />} />
          <Route path="/explainability/:caseId" element={<Explainability />} />
          <Route path="/lifecycle" element={<LifecycleTracking />} />
          <Route path="/lifecycle/:caseId" element={<LifecycleTracking />} />
          <Route path="/audit-trail" element={<AuditTrail />} />
          <Route path="/reviewer" element={<ReviewerDashboard />} />
          <Route path="/pdf-test" element={<Navigate to="/cioms-upload" replace />} />
        </Routes>
      </div>
    </CaseEventProvider>
  );
}

export default App;
