import os
import subprocess
import re


def renombrar_archivos_con_espacios(destino, extensiones):
    """Reemplaza '_' por espacios en nombres de archivos descargados."""
    if not os.path.isdir(destino):
        return

    for entrada in os.scandir(destino):
        if not entrada.is_file():
            continue

        nombre_lower = entrada.name.lower()
        if not any(nombre_lower.endswith(ext) for ext in extensiones):
            continue

        nombre_sanitizado = entrada.name.replace('_', ' ')
        if nombre_sanitizado == entrada.name:
            continue

        ruta_original = entrada.path
        ruta_nueva = os.path.join(destino, nombre_sanitizado)

        contador = 1
        while os.path.exists(ruta_nueva) and ruta_nueva != ruta_original:
            base, ext = os.path.splitext(nombre_sanitizado)
            ruta_nueva = os.path.join(destino, f"{base} ({contador}){ext}")
            contador += 1

        os.rename(ruta_original, ruta_nueva)


def construir_comando_audio(destino, ytdlp_path, ffmpeg_dir, formato="mp3", calidad="192K"):
    """Construye el comando de yt-dlp para la descarga de audio."""
    comando = [
        ytdlp_path,
        "--ffmpeg-location",
        ffmpeg_dir,
        "--no-playlist",
        "--no-part",
        "--format",
        "bestaudio/best",
        "--extract-audio",
        "--audio-format",
        formato,
        "--output",
        os.path.join(destino, "%(title)s.%(ext)s")
    ]

    if calidad and formato == "mp3":
        comando.extend(["--audio-quality", calidad])

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

    # Regex más estricta para evitar mezclar minutos con segundos.
    # Busca primero formatos tipo 01:23 o 01:23:45.
    match = re.search(r'ETA\s*([0-9]{1,2}:[0-9]{2}(?::[0-9]{2})?)', linea, re.IGNORECASE)
    if match:
        eta = match.group(1)
    else:
        # Luego acepta formatos tipo 1m 23s o 1 min 23 sec.
        match = re.search(r'ETA\s*([0-9]+\s*(?:m|min|mins|minute|minutes)\s*[0-9]+\s*(?:s|sec|secs|second|seconds)?)', linea, re.IGNORECASE)
        if match:
            eta = match.group(1)

    return porcentaje, velocidad, eta


def mostrar_barra_progreso(linea):
    porcentaje, velocidad, eta = extraer_progreso(linea)
    if porcentaje is None:
        print(f"  {linea}")
        return

    p = float(porcentaje)
    bloques = int(min(20, max(0, p // 5)))
    barra = "█" * bloques + "-" * (20 - bloques)
    info = f"{p:.1f}%"
    if velocidad:
        info += f"  |  Vel: {velocidad}"
    if eta:
        info += f"  |  ETA: {eta}"
    print(f"\r  [{barra}] {info}", end="", flush=True)


def descargar_audio(url, destino, ytdlp_path, ffmpeg_dir, formato="mp3", calidad="192K"):
    """Ejecuta la descarga de audio y devuelve True/False según el resultado."""
    comando = construir_comando_audio(destino, ytdlp_path, ffmpeg_dir, formato=formato, calidad=calidad)
    comando.append(url)

    try:
        proceso = subprocess.Popen(
            comando,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        salida = []
        for linea in proceso.stdout:
            if not linea:
                continue
            linea = linea.strip()
            if linea:
                salida.append(linea)
                mostrar_barra_progreso(linea)

        proceso.wait()
        print("\n")
        if proceso.returncode != 0:
            ultimas = [linea for linea in salida[-12:] if linea]
            mensaje = "\n".join(ultimas) if ultimas else "La descarga terminó con un error."
            return False, mensaje

        renombrar_archivos_con_espacios(
            destino,
            (".mp3", ".wav", ".ogg", ".m4a", ".aac", ".webm")
        )
        return True, ""
    except Exception as e:
        print("\n")
        return False, str(e)
