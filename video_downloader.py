import os
import subprocess
import re
import time


def verificar_codec_rapido(url, limite_res, ytdlp_path):
    """Verifica si existe H.264 nativo. Si no, devuelve el codec principal disponible."""
    print("  🔍 Inspeccionando la metadata del video en el servidor...")
    
    # PASO 1: Buscar forzosamente si existe una versión en H.264 (avc)
    comando_h264 = [
        ytdlp_path,
        "--no-playlist",
        "-f", f"bestvideo[vcodec^=avc][height<={limite_res}]",
        "--print", "vcodec",
        url
    ]
    try:
        resultado = subprocess.run(
            comando_h264, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, check=True, timeout=45
        )
        codec = resultado.stdout.strip().lower()
        if codec and "avc" in codec:
            return True, codec  # True = Sí existe H.264
    except subprocess.CalledProcessError:
        pass
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, f"error: {e}"

    # PASO 2: Si no hay H.264, buscar cuál es el mejor codec disponible
    comando_general = [
        ytdlp_path,
        "--no-playlist",
        "-f", f"bestvideo[height<={limite_res}]/best[height<={limite_res}]",
        "--print", "vcodec",
        url
    ]
    try:
        resultado = subprocess.run(
            comando_general, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, check=True, timeout=45
        )
        codec = resultado.stdout.strip().lower()
        return False, codec  # False = No hay H.264, devolvemos el extraño
    except subprocess.CalledProcessError:
        return False, "desconocido"
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, f"error: {e}"


def renombrar_archivos_con_espacios(destino, extensiones, hora_inicio, archivo=None):
    """Encuentra el archivo descargado más recientemente tras hora_inicio y reemplaza '_' por espacios."""
    if not os.path.isdir(destino):
        return None

    ruta_original = archivo if archivo and os.path.isfile(archivo) else None
    if ruta_original is None:
        archivo_mas_reciente = None
        tiempo_mas_reciente = None
        for entrada in os.scandir(destino):
            if not entrada.is_file():
                continue
            nombre_lower = entrada.name.lower()
            if not any(nombre_lower.endswith(ext) for ext in extensiones):
                continue
            stat = entrada.stat()
            if stat.st_mtime >= hora_inicio:
                if tiempo_mas_reciente is None or stat.st_mtime > tiempo_mas_reciente:
                    tiempo_mas_reciente = stat.st_mtime
                    archivo_mas_reciente = entrada
        if archivo_mas_reciente is None:
            return None
        ruta_original = archivo_mas_reciente.path

    nombre_original = os.path.basename(ruta_original)
    if any(nombre_original.lower().endswith(ext) for ext in extensiones):
        nombre_sanitizado = nombre_original.replace('_', ' ')
        if nombre_sanitizado != nombre_original:
            ruta_nueva = os.path.join(destino, nombre_sanitizado)

            contador = 1
            while os.path.exists(ruta_nueva) and ruta_nueva != ruta_original:
                base, ext = os.path.splitext(nombre_sanitizado)
                ruta_nueva = os.path.join(destino, f"{base} ({contador}){ext}")
                contador += 1
            os.replace(ruta_original, ruta_nueva)
            return ruta_nueva
    return ruta_original


def construir_comando_video(opcion, destino, ytdlp_path, ffmpeg_dir, modo="compat"):
    """Construye el comando de yt-dlp para la descarga de video."""
    
    comando = [
        ytdlp_path,
        "--ffmpeg-location",
        ffmpeg_dir,
        "--no-playlist", 
        "--windows-filenames", 
        "--no-mtime" 
    ]

    opciones = {
        "1": {"limite": "1080", "etiqueta": "1080p"},
        "2": {"limite": "720",  "etiqueta": "720p"},
        "3": {"limite": "480",  "etiqueta": "480p"},
        "4": {"limite": "360",  "etiqueta": "360p"}
    }

    if opcion not in opciones:
        raise ValueError("Opción de video no válida")

    config = opciones[opcion]
    
    # Aplicamos la plantilla del nombre seguro (máximo 100 caracteres)
    plantilla_salida = os.path.join(destino, f"%(title).100s_[{config['etiqueta']}].%(ext)s")
    comando.extend(["--output", plantilla_salida])

    comando.extend(["--print", "after_move:filepath"])

    # Formatos limpios y universales
    if modo == "convertir":
        comando.extend([
            "--format", f"bestvideo[height<={config['limite']}]+bestaudio/best[height<={config['limite']}]",
            "--merge-output-format", "mp4",
            "--recode-video", "mp4",
            "--postprocessor-args", "ffmpeg:-c:v libx264 -c:a aac -movflags +faststart"
        ])
        return comando

    if modo == "nativo":
        comando.extend([
            "--format", f"bestvideo[height<={config['limite']}]+bestaudio/best[height<={config['limite']}]"
        ])
        return comando

    # Modo por defecto (compat): Intentamos buscar H.264/m4a, y si no, caemos al mejor disponible
    comando.extend([
        "--format",
        f"bestvideo[vcodec^=avc][height<={config['limite']}]+bestaudio[ext=m4a]/"
        f"bestvideo[height<={config['limite']}]+bestaudio/best[height<={config['limite']}]",
        "--merge-output-format", "mp4",
        "--embed-chapters"
    ])

    return comando


def extraer_progreso(linea):
    """Intenta extraer porcentaje, velocidad y ETA desde la salida de yt-dlp."""
    porcentaje = None
    velocidad = None
    eta = None

    match = re.search(r'(\d+(?:\.\d+)?)%|\[(\d+(?:\.\d+)?)%\]', linea)
    if match:
        porcentaje = match.group(1) or match.group(2)

    match = re.search(r'(\d+(?:\.\d+)?(?:\s?(?:KiB|MiB|GiB|KB|MB|GB)/s))', linea)
    if match:
        velocidad = match.group(1)

    match = re.search(r'ETA\s*([0-9]{1,2}:[0-9]{2}(?::[0-9]{2})?)', linea, re.IGNORECASE)
    if match:
        eta = match.group(1)
    else:
        match = re.search(r'ETA\s*([0-9]+\s*(?:m|min|mins|minute|minutes)\s*[0-9]+\s*(?:s|sec|secs|second|seconds)?)', linea, re.IGNORECASE)
        if match:
            eta = match.group(1)

    return porcentaje, velocidad, eta


def mostrar_barra_progreso(linea):
    porcentaje, velocidad, eta = extraer_progreso(linea)
    if porcentaje is None:
        return

    p = float(porcentaje)
    bloques = int(min(20, max(0, p // 5)))
    barra = "█" * bloques + "-" * (20 - bloques)
    info = f"{p:.1f}%"
    if velocidad:
        info += f"  |  Vel: {velocidad}"
    if eta:
        info += f"  |  ETA: {eta}"
    
    # Se asegura de imprimir correctamente en la misma línea
    print(f"\r  [{barra}] {info}", end="", flush=True)


def descargar_video(url, opcion, destino, ytdlp_path, ffmpeg_dir, modo="compat"):
    comando = construir_comando_video(opcion, destino, ytdlp_path, ffmpeg_dir, modo=modo)
    comando.append(url)

    hora_inicio = time.time()
    try:
        proceso = subprocess.Popen(
            comando,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            universal_newlines=True
        )

        salida = []
        procesando_conversion = False
        archivo_final = None
        
        for linea in proceso.stdout:
            if not linea:
                continue
            linea = linea.strip()
            if not linea:
                continue

            salida.append(linea)
            if os.path.isfile(linea):
                archivo_final = linea
                continue
            if any(indicador in linea.lower() for indicador in (
                "has already been downloaded", "converting video", "re-encoding"
            )):
                if not procesando_conversion:
                    print("\n  --- Descarga completada. Iniciando conversión (puede tardar) ---")
                    procesando_conversion = True
            if not procesando_conversion:
                mostrar_barra_progreso(linea)

        proceso.wait()
        print("\n")

        if proceso.returncode != 0:
            ultimas = [linea for linea in salida[-12:] if linea]
            mensaje = "\n".join(ultimas) if ultimas else "La descarga terminó con un error."
            return False, mensaje, None

        try:
            archivo_final = renombrar_archivos_con_espacios(
                destino,
                (".mp4", ".mkv", ".webm", ".avi", ".mov"),
                hora_inicio,
                archivo_final
            )
        except OSError as e:
            print(f"\n  [AVISO] No se pudo normalizar el nombre del archivo: {e}")
        if archivo_final is None:
            return False, "yt-dlp terminó sin error, pero no se pudo localizar el archivo final.", None
        return True, "", archivo_final
    except Exception as e:
        print("\n")
        return False, str(e), None