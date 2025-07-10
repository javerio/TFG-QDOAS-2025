
# -*- coding: utf-8 -*-

import numpy as np
import logging
import os
import sys

# Configuración del logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def procesar_archivo(nombre_archivo, inicio_espectro, fin_espectro):
    with open(nombre_archivo, 'r') as file:
        file.readline()  # Saltar encabezado
        array_datos = []
        for line in file:
            elementos = [float(x) for x in line.split()]
            array_datos.extend(elementos)

    cantidad_puntos = len(array_datos)
    espectro = np.linspace(inicio_espectro,
                           fin_espectro,
                           cantidad_puntos)

    salida = np.zeros((cantidad_puntos, 2))
    salida[:, 0] = (1 / espectro) * 1e7  # Convertir de cm⁻¹ a nm
    salida[:, 1] = array_datos

    return salida

def solicitar_valor(mensaje):
    while True:
        valor = input(mensaje)
        try:
            valor = float(valor)
            if valor > 0:
                return valor
            else:
                logger.error("El valor debe ser mayor que cero.")
        except ValueError:
            logger.error("Entrada no válida. Intente de nuevo.")

# Solicitar archivo de entrada
while True:
    nombre_archivo = input("Ingrese la ruta del archivo HITRAN (.xsc o .txt): ")
    if os.path.isfile(nombre_archivo) and nombre_archivo.lower().endswith(('.xsc', '.txt')):
        break
    else:
        logger.error("Archivo inválido. Intente de nuevo.")

# Rango espectral (en cm⁻¹)
inicio_espectro = solicitar_valor("Inicio del espectro (cm⁻¹): ")
fin_espectro = solicitar_valor("Fin del espectro (cm⁻¹): ")

# Nombres de molécula y descripción
molecula = input("Nombre de la molécula (ej. SO2): ")
descripcion = input("Descripción del archivo (ej. 298K): ")

# Directorio de salida
ruta_salida = input("Ruta del directorio de salida: ")
if not os.path.isdir(ruta_salida):
    logger.error("Ruta de salida no válida.")
    sys.exit()

output_file = os.path.join(ruta_salida, f"{molecula}_{descripcion}.xs")

# Verificación y procesamiento
if inicio_espectro >= fin_espectro:
    logger.error("El inicio del espectro debe ser menor que el final.")
else:
    resultado = procesar_archivo(nombre_archivo, inicio_espectro, fin_espectro)
    np.savetxt(output_file, resultado, delimiter='  ',
               header="X=wavelengths (nm)  Y=Cross section (cm^2/molecule)")
    logger.info(f"Archivo XS generado: {output_file}")
