import { createContext, useContext, useState, useCallback } from 'react';
import { authApi } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem('caep_user');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });

  const [token, setToken] = useState(() => {
    try {
      return localStorage.getItem('caep_token');
    } catch {
      return null;
    }
  });

  const isVerified = user ? user.is_verified === true : false;

  const login = useCallback(async (email, password) => {
    const data = await authApi.login(email, password);
    setUser(data.user);
    setToken(data.access_token);
    localStorage.setItem('caep_user', JSON.stringify(data.user));
    localStorage.setItem('caep_token', data.access_token);
    return data;
  }, []);

  const setVerified = useCallback((verifiedUser) => {
    setUser(verifiedUser);
    localStorage.setItem('caep_user', JSON.stringify(verifiedUser));
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('caep_user');
    localStorage.removeItem('caep_token');
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, login, setVerified, logout, isAuthenticated: !!user, isVerified }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
