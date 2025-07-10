
import serial
import time
import os
import pandas as pd
import numpy as np
import logging
import threading
from datetime import datetime
from math import cos, sin, acos, radians, degrees, asin
from astral import LocationInfo
from astral.sun import sun

# ---------- CONFIGURACIÓN DEL LOGGER ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- FUNCIÓN PARA CALCULAR EL ÁNGULO SOLAR ----------
def calcular_sza(fecha_hora, latitud, longitud):
    location = LocationInfo(latitude=latitud, longitude=longitud)
    s = sun(location.observer, date=fecha_hora.date(), tzinfo=fecha_hora.tzinfo)
    solar_vector = location.solar_elevation(fecha_hora)
    sza = 90 - solar_vector
    return sza

# ---------- CONEXIÓN AL SENSOR BNO055 ----------
def leer_angulos_bno055(puerto='/dev/ttyUSB0', baudrate=115200):
    try:
        ser = serial.Serial(puerto, baudrate, timeout=1)
        time.sleep(2)
        ser.flushInput()
        linea = ser.readline().decode('utf-8').strip()
        partes = linea.split(',')
        if len(partes) >= 3:
            eva = float(partes[0])
            vaa = float(partes[1])
            roll = float(partes[2])
            return eva, vaa
    except Exception as e:
        logger.warning(f"No se pudo leer del BNO055: {e}")
    return None, None

# ---------- CÁLCULO DEL PROMEDIO DARK ----------
def calcular_dark_correction(input_directory_dark):
    d_files = [f for f in os.listdir(input_directory_dark) if f.endswith('.txt')]
    if not d_files:
        logger.error("No se encontraron archivos de dark correction.")
        raise FileNotFoundError("No dark files found.")
    espectros = []
    for file in d_files:
        path = os.path.join(input_directory_dark, file)
        try:
            _, spectre = np.loadtxt(path, skiprows=13, unpack=True)
            espectros.append(spectre)
        except Exception as e:
            logger.error(f"Error en {file}: {e}")
    return np.mean(espectros, axis=0)

# ---------- MONITORIZACIÓN DE NUEVOS ARCHIVOS ----------
def esperar_nuevo_archivo(directorio, existentes):
    while True:
        actuales = set(f for f in os.listdir(directorio) if f.endswith('.txt'))
        nuevos = actuales - existentes
        if nuevos:
            return nuevos.pop()
        time.sleep(1)

# ---------- LECTURA DE ESPECTRO Y GENERACIÓN .SPE y .CLB ----------
def procesar_archivo(nombre_archivo, dark, eva, vaa, sza, output_dir, fr_time, fecha, lambda_central):
    full_path = os.path.join(directorio_medidas, nombre_archivo)
    lambda_nm, espectro = np.loadtxt(full_path, skiprows=13, unpack=True)
    espectro_corr = espectro - dark
    archivo_base = os.path.splitext(nombre_archivo)[0]

    spe_path = os.path.join(output_dir, f"{archivo_base}.spe")
    with open(spe_path, 'w') as f:
        f.write("Measured spectrum\n")
        f.write(f"{archivo_base}\n")
        f.write(f"{lambda_central:.2f}\n")
        f.write(f"{fecha} {fr_time:.6f}\n")
        f.write(f"{vaa:.2f} {eva:.2f} {sza:.2f}\n")
        f.write("1.0\n")
        for l, val in zip(lambda_nm, espectro_corr):
            f.write(f"{l:.2f} {val:.0f}\n")

    clb_path = os.path.join(output_dir, f"{archivo_base}.clb")
    with open(clb_path, 'w') as f:
        f.write("Instrumental calibration file\n")
        f.write(f"{archivo_base}\n")
        f.write(f"{lambda_central:.2f}\n")
        f.write(f"{fecha} {fr_time:.6f}\n")
        for l in lambda_nm:
            f.write(f"{l:.2f}\n")

    logger.info(f"Archivos generados: {spe_path}, {clb_path}")

# ---------- PROGRAMA PRINCIPAL ----------
if __name__ == "__main__":
    input_directory_dark = input("Directorio con archivos dark: ")
    directorio_medidas = input("Directorio donde se guardan los .txt de OceanView: ")
    output_dir = input("Directorio de salida para .spe y .clb: ")
    lat = float(input("Latitud de la localización (ej. 28.48): "))
    lon = float(input("Longitud de la localización (ej. -16.32): "))
    lambda_central = float(input("Longitud de onda central (nm): "))

    dark = calcular_dark_correction(input_directory_dark)
    logger.info("Dark correction calculada.")

    logger.info("Esperando nuevos archivos de OceanView...")

    archivos_existentes = set(os.listdir(directorio_medidas))
    while True:
        nuevo = esperar_nuevo_archivo(directorio_medidas, archivos_existentes)
        archivos_existentes.add(nuevo)

        logger.info(f"Nuevo archivo detectado: {nuevo}")
        ahora = datetime.now()
        eva, vaa = leer_angulos_bno055()
        if eva is None or vaa is None:
            logger.warning("No se pudieron leer ángulos del sensor. Se omite el archivo.")
            continue
        sza = calcular_sza(ahora, lat, lon)
        fecha = ahora.strftime("%d/%m/%Y")
        fr_time = ahora.hour + ahora.minute/60 + ahora.second/3600

        procesar_archivo(nuevo, dark, eva, vaa, sza, output_dir, fr_time, fecha, lambda_central)
