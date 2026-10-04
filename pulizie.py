import calendar
import csv
import json
import os
import random
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageDraw, ImageFont

CONFIG_FILE = "config_pulizie.json"

DEFAULT_PERSONE = {
    1: "Persona 1",
    2: "Persona 2",
    3: "Persona 3",
    4: "Persona 4",
    5: "Persona 5",
    6: "Persona 6",
    7: "Persona 7",
}

DEFAULT_MANSIONI = ["Bagno Piccolo", "Bagno Grande", "Cucina", "Spazzatura"]


class TurniPulizieApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Gestione Turni Pulizie")
        self.root.geometry("1020x820")

        # Carica la configurazione da file JSON se presente, altrimenti usa i default
        self.persone, self.mansioni = self.carica_configurazione()

        self.setup_styles()
        self.reset_storico()
        self.setup_ui()

    def reset_storico(self):
        """Azzera il conteggio delle assegnazioni passate per l'estrazione equa."""
        self.storico_mansioni = {
            pid: {m: 0 for m in self.mansioni} for pid in self.persone
        }
        self.storico_totale = {pid: 0 for pid in self.persone}

    def carica_configurazione(self):
        """Carica la lista di persone e mansioni da un file JSON locale."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    persone = {int(k): v for k, v in data.get("persone", {}).items()}
                    mansioni = data.get("mansioni", DEFAULT_MANSIONI)
                    if persone and mansioni:
                        return persone, mansioni
            except Exception:
                pass
        return DEFAULT_PERSONE.copy(), DEFAULT_MANSIONI.copy()

    def salva_configurazione(self):
        """Salva la lista aggiornata di persone e mansioni in JSON."""
        data = {"persone": self.persone, "mansioni": self.mansioni}
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            messagebox.showwarning(
                "Attenzione", f"Impossibile salvare la configurazione: {e}"
            )

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Custom.Treeview",
            background="#FFFFFF",
            foreground="#2C3E50",
            rowheight=36,
            fieldbackground="#FFFFFF",
            font=("Segoe UI", 10),
            borderwidth=0,
        )

        style.configure(
            "Custom.Treeview.Heading",
            background="#34495E",
            foreground="#FFFFFF",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padding=8,
        )

        style.map("Custom.Treeview.Heading", background=[("active", "#2C3E50")])

    def setup_ui(self):
        # --- Frame Selezione Periodo e Configurazione ---
        top_frame = ttk.LabelFrame(self.root, text=" 🗓️ Seleziona Periodo ")
        top_frame.pack(fill="x", padx=15, pady=8)

        ttk.Label(top_frame, text="Mese:").grid(
            row=0, column=0, padx=5, pady=5, sticky="w"
        )
        self.combo_mese = ttk.Combobox(
            top_frame,
            values=[calendar.month_name[i] for i in range(1, 13)],
            state="readonly",
            width=12,
        )
        self.combo_mese.current(0)
        self.combo_mese.grid(row=0, column=1, padx=5, pady=5)
        self.combo_mese.bind("<<ComboboxSelected>>", self.aggiorna_settimane_ui)

        ttk.Label(top_frame, text="Anno:").grid(
            row=0, column=2, padx=5, pady=5, sticky="w"
        )
        self.entry_anno = ttk.Entry(top_frame, width=8)
        self.entry_anno.insert(0, "2026")
        self.entry_anno.grid(row=0, column=3, padx=5, pady=5)

        btn_carica = ttk.Button(
            top_frame,
            text="Carica Mese",
            command=self.aggiorna_settimane_ui,
        )
        btn_carica.grid(row=0, column=4, padx=15, pady=5)

        btn_gestisci_persone = ttk.Button(
            top_frame,
            text="⚙️ Gestisci Coinquilini",
            command=self.apri_gestione_persone,
        )
        btn_gestisci_persone.grid(row=0, column=5, padx=10, pady=5)

        # --- Frame Presenze ---
        self.frame_presenze = ttk.LabelFrame(
            self.root, text=" 👥 Presenze Settimanali (Spunta chi c'è) "
        )
        self.frame_presenze.pack(fill="x", padx=15, pady=5)

        # --- Frame Pulsanti Azione ---
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill="x", padx=15, pady=8)

        btn_calcola = ttk.Button(
            btn_frame,
            text="🎲 Genera Turni Equi",
            command=self.genera_turni,
        )
        btn_calcola.pack(side="left", padx=5)

        btn_export_csv = ttk.Button(
            btn_frame,
            text="💾 Esporta CSV",
            command=self.esporta_csv,
        )
        btn_export_csv.pack(side="left", padx=5)

        btn_export_png = ttk.Button(
            btn_frame,
            text="📸 Salva Tabella come PNG",
            command=self.esporta_png,
        )
        btn_export_png.pack(side="left", padx=5)

        # --- Frame Tabella Risultati ---
        self.frame_risultati = ttk.LabelFrame(
            self.root, text=" 📊 Tabella Turni Estrapolati "
        )
        self.frame_risultati.pack(fill="both", expand=True, padx=15, pady=8)

        self.crea_tabella_ui()
        self.aggiorna_settimane_ui()

    def crea_tabella_ui(self):
        """Ricrea la tabella in base alle mansioni attuali."""
        for widget in self.frame_risultati.winfo_children():
            widget.destroy()

        colonne = ["Settimana", "Inizio - Fine"] + self.mansioni
        self.tree = ttk.Treeview(
            self.frame_risultati,
            columns=colonne,
            show="headings",
            style="Custom.Treeview",
        )

        width_map = {"Settimana": 110, "Inizio - Fine": 140}
        for col in colonne:
            self.tree.heading(col, text=col.upper())
            self.tree.column(col, anchor="center", width=width_map.get(col, 150))

        self.tree.tag_configure(
            "pari", background="#F8F9FA", foreground="#2C3E50"
        )
        self.tree.tag_configure(
            "dispari", background="#EAECEE", foreground="#1A252F"
        )

        scrollbar = ttk.Scrollbar(
            self.frame_risultati, orient="vertical", command=self.tree.yview
        )
        self.tree.configure(yscroll=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y", pady=5)

    def apri_gestione_persone(self):
        """Apre una finestra pop-up per aggiungere, rimuovere e rinominare i coinquilini."""
        win = tk.Toplevel(self.root)
        win.title("Gestisci Coinquilini")
        win.geometry("450x500")
        win.grab_set()

        ttk.Label(
            win,
            text="Gestisci il numero e i nomi dei coinquilini:",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", padx=15, pady=10)

        # Container scrollabile per la lista delle persone
        canvas = tk.Canvas(win, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(win, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="top", fill="both", expand=True, padx=15, pady=5)
        scrollbar.pack(side="right", fill="y")

        entries = {}

        def render_lista():
            for child in scrollable_frame.winfo_children():
                child.destroy()
            entries.clear()

            for pid, nome in sorted(self.persone.items()):
                row = ttk.Frame(scrollable_frame)
                row.pack(fill="x", pady=3, expand=True)

                ttk.Label(row, text=f"ID {pid}:", width=6).pack(side="left")
                ent = ttk.Entry(row)
                ent.insert(0, nome)
                ent.pack(side="left", fill="x", expand=True, padx=5)
                entries[pid] = ent

                def elimina_persona(p_id=pid):
                    if len(self.persone) <= len(self.mansioni):
                        messagebox.showwarning(
                            "Attenzione",
                            f"Devono esserci almeno {len(self.mansioni)} persone per coprire le mansioni!",
                        )
                        return
                    del self.persone[p_id]
                    render_lista()

                btn_del = ttk.Button(
                    row, text="🗑️", width=3, command=elimina_persona
                )
                btn_del.pack(side="right", padx=2)

        def aggiungi_persona():
            nuovo_id = max(self.persone.keys(), default=0) + 1
            self.persone[nuovo_id] = f"Persona {nuovo_id}"
            render_lista()

        render_lista()

        btn_box = ttk.Frame(win)
        btn_box.pack(fill="x", padx=15, pady=10)

        ttk.Button(
            btn_box, text="➕ Aggiungi Coinquilino", command=aggiungi_persona
        ).pack(side="left", padx=5)

        def salva_modifiche():
            for pid, ent in entries.items():
                val = ent.get().strip()
                if val:
                    self.persone[pid] = val
            self.salva_configurazione()
            self.reset_storico()
            self.aggiorna_settimane_ui()
            win.destroy()
            messagebox.showinfo("Successo", "Lista coinquilini aggiornata!")

        ttk.Button(btn_box, text="💾 Salva Modifiche", command=salva_modifiche).pack(
            side="right", padx=5
        )

    def get_date_settimane(self):
        try:
            anno = int(self.entry_anno.get())
            mese = self.combo_mese.current() + 1
            cal = calendar.Calendar(firstweekday=0)

            settimane = []
            for month_week in cal.monthdatescalendar(anno, mese):
                lunedi = month_week[0]
                domenica = month_week[-1]
                settimane.append((lunedi, domenica))
            return settimane
        except ValueError:
            return []

    def aggiorna_settimane_ui(self, event=None):
        """Aggiorna le caselle di spunta delle presenze in base al mese e alle persone attuali."""
        for widget in self.frame_presenze.winfo_children():
            widget.destroy()

        settimane = self.get_date_settimane()
        self.check_vars = {}

        for idx, (lun, dom) in enumerate(settimane, start=1):
            lbl_text = f"Sett. {idx} ({lun.strftime('%d/%m')} - {dom.strftime('%d/%m')}):"
            lbl_sett = ttk.Label(
                self.frame_presenze,
                text=lbl_text,
                font=("Segoe UI", 9, "bold"),
            )
            lbl_sett.grid(row=idx - 1, column=0, padx=8, pady=3, sticky="w")

            self.check_vars[idx] = {}
            col = 1
            for pid, nome in sorted(self.persone.items()):
                var = tk.BooleanVar(value=True)
                chk = ttk.Checkbutton(
                    self.frame_presenze, text=f"{pid}. {nome}", variable=var
                )
                chk.grid(row=idx - 1, column=col, padx=4, pady=3, sticky="w")
                self.check_vars[idx][pid] = var
                col += 1

    def estrai_equo(self, candidati, mansione):
        """Sceglie la persona con meno assegnazioni per quella mansione e in totale."""
        candidati_ordinati = sorted(
            candidati,
            key=lambda pid: (
                self.storico_mansioni[pid][mansione],
                self.storico_totale[pid],
                random.random(),
            ),
        )
        return candidati_ordinati[0]

    def genera_turni(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        settimane = self.get_date_settimane()

        for s_idx, (lun, dom) in enumerate(settimane, start=1):
            disponibili = [
                pid
                for pid, var in self.check_vars[s_idx].items()
                if var.get() is True
            ]

            if len(disponibili) < len(self.mansioni):
                messagebox.showerror(
                    "Errore Presenze",
                    f"Servono almeno {len(self.mansioni)} persone per la Settimana {s_idx}! Presenti: {len(disponibili)}",
                )
                return

            assegnati_settimana = {}
            candidati_rimasti = disponibili.copy()

            for m in self.mansioni:
                scelto = self.estrai_equo(candidati_rimasti, m)
                assegnati_settimana[m] = scelto
                candidati_rimasti.remove(scelto)

                self.storico_mansioni[scelto][m] += 1
                self.storico_totale[scelto] += 1

            range_date = f"{lun.strftime('%d/%m')} - {dom.strftime('%d/%m')}"
            valori_riga = [f"Settimana {s_idx}", range_date] + [
                f"{self.persone[assegnati_settimana[m]]} (#{assegnati_settimana[m]})"
                for m in self.mansioni
            ]

            tag_colore = "pari" if s_idx % 2 == 0 else "dispari"
            self.tree.insert("", "end", values=valori_riga, tags=(tag_colore,))

    def esporta_csv(self):
        if not self.tree.get_children():
            messagebox.showwarning(
                "Attenzione", "Genera prima i turni prima di esportare!"
            )
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV File", "*.csv"), ("Tutti i file", "*.*")],
            title="Salva Turni in CSV",
        )

        if filepath:
            with open(
                filepath, mode="w", newline="", encoding="utf-8"
            ) as file:
                writer = csv.writer(file, delimiter=";")
                mese_str = self.combo_mese.get()
                anno_str = self.entry_anno.get()
                writer.writerow(
                    [f"CALENDARIO TURNI PULIZIE - {mese_str.upper()} {anno_str}"]
                )
                writer.writerow([])

                writer.writerow(["Settimana", "Inizio - Fine"] + self.mansioni)
                for row_id in self.tree.get_children():
                    row = self.tree.item(row_id)["values"]
                    writer.writerow(row)

            messagebox.showinfo(
                "Successo", "Calendario esportato con successo in CSV!"
            )

    def esporta_png(self):
        if not self.tree.get_children():
            messagebox.showwarning(
                "Attenzione", "Genera prima i turni prima di esportare!"
            )
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("Immagine PNG", "*.png"), ("Tutti i file", "*.*")],
            title="Salva Tabella come PNG",
        )

        if not filepath:
            return

        mese_str = self.combo_mese.get()
        anno_str = self.entry_anno.get()
        titolo_banner = f"TURNI PULIZIE - {mese_str.upper()} {anno_str}"

        headers = ["SETTIMANA", "INIZIO - FINE"] + [m.upper() for m in self.mansioni]
        rows = [self.tree.item(r)["values"] for r in self.tree.get_children()]

        col_width = 175
        row_height = 42
        banner_height = 60
        padding = 20

        img_width = col_width * len(headers) + (padding * 2)
        img_height = banner_height + row_height * (len(rows) + 1) + (padding * 2)

        image = Image.new("RGB", (img_width, img_height), color="#FFFFFF")
        draw = ImageDraw.Draw(image)

        try:
            font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 20)
            font_bold = ImageFont.truetype("DejaVuSans-Bold.ttf", 13)
            font = ImageFont.truetype("DejaVuSans.ttf", 13)
        except OSError:
            font_title = font_bold = font = ImageFont.load_default()

        # Banner Titolo
        draw.rectangle(
            [padding, padding, img_width - padding, padding + banner_height],
            fill="#2C3E50",
        )
        draw.text(
            (padding + 20, padding + 18),
            titolo_banner,
            fill="#FFFFFF",
            font=font_title,
        )

        # Header Tabella
        y_header = padding + banner_height
        draw.rectangle(
            [padding, y_header, img_width - padding, y_header + row_height],
            fill="#34495E",
        )

        for i, header in enumerate(headers):
            x = padding + (i * col_width) + 15
            y = y_header + 13
            draw.text((x, y), str(header), fill="#FFFFFF", font=font_bold)

        # Righe Dati
        colors = ["#F8F9FA", "#EAECEE"]
        for row_idx, row in enumerate(rows):
            y_start = y_header + ((row_idx + 1) * row_height)
            bg_color = colors[row_idx % 2]

            draw.rectangle(
                [padding, y_start, img_width - padding, y_start + row_height],
                fill=bg_color,
            )

            for col_idx, cell_value in enumerate(row):
                x = padding + (col_idx * col_width) + 15
                y = y_start + 13
                draw.text((x, y), str(cell_value), fill="#2C3E50", font=font)

        # Bordo Esterno
        draw.rectangle(
            [padding, padding, img_width - padding, img_height - padding],
            outline="#BDC3C7",
            width=2,
        )

        image.save(filepath, "PNG")
        messagebox.showinfo(
            "Successo", f"Tabella per {mese_str} {anno_str} salvata come PNG!"
        )


if __name__ == "__main__":
    root = tk.Tk()
    app = TurniPulizieApp(root)
    root.mainloop()
