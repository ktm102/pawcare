import React, { useEffect, useState, useRef, useCallback } from "react";
import api from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ChatCircleDots, PaperPlaneTilt, PawPrint } from "@phosphor-icons/react";

const suggestions = [
  "Come faccio a capire se il mio cane è in sovrappeso?",
  "Ogni quanto devo fare l'antiparassitario in estate?",
  "Il mio gatto vomita spesso, cosa può essere?",
];

export default function Assistant() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [pets, setPets] = useState([]);
  const [petId, setPetId] = useState("none");
  const [busy, setBusy] = useState(false);
  const bottomRef = useRef(null);

  const loadHistory = useCallback(async () => {
    const [h, p] = await Promise.all([api.get("/ai/chat/history"), api.get("/pets")]);
    setMessages(h.data);
    setPets(p.data);
  }, []);

  useEffect(() => { loadHistory(); }, [loadHistory]);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, busy]);

  const send = async (text) => {
    const msg = text ?? input;
    if (!msg.trim() || busy) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: msg, id: Date.now() }]);
    setBusy(true);
    try {
      const { data } = await api.post("/ai/chat", { message: msg, pet_id: petId === "none" ? null : petId });
      setMessages((m) => [...m, { role: "assistant", content: data.reply, id: Date.now() + 1 }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", content: "Si è verificato un errore. Riprova.", id: Date.now() + 1 }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-10rem)]">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <ChatCircleDots size={24} weight="duotone" className="text-primary" />
            <p className="text-xs tracking-[0.2em] uppercase font-bold text-muted-foreground">Assistente AI</p>
          </div>
          <h1 className="font-heading text-2xl sm:text-3xl font-extrabold tracking-tighter">Chiedi al veterinario virtuale</h1>
        </div>
        <Select value={petId} onValueChange={setPetId}>
          <SelectTrigger className="w-56" data-testid="chat-pet-select"><SelectValue placeholder="Nessun animale" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="none">Domanda generica</SelectItem>
            {pets.map((p) => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      <Card className="flex-1 flex flex-col border-border overflow-hidden">
        <div className="flex-1 overflow-y-auto p-4 space-y-4" data-testid="chat-messages">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center gap-4 py-8">
              <PawPrint size={48} weight="duotone" className="text-primary/50" />
              <p className="text-muted-foreground max-w-sm">Fai una domanda su alimentazione, vaccini, comportamento o prevenzione. Seleziona un animale per risposte più mirate.</p>
              <div className="flex flex-col gap-2 w-full max-w-md">
                {suggestions.map((s, i) => (
                  <button key={i} onClick={() => send(s)} className="text-sm text-left px-4 py-3 rounded-lg border border-border hover:bg-muted transition-colors" data-testid={`suggestion-${i}`}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m) => (
            <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`} data-testid={`message-${m.role}`}>
              <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap leading-relaxed ${m.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"}`}>
                {m.content}
              </div>
            </div>
          ))}
          {busy && (
            <div className="flex justify-start">
              <div className="bg-muted rounded-2xl px-4 py-3 flex gap-1">
                <span className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" />
                <span className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: "0.15s" }} />
                <span className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: "0.3s" }} />
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <form onSubmit={(e) => { e.preventDefault(); send(); }} className="border-t border-border p-3 flex gap-2">
          <Input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Scrivi la tua domanda..." data-testid="chat-input" className="rounded-full" />
          <Button type="submit" size="icon" className="rounded-full shrink-0" disabled={busy || !input.trim()} data-testid="chat-send-button">
            <PaperPlaneTilt size={18} weight="fill" />
          </Button>
        </form>
      </Card>
    </div>
  );
}
