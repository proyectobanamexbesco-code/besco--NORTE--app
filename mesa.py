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
st.set_page_config(page_title="BESCO NORTE | Reportes Técnicos", layout="wide")

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
        self.cell(0, 10, 'REPORTE DE SERVICIO TÉCNICO - NORTE', 0, 1, 'R')
        self.set_font('Arial', '', 9)
        self.set_x(100)
        self.cell(0, 5, f"Emisión del Reporte: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1, 'R')
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

def enviar_correo(pdf_bytes, cliente, folio, sucursal, oficina, nombre_archivo, correos_extra, fecha_ejec, correo_destino):
    try:
        remitente = st.secrets["EMAIL_SENDER"]
        password = st.secrets["EMAIL_PASSWORD"]
        
        destinatarios = [correo_destino]
        
        if correos_extra:
            extras = [correo.strip() for correo in correos_extra.split(",") if correo.strip()]
            destinatarios.extend(extras)

        msg = EmailMessage()
        
        asunto = f"Reporte Fotográfico BESCO NORTE: {cliente}"
        if folio: asunto += f" | TK: {folio}"
        if oficina: asunto += f" | Of: {oficina}"
        
        msg['Subject'] = asunto
        msg['From'] = remitente
        msg['To'] = ", ".join(destinatarios) 
        msg.set_content(f"Se ha generado un nuevo reporte múltiple desde la aplicación BESCO NORTE.\n\nFecha de Ejecución: {fecha_ejec}\nOficina: {oficina}\nCliente: {cliente}\nFolio/TK: {folio}\nSucursal: {sucursal}\n\nSe adjunta el documento PDF con la evidencia.")
        
        msg.add_attachment(pdf_bytes, maintype='application', subtype='pdf', filename=nombre_archivo)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(remitente, password)
            smtp.send_message(msg)
        return True
    except Exception as e:
        print(f"Error de correo: {e}")
        return False

# --- INTERFAZ ---
st.title("📑 Sistema de Evidencia - BESCO NORTE")

st.subheader("1. Identificación General del Servicio")
col_cl1, col_cl2, col_cl3, col_cl4 = st.columns([2, 1, 1, 1.5])
cliente = col_cl1.text_input("Cliente")
folio = col_cl2.text_input("Folio / OT / TK")
estado_op = col_cl3.selectbox("Estado Global", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], index=4)
fecha_ejecucion = col_cl4.date_input("Fecha de Ejecución", datetime.now())

col_loc1, col_loc2 = st.columns(2)
sucursal = col_loc1.text_input("Sucursal / Inmueble")
oficina = col_loc2.selectbox("Oficina Responsable", [
    "Torreon", "Monterrey", "Ciudad Juarez", "Reynosa", "Chihuahua", "Saltillo", "Tampico"
])

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
        "numero": i + 1, "esp": esp, "mediciones": mediciones, "otros_detalles": otros_detalles,
        "tag": tag, "marca": marca, "capacidad": capacidad, "comentarios": comentarios,
        "f_antes": f_antes, "f_despues": f_despues
    })
    st.markdown("---")

st.subheader("3. Materiales Utilizados (Global)")
df_mat = st.data_editor(pd.DataFrame(columns=["Cantidad", "Descripción"]), num_rows="dynamic")

st.subheader("4. Evidencia Documental (Reporte Físico)")
st.info("📌 Cargue aquí una fotografía o un archivo PDF del reporte físico firmado y sellado por el cliente.")
f_folio = st.file_uploader("FOLIO BESCO", type=["jpg", "jpeg", "png", "pdf"], accept_multiple_files=False)

st.markdown("---")
st.subheader("5. Envío de Reporte")

# --- LÓGICA DE ASIGNACIÓN DE CORREO INFORMATIVO ---
mapeo_correos = {
    "Torreon": "alberto.ruiz@besco.mx",
