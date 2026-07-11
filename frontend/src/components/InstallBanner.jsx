import React, { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DownloadSimple, X, ShareNetwork, Plus, PawPrint, DotsThreeVertical } from "@phosphor-icons/react";

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

function isAndroid() {
  return /android/i.test(window.navigator.userAgent);
}

export default function InstallBanner() {
  const [deferredPrompt, setDeferredPrompt] = useState(null);
  const [visible, setVisible] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  const ios = isIOS();
  const android = isAndroid();

  useEffect(() => {
    if (isStandalone() || localStorage.getItem(DISMISS_KEY) === "1") return;

    // iOS and Android always get the banner (with manual instructions as fallback)
    if (ios || android) {
      setVisible(true);
    }

    const handler = (e) => {
      e.preventDefault();
      setDeferredPrompt(e);
      setVisible(true);
    };
    window.addEventListener("beforeinstallprompt", handler);
    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, [ios, android]);

  const dismiss = () => {
    localStorage.setItem(DISMISS_KEY, "1");
    setVisible(false);
  };

  const primaryAction = async () => {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;
      setDeferredPrompt(null);
      if (outcome === "accepted") dismiss();
      return;
    }
    // No native prompt available -> show manual steps
    setShowHelp((s) => !s);
  };

  if (!visible) return null;

  const nativeAvailable = !!deferredPrompt;
  const subtitle = ios
    ? "Aggiungila alla Home per aprirla come un'app e ricevere le notifiche."
    : "Accesso rapido a schermo intero, come un'app nativa.";

  return (
    <Card className="mb-6 border-primary/30 bg-primary/5 overflow-hidden" data-testid="install-banner">
      <div className="p-4 flex items-center gap-4">
        <div className="h-11 w-11 rounded-xl bg-primary/15 flex items-center justify-center shrink-0">
          <PawPrint size={24} weight="duotone" className="text-primary" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-heading font-bold">Installa PawCare sul telefono</p>
          <p className="text-sm text-muted-foreground">{subtitle}</p>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <Button size="sm" className="rounded-full gap-1" onClick={primaryAction} data-testid="install-app-button">
            {nativeAvailable ? <DownloadSimple size={16} weight="bold" /> : <ShareNetwork size={16} weight="bold" />}
            {nativeAvailable ? "Installa" : "Come fare"}
          </Button>
          <Button size="icon" variant="ghost" onClick={dismiss} data-testid="dismiss-install-banner" title="Chiudi"><X size={18} /></Button>
        </div>
      </div>

      {ios && showHelp && (
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

      {!ios && showHelp && (
        <div className="px-4 pb-4 pt-1 border-t border-primary/20 text-sm text-muted-foreground space-y-2" data-testid="android-install-help">
          <p className="font-medium text-foreground">Su Android (Chrome):</p>
          <ol className="space-y-1.5 list-decimal list-inside">
            <li>Tocca il menu <DotsThreeVertical size={15} className="inline align-text-bottom" weight="bold" /> <strong>(tre puntini)</strong> in alto a destra.</li>
            <li>Seleziona <Plus size={14} className="inline align-text-bottom" weight="bold" /> <strong>"Installa app"</strong> (o "Aggiungi a schermata Home").</li>
            <li>Conferma con <strong>"Installa"</strong>.</li>
          </ol>
          <p className="text-xs">L'icona 🐾 apparirà tra le tue app e le notifiche push funzioneranno subito.</p>
        </div>
      )}
    </Card>
  );
}
