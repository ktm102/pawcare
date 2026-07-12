import React, { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card } from "@/components/ui/card";
import { PawPrint, CheckCircle } from "@phosphor-icons/react";
import { toast } from "sonner";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get("token");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    if (password.length < 6) { toast.error("La password deve avere almeno 6 caratteri"); return; }
    if (password !== confirm) { toast.error("Le password non coincidono"); return; }
    setBusy(true);
    try {
      await api.post("/auth/reset-password", { token, new_password: password });
      setDone(true);
      toast.success("Password aggiornata!");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Impossibile reimpostare la password");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen grain flex items-center justify-center p-4 bg-background">
      <Card className="w-full max-w-md p-8 border-border relative z-10">
        <div className="flex items-center gap-2 mb-6 justify-center">
          <PawPrint size={32} weight="duotone" className="text-primary" />
          <span className="font-heading font-extrabold text-2xl">PawCare</span>
        </div>

        {!token ? (
          <div className="text-center">
            <p className="text-muted-foreground mb-4">Link non valido o mancante.</p>
            <Button className="rounded-full" onClick={() => navigate("/login")} data-testid="go-login-button">Vai al login</Button>
          </div>
        ) : done ? (
          <div className="text-center" data-testid="reset-success">
            <CheckCircle size={48} weight="duotone" className="text-primary mx-auto mb-3" />
            <h2 className="font-heading text-xl font-bold mb-1">Password aggiornata</h2>
            <p className="text-muted-foreground text-sm mb-5">Ora puoi accedere con la nuova password.</p>
            <Button className="rounded-full w-full" onClick={() => navigate("/login")} data-testid="go-login-button">Accedi</Button>
          </div>
        ) : (
          <>
            <h2 className="font-heading text-2xl font-bold mb-1">Nuova password</h2>
            <p className="text-muted-foreground text-sm mb-6">Scegli una nuova password per il tuo account.</p>
            <form onSubmit={submit} className="space-y-4">
              <div>
                <Label htmlFor="password">Nuova password</Label>
                <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required className="mt-1" placeholder="••••••••" data-testid="new-password-input" />
              </div>
              <div>
                <Label htmlFor="confirm">Conferma password</Label>
                <Input id="confirm" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required className="mt-1" placeholder="••••••••" data-testid="confirm-password-input" />
              </div>
              <Button type="submit" disabled={busy} className="w-full rounded-full" data-testid="reset-submit-button">
                {busy ? "Salvataggio..." : "Reimposta password"}
              </Button>
            </form>
          </>
        )}
      </Card>
    </div>
  );
}
