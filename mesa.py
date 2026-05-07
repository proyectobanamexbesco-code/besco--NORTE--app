import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
from PIL import Image
import os
import smtplib
from email.message import EmailMessage
import io
import time
from pypdf import PdfWriter

# --- RUTAS PARA LA NUBE ---
LOGO_PATH = "logo besco 2026.jpeg"

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="BESCO | Reportes Técnicos", layout="wide")

st.markdown("""
    <style>
    .stApp { color: #262730 !important; }
    .stButton > button { color: white !important; background-color: #E21836 !important; }
    h1, h2, h3 { color: #1E3A5F !important; }
    div[data-testid="stExpander"] div[role="button"] p { font-weight: bold !important; color: #1E3A5F !important; }
    </style>
    """, unsafe_allow_html=True)

class BESCO_PDF(FPDF):
    def __init__(self):
        super().__init__()
        self.section_count = 1

    def header(self):
        if os.path.exists(LOGO_PATH):
            self.image(LOGO_PATH, x=10, y=8, h=25)
        self.set_font('Arial', 'B', 12)
        self.set_text_color(30, 58, 95)
        self.set_xy(100, 15)
        self.cell(0, 10, 'REPORTE DE SERVICIO TÉCNICO', 0, 1, 'R')
        self.set_font('Arial', '', 9)
        self.set_x(100)
        self.cell(0, 5, f"Emisión: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1, 'R')
        self.ln(12)

    def add_custom_section(self, title):
        self.set_fill_color(30, 58, 95)
        self.set_font('Arial', 'B', 11)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, f"{self.section_count}. {title.upper()}", 0, 1, 'L', fill=True)
        self.section_count += 1
        self.ln(2)
        self.set_text_color(0, 0, 0)

    def photo_grid(self, title, photos, eq_index=0):
        if not photos:
            return

        self.add_custom_section(title)
        
        ancho_foto = 90
        alto_foto = 65
        espacio_vertical = 75
        margen_inferior_seguro = 280
        
        for i, foto in enumerate(photos):
            img = Image.open(foto).convert("RGB")
            id_foto = title.replace(" ", "_")
            marca_tiempo = int(time.time() * 1000)
            temp_p = f"temp_{id_foto}_eq{eq_index}_{marca_tiempo}_{i}.jpg"
            img.save(temp_p)
            
            col = i % 2
            
            if col == 0:
                if self.get_y() + espacio_vertical > margen_inferior_seguro:
                    self.add_page()
                    self.set_font('Arial', 'I', 9)
                    self.set_text_color(100, 100, 100)
                    self.cell(0, 6, f"(Continuación) {title}", 0, 1, 'L')
                    self.set_text_color(0, 0, 0)
                    self.ln(2)

            y_actual = self.get_y()
            self.image(temp_p, x=10 + (col * 95), y=y_actual, w=ancho_foto, h=alto_foto)
            
            if col == 1 or i == len(photos) - 1:
                self.set_y(y_actual + espacio_vertical)
        
        self.ln(5)

# --- FUNCIÓN DE CORREO AUTOMÁTICO (MODIFICADA PARA EL ASUNTO) ---
def enviar_correo(pdf_bytes, cliente, folio, sucursal, oficina, nombre_archivo, correos_extra):
    try:
        remitente = st.secrets["EMAIL_SENDER"]
        password = st.secrets["EMAIL_PASSWORD"]
        destinatarios = ["gerardo.mendez@besco.mx"]
        
        if correos_extra:
            extras = [correo.strip() for correo in correos_extra.split(",") if correo.strip()]
            destinatarios.extend(extras)

        msg = EmailMessage()
        
        # --- NUEVO ASUNTO DEL CORREO ---
        asunto = f"Reporte Fotográfico BESCO: {cliente}"
        if folio: asunto += f" | TK: {folio}"
        if sucursal: asunto += f" | Suc: {sucursal}"
        if oficina: asunto += f" | Of: {oficina}"
        
        msg['Subject'] = asunto
        msg['From'] = remitente
        msg['To'] = ", ".join(destinatarios) 
        msg.set_content(f"Se ha generado un nuevo reporte múltiple desde la aplicación BESCO.\n\nCliente: {cliente}\nFolio/TK: {folio}\nSucursal: {sucursal}\nOficina: {oficina}\n\nSe adjunta el documento PDF con la evidencia.")
        
        msg.add_attachment(pdf_bytes, maintype='application', subtype='pdf', filename=nombre_archivo)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(remitente, password)
            smtp.send_message(msg)
        return True
    except Exception as e:
        print(f"Error de correo: {e}")
        return False

# --- INTERFAZ ---
st.title("📑 Sistema de Evidencia Técnica BESCO")

st.subheader("1. Identificación General del Servicio")
col_cl1, col_cl2, col_cl3 = st.columns([2, 1, 1])
cliente = col_cl1.text_input("Cliente")
folio = col_cl2.text_input("Folio / OT / TK")
estado_op = col_cl3.selectbox("Estado Global de Operación", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], index=4)

col_loc1, col_loc2 = st.columns(2)
sucursal = col_loc1.text_input("Sucursal / Inmueble")
oficina = col_loc2.text_input("Oficina / Área específica")

c1, c2, c3, c4 = st.columns(4)
tecnico = c1.text_input("Técnico Asignado")
supervisor = c2.text_input("Supervisor")
tipo_serv = c3.selectbox("Servicio", ["Preventivo", "Correctivo", "Emergencia"])
referencia = c4.selectbox("Referencia", ["Con Ticket", "Sin Ticket"])

st.markdown("---")

st.subheader("2. Equipos a Reportar")
num_equipos = st.number_input("¿Cuántos equipos diferentes se atendieron?", min_value=1, max_value=20, value=1)

equipos_data = []

for i in range(num_equipos):
    st.markdown(f"### ⚙️ DETALLES DEL EQUIPO {i+1}")
    
    esp = st.selectbox("Categoría de Equipo", ["Ninguna", "Aire Acondicionado", "Tableros Eléctricos", "Hidroneumático", "Plantas de Emergencia", "Transformadores", "Otros"], key=f"esp_{i}")

    mediciones = {}
    otros_detalles = "" 

    if esp == "Aire Acondicionado":
        cols = st.columns(4)
        mediciones['P. Succión'] = cols[0].text_input("Succión (PSI)", key=f"suc_{i}")
        mediciones['P. Descarga'] = cols[1].text_input("Descarga (PSI)", key=f"des_{i}")
        mediciones['T. Salida'] = cols[2].text_input("Salida (°C)", key=f"sal_{i}")
        mediciones['Amp. Comp.'] = cols[3].text_input("Amperaje (A)", key=f"amp_{i}")
    elif esp == "Tableros Eléctricos":
        cols = st.columns(3)
        mediciones['V L1-L2'] = cols[0].text_input("V L1-L2", key=f"v_{i}")
        mediciones['Amp A'] = cols[1].text_input("Amp A", key=f"ampa_{i}")
        mediciones['Amp B'] = cols[2].text_input("Amp B", key=f"ampb_{i}")
    elif esp == "Otros":
        otros_detalles = st.text_area("Especifique detalles/mediciones:", key=f"otr_{i}")

    c_eq1, c_eq2, c_eq3 = st.columns(3)
    tag = c_eq1.text_input("TAG", key=f"tag_{i}")
    marca = c_eq2.text_input("Marca/Modelo", key=f"mar_{i}")
    capacidad = c_eq3.text_input("Capacidad", key=f"cap_{i}")

    comentarios = st.text_area("Comentarios y Observaciones", key=f"com_{i}")

    f_antes = st.file_uploader("Fotos ANTES", accept_multiple_files=True, key=f"f_ant_{i}")
    f_despues = st.file_uploader("Fotos DESPUÉS", accept_multiple_files=True, key=f"f_des_{i}")
    
    equipos_data.append({
        "numero": i + 1,
        "esp": esp,
        "mediciones": mediciones,
        "otros_detalles": otros_detalles,
        "tag": tag,
        "marca": marca,
        "capacidad": capacidad,
        "comentarios": comentarios,
        "f_antes": f_antes,
        "f_despues": f_despues
    })
    st.markdown("---")

st.subheader("3. Materiales Utilizados (Global)")
df_mat = st.data_editor(pd.DataFrame(columns=["Cantidad", "Descripción"]), num_rows="dynamic")

st.subheader("4. Evidencia Documental (Reporte Físico)")
st.info("📌 Cargue aquí una fotografía o un archivo PDF del reporte físico firmado y sellado por el cliente que ampara esta visita.")
f_folio = st.file_uploader("FOLIO BESCO", type=["jpg", "jpeg", "png", "pdf"], accept_multiple_files=False)

st.markdown("---")
st.subheader("5. Envío de Reporte")
st.info("💡 Tu reporte siempre se enviará a gerardo.mendez@besco.mx por seguridad.")
correos_adicionales = st.text_input("Agregar destinatarios extra (separe los correos con una coma)", placeholder="ejemplo@cliente.com")

if st.button("🚀 Generar Reporte Final Múltiple", type="primary"):
    pdf = BESCO_PDF()
    pdf.add_page()
    
    pdf.add_custom_section("Información General del Servicio")
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 7, f"Cliente: {cliente} | Folio: {folio}", 0, 1)
    
    loc_str = ""
    if sucursal: loc_str += f"Sucursal: {sucursal} "
    if oficina: loc_str += f"| Oficina: {oficina}"
    if loc_str: pdf.cell(0, 7, loc_str, 0, 1)

    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 7, f"ESTADO GLOBAL DE OPERACIÓN: {estado_op}/10", 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 7, f"Servicio: {tipo_serv} ({referencia}) | Técnico: {tecnico}", 0, 1)
    pdf.ln(5)

    for eq in equipos_data:
        if pdf.get_y() > 240: pdf.add_page()
        
        pdf.add_custom_section(f"EQUIPO {eq['numero']}: {eq['esp']}")
        
        if eq['tag'] or eq['marca']:
            pdf.set_font('Arial', 'B', 9)
            pdf.cell(0, 7, f"TAG: {eq['tag']} | Modelo: {eq['marca']} | Capacidad: {eq['capacidad']}", 0, 1)
            pdf.set_font('Arial', '', 10)

        valid_meds = {k: v for k, v in eq['mediciones'].items() if v}
        if valid_meds:
            for k, v in valid_meds.items():
                pdf.cell(60, 6, f"{k}:", 1); pdf.cell(130, 6, f"{v}", 1, 1)
            pdf.ln(2)
        
        if eq['esp'] == "Otros" and eq['otros_detalles']:
            pdf.multi_cell(0, 6, f"Detalles: {eq['otros_detalles']}", 1); pdf.ln(2)

        if eq['comentarios']:
            pdf.multi_cell(0, 6, f"Comentarios: {eq['comentarios']}", 1); pdf.ln(2)

        if eq['f_antes']: pdf.photo_grid(f"Evidencia Antes (Eq. {eq['numero']})", eq['f_antes'], eq['numero'])
        if eq['f_despues']: pdf.photo_grid(f"Evidencia Después (Eq. {eq['numero']})", eq['f_despues'], eq['numero'])
        pdf.ln(5)

    df_c = df_mat.dropna(subset=["Descripción"])
    if not df_c.empty:
        if pdf.get_y() > 220: pdf.add_page()
        pdf.add_custom_section("Materiales Utilizados (Global)")
        pdf.set_font('Arial', 'B', 9)
        pdf.cell(30, 7, "CANT.", 1, 0, 'C')
        pdf.cell(160, 7, "DESCRIPCIÓN", 1, 1, 'C')
        pdf.set_font('Arial', '', 9)
        for _, row in df_c.iterrows():
            pdf.cell(30, 7, str(row["Cantidad"]), 1); pdf.cell(160, 7, str(row["Descripción"]), 1, 1)

    if f_folio and not f_folio.name.lower().endswith('.pdf'):
        pdf.add_page()
        pdf.add_custom_section("FOLIO BESCO (Reporte Firmado y Sellado)")
        img = Image.open(f_folio).convert("RGB")
        temp_folio = "temp_folio_full.jpg"
        img.save(temp_folio)
        
        y_start = pdf.get_y()
        avail_w = 190
        avail_h = 280 - y_start
        
        img_w, img_h = img.size
        escala = min(avail_w/img_w, avail_h/img_h)
        final_w = img_w * escala
        final_h = img_h * escala
        x_pos = 10 + (190 - final_w) / 2  
        
        pdf.image(temp_folio, x=x_pos, y=y_start, w=final_w, h=final_h)

    pdf_bytes = pdf.output(dest='S').encode('latin-1')
    
    if f_folio and f_folio.name.lower().endswith('.pdf'):
        merger = PdfWriter()
        merger.append(io.BytesIO(pdf_bytes))
        merger.append(f_folio)
        salida_pdf = io.BytesIO()
        merger.write(salida_pdf)
        pdf_bytes = salida_pdf.getvalue()

    # --- NUEVO NOMBRE DE ARCHIVO PDF ---
    # Limpiamos los espacios en blanco adicionales para que el nombre del archivo se vea prolijo
    nom_cliente = cliente.strip() if cliente else "SinCliente"
    nom_folio = folio.strip() if folio else "SinFolio"
    nom_sucursal = f"_{sucursal.strip()}" if sucursal else ""
    nom_oficina = f"_{oficina.strip()}" if oficina else ""
    
    # El archivo se llamará: Reporte_BESCO_Cliente_Folio_Sucursal_Oficina.pdf
    # Ejemplo: Reporte_BESCO_Banamex_TK-9999_Centro_Piso2.pdf
    nombre_pdf = f"Reporte_BESCO_{nom_cliente}_{nom_folio}{nom_sucursal}{nom_oficina}.pdf"
    
    # Quitamos caracteres que podrían dar error en el nombre del archivo de Windows
    nombre_pdf = nombre_pdf.replace(" ", "_").replace("/", "-").replace("\\", "-")
    
    if "EMAIL_SENDER" in st.secrets:
        # Pasamos el nombre del archivo a la función de correo
        exito = enviar_correo(pdf_bytes, cliente, folio, sucursal, oficina, nombre_pdf, correos_adicionales)
        if exito:
            st.success(f"✅ ¡Reporte Listo y enviado a los destinatarios!")
        else:
            st.warning("El reporte se generó pero hubo un error al enviar el correo.")
    else:
        st.warning("⚠️ Reporte generado. (El envío por correo está inactivo).")

    st.download_button(
        label="📥 Descargar PDF a mi Celular",
        data=pdf_bytes,
        file_name=nombre_pdf,
        mime="application/pdf"
    )
