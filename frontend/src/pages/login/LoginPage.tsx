import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import type { FormEvent } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import logoBnb from "@/assets/logo-bnb.svg";
import { KeyboardArrowRightIcon } from "@/components/icons/MaterialIcons";
import { Tag } from "@/components/ui/Tag";
import { APP_DISCLAIMER, APP_NAME } from "@/config/app";
import type { Tone } from "@/domain/qualitative";
import type { User } from "@/domain/types";
import { useAuth } from "@/features/auth/authState";
import { initials } from "@/lib/format";
import { paths } from "@/routes/paths";
import { listDemoUsers, login } from "@/services/api";

/** Only same-app paths are accepted as "next", never another origin */
const safeNext = (next: string | null) =>
  next && next.startsWith("/") && !next.startsWith("//") ? next : paths.projects();

const HIGHLIGHTS: { tone: Tone; text: string }[] = [
  { tone: "positive", text: "Grafo de evidências por critério, regra e documento" },
  { tone: "attention", text: "Divergências apontadas, nunca resolvidas pelo sistema" },
  { tone: "neutral", text: "A decisão é sempre do analista, com trilha completa" },
];

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
    <div className="relative isolate flex min-h-dvh items-center justify-center overflow-hidden bg-canvas p-4 sm:p-10">
      {/* Same background glows as the app */}
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute -top-60 -left-96 size-[594px] rounded-full bg-action opacity-60 blur-[180px]" />
        <div className="absolute -right-96 -bottom-80 size-[594px] rounded-full bg-brand-orange opacity-60 blur-[180px]" />
      </div>

      <div className="grid w-full max-w-5xl items-center gap-10 lg:grid-cols-[1fr_440px]">
        <section className="flex flex-col gap-6">
          <img src={logoBnb} alt="Banco do Nordeste" width={101} height={36} />
          <div className="flex flex-col gap-3">
            <p className="caps-label text-accent">{APP_NAME}</p>
            <h1 className="max-w-lg text-[28px] leading-9 font-semibold sm:text-[32px] sm:leading-10">
              Análise preliminar de enquadramento na Lei do Bem, com cada nota rastreável até a
              evidência.
            </h1>
          </div>
          <ul className="flex flex-col gap-3 text-sm leading-5 text-fg-secondary">
            {HIGHLIGHTS.map(({ tone, text }) => (
              <li key={text} className="flex items-center gap-3">
                <Tag tone={tone} label={text} iconOnly />
                {text}
              </li>
            ))}
          </ul>
        </section>

        <div className="flex flex-col gap-4">
          <form
            onSubmit={handleSubmit}
            className="flex flex-col gap-5 rounded-2xl border border-border bg-white/80 p-6 shadow-card sm:p-8"
          >
            <div className="flex flex-col gap-1">
              <h2 className="text-xl leading-6 font-semibold">Entrar</h2>
              <p className="text-sm leading-5 text-fg-muted">
                Cada analista vê e organiza os próprios projetos.
              </p>
            </div>
            <div className="flex flex-col gap-2">
              <label htmlFor="login-email" className="label mb-0">
                E-mail
              </label>
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
            <div className="flex flex-col gap-2">
              <label htmlFor="login-password" className="label mb-0">
                Senha
              </label>
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
              {signInMutation.isPending ? "Entrando…" : "Entrar"}
            </button>
          </form>

          <section className="flex flex-col gap-3 rounded-2xl border border-dashed border-border-strong bg-white/50 p-4">
            <div>
              <h2 className="caps-label text-fg-muted">Ambiente de demonstração</h2>
              <p className="text-xs leading-4 text-fg-muted">
                Login simulado: escolha um analista fictício (qualquer senha funciona).
              </p>
            </div>
            <ul className="flex flex-col gap-2">
              {demoUsers.data?.map((demo) => (
                <li key={demo.id}>
                  <button
                    type="button"
                    className="flex w-full items-center gap-3 rounded-full border border-border-strong bg-surface py-1.5 pr-4 pl-1.5 text-left transition-colors hover:border-action hover:bg-accent-soft disabled:opacity-50"
                    disabled={signInMutation.isPending}
                    onClick={() => signInMutation.mutate({ email: demo.email, password: "demo" })}
                  >
                    <span
                      aria-hidden
                      className="flex size-9 shrink-0 items-center justify-center rounded-full bg-surface-sunken text-xs font-semibold text-fg-secondary"
                    >
                      {initials(demo.name)}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm leading-5 font-semibold">{demo.name}</span>
                      <span className="block truncate text-xs leading-4 text-fg-muted">{demo.email}</span>
                    </span>
                    <KeyboardArrowRightIcon className="size-5 shrink-0 text-fg-secondary" />
                  </button>
                </li>
              ))}
            </ul>
          </section>

          <p className="text-center text-xs leading-4 text-fg-muted">{APP_DISCLAIMER}</p>
        </div>
      </div>
    </div>
  );
};
