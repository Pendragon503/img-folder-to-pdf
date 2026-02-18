import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageOps
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"}


def natural_key(path: str):
    """
    Orden natural: img2 < img10
    Si tus archivos son 001, 002, 010 igual queda bien.
    """
    name = os.path.basename(path).lower()
    return [int(s) if s.isdigit() else s for s in re.split(r"(\d+)", name)]


def iter_images(input_dir: str):
    files = []
    for name in os.listdir(input_dir):
        ext = os.path.splitext(name)[1].lower()
        if ext in SUPPORTED_EXT:
            files.append(os.path.join(input_dir, name))
    files.sort(key=natural_key)
    return files


def image_size_in_points(img: Image.Image, dpi_fallback: int = 300):
    # ReportLab usa puntos: 72 puntos = 1 pulgada
    w_px, h_px = img.size
    dpi = img.info.get("dpi", None)
    if isinstance(dpi, tuple) and len(dpi) >= 2 and dpi[0] and dpi[1]:
        x_dpi, y_dpi = dpi[0], dpi[1]
    else:
        x_dpi = y_dpi = dpi_fallback

    w_pt = (w_px / x_dpi) * 72.0
    h_pt = (h_px / y_dpi) * 72.0
    return w_pt, h_pt


def convert_folder_to_pdf(input_dir: str, output_pdf: str, dpi_fallback: int = 300):
    images = iter_images(input_dir)
    if not images:
        raise FileNotFoundError("No encontré imágenes soportadas en esa carpeta.")

    c = None

    for path in images:
        with Image.open(path) as img:
            # Respeta orientación EXIF (fotos de celular)
            img = ImageOps.exif_transpose(img)

            # Evita problemas con alpha/CMYK/etc.
            if img.mode in ("RGBA", "LA"):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.getchannel("A"))
                img = bg
            elif img.mode != "RGB":
                img = img.convert("RGB")

            page_w, page_h = image_size_in_points(img, dpi_fallback=dpi_fallback)

            if c is None:
                c = canvas.Canvas(output_pdf, pagesize=(page_w, page_h))
            else:
                c.setPageSize((page_w, page_h))

            c.drawImage(
                ImageReader(img),
                0, 0,
                width=page_w,
                height=page_h,
                preserveAspectRatio=False,
                mask="auto"
            )
            c.showPage()

    c.save()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Imágenes → PDF (página completa)")
        self.geometry("720x340")
        self.resizable(False, False)
        
        # Colores modernos
        self.bg_color = "#1e293b"  # Azul oscuro
        self.fg_color = "#f8fafc"  # Blanco suave
        self.accent_color = "#3b82f6"  # Azul brillante
        self.secondary_bg = "#334155"  # Gris azulado
        self.button_color = "#10b981"  # Verde moderno
        self.button_hover = "#059669"  # Verde oscuro
        
        self.configure(bg=self.bg_color)

        self.input_dir = tk.StringVar(value="")
        self.output_pdf = tk.StringVar(value="")
        self.dpi_fallback = tk.IntVar(value=300)

        self._build_ui()

    def _build_ui(self):
        pad = 10

        # Título principal con gradiente visual
        title_frame = tk.Frame(self, bg=self.accent_color, height=60)
        title_frame.pack(fill="x", pady=0)
        title_frame.pack_propagate(False)
        
        title = tk.Label(
            title_frame, 
            text="📄 Convertir imágenes a PDF", 
            font=("Segoe UI", 16, "bold"),
            bg=self.accent_color,
            fg="white"
        )
        title.pack(expand=True)

        # Frame principal con fondo
        frm = tk.Frame(self, bg=self.bg_color)
        frm.pack(fill="both", expand=True, padx=pad, pady=10)

        # Carpeta imágenes
        row1 = tk.Frame(frm, bg=self.bg_color)
        row1.pack(fill="x", pady=8)
        tk.Label(
            row1, 
            text="📁 Carpeta de imágenes:", 
            width=20, 
            anchor="w",
            bg=self.bg_color,
            fg=self.fg_color,
            font=("Segoe UI", 10)
        ).pack(side="left")
        tk.Entry(
            row1, 
            textvariable=self.input_dir,
            bg=self.secondary_bg,
            fg=self.fg_color,
            insertbackground=self.fg_color,
            relief="flat",
            font=("Segoe UI", 9)
        ).pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=4)
        tk.Button(
            row1, 
            text="Elegir...", 
            command=self.pick_folder, 
            width=12,
            bg=self.accent_color,
            fg="white",
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 9, "bold")
        ).pack(side="left")

        # Salida PDF
        row2 = tk.Frame(frm, bg=self.bg_color)
        row2.pack(fill="x", pady=8)
        tk.Label(
            row2, 
            text="💾 Guardar PDF en:", 
            width=20, 
            anchor="w",
            bg=self.bg_color,
            fg=self.fg_color,
            font=("Segoe UI", 10)
        ).pack(side="left")
        tk.Entry(
            row2, 
            textvariable=self.output_pdf,
            bg=self.secondary_bg,
            fg=self.fg_color,
            insertbackground=self.fg_color,
            relief="flat",
            font=("Segoe UI", 9)
        ).pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=4)
        tk.Button(
            row2, 
            text="Elegir...", 
            command=self.pick_output, 
            width=12,
            bg=self.accent_color,
            fg="white",
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 9, "bold")
        ).pack(side="left")

        # DPI fallback (opcional)
        row3 = tk.Frame(frm, bg=self.bg_color)
        row3.pack(fill="x", pady=8)
        tk.Label(
            row3, 
            text="⚙️ DPI si no viene:", 
            width=20, 
            anchor="w",
            bg=self.bg_color,
            fg=self.fg_color,
            font=("Segoe UI", 10)
        ).pack(side="left")
        tk.Spinbox(
            row3, 
            from_=72, 
            to=600, 
            textvariable=self.dpi_fallback, 
            width=10,
            bg=self.secondary_bg,
            fg=self.fg_color,
            buttonbackground=self.accent_color,
            relief="flat",
            font=("Segoe UI", 9)
        ).pack(side="left")
        tk.Label(
            row3, 
            text="(afecta tamaño de impresión, no la calidad visual)", 
            fg="#94a3b8",
            bg=self.bg_color,
            font=("Segoe UI", 8, "italic")
        ).pack(side="left", padx=10)

        # Botones
        row4 = tk.Frame(frm, bg=self.bg_color)
        row4.pack(fill="x", pady=(10, 0))

        self.btn_run = tk.Button(
            row4, 
            text="✨ Crear PDF", 
            command=self.run, 
            width=18, 
            height=2,
            bg=self.button_color,
            fg="white",
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 11, "bold")
        )
        self.btn_run.pack(side="right")

        self.status = tk.Label(
            frm, 
            text="✓ Listo para comenzar", 
            anchor="w", 
            fg="#94a3b8",
            bg=self.bg_color,
            font=("Segoe UI", 9)
        )
        self.status.pack(fill="x", pady=(8, 0))
        
        # Footer con información del desarrollador
        footer = tk.Frame(self, bg=self.secondary_bg, height=45)
        footer.pack(side="bottom", fill="x")
        footer.pack_propagate(False)
        
        dev_info = tk.Label(
            footer,
            text="Desarrollador: William Martínez  |  GitHub: Pendragon503",
            bg=self.secondary_bg,
            fg="#94a3b8",
            font=("Segoe UI", 9)
        )
        dev_info.pack(expand=True)

    def pick_folder(self):
        folder = filedialog.askdirectory(title="Selecciona la carpeta de imágenes")
        if folder:
            self.input_dir.set(folder)
            self.status.config(text=f"📁 Carpeta seleccionada: {folder}", fg="#10b981")

            # Si todavía no eligió salida, proponemos un nombre
            if not self.output_pdf.get():
                suggested = os.path.join(folder, "salida.pdf")
                self.output_pdf.set(suggested)

    def pick_output(self):
        path = filedialog.asksaveasfilename(
            title="Guardar PDF como",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")]
        )
        if path:
            self.output_pdf.set(path)
            self.status.config(text=f"💾 Salida seleccionada: {path}", fg="#10b981")

    def run(self):
        input_dir = self.input_dir.get().strip()
        output_pdf = self.output_pdf.get().strip()

        if not input_dir or not os.path.isdir(input_dir):
            messagebox.showerror("Falta carpeta", "Selecciona una carpeta válida de imágenes.")
            return

        if not output_pdf:
            messagebox.showerror("Falta salida", "Selecciona dónde guardar el PDF.")
            return

        # Evitar “guardar en carpeta inexistente”
        out_dir = os.path.dirname(output_pdf) or "."
        if not os.path.isdir(out_dir):
            messagebox.showerror("Ruta inválida", "La carpeta destino del PDF no existe.")
            return

        try:
            self.btn_run.config(state="disabled")
            self.status.config(text="⏳ Creando PDF...", fg="#f59e0b")
            self.update_idletasks()

            convert_folder_to_pdf(input_dir, output_pdf, dpi_fallback=int(self.dpi_fallback.get()))

            self.status.config(text=f"✓ PDF creado: {output_pdf}", fg="#10b981")
            messagebox.showinfo("Listo", f"PDF creado correctamente:\n{output_pdf}")

        except Exception as e:
            self.status.config(text=f"❌ Error: {str(e)}", fg="#ef4444")
            messagebox.showerror("Error", str(e))
        finally:
            self.btn_run.config(state="normal")


if __name__ == "__main__":
    App().mainloop()
