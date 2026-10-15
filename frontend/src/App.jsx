import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Navbar from './components/Navbar';
import HomePage from './pages/HomePage';
import EventsPage from './pages/EventsPage';
import EventDetailPage from './pages/EventDetailPage';
import AuthPage from './pages/AuthPage';
import OrganizerDashboard from './pages/OrganizerDashboard';
import RegistrationPage from './pages/RegistrationPage';
import CreateEventPage from './pages/CreateEventPage';
import MyEventsPage from './pages/MyEventsPage';

import './App.css';

// Protected Route wrapper
function ProtectedRoute({ children, role }) {
  const { user, isAuthenticated } = useAuth();
  
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (role && user?.role !== role) return <Navigate to="/" replace />;
  
  return children;
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="app-container" style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
          <Navbar />
          <main className="main-content" style={{ flexGrow: 1 }}>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/login" element={<AuthPage />} />
              <Route path="/events" element={<EventsPage />} />
              <Route path="/events/:id" element={<EventDetailPage />} />
              <Route path="/events/:id/register" element={
                <ProtectedRoute>
                  <RegistrationPage />
                </ProtectedRoute>
              } />
              <Route path="/my-events" element={
                <ProtectedRoute>
                  <MyEventsPage />
                </ProtectedRoute>
              } />
              
              {/* Protected Organizer Routes */}
              <Route 
                path="/organizer/create" 
                element={
                  <ProtectedRoute role="ORGANIZER">
                    <CreateEventPage />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/organizer/edit/:eventId" 
                element={
                  <ProtectedRoute role="ORGANIZER">
                    <CreateEventPage />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/organizer/events/:id" 
                element={
                  <ProtectedRoute role="ORGANIZER">
                    <EventDetailPage isOrganizerView={true} />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/organizer/*" 
                element={
                  <ProtectedRoute role="ORGANIZER">
                    <OrganizerDashboard />
                  </ProtectedRoute>
                } 
              />
            </Routes>
          </main>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;
