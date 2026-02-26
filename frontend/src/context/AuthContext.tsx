import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';

interface AuthState {
  token: string | null;
  email: string | null;
  isAdmin: boolean;
  isInstructor: boolean;
}

function parseJwtClaims(token: string): { isAdmin: boolean; isInstructor: boolean } {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return {
      isAdmin: !!payload.is_admin,
      isInstructor: !!payload.is_instructor,
    };
  } catch {
    return { isAdmin: false, isInstructor: false };
  }
}

interface AuthContextType extends AuthState {
  login: (token: string, email: string) => void;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<AuthState>(() => {
    const token = localStorage.getItem('token');
    const claims = token ? parseJwtClaims(token) : { isAdmin: false, isInstructor: false };
    return {
      token,
      email: localStorage.getItem('email'),
      ...claims,
    };
  });

  const login = useCallback((token: string, email: string) => {
    localStorage.setItem('token', token);
    localStorage.setItem('email', email);
    const claims = parseJwtClaims(token);
    setAuth({ token, email, ...claims });
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('token');
    localStorage.removeItem('email');
    setAuth({ token: null, email: null, isAdmin: false, isInstructor: false });
  }, []);

  return (
    <AuthContext.Provider value={{ ...auth, login, logout, isAuthenticated: !!auth.token }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
