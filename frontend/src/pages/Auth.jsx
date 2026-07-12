import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card } from "@/components/ui/card";
import { PawPrint, GoogleLogo } from "@phosphor-icons/react";
import { toast } from "sonner";

function formatApiErrorDetail(detail) {
  if (detail == null) return "Qualcosa è andato storto. Riprova.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail.map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e))).join(" ");
  if (detail && typeof detail.msg === "string") return detail.msg;
  return String(detail);
}

export default function Auth() {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [resetInfo, setResetInfo] = useState(null);
  const { setUser } = useAuth();
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      if (mode === "forgot") {
        const { data } = await api.post("/auth/forgot-password", { email });
        setResetInfo(data);
        return;
      }
      const endpoint = mode === "login" ? "/auth/login" : "/auth/register";
      const payload = mode === "login" ? { email, password } : { email, password, name };
      const { data } = await api.post(endpoint, payload);
      setUser(data.user);
      navigate("/dashboard", { state: { user: data.user } });
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail) || err.message);
    } finally {
      setBusy(false);
    }
  };

  const googleLogin = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + "/dashboard";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <div className="min-h-screen grain flex items-center justify-center p-4 bg-background">
      <div className="w-full max-w-5xl grid lg:grid-cols-2 gap-8 items-center relative z-10">
        <div className="hidden lg:block">
          <div className="flex items-center gap-2 mb-6">
            <PawPrint size={40} weight="duotone" className="text-primary" />
            <span className="font-heading font-extrabold text-3xl tracking-tight">PawCare</span>
          </div>
          <h1 className="font-heading text-4xl xl:text-5xl font-extrabold tracking-tighter leading-tight mb-4">
            La salute del tuo animale, sempre sotto controllo.
          </h1>
          <p className="text-muted-foreground text-lg leading-relaxed mb-8 max-w-md">
            Tieni traccia di visite, vaccini e trattamenti. Ricevi promemoria e consigli su misura basati su età e razza, con l'aiuto dell'AI.
          </p>
          <div className="rounded-xl overflow-hidden border border-border max-w-md">
            <img
              src="https://images.pexels.com/photos/5748620/pexels-photo-5748620.jpeg"
              alt="Proprietario con cane"
              className="w-full h-64 object-cover"
            />
          </div>
        </div>

        <Card className="p-8 border-border">
          <div className="lg:hidden flex items-center gap-2 mb-6 justify-center">
            <PawPrint size={32} weight="duotone" className="text-primary" />
            <span className="font-heading font-extrabold text-2xl">PawCare</span>
          </div>
          <h2 className="font-heading text-2xl font-bold mb-1">
            {mode === "login" ? "Bentornato" : mode === "register" ? "Crea il tuo account" : "Recupera la password"}
          </h2>
          <p className="text-muted-foreground text-sm mb-6">
            {mode === "login" ? "Accedi per gestire i tuoi animali" : mode === "register" ? "Inizia a prenderti cura dei tuoi amici a quattro zampe" : "Inserisci la tua email per ricevere il link di reset"}
          </p>

          {mode !== "forgot" && (
            <>
          <Button
            type="button"
            variant="outline"
            className="w-full rounded-full mb-4 gap-2"
            onClick={googleLogin}
            data-testid="google-login-button"
          >
            <GoogleLogo size={20} weight="bold" />
            Continua con Google
          </Button>

          <div className="flex items-center gap-3 my-4">
            <div className="h-px bg-border flex-1" />
            <span className="text-xs text-muted-foreground uppercase tracking-wider">oppure</span>
            <div className="h-px bg-border flex-1" />
          </div>
            </>
          )}

          {mode === "forgot" && resetInfo ? (
            <div className="space-y-4" data-testid="reset-link-box">
              <div className="rounded-lg border border-primary/30 bg-primary/5 p-4 text-sm">
                {resetInfo.reset_url ? (
                  <>
                    <p className="font-medium text-foreground mb-2">Link di reset generato (modalità test):</p>
                    <a href={resetInfo.reset_url} className="text-primary break-all underline" data-testid="reset-link">{resetInfo.reset_url}</a>
                    <p className="text-xs text-muted-foreground mt-2">In produzione questo link verrà inviato via email. Valido 1 ora.</p>
                  </>
                ) : (
                  <p className="text-muted-foreground">{resetInfo.message}</p>
                )}
              </div>
              <Button type="button" variant="outline" className="w-full rounded-full" onClick={() => { setMode("login"); setResetInfo(null); }} data-testid="back-to-login">Torna al login</Button>
            </div>
          ) : (
          <form onSubmit={submit} className="space-y-4">
            {mode === "register" && (
              <div>
                <Label htmlFor="name">Nome</Label>
                <Input id="name" data-testid="name-input" value={name} onChange={(e) => setName(e.target.value)} required className="mt-1" placeholder="Mario Rossi" />
              </div>
            )}
            <div>
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" data-testid="email-input" value={email} onChange={(e) => setEmail(e.target.value)} required className="mt-1" placeholder="mario@esempio.it" />
            </div>
            {mode !== "forgot" && (
              <div>
                <div className="flex items-center justify-between">
                  <Label htmlFor="password">Password</Label>
                  {mode === "login" && (
                    <button type="button" className="text-xs text-primary hover:underline" onClick={() => { setMode("forgot"); setResetInfo(null); }} data-testid="forgot-password-link">Password dimenticata?</button>
                  )}
                </div>
                <Input id="password" type="password" data-testid="password-input" value={password} onChange={(e) => setPassword(e.target.value)} required className="mt-1" placeholder="••••••••" />
              </div>
            )}
            <Button type="submit" disabled={busy} className="w-full rounded-full" data-testid="submit-auth-button">
              {busy ? "Attendere..." : mode === "login" ? "Accedi" : mode === "register" ? "Registrati" : "Invia link di reset"}
            </Button>
          </form>
          )}

          <p className="text-center text-sm text-muted-foreground mt-6">
            {mode === "forgot" ? (
              <button type="button" className="text-primary font-semibold hover:underline" onClick={() => { setMode("login"); setResetInfo(null); }} data-testid="toggle-auth-mode">Torna al login</button>
            ) : (
              <>
                {mode === "login" ? "Non hai un account?" : "Hai già un account?"}{" "}
                <button
                  type="button"
                  className="text-primary font-semibold hover:underline"
                  onClick={() => setMode(mode === "login" ? "register" : "login")}
                  data-testid="toggle-auth-mode"
                >
                  {mode === "login" ? "Registrati" : "Accedi"}
                </button>
              </>
            )}
          </p>
        </Card>
      </div>
    </div>
  );
}
