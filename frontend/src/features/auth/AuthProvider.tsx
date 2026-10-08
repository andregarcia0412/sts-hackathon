import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import type { User } from "@/domain/types";
import { AuthContext, useAuth } from "@/features/auth/authState";

/*
 * MOCK session: the signed-in user is kept in localStorage. With a real
 * back-end this becomes a token (cookie) and /me; the rest of the app only
 * uses useAuth()/useCurrentUser().
 */
const SESSION_KEY = "lei-do-bem:session";

const readSession = (): User | null => {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    return raw ? (JSON.parse(raw) as User) : null;
  } catch {
    return null;
  }
};

const writeSession = (user: User | null) => {
  try {
    if (user) localStorage.setItem(SESSION_KEY, JSON.stringify(user));
    else localStorage.removeItem(SESSION_KEY);
  } catch {
    // Without storage the session lasts until the tab is closed
  }
};

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(readSession);
  const queryClient = useQueryClient();

  const signIn = (next: User) => {
    writeSession(next);
    setUser(next);
  };

  const signOut = () => {
    writeSession(null);
    setUser(null);
    // Nothing from the previous user may leak into the next session
    queryClient.clear();
  };

  return <AuthContext value={{ user, signIn, signOut }}>{children}</AuthContext>;
};

/** Sends visitors without a session to the login, then back where they were */
export const RequireAuth = ({ children }: { children: ReactNode }) => {
  const { user } = useAuth();
  const location = useLocation();
  if (!user) {
    const next = `${location.pathname}${location.search}`;
    return <Navigate to={`/login?next=${encodeURIComponent(next)}`} replace />;
  }
  return children;
};
