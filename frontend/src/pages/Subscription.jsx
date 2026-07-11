import React, { useEffect, useState, useCallback } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { Crown, Check, Sparkle, FileText, ChatCircleDots, CalendarCheck } from "@phosphor-icons/react";

const perks = [
  { icon: ChatCircleDots, text: "Domande AI illimitate (chat e consigli)" },
  { icon: FileText, text: "Allegati documenti medici illimitati" },
  { icon: Sparkle, text: "Tutte le funzioni sbloccate" },
  { icon: CalendarCheck, text: "Promemoria e calendario completi" },
];

export default function Subscription() {
  const [sub, setSub] = useState(null);
  const [busy, setBusy] = useState(null);
  const [polling, setPolling] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  const load = useCallback(async () => {
    const { data } = await api.get("/subscription/status");
    setSub(data);
  }, []);
  useEffect(() => { load(); }, [load]);

  const pollStatus = useCallback(async (sessionId, attempts = 0) => {
    if (attempts >= 6) { setPolling(false); toast.error("Verifica pagamento scaduta. Riprova o controlla più tardi."); return; }
    try {
      const { data } = await api.get(`/subscription/checkout/status/${sessionId}`);
      if (data.payment_status === "paid") {
        setPolling(false);
        toast.success("Pagamento riuscito! Sei ora Premium 🎉");
        await load();
        navigate("/abbonamento", { replace: true });
        return;
      }
      if (data.status === "expired") { setPolling(false); toast.error("Sessione di pagamento scaduta."); return; }
      setTimeout(() => pollStatus(sessionId, attempts + 1), 2000);
    } catch (e) {
      setPolling(false);
      toast.error("Errore nella verifica del pagamento.");
    }
  }, [load, navigate]);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const sessionId = params.get("session_id");
    if (sessionId) {
      setPolling(true);
      pollStatus(sessionId);
    }
  }, [location.search, pollStatus]);

  const buy = async (packageId) => {
    setBusy(packageId);
    try {
      const { data } = await api.post("/subscription/checkout", { package_id: packageId, origin_url: window.location.origin });
      window.location.href = data.url;
    } catch (e) {
      toast.error("Impossibile avviare il pagamento");
      setBusy(null);
    }
  };

  const startTrial = async () => {
    setBusy("trial");
    try {
      await api.post("/subscription/trial");
      toast.success("Prova gratuita di 7 giorni attivata! 🎉");
      await load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Impossibile attivare la prova");
    } finally {
      setBusy(null);
    }
  };

  const isPremium = sub?.premium;

  return (
    <div className="space-y-8 max-w-4xl">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <Crown size={24} weight="duotone" className="text-accent" />
          <p className="text-xs tracking-[0.2em] uppercase font-bold text-muted-foreground">Abbonamento</p>
        </div>
        <h1 className="font-heading text-3xl sm:text-4xl font-extrabold tracking-tighter">PawCare Premium</h1>
      </div>

      {polling && (
        <Card className="p-4 border-primary/30 bg-primary/5 text-sm" data-testid="payment-polling">Verifica del pagamento in corso...</Card>
      )}

      {isPremium ? (
        <Card className="p-6 border-primary/40 bg-primary/5" data-testid="premium-active">
          <div className="flex items-center gap-3">
            <div className="h-12 w-12 rounded-xl bg-primary/15 flex items-center justify-center"><Crown size={26} weight="fill" className="text-accent" /></div>
            <div>
              <h2 className="font-heading text-xl font-bold">Sei Premium 🎉</h2>
              <p className="text-sm text-muted-foreground">Attivo fino al {new Date(sub.premium_until).toLocaleDateString("it-IT", { day: "numeric", month: "long", year: "numeric" })}</p>
            </div>
          </div>
          <p className="text-sm text-muted-foreground mt-4">L'accesso Premium non si rinnova automaticamente: puoi rinnovarlo quando vuoi da questa pagina prima della scadenza. Nessun addebito a sorpresa.</p>
        </Card>
      ) : (
        <>
          <Card className="p-6 border-border">
            <h2 className="font-heading text-lg font-bold mb-4">Cosa include Premium</h2>
            <div className="grid sm:grid-cols-2 gap-3">
              {perks.map((p, i) => {
                const Icon = p.icon;
                return (
                  <div key={i} className="flex items-center gap-3">
                    <div className="h-9 w-9 rounded-lg bg-primary/10 flex items-center justify-center shrink-0"><Icon size={18} weight="duotone" className="text-primary" /></div>
                    <span className="text-sm">{p.text}</span>
                  </div>
                );
              })}
            </div>
            <p className="text-xs text-muted-foreground mt-4">Nel piano gratuito: fino a {sub?.ai_limit ?? 5} domande AI al giorno e nessun allegato documenti.</p>
          </Card>

          <div className="grid sm:grid-cols-2 gap-4">
            <Card className="p-6 border-border flex flex-col" data-testid="plan-monthly">
              <p className="text-xs tracking-[0.15em] uppercase font-bold text-muted-foreground">Mensile</p>
              <p className="font-heading text-4xl font-extrabold mt-2">€7,99<span className="text-base font-normal text-muted-foreground">/mese</span></p>
              <p className="text-sm text-muted-foreground mt-1">Accesso Premium per 30 giorni.</p>
              <Button className="rounded-full mt-6 gap-2" disabled={busy} onClick={() => buy("monthly")} data-testid="buy-monthly-button">
                <Crown size={16} weight="fill" /> {busy === "monthly" ? "Attendere..." : "Attiva mensile"}
              </Button>
            </Card>

            <Card className="p-6 border-accent/40 bg-accent/5 flex flex-col relative" data-testid="plan-yearly">
              <Badge className="absolute top-4 right-4 bg-accent text-accent-foreground">Risparmi il 17%</Badge>
              <p className="text-xs tracking-[0.15em] uppercase font-bold text-muted-foreground">Annuale</p>
              <p className="font-heading text-4xl font-extrabold mt-2">€79,99<span className="text-base font-normal text-muted-foreground">/anno</span></p>
              <p className="text-sm text-muted-foreground mt-1">Accesso Premium per 365 giorni.</p>
              <Button className="rounded-full mt-6 gap-2" disabled={busy} onClick={() => buy("yearly")} data-testid="buy-yearly-button">
                <Crown size={16} weight="fill" /> {busy === "yearly" ? "Attendere..." : "Attiva annuale"}
              </Button>
            </Card>
          </div>

          {!sub?.trial_used && (
            <Card className="p-5 border-dashed text-center" data-testid="trial-card">
              <p className="font-heading font-bold">Provalo gratis per {sub?.trial_days ?? 7} giorni</p>
              <p className="text-sm text-muted-foreground mb-4">Nessun pagamento richiesto. Sblocca tutte le funzioni Premium.</p>
              <Button variant="outline" className="rounded-full gap-2" disabled={busy} onClick={startTrial} data-testid="start-trial-button">
                <Sparkle size={16} weight="fill" /> {busy === "trial" ? "Attivazione..." : "Inizia la prova gratuita"}
              </Button>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
