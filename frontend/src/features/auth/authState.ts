import { createContext, useContext } from "react";
import type { User } from "@/domain/types";

export interface AuthState {
  user: User | null;
  signIn: (user: User) => void;
  signOut: () => void;
}

export const AuthContext = createContext<AuthState | null>(null);

export const useAuth = () => {
  const state = useContext(AuthContext);
  if (!state) throw new Error("useAuth must be used inside AuthProvider");
  return state;
};

/** Current user on screens behind RequireAuth (never null there) */
export const useCurrentUser = (): User => {
  const { user } = useAuth();
  if (!user) throw new Error("useCurrentUser used outside a protected route");
  return user;
};
