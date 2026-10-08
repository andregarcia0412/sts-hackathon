import { useMutation, useQuery } from "@tanstack/react-query";
import { LogIn, Scale, UserRound } from "lucide-react";
import { useState } from "react";
import type { FormEvent } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { APP_DISCLAIMER, APP_NAME } from "@/config/app";
import type { User } from "@/domain/types";
import { useAuth } from "@/features/auth/authState";
import { paths } from "@/routes/paths";
import { listDemoUsers, login } from "@/services/api";

/** Only same-app paths are accepted as "next", never another origin */
const safeNext = (next: string | null) =>
  next && next.startsWith("/") && !next.startsWith("//") ? next : paths.projects();

export const LoginPage = () => {
  const { user, signIn } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const next = safeNext(searchParams.get("next"));
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const demoUsers = useQuery({ queryKey: ["demo-users"], queryFn: listDemoUsers });
  const signInMutation = useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) => login(email, password),
    onSuccess: (signedIn: User) => {
      signIn(signedIn);
      navigate(next, { replace: true });
    },
  });

  if (user) return <Navigate to={next} replace />;

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    signInMutation.mutate({ email, password });
  };

  return (
    <div className="flex min-h-dvh items-center justify-center bg-canvas p-4">
      <div className="w-full max-w-md space-y-6">
        <div className="flex items-center justify-center gap-2 text-lg font-semibold">
          <Scale className="size-6 text-accent" aria-hidden />
          {APP_NAME}
        </div>

        <form
          onSubmit={handleSubmit}
          className="space-y-4 rounded-xl border border-border bg-surface p-6 shadow-sm"
        >
          <div>
            <h1 className="text-xl font-semibold">Entrar</h1>
            <p className="text-sm text-fg-muted">Cada analista vê e organiza os próprios projetos.</p>
          </div>
          <div>
            <label htmlFor="login-email" className="label">E-mail</label>
            <input
              id="login-email"
              type="email"
              autoComplete="username"
              className="input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div>
            <label htmlFor="login-password" className="label">Senha</label>
            <input
              id="login-password"
              type="password"
              autoComplete="current-password"
              className="input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          {signInMutation.isError && (
            <p role="alert" className="text-sm text-danger">
              {signInMutation.error.message}
            </p>
          )}
          <button type="submit" className="btn-primary w-full" disabled={signInMutation.isPending}>
            <LogIn className="size-4" aria-hidden />
            {signInMutation.isPending ? "Entrando…" : "Entrar"}
          </button>
        </form>

        <section className="space-y-2 rounded-xl border border-dashed border-border-strong p-4">
          <h2 className="text-sm font-semibold">Ambiente de demonstração</h2>
          <p className="text-xs text-fg-muted">
            Login simulado: escolha um analista fictício (qualquer senha funciona).
          </p>
          <ul className="space-y-1.5">
            {demoUsers.data?.map((demo) => (
              <li key={demo.id}>
                <button
                  type="button"
                  className="btn-secondary w-full justify-start"
                  disabled={signInMutation.isPending}
                  onClick={() => signInMutation.mutate({ email: demo.email, password: "demo" })}
                >
                  <UserRound className="size-4 text-fg-muted" aria-hidden />
                  <span className="flex-1 text-left">{demo.name}</span>
                  <span className="text-xs font-normal text-fg-muted">{demo.email}</span>
                </button>
              </li>
            ))}
          </ul>
        </section>

        <p className="text-center text-xs text-fg-muted">{APP_DISCLAIMER}</p>
      </div>
    </div>
  );
};
