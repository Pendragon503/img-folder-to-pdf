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
        self.geometry("720x260")
        self.resizable(False, False)

        self.input_dir = tk.StringVar(value="")
        self.output_pdf = tk.StringVar(value="")
        self.dpi_fallback = tk.IntVar(value=300)

        self._build_ui()

    def _build_ui(self):
        pad = 10

        title = tk.Label(self, text="Convertir carpeta de imágenes a 1 PDF", font=("Segoe UI", 14, "bold"))
        title.pack(pady=(12, 6))

        frm = tk.Frame(self)
        frm.pack(fill="x", padx=pad, pady=6)

        # Carpeta imágenes
        row1 = tk.Frame(frm)
        row1.pack(fill="x", pady=6)
        tk.Label(row1, text="Carpeta de imágenes:", width=18, anchor="w").pack(side="left")
        tk.Entry(row1, textvariable=self.input_dir).pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Button(row1, text="Elegir...", command=self.pick_folder, width=12).pack(side="left")

        # Salida PDF
        row2 = tk.Frame(frm)
        row2.pack(fill="x", pady=6)
        tk.Label(row2, text="Guardar PDF en:", width=18, anchor="w").pack(side="left")
        tk.Entry(row2, textvariable=self.output_pdf).pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Button(row2, text="Elegir...", command=self.pick_output, width=12).pack(side="left")

        # DPI fallback (opcional)
        row3 = tk.Frame(frm)
        row3.pack(fill="x", pady=6)
        tk.Label(row3, text="DPI si no viene:", width=18, anchor="w").pack(side="left")
        tk.Spinbox(row3, from_=72, to=600, textvariable=self.dpi_fallback, width=10).pack(side="left")
        tk.Label(row3, text="(afecta tamaño de impresión, no la calidad visual)", fg="gray").pack(side="left", padx=10)

        # Botones
        row4 = tk.Frame(self)
        row4.pack(fill="x", padx=pad, pady=(10, 0))

        self.btn_run = tk.Button(row4, text="Crear PDF", command=self.run, width=16, height=2)
        self.btn_run.pack(side="right")

        self.status = tk.Label(self, text="Listo.", anchor="w", fg="gray")
        self.status.pack(fill="x", padx=pad, pady=(8, 0))

    def pick_folder(self):
        folder = filedialog.askdirectory(title="Selecciona la carpeta de imágenes")
        if folder:
            self.input_dir.set(folder)
            self.status.config(text=f"Carpeta seleccionada: {folder}")

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
            self.status.config(text=f"Salida seleccionada: {path}")

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
            self.status.config(text="Creando PDF...")
            self.update_idletasks()

            convert_folder_to_pdf(input_dir, output_pdf, dpi_fallback=int(self.dpi_fallback.get()))

            self.status.config(text=f"PDF creado: {output_pdf}")
            messagebox.showinfo("Listo", f"PDF creado correctamente:\n{output_pdf}")

        except Exception as e:
            self.status.config(text="Error.")
            messagebox.showerror("Error", str(e))
        finally:
            self.btn_run.config(state="normal")


if __name__ == "__main__":
    App().mainloop()
