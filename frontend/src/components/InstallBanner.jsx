import React, { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DownloadSimple, X, ShareNetwork, Plus, PawPrint } from "@phosphor-icons/react";

const DISMISS_KEY = "pawcare_install_dismissed";

function isStandalone() {
  return (
    window.matchMedia?.("(display-mode: standalone)").matches ||
    window.navigator.standalone === true
  );
}

function isIOS() {
  return /iphone|ipad|ipod/i.test(window.navigator.userAgent) && !window.MSStream;
}

export default function InstallBanner() {
  const [deferredPrompt, setDeferredPrompt] = useState(null);
  const [visible, setVisible] = useState(false);
  const [showIosHelp, setShowIosHelp] = useState(false);
  const ios = isIOS();

  useEffect(() => {
    if (isStandalone() || localStorage.getItem(DISMISS_KEY) === "1") return;

    if (ios) {
      // iOS has no beforeinstallprompt; show manual instructions
      setVisible(true);
      return;
    }

    const handler = (e) => {
      e.preventDefault();
      setDeferredPrompt(e);
      setVisible(true);
    };
    window.addEventListener("beforeinstallprompt", handler);
    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, [ios]);

  const dismiss = () => {
    localStorage.setItem(DISMISS_KEY, "1");
    setVisible(false);
  };

  const install = async () => {
    if (ios) {
      setShowIosHelp((s) => !s);
      return;
    }
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    setDeferredPrompt(null);
    if (outcome === "accepted") dismiss();
  };

  if (!visible) return null;

  return (
    <Card className="mb-6 border-primary/30 bg-primary/5 overflow-hidden" data-testid="install-banner">
      <div className="p-4 flex items-center gap-4">
        <div className="h-11 w-11 rounded-xl bg-primary/15 flex items-center justify-center shrink-0">
          <PawPrint size={24} weight="duotone" className="text-primary" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-heading font-bold">Installa PawCare sul telefono</p>
          <p className="text-sm text-muted-foreground">
            {ios ? "Aggiungila alla Home per aprirla come un'app e ricevere le notifiche." : "Accesso rapido a schermo intero, come un'app nativa."}
          </p>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <Button size="sm" className="rounded-full gap-1" onClick={install} data-testid="install-app-button">
            {ios ? <ShareNetwork size={16} weight="bold" /> : <DownloadSimple size={16} weight="bold" />}
            {ios ? "Come fare" : "Installa"}
          </Button>
          <Button size="icon" variant="ghost" onClick={dismiss} data-testid="dismiss-install-banner" title="Chiudi"><X size={18} /></Button>
        </div>
      </div>

      {ios && showIosHelp && (
        <div className="px-4 pb-4 pt-1 border-t border-primary/20 text-sm text-muted-foreground space-y-2" data-testid="ios-install-help">
          <p className="font-medium text-foreground">Su iPhone (Safari):</p>
          <ol className="space-y-1.5 list-decimal list-inside">
            <li>Tocca l'icona <ShareNetwork size={15} className="inline align-text-bottom" weight="bold" /> <strong>Condividi</strong> nella barra di Safari.</li>
            <li>Scorri e seleziona <Plus size={14} className="inline align-text-bottom" weight="bold" /> <strong>"Aggiungi a Home"</strong>.</li>
            <li>Conferma con <strong>"Aggiungi"</strong> in alto a destra.</li>
          </ol>
          <p className="text-xs">Nota: le notifiche push su iPhone richiedono iOS 16.4+ e l'app installata sulla Home.</p>
        </div>
      )}
    </Card>
  );
}
