import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import type { FormEvent } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import loginCorner from "@/assets/login-corner.svg";
import headquarters from "@/assets/login-bnb-sede.webp";
import logoBnb from "@/assets/logo-bnb.svg";
import { APP_DISCLAIMER, PRODUCT_NAME } from "@/config/app";
import type { User } from "@/domain/types";
import { useAuth } from "@/features/auth/authState";
import { paths } from "@/routes/paths";
import { listDemoUsers, login, registerUser } from "@/services/api";

/** Only same-app paths are accepted as "next", never another origin */
const safeNext = (next: string | null) =>
  next && next.startsWith("/") && !next.startsWith("//") ? next : paths.projects();

type Mode = "login" | "signup";

const pillInput =
  "h-12 w-full rounded-full border border-border-strong bg-surface px-4 text-base leading-5 placeholder:text-fg-muted focus-visible:outline-2 focus-visible:outline-offset-0 focus-visible:outline-action";

export const LoginPage = () => {
  const { user, signIn } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const next = safeNext(searchParams.get("next"));
  const [mode, setMode] = useState<Mode>("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const demoUsers = useQuery({ queryKey: ["demo-users"], queryFn: listDemoUsers });
  const enter = (signedIn: User) => {
    signIn(signedIn);
    navigate(next, { replace: true });
  };
  const signInMutation = useMutation({
    mutationFn: (credentials: { email: string; password: string }) =>
      login(credentials.email, credentials.password),
    onSuccess: enter,
  });
  const signUpMutation = useMutation({
    mutationFn: () => registerUser(name, email, password),
    onSuccess: enter,
  });

  if (user) return <Navigate to={next} replace />;

  const pending = signInMutation.isPending || signUpMutation.isPending;
  const error = mode === "login" ? signInMutation.error : signUpMutation.error;

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (mode === "login") signInMutation.mutate({ email, password });
    else signUpMutation.mutate();
  };

  const switchTo = (next: Mode) => {
    setMode(next);
    signInMutation.reset();
    signUpMutation.reset();
  };

  return (
    <div className="relative isolate flex min-h-dvh flex-col justify-center overflow-hidden bg-surface-sunken p-4 sm:p-10 lg:flex-row lg:items-center">
      {/* Background: BNB headquarters, a white glow behind the form and a dark fade at the bottom.
          Fixed to the window, so switching tabs (taller form) never resizes the photo */}
      <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
        <img src={headquarters} alt="" className="size-full object-cover object-left" />
        <div className="absolute -top-[308px] -right-[380px] h-[552px] w-[997px] rounded-full bg-white opacity-80 blur-[160px]" />
        <div className="absolute inset-x-0 bottom-0 h-[34%] bg-gradient-to-b from-transparent to-black" />
        <img src={loginCorner} alt="" width={306} height={371} className="absolute top-0 right-[-7%] max-lg:hidden" />
        <img src={loginCorner} alt="" width={306} height={371} className="absolute bottom-0 -left-[90px] rotate-180 max-lg:hidden" />
      </div>

      <div className="mx-auto flex w-full max-w-[508px] flex-col items-start gap-10 rounded-3xl max-lg:bg-white/75 max-lg:p-6 max-lg:backdrop-blur-md lg:mr-0 lg:ml-[56%] lg:w-auto">
        <img src={logoBnb} alt="Banco do Nordeste" width={202} height={72} className="h-auto w-[160px] p-1.5 sm:w-[223px]" />

        <h1 className="max-w-[329px] text-4xl leading-[1.3] font-semibold tracking-[-0.01em] text-fg sm:text-5xl sm:leading-[63px]">
          Seja muito bem-vindo ao <span className="text-action">{PRODUCT_NAME}</span>!
        </h1>

        <form
          onSubmit={handleSubmit}
          className="flex w-full flex-col gap-10 rounded-2xl bg-surface p-5 shadow-float"
        >
          <div className="flex flex-col gap-2">
            <div role="tablist" aria-label="Acesso" className="flex gap-3.5">
              {(
                [
                  ["signup", "Cadastro"],
                  ["login", "Login"],
                ] as const
              ).map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  role="tab"
                  aria-selected={mode === value}
                  onClick={() => switchTo(value)}
                  className={mode === value ? "btn-primary" : "btn-secondary"}
                >
                  {label}
                </button>
              ))}
            </div>
            <h2 className="text-[28px] font-semibold text-action">{mode === "login" ? "Login" : "Cadastro"}</h2>
          </div>

          <div className="flex flex-col gap-4">
            {mode === "signup" && (
              <div className="flex flex-col gap-2">
                <label htmlFor="signup-name" className="text-base leading-6 font-semibold text-fg-soft">
                  Nome
                </label>
                <input
                  id="signup-name"
                  autoComplete="name"
                  className={pillInput}
                  placeholder="Digite o seu nome..."
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </div>
            )}
            <div className="flex flex-col gap-2">
              <label htmlFor="login-email" className="text-base leading-6 font-semibold text-fg-soft">
                Email
              </label>
              <input
                id="login-email"
                type="email"
                autoComplete={mode === "login" ? "username" : "email"}
                className={pillInput}
                placeholder="Digite o seu e-mail..."
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="flex flex-col gap-2">
              <label htmlFor="login-password" className="text-base leading-6 font-semibold text-fg-soft">
                Senha
              </label>
              <input
                id="login-password"
                type="password"
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                className={pillInput}
                placeholder="Digite a sua senha..."
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            {error && (
              <p role="alert" className="text-sm text-danger">
                {error.message}
              </p>
            )}
          </div>

          <div className="flex flex-col gap-3">
            <button type="submit" className="btn-primary w-full" disabled={pending}>
              {pending ? "Entrando…" : mode === "login" ? "Entrar" : "Criar conta e entrar"}
            </button>
            <p className="text-center text-xs leading-5 text-fg-muted">
              Demonstração (qualquer senha): entre como{" "}
              {demoUsers.data?.map((demo, i, all) => (
                <span key={demo.id}>
                  <button
                    type="button"
                    className="btn-link"
                    disabled={pending}
                    onClick={() => signInMutation.mutate({ email: demo.email, password: "demo" })}
                  >
                    {demo.name}
                  </button>
                  {i < all.length - 2 ? ", " : i === all.length - 2 ? " ou " : "."}
                </span>
              ))}
            </p>
          </div>
        </form>
      </div>

      <p className="mt-6 text-center text-xs text-white/85 lg:absolute lg:inset-x-0 lg:bottom-4 lg:mt-0 lg:px-4">
        {APP_DISCLAIMER}
      </p>
    </div>
  );
};
