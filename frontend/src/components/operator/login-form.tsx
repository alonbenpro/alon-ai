"use client";

import { useState, type FormEvent } from "react";

export function LoginForm() {
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
        cache: "no-store",
      });
      if (response.ok) {
        setPassword("");
        window.location.replace("/");
        return;
      }
      setError(response.status === 401 || response.status === 403 ? "The password was not accepted." : "Access could not be verified. Try again.");
    } catch {
      setError("Access could not be verified. Check your connection and try again.");
    } finally {
      setBusy(false);
    }
  };

  return <form className="login-form" onSubmit={(event) => void submit(event)}>
    <label htmlFor="operator-password">Operator password</label>
    <input id="operator-password" name="password" type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} aria-invalid={!!error} aria-describedby={error ? "login-error" : undefined} />
    {error && <p id="login-error" className="form-error" role="alert">{error}</p>}
    <button type="submit" disabled={busy || !password}>{busy ? "Verifying…" : "Sign in"}<span aria-hidden="true">↗</span></button>
  </form>;
}
