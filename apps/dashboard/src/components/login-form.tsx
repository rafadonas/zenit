"use client";

import { type FormEvent, useState } from "react";

interface LoginFormProps {
  returnTo: string;
}

export function LoginForm({ returnTo }: LoginFormProps) {
  const [submitting, setSubmitting] = useState(false);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    if (submitting) {
      event.preventDefault();
      return;
    }
    setSubmitting(true);
  }

  return (
    <form
      action="/api/auth/session"
      aria-busy={submitting}
      className="login-form"
      method="post"
      onSubmit={handleSubmit}
    >
      <input name="return_to" type="hidden" value={returnTo} />
      <label htmlFor="email">E-mail</label>
      <input
        autoComplete="username"
        autoFocus
        disabled={submitting}
        id="email"
        maxLength={320}
        name="email"
        placeholder="nome@empresa.com"
        required
        type="email"
      />
      <label htmlFor="password">Senha</label>
      <input
        autoComplete="current-password"
        disabled={submitting}
        id="password"
        maxLength={1024}
        name="password"
        required
        type="password"
      />
      <button
        aria-describedby="login-submit-status"
        className="primary-button"
        disabled={submitting}
        type="submit"
      >
        {submitting ? "Entrando…" : "Entrar"}
      </button>
      <span
        aria-live="polite"
        className="login-submit-status"
        id="login-submit-status"
        role="status"
      >
        {submitting ? "Validando o acesso e carregando seu perfil." : ""}
      </span>
    </form>
  );
}
