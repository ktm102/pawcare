import React, { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api, { API } from "@/lib/api";
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Dog, Cat, ArrowLeft, Plus, Syringe, ShieldCheck, Stethoscope, Trash,
  Sparkle, PencilSimple, CalendarBlank, ChartLineUp, Scales, FileText, UploadSimple, DownloadSimple, Crown,
} from "@phosphor-icons/react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

const fmt = (d) => (d ? new Date(d).toLocaleDateString("it-IT") : "—");

export default function PetDetail() {
  const { petId } = useParams();
  const navigate = useNavigate();
  const [pet, setPet] = useState(null);
  const [visits, setVisits] = useState([]);
  const [vaccines, setVaccines] = useState([]);
  const [treatments, setTreatments] = useState([]);
  const [weights, setWeights] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [isPremium, setIsPremium] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [docCategory, setDocCategory] = useState("referto");
  const fileRef = useRef(null);
  const [editOpen, setEditOpen] = useState(false);
  const [recordDialog, setRecordDialog] = useState(null); // 'visit'|'vaccine'|'treatment'|'weight'
  const [advice, setAdvice] = useState("");
  const [adviceLoading, setAdviceLoading] = useState(false);

  const loadAll = useCallback(async () => {
    try {
      const [p, v, vac, tr, w] = await Promise.all([
        api.get(`/pets/${petId}`),
        api.get(`/pets/${petId}/visits`),
        api.get(`/pets/${petId}/vaccines`),
        api.get(`/pets/${petId}/treatments`),
        api.get(`/pets/${petId}/weights`),
      ]);
      setPet(p.data); setVisits(v.data); setVaccines(vac.data); setTreatments(tr.data); setWeights(w.data);
      const d = await api.get(`/pets/${petId}/documents`);
      setDocuments(d.data);
      const sub = await api.get("/subscription/status");
      setIsPremium(sub.data.premium);
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
    const map = { visit: "visits", vaccine: "vaccines", treatment: "treatments", weight: "weights" };
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
      if (e.response?.status === 402) {
        toast.error(e.response?.data?.detail || "Funzione Premium");
        navigate("/abbonamento");
      } else {
        toast.error("Errore nel generare i consigli");
      }
    } finally {
      setAdviceLoading(false);
    }
  };

  const uploadDoc = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("category", docCategory);
      await api.post(`/pets/${petId}/documents`, fd, { headers: { "Content-Type": "multipart/form-data" } });
      toast.success("Documento caricato");
      loadAll();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Caricamento fallito");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const openDoc = async (doc) => {
    try {
      const res = await fetch(`${API}/documents/${doc.id}/download`, { credentials: "include" });
      if (!res.ok) throw new Error();
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank");
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (e) {
      toast.error("Impossibile aprire il documento");
    }
  };

  const deleteDoc = async (docId) => {
    await api.delete(`/pets/${petId}/documents/${docId}`);
    toast.success("Documento eliminato");
    loadAll();
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
          <TabsTrigger value="weight" className="rounded-full gap-1" data-testid="tab-weight"><Scales size={16} /> Peso</TabsTrigger>
          <TabsTrigger value="documents" className="rounded-full gap-1" data-testid="tab-documents"><FileText size={16} /> Documenti</TabsTrigger>
        </TabsList>

        <TabsContent value="visits" className="mt-6 space-y-3">
          <div className="flex justify-end">
            <Button size="sm" className="rounded-full gap-1" onClick={() => setRecordDialog("visit")} data-testid="add-visit-button"><Plus size={16} weight="bold" /> Aggiungi visita</Button>
          </div>
          {visits.length === 0 ? <Empty text="Nessuna visita registrata" /> : visits.map((v) => (
            <RecordRow key={v.id} onDelete={() => delRecord("visit", v.id)} testid="visit-row">
              <div>
                <p className="font-semibold">{v.reason}</p>
                <p className="text-sm text-muted-foreground">{fmt(v.date)}{v.veterinarian ? ` · ${v.veterinarian}` : ""}</p>
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

        <TabsContent value="weight" className="mt-6 space-y-4">
          <div className="flex justify-end">
            <Button size="sm" className="rounded-full gap-1" onClick={() => setRecordDialog("weight")} data-testid="add-weight-button"><Plus size={16} weight="bold" /> Registra peso</Button>
          </div>
          {weights.length === 0 ? <Empty text="Nessuna misurazione del peso registrata" /> : (
            <>
              <Card className="p-5 border-border" data-testid="weight-chart">
                <div className="flex items-center gap-2 mb-4">
                  <ChartLineUp size={20} weight="duotone" className="text-primary" />
                  <h3 className="font-heading font-bold">Andamento del peso (kg)</h3>
                </div>
                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={weights.map((w) => ({ ...w, label: new Date(w.date).toLocaleDateString("it-IT", { day: "2-digit", month: "short", year: "2-digit" }) }))} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="label" tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }} />
                      <YAxis tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }} domain={["auto", "auto"]} />
                      <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8 }} formatter={(val) => [`${val} kg`, "Peso"]} />
                      <Line type="monotone" dataKey="weight" stroke="hsl(var(--primary))" strokeWidth={2.5} dot={{ r: 4, fill: "hsl(var(--primary))" }} activeDot={{ r: 6 }} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </Card>
              <div className="space-y-3">
                {[...weights].reverse().map((w) => (
                  <RecordRow key={w.id} onDelete={() => delRecord("weight", w.id)} testid="weight-row">
                    <div>
                      <p className="font-semibold">{w.weight} kg</p>
                      <p className="text-sm text-muted-foreground">{fmt(w.date)}</p>
                    </div>
                  </RecordRow>
                ))}
              </div>
            </>
          )}
        </TabsContent>

        <TabsContent value="documents" className="mt-6 space-y-4">
          {!isPremium ? (
            <Card className="p-8 border-accent/40 bg-accent/5 text-center" data-testid="documents-premium-gate">
              <Crown size={40} weight="duotone" className="text-accent mx-auto mb-3" />
              <h3 className="font-heading font-bold text-lg">Gli allegati sono una funzione Premium</h3>
              <p className="text-muted-foreground text-sm mb-4 max-w-md mx-auto">Conserva referti, analisi e ricette del tuo animale in un unico posto. Sblocca gli allegati con PawCare Premium.</p>
              <Button className="rounded-full gap-2" onClick={() => navigate("/abbonamento")} data-testid="documents-upgrade-button">
                <Crown size={16} weight="fill" /> Passa a Premium
              </Button>
            </Card>
          ) : (
          <>
          <Card className="p-5 border-border">
            <div className="flex flex-col sm:flex-row sm:items-end gap-3">
              <div className="flex-1">
                <label className="text-xs tracking-[0.15em] uppercase font-bold text-muted-foreground">Categoria</label>
                <Select value={docCategory} onValueChange={setDocCategory}>
                  <SelectTrigger className="mt-1" data-testid="document-category-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="referto">Referto</SelectItem>
                    <SelectItem value="analisi">Analisi</SelectItem>
                    <SelectItem value="ricetta">Ricetta / Prescrizione</SelectItem>
                    <SelectItem value="libretto">Libretto sanitario</SelectItem>
                    <SelectItem value="altro">Altro</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <input ref={fileRef} type="file" accept=".pdf,.jpg,.jpeg,.png,.webp,.heic,.txt" onChange={uploadDoc} className="hidden" data-testid="document-file-input" />
              <Button className="rounded-full gap-2" disabled={uploading} onClick={() => fileRef.current?.click()} data-testid="upload-document-button">
                <UploadSimple size={18} weight="bold" /> {uploading ? "Caricamento..." : "Carica documento"}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground mt-2">PDF o immagini, max 15MB.</p>
          </Card>
          {documents.length === 0 ? <Empty text="Nessun documento caricato" /> : (
            <div className="space-y-3">
              {documents.map((d) => (
                <Card key={d.id} className="p-4 border-border flex items-center justify-between gap-4" data-testid="document-row">
                  <button onClick={() => openDoc(d)} className="flex items-center gap-3 text-left flex-1 min-w-0" data-testid="open-document-button">
                    <div className="h-10 w-10 rounded-lg bg-secondary flex items-center justify-center shrink-0">
                      <FileText size={20} weight="duotone" className="text-secondary-foreground" />
                    </div>
                    <div className="min-w-0">
                      <p className="font-semibold truncate">{d.name}</p>
                      <p className="text-sm text-muted-foreground capitalize">{d.category} · {fmt(d.created_at)}</p>
                    </div>
                  </button>
                  <div className="flex gap-1 shrink-0">
                    <Button variant="ghost" size="icon" onClick={() => openDoc(d)} title="Apri" data-testid="download-document-button"><DownloadSimple size={18} /></Button>
                    <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-destructive" onClick={() => deleteDoc(d.id)} data-testid="delete-document-button"><Trash size={16} /></Button>
                  </div>
                </Card>
              ))}
            </div>
          )}
          </>
          )}
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

  const titles = { visit: "Nuova visita", vaccine: "Nuovo vaccino", treatment: "Nuovo trattamento", weight: "Registra peso" };

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
      } else if (kind === "weight") {
        if (!form.date || !form.weight) { toast.error("Data e peso obbligatori"); setBusy(false); return; }
        await api.post(`/pets/${petId}/weights`, { date: form.date, weight: parseFloat(form.weight) });
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
          {kind === "weight" && (
            <>
              <Field label="Data"><Input type="date" onChange={(e) => set("date", e.target.value)} data-testid="weight-date-input" /></Field>
              <Field label="Peso (kg)"><Input type="number" step="0.1" min="0.1" onChange={(e) => set("weight", e.target.value)} placeholder="12.5" data-testid="weight-value-input" /></Field>
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
