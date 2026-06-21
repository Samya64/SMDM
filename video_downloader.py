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


def construir_comando_video(opcion, destino, ytdlp_path, ffmpeg_dir, modo="compat"):
    """Construye el comando de yt-dlp para la descarga de video."""
    comando = [
        ytdlp_path,
        "--ffmpeg-location",
        ffmpeg_dir,
        "--no-playlist",
        "--no-part"
    ]

    # 1080p sigue siendo la opción por defecto y se prioriza el formato compatible.
    opciones = {
        "1": {
            "altura": 1080,
            "etiqueta": "1080p",
            "formato_compat": "bestvideo[height<=1080][vcodec^=avc]+bestaudio[ext=m4a]/best[height<=1080][vcodec^=avc]"
        },
        "2": {
            "altura": 720,
            "etiqueta": "720p",
            "formato_compat": "bestvideo[height<=720][vcodec^=avc]+bestaudio[ext=m4a]/best[height<=720][vcodec^=avc]"
        },
        "3": {
            "altura": 480,
            "etiqueta": "480p",
            "formato_compat": "bestvideo[height<=480][vcodec^=avc]+bestaudio[ext=m4a]/best[height<=480][vcodec^=avc]"
        },
        "4": {
            "altura": 360,
            "etiqueta": "360p",
            "formato_compat": "bestvideo[height<=360][vcodec^=avc]+bestaudio[ext=m4a]/best[height<=360][vcodec^=avc]"
        }
    }

    if opcion not in opciones:
        raise ValueError("Opción de video no válida")

    config = opciones[opcion]
    base = config["formato_compat"]

    if modo == "convertir":
        formato = f"bestvideo[height<={config['altura']}]+bestaudio/best"
        comando.extend([
            "--format",
            formato,
            "--merge-output-format",
            "mp4",
            "--recode-video",
            "mp4",
            "--recode-audio",
            "aac",
            "--output",
            os.path.join(destino, f"%(title)s_[{config['etiqueta']}].%(ext)s")
        ])
        return comando

    if modo == "nativo":
        formato = f"bestvideo[height<={config['altura']}]+bestaudio/best"
        comando.extend([
            "--format",
            formato,
            "--output",
            os.path.join(destino, f"%(title)s_[{config['etiqueta']}].%(ext)s")
        ])
        return comando

    # Modo por defecto: priorizar explícitamente el codec H.264/AAC para evitar AV1 en la descarga inicial.
    comando.extend([
        "--format",
        base,
        "--merge-output-format",
        "mp4",
        "--embed-chapters",
        "--output",
        os.path.join(destino, f"%(title)s_[{config['etiqueta']}].%(ext)s")
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
        # si no hay porcentaje claro, mostramos la línea tal como viene para que el usuario vea el progreso real.
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


def descargar_video(url, opcion, destino, ytdlp_path, ffmpeg_dir, modo="compat"):
    """Ejecuta la descarga de video y devuelve True/False según el resultado."""
    comando = construir_comando_video(opcion, destino, ytdlp_path, ffmpeg_dir, modo=modo)
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
            (".mp4", ".mkv", ".webm", ".avi", ".mov")
        )
        return True, ""
    except Exception as e:
        print("\n")
        return False, str(e)
