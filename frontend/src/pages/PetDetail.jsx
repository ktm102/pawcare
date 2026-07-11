import React, { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import PetDialog from "@/components/PetDialog";
import { toast } from "sonner";
import {
  Dog, Cat, ArrowLeft, Plus, Syringe, ShieldCheck, Stethoscope, Trash,
  Sparkle, PencilSimple, CalendarBlank,
} from "@phosphor-icons/react";

const fmt = (d) => (d ? new Date(d).toLocaleDateString("it-IT") : "—");

export default function PetDetail() {
  const { petId } = useParams();
  const navigate = useNavigate();
  const [pet, setPet] = useState(null);
  const [visits, setVisits] = useState([]);
  const [vaccines, setVaccines] = useState([]);
  const [treatments, setTreatments] = useState([]);
  const [editOpen, setEditOpen] = useState(false);
  const [recordDialog, setRecordDialog] = useState(null); // 'visit'|'vaccine'|'treatment'
  const [advice, setAdvice] = useState("");
  const [adviceLoading, setAdviceLoading] = useState(false);

  const loadAll = useCallback(async () => {
    try {
      const [p, v, vac, tr] = await Promise.all([
        api.get(`/pets/${petId}`),
        api.get(`/pets/${petId}/visits`),
        api.get(`/pets/${petId}/vaccines`),
        api.get(`/pets/${petId}/treatments`),
      ]);
      setPet(p.data); setVisits(v.data); setVaccines(vac.data); setTreatments(tr.data);
    } catch (e) {
      toast.error("Impossibile caricare l'animale");
      navigate("/dashboard");
    }
  }, [petId, navigate]);

  useEffect(() => { loadAll(); }, [loadAll]);

  const deletePet = async () => {
    await api.delete(`/pets/${petId}`);
    toast.success("Animale eliminato");
    navigate("/dashboard");
  };

  const delRecord = async (kind, id) => {
    const map = { visit: "visits", vaccine: "vaccines", treatment: "treatments" };
    await api.delete(`/pets/${petId}/${map[kind]}/${id}`);
    toast.success("Eliminato");
    loadAll();
  };

  const getAdvice = async () => {
    setAdviceLoading(true);
    setAdvice("");
    try {
      const { data } = await api.post("/ai/advice", { pet_id: petId });
      setAdvice(data.advice);
    } catch (e) {
      toast.error("Errore nel generare i consigli");
    } finally {
      setAdviceLoading(false);
    }
  };

  if (!pet) return <p className="text-muted-foreground">Caricamento...</p>;
  const Icon = pet.species === "dog" ? Dog : Cat;

  return (
    <div className="space-y-8">
      <Button variant="ghost" className="gap-2 -ml-2" onClick={() => navigate("/dashboard")} data-testid="back-button">
        <ArrowLeft size={18} /> Indietro
      </Button>

      {/* Header */}
      <Card className="p-6 border-border">
        <div className="flex flex-col sm:flex-row gap-6 items-start sm:items-center">
          <div className="h-24 w-24 rounded-2xl bg-muted overflow-hidden border border-border flex items-center justify-center shrink-0">
            {pet.photo ? <img src={pet.photo} alt={pet.name} className="h-full w-full object-cover" /> : <Icon size={48} weight="duotone" className="text-primary/50" />}
          </div>
          <div className="flex-1">
            <h1 className="font-heading text-3xl font-extrabold tracking-tighter">{pet.name}</h1>
            <div className="flex flex-wrap gap-2 mt-2">
              <Badge variant="secondary">{pet.species === "dog" ? "Cane" : "Gatto"}</Badge>
              <Badge variant="secondary">{pet.breed}</Badge>
              <Badge variant="secondary">{pet.age} {pet.age === 1 ? "anno" : "anni"}</Badge>
              <Badge variant="secondary">{pet.sex === "M" ? "Maschio" : "Femmina"}</Badge>
              {pet.weight ? <Badge variant="secondary">{pet.weight} kg</Badge> : null}
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="icon" className="rounded-full" onClick={() => setEditOpen(true)} data-testid="edit-pet-button"><PencilSimple size={18} /></Button>
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="outline" size="icon" className="rounded-full text-destructive" data-testid="delete-pet-button"><Trash size={18} /></Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Eliminare {pet.name}?</AlertDialogTitle>
                  <AlertDialogDescription>Verranno eliminati anche tutti i dati sanitari associati. L'azione è irreversibile.</AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Annulla</AlertDialogCancel>
                  <AlertDialogAction onClick={deletePet} data-testid="confirm-delete-pet">Elimina</AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </div>
      </Card>

      {/* AI advice */}
      <Card className="p-6 border-border bg-secondary/30">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <Sparkle size={22} weight="duotone" className="text-primary" />
            <h2 className="font-heading text-xl font-bold">Consigli AI personalizzati</h2>
          </div>
          <Button className="rounded-full gap-2" onClick={getAdvice} disabled={adviceLoading} data-testid="get-advice-button">
            <Sparkle size={16} weight="fill" /> {adviceLoading ? "Genero consigli..." : "Genera consigli"}
          </Button>
        </div>
        <p className="text-sm text-muted-foreground mt-1">In base a età ({pet.age} anni) e razza ({pet.breed}).</p>
        {advice && (
          <div className="mt-4 whitespace-pre-wrap text-sm leading-relaxed bg-card p-4 rounded-lg border border-border" data-testid="advice-content">
            {advice}
          </div>
        )}
      </Card>

      {/* Tabs */}
      <Tabs defaultValue="visits">
        <TabsList className="rounded-full">
          <TabsTrigger value="visits" className="rounded-full gap-1" data-testid="tab-visits"><Stethoscope size={16} /> Visite</TabsTrigger>
          <TabsTrigger value="vaccines" className="rounded-full gap-1" data-testid="tab-vaccines"><Syringe size={16} /> Vaccini</TabsTrigger>
          <TabsTrigger value="treatments" className="rounded-full gap-1" data-testid="tab-treatments"><ShieldCheck size={16} /> Antiparassitari</TabsTrigger>
        </TabsList>

        <TabsContent value="visits" className="mt-6 space-y-3">
          <div className="flex justify-end">
            <Button size="sm" className="rounded-full gap-1" onClick={() => setRecordDialog("visit")} data-testid="add-visit-button"><Plus size={16} weight="bold" /> Aggiungi visita</Button>
          </div>
          {visits.length === 0 ? <Empty text="Nessuna visita registrata" /> : visits.map((v) => (
            <RecordRow key={v.id} onDelete={() => delRecord("visit", v.id)} testid="visit-row">
              <div>
                <p className="font-semibold">{v.reason}</p>
                <p className="text-sm text-muted-foreground">{fmt(v.date)}{v.veterinarian ? ` · Dr. ${v.veterinarian}` : ""}</p>
                {v.notes && <p className="text-sm mt-1">{v.notes}</p>}
              </div>
            </RecordRow>
          ))}
        </TabsContent>

        <TabsContent value="vaccines" className="mt-6 space-y-3">
          <div className="flex justify-end">
            <Button size="sm" className="rounded-full gap-1" onClick={() => setRecordDialog("vaccine")} data-testid="add-vaccine-button"><Plus size={16} weight="bold" /> Aggiungi vaccino</Button>
          </div>
          {vaccines.length === 0 ? <Empty text="Nessun vaccino registrato" /> : vaccines.map((v) => (
            <RecordRow key={v.id} onDelete={() => delRecord("vaccine", v.id)} testid="vaccine-row">
              <div>
                <p className="font-semibold">{v.name}</p>
                <p className="text-sm text-muted-foreground">Somministrato: {fmt(v.date_given)}</p>
                {v.next_due && <p className="text-sm text-primary flex items-center gap-1 mt-1"><CalendarBlank size={14} /> Prossimo: {fmt(v.next_due)}</p>}
              </div>
            </RecordRow>
          ))}
        </TabsContent>

        <TabsContent value="treatments" className="mt-6 space-y-3">
          <div className="flex justify-end">
            <Button size="sm" className="rounded-full gap-1" onClick={() => setRecordDialog("treatment")} data-testid="add-treatment-button"><Plus size={16} weight="bold" /> Aggiungi trattamento</Button>
          </div>
          {treatments.length === 0 ? <Empty text="Nessun trattamento registrato" /> : treatments.map((t) => (
            <RecordRow key={t.id} onDelete={() => delRecord("treatment", t.id)} testid="treatment-row">
              <div>
                <p className="font-semibold">{t.name}</p>
                <p className="text-sm text-muted-foreground">Somministrato: {fmt(t.date_given)} · Ogni {t.frequency_days} giorni</p>
                {t.next_due && <p className="text-sm text-primary flex items-center gap-1 mt-1"><CalendarBlank size={14} /> Prossimo: {fmt(t.next_due)}</p>}
              </div>
            </RecordRow>
          ))}
        </TabsContent>
      </Tabs>

      <PetDialog open={editOpen} onOpenChange={setEditOpen} onSaved={loadAll} pet={pet} />
      <RecordDialog kind={recordDialog} petId={petId} onClose={() => setRecordDialog(null)} onSaved={loadAll} />
    </div>
  );
}

const Empty = ({ text }) => (
  <Card className="p-6 border-dashed text-muted-foreground text-sm text-center">{text}</Card>
);

const RecordRow = ({ children, onDelete, testid }) => (
  <Card className="p-4 border-border flex items-start justify-between gap-4" data-testid={testid}>
    {children}
    <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-destructive shrink-0" onClick={onDelete} data-testid="delete-record-button"><Trash size={16} /></Button>
  </Card>
);

function RecordDialog({ kind, petId, onClose, onSaved }) {
  const [form, setForm] = useState({});
  const [busy, setBusy] = useState(false);
  useEffect(() => { setForm({}); }, [kind]);
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const titles = { visit: "Nuova visita", vaccine: "Nuovo vaccino", treatment: "Nuovo trattamento" };

  const save = async () => {
    setBusy(true);
    try {
      if (kind === "visit") {
        if (!form.date || !form.reason) { toast.error("Data e motivo obbligatori"); setBusy(false); return; }
        await api.post(`/pets/${petId}/visits`, { date: form.date, reason: form.reason, veterinarian: form.veterinarian || "", notes: form.notes || "" });
      } else if (kind === "vaccine") {
        if (!form.name || !form.date_given) { toast.error("Nome e data obbligatori"); setBusy(false); return; }
        await api.post(`/pets/${petId}/vaccines`, { name: form.name, date_given: form.date_given, next_due: form.next_due || null });
      } else if (kind === "treatment") {
        if (!form.name || !form.date_given || !form.frequency_days) { toast.error("Nome, data e frequenza obbligatori"); setBusy(false); return; }
        await api.post(`/pets/${petId}/treatments`, { name: form.name, date_given: form.date_given, frequency_days: parseInt(form.frequency_days), next_due: form.next_due || null });
      }
      toast.success("Salvato");
      onSaved(); onClose();
    } catch (e) {
      toast.error("Errore nel salvataggio");
    } finally { setBusy(false); }
  };

  return (
    <Dialog open={!!kind} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader><DialogTitle className="font-heading">{titles[kind]}</DialogTitle></DialogHeader>
        <div className="space-y-4">
          {kind === "visit" && (
            <>
              <Field label="Data"><Input type="date" onChange={(e) => set("date", e.target.value)} data-testid="visit-date-input" /></Field>
              <Field label="Motivo"><Input onChange={(e) => set("reason", e.target.value)} placeholder="Controllo annuale" data-testid="visit-reason-input" /></Field>
              <Field label="Veterinario"><Input onChange={(e) => set("veterinarian", e.target.value)} placeholder="Dr. Bianchi" data-testid="visit-vet-input" /></Field>
              <Field label="Note"><Textarea onChange={(e) => set("notes", e.target.value)} placeholder="Note..." data-testid="visit-notes-input" /></Field>
            </>
          )}
          {kind === "vaccine" && (
            <>
              <Field label="Nome vaccino"><Input onChange={(e) => set("name", e.target.value)} placeholder="Antirabbica" data-testid="vaccine-name-input" /></Field>
              <Field label="Data somministrazione"><Input type="date" onChange={(e) => set("date_given", e.target.value)} data-testid="vaccine-date-input" /></Field>
              <Field label="Prossimo richiamo"><Input type="date" onChange={(e) => set("next_due", e.target.value)} data-testid="vaccine-nextdue-input" /></Field>
            </>
          )}
          {kind === "treatment" && (
            <>
              <Field label="Nome trattamento"><Input onChange={(e) => set("name", e.target.value)} placeholder="Antipulci spot-on" data-testid="treatment-name-input" /></Field>
              <Field label="Data somministrazione"><Input type="date" onChange={(e) => set("date_given", e.target.value)} data-testid="treatment-date-input" /></Field>
              <Field label="Frequenza (giorni)"><Input type="number" onChange={(e) => set("frequency_days", e.target.value)} placeholder="30" data-testid="treatment-frequency-input" /></Field>
              <Field label="Prossima somministrazione"><Input type="date" onChange={(e) => set("next_due", e.target.value)} data-testid="treatment-nextdue-input" /></Field>
            </>
          )}
          <Button onClick={save} disabled={busy} className="w-full rounded-full" data-testid="save-record-button">{busy ? "Salvataggio..." : "Salva"}</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

const Field = ({ label, children }) => (
  <div><Label className="mb-1 block">{label}</Label>{children}</div>
);
