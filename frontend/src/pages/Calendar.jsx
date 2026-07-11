import React, { useEffect, useState, useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CalendarBlank, CaretLeft, CaretRight, Syringe, ShieldCheck, Stethoscope } from "@phosphor-icons/react";

const MONTHS = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"];
const DAYS = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"];

const typeMeta = {
  visit: { label: "Visita", color: "bg-chart-3/20 text-chart-3 border-chart-3/30", icon: Stethoscope },
  vaccine: { label: "Vaccino", color: "bg-primary/15 text-primary border-primary/30", icon: Syringe },
  treatment: { label: "Antiparassitario", color: "bg-accent/20 text-accent-foreground border-accent/40", icon: ShieldCheck },
};

function toKey(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export default function Calendar() {
  const navigate = useNavigate();
  const [events, setEvents] = useState([]);
  const [cursor, setCursor] = useState(() => new Date());

  const load = useCallback(async () => {
    const { data } = await api.get("/calendar/events");
    setEvents(data);
  }, []);
  useEffect(() => { load(); }, [load]);

  const byDay = useMemo(() => {
    const map = {};
    for (const e of events) {
      const key = e.date.slice(0, 10);
      (map[key] = map[key] || []).push(e);
    }
    return map;
  }, [events]);

  const year = cursor.getFullYear();
  const month = cursor.getMonth();
  const todayKey = toKey(new Date());

  const cells = useMemo(() => {
    const first = new Date(year, month, 1);
    const startOffset = (first.getDay() + 6) % 7; // Monday-first
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const arr = [];
    for (let i = 0; i < startOffset; i++) arr.push(null);
    for (let d = 1; d <= daysInMonth; d++) arr.push(new Date(year, month, d));
    return arr;
  }, [year, month]);

  const monthEvents = useMemo(
    () => events.filter((e) => e.date.slice(0, 7) === `${year}-${String(month + 1).padStart(2, "0")}`)
      .sort((a, b) => a.date.localeCompare(b.date)),
    [events, year, month]
  );

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <CalendarBlank size={24} weight="duotone" className="text-primary" />
            <p className="text-xs tracking-[0.2em] uppercase font-bold text-muted-foreground">Calendario</p>
          </div>
          <h1 className="font-heading text-3xl sm:text-4xl font-extrabold tracking-tighter">Tutti gli appuntamenti</h1>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" className="rounded-full" onClick={() => setCursor(new Date(year, month - 1, 1))} data-testid="cal-prev"><CaretLeft size={18} /></Button>
          <span className="font-heading font-bold text-lg w-40 text-center" data-testid="cal-label">{MONTHS[month]} {year}</span>
          <Button variant="outline" size="icon" className="rounded-full" onClick={() => setCursor(new Date(year, month + 1, 1))} data-testid="cal-next"><CaretRight size={18} /></Button>
        </div>
      </div>

      <div className="flex flex-wrap gap-3">
        {Object.entries(typeMeta).map(([k, m]) => {
          const Icon = m.icon;
          return (
            <span key={k} className={`inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1 rounded-full border ${m.color}`}>
              <Icon size={14} weight="fill" /> {m.label}
            </span>
          );
        })}
      </div>

      <Card className="p-4 sm:p-6 border-border" data-testid="calendar-grid">
        <div className="grid grid-cols-7 gap-1 sm:gap-2 mb-2">
          {DAYS.map((d) => <div key={d} className="text-center text-xs font-bold text-muted-foreground py-1">{d}</div>)}
        </div>
        <div className="grid grid-cols-7 gap-1 sm:gap-2">
          {cells.map((date, i) => {
            if (!date) return <div key={i} />;
            const key = toKey(date);
            const dayEvents = byDay[key] || [];
            const isToday = key === todayKey;
            return (
              <div key={i} className={`min-h-[72px] sm:min-h-[96px] rounded-lg border p-1.5 ${isToday ? "border-primary bg-primary/5" : "border-border"}`}>
                <div className={`text-xs font-semibold mb-1 ${isToday ? "text-primary" : "text-muted-foreground"}`}>{date.getDate()}</div>
                <div className="space-y-1">
                  {dayEvents.slice(0, 3).map((e, j) => {
                    const m = typeMeta[e.type];
                    return (
                      <button
                        key={j}
                        onClick={() => navigate(`/pet/${e.pet_id}`)}
                        className={`w-full text-left text-[10px] sm:text-xs px-1.5 py-0.5 rounded border truncate ${m.color} hover:opacity-80 transition-opacity`}
                        title={`${e.title} · ${e.pet_name}`}
                        data-testid="calendar-event"
                      >
                        <span className="hidden sm:inline">{e.pet_name}: </span>{e.title}
                      </button>
                    );
                  })}
                  {dayEvents.length > 3 && <div className="text-[10px] text-muted-foreground pl-1">+{dayEvents.length - 3}</div>}
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Month list */}
      <div>
        <h2 className="font-heading text-xl font-bold mb-3">Eventi del mese</h2>
        {monthEvents.length === 0 ? (
          <Card className="p-6 border-dashed text-muted-foreground text-sm text-center" data-testid="no-month-events">Nessun evento in {MONTHS[month]}.</Card>
        ) : (
          <div className="space-y-3">
            {monthEvents.map((e, i) => {
              const m = typeMeta[e.type];
              const Icon = m.icon;
              return (
                <Card key={i} className="p-4 border-border flex items-center gap-3 cursor-pointer hover:-translate-y-0.5 transition-transform" onClick={() => navigate(`/pet/${e.pet_id}`)} data-testid="month-event-row">
                  <div className={`h-10 w-10 rounded-lg flex items-center justify-center border ${m.color}`}><Icon size={20} weight="fill" /></div>
                  <div className="flex-1">
                    <p className="font-semibold">{e.title}</p>
                    <p className="text-sm text-muted-foreground">{e.pet_name} · {new Date(e.date).toLocaleDateString("it-IT", { weekday: "long", day: "numeric", month: "long" })}</p>
                  </div>
                  <span className={`text-xs font-medium px-2 py-1 rounded-full border ${m.color}`}>{m.label}</span>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
