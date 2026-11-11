import os
import subprocess
import sys
import re
import time


# Evitar UnicodeEncodeError en Windows al imprimir caracteres especiales/box-drawing
if sys.platform.startswith('win') and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Importamos el módulo local updater y sus variables de control visual
try:
    import updater
    from updater import VERDE, AMARILLO, ROJO, CYAN, RESET
except ImportError:
    print("[ERROR] No se encontró 'updater.py' en la misma carpeta para compilar.")
    input("Presiona Enter para salir...")
    sys.exit(1)

from audio_downloader import descargar_audio
from audio_menu import mostrar_menu_audio, obtener_formato_audio
from video_downloader import descargar_video, verificar_codec_rapido
from video_menu import mostrar_menu_video
from version import __version__

# --- Archivo donde se guarda la carpeta elegida por el usuario ---
CONFIG_FILE = "config.txt"

# --- Ruta base del proyecto ---
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Rutas necesarias para ejecutar yt-dlp y ffmpeg ---
YTDLP_PATH = updater.YTDLP_PATH
FFMPEG_DIR = BASE_DIR


def limpiar_pantalla():
    # Esto ayuda a que los colores ANSI funcionen correctamente en Windows.
    os.system("")
    os.system("cls" if os.name == "nt" else "clear")


def mostrar_titulo(titulo):
    # Muestra solo el arte ASCII sin borde adicional para evitar problemas de visualización.
    ascii_lines = [
        r"""
 ___ ___ __  __ ___ _    ___                        
/ __|_ _|  \/  | _ \ |  | __|                       
\__ \| || |\/| |  _/ |__| _|                        
|___/___|_| _|_|_|_|____|___|  __ ___ ___ ___   _   
|  \/  | | | | ||_   _|_ _|  \/  | __|   \_ _| /_\  
| |\/| | |_| | |__| |  | || |\/| | _|| |) | | / _ \ 
|_|_ |_|\___/|____|_| |___|_| _|_|___|___/___/_/ \_\
|   \ / _ \ \    / / \| | |  / _ \ /_\ |   \        
| |) | (_) \ \/\/ /| .` | |_| (_) / _ \| |) |       
|___/_\___/ \_/\_/ |_|\_|____\___/_/ \_\___/        
|  \/  | /_\ | \| | /_\ / __| __| _ \               
| |\/| |/ _ \| .` |/ _ \ (_ | _||   /               
|_|  |_/_/ \_\_|\_/_/ \_\___|___|_|_\               
"""
    ]

    for linea in ascii_lines:
        print(f"  {CYAN}{linea}{RESET}")
    print()


def mostrar_error(mensaje):
    print(f"\n  {ROJO}[ERROR] {mensaje}{RESET}")


def pausar():
    input(f"\n  {AMARILLO}Presiona Enter para continuar...{RESET}")


def normalizar_ruta(ruta):
    ruta = ruta.replace('\x00', '').strip().strip('"')
    return os.path.abspath(os.path.expanduser(ruta))


def cargar_configuracion():
    ruta_config = os.path.join(BASE_DIR, CONFIG_FILE)
    if os.path.exists(ruta_config):
        try:
            with open(ruta_config, "r", encoding="utf-8", errors="ignore") as f:
                contenido = f.read().replace('\x00', '').strip()
                if contenido:
                    ruta = normalizar_ruta(contenido)
                    os.makedirs(ruta, exist_ok=True)
                    return ruta
        except (OSError, ValueError) as e:
            print(f"\n  {AMARILLO}[AVISO] No se pudo usar '{CONFIG_FILE}': {e}{RESET}")

    ruta_defecto = os.path.join(os.path.expanduser("~"), "Downloads", "yt-dlp")
    ruta_defecto = normalizar_ruta(ruta_defecto)
    guardar_configuracion(ruta_defecto)
    return ruta_defecto


def guardar_configuracion(nueva_ruta):
    nueva_ruta = normalizar_ruta(nueva_ruta)
    try:
        os.makedirs(nueva_ruta, exist_ok=True)
        with open(os.path.join(BASE_DIR, CONFIG_FILE), "w", encoding="utf-8") as f:
            f.write(nueva_ruta)
    except Exception as e:
        raise RuntimeError(f"No se pudo guardar la ruta de descarga: {e}")

def mostrar_menu(destino, alerta_sistema):
    limpiar_pantalla()

    # Encabezado principal del programa.
    mostrar_titulo("SIMPLE MULTIMEDIA DOWNLOAD MANAGER - yt-dlp GUI")

    # Alerta sutil integrada (Minimalismo puro)
    if alerta_sistema:
        print(f"  {alerta_sistema}")
        print(f"  {CYAN}{'─' * 58}{RESET}")

    print(f"  {CYAN}Ruta:{RESET} {destino}\n")
    print(f"  {CYAN}┌──────────────────────────────────────────────────┐{RESET}")
    print(f"  {CYAN}│{RESET}  [1]  Descargar video                            {CYAN}│{RESET}")
    print(f"  {CYAN}│{RESET}  [2]  Descargar audio                            {CYAN}│{RESET}")
    print(f"  {CYAN}│{RESET}  [3]  Cambiar carpeta de descarga                {CYAN}│{RESET}")
    print(f"  {CYAN}│{RESET}  [4]  Actualizar / Reparar Componentes (.exe)    {CYAN}│{RESET}")
    print(f"  {CYAN}│{RESET}  [5]  Salir                                      {CYAN}│{RESET}")
    print(f"  {CYAN}└──────────────────────────────────────────────────┘{RESET}\n")

def verificar_archivos(destino):
    print("\n  Archivos disponibles en la carpeta de descarga:")
    print("  ─────────────────────────────────────────────────────")
    if os.path.isdir(destino):
        try:
            extensiones = (".mp4", ".mkv", ".webm", ".avi", ".mov", ".m4a", ".mp3", ".wav", ".ogg")
            archivos = [
                f for f in os.listdir(destino)
                if f.lower().endswith(extensiones)
            ]
            if archivos:
                for archivo in archivos:
                    print(f"  {archivo}")
            else:
                print("  (No se encontraron archivos multimedia)")
        except OSError as e:
            print(f"  (No se pudo leer la carpeta: {e})")
    else:
        print("  (La carpeta de descarga no existe o no se puede leer)")
    print("  ─────────────────────────────────────────────────────")


def validar_destino(destino):
    if not os.path.isdir(destino):
        try:
            os.makedirs(destino, exist_ok=True)
        except Exception:
            return False
    return os.access(destino, os.W_OK)


def obtener_estado_del_sistema():
    # Recolecta el estado actual de los componentes externos.
    return (
        updater.comprobar_estado_ytdlp(),
        updater.comprobar_estado_ffmpeg(),
        updater.comprobar_estado_deno()
    )


def obtener_alerta(status_yt, status_ff, status_dn):
    # Decide si mostrar una alerta simple en el menú principal.
    if "No instalado" in status_yt or "No instalado" in status_ff or "No instalado" in status_dn:
        return f"{ROJO} [Alerta]: Faltan componentes. Ejecuta la opción [4] para reparar.{RESET}"
    elif "Disp." in status_yt or "Disp." in status_ff or "Disp." in status_dn:
        return f"{AMARILLO} [Info]: Hay actualizaciones disponibles. Revisa la opción [4].{RESET}"
    return ""


def mostrar_configuracion_video(opcion):
    opciones = {
        "1": "1080p (H.264 + AAC)",
        "2": "720p (H.264 + AAC)",
        "3": "480p (H.264 + AAC)",
        "4": "360p (H.264 + AAC)",
    }
    print(f"\n  Configuración seleccionada: Video {opciones.get(opcion, opcion)}")


def mostrar_configuracion_audio(formato, calidad):
    if formato == "mp3" and calidad:
        detalle = f"{formato.upper()} ({calidad})"
    else:
        detalle = formato.upper()
    print(f"\n  Configuración seleccionada: Audio {detalle}")


def detectar_error_codec(mensaje):
    texto = mensaje.lower()
    return any(
        patron in texto
        for patron in (
            "requested format is not available",
            "no matching format found",
            "no video formats found",
            "format not available",
            "video format not available",
            "requested video format",
            "requested format"
        )
    )


def obtener_duracion_video(archivo, ffmpeg_dir):
    """Obtiene la duración total del video en segundos usando ffprobe (si existe) o ffmpeg."""
    ffprobe_exe = os.path.join(ffmpeg_dir, "ffprobe.exe")
    if not os.path.exists(ffprobe_exe):
        ffprobe_exe = "ffprobe"
        
    comando = [
        ffprobe_exe, "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", archivo
    ]
    try:
        resultado = subprocess.run(comando, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=5)
        duracion = float(resultado.stdout.strip())
        if duracion > 0:
            return duracion
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return None


def convertir_a_h264(archivo, ffmpeg_dir):
    if not archivo or not os.path.exists(archivo):
        return False, "No se encontró el archivo descargado."

    duracion_total = obtener_duracion_video(archivo, ffmpeg_dir)

    ffmpeg_exe = os.path.join(ffmpeg_dir, "ffmpeg.exe")
    if not os.path.exists(ffmpeg_exe):
        ffmpeg_exe = "ffmpeg"

    base, _ = os.path.splitext(archivo)
    salida = base + "_h264.mp4"
    salida_temporal = base + "_h264.tmp.mp4"

    comando = [
        ffmpeg_exe, "-y", "-nostats", "-progress", "pipe:1", "-i", archivo,
        "-c:v", "libx264", "-c:a", "aac",
        "-movflags", "+faststart", salida_temporal
    ]

    print(f"\n  {CYAN}Iniciando conversión a H.264...{RESET}")
    tiempo_inicio_cronometro = time.time()
    largo_barra = 25
    proceso = None

    try:
        proceso = subprocess.Popen(
            comando, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", errors="replace", bufsize=1
        )
        for linea in proceso.stdout:
            if not linea.startswith("out_time="):
                continue
            tiempo_crudo = linea[len("out_time="):].strip()
            try:
                horas, minutos, segundos = tiempo_crudo.split(":")
                segundos_procesados = (
                    float(horas) * 3600 + float(minutos) * 60 + float(segundos)
                )
                if duracion_total:
                    porcentaje = min(100.0, segundos_procesados / duracion_total * 100)
                    bloques_llenos = int(round(porcentaje / 100 * largo_barra))
                    barra_texto = "█" * bloques_llenos + " " * (largo_barra - bloques_llenos)
                    print(
                        f"\r  {CYAN}[{barra_texto}]{RESET} "
                        f"{porcentaje:.1f}% convertido...",
                        end="", flush=True
                    )
                else:
                    print(
                        f"\r  {CYAN}Progreso de conversión:{RESET} "
                        f"{tiempo_crudo[:11]}...",
                        end="", flush=True
                    )
            except ValueError:
                continue

        proceso.wait()

        if proceso.returncode == 0:
            if not os.path.isfile(salida_temporal) or os.path.getsize(salida_temporal) == 0:
                eliminar_si_existe(salida_temporal)
                return False, "FFmpeg terminó sin generar un archivo válido."
            os.replace(salida_temporal, salida)
            if duracion_total:
                barra_llena = "█" * largo_barra
                print(f"\r  {CYAN}[{barra_llena}]{RESET} 100.0% convertido...", end="", flush=True)
            tiempo_total_segundos = int(round(time.time() - tiempo_inicio_cronometro))
            if tiempo_total_segundos < 60:
                texto_duracion = f"{tiempo_total_segundos} segundos"
            else:
                m = tiempo_total_segundos // 60
                s = tiempo_total_segundos % 60
                texto_duracion = f"{m} minuto{'s' if m > 1 else ''} y {s} segundo{'s' if s != 1 else ''}"

            print(f"\n  {VERDE}¡Conversión completada con éxito! [{texto_duracion}]{RESET}")
            return True, salida

        eliminar_si_existe(salida_temporal)
        return False, "La conversión falló durante el proceso de FFmpeg."
    except Exception as e:
        if proceso is not None and proceso.poll() is None:
            proceso.terminate()
            try:
                proceso.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proceso.kill()
                proceso.wait()
        eliminar_si_existe(salida_temporal)
        return False, str(e)
                
def eliminar_si_existe(ruta):
    if not ruta or not os.path.exists(ruta):
        return True
    try:
        os.remove(ruta)
        return True
    except OSError as e:
        print(f"\n  {AMARILLO}[AVISO] No se pudo eliminar '{ruta}': {e}{RESET}")
        return False


def main():
    # Establecer título de la consola
    if sys.platform.startswith('win'):
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW(f"SMDM {__version__}")
        except Exception:
            pass
    else:
        sys.stdout.write(f"\033]0;SMDM {__version__}\a")
        sys.stdout.flush()

    destino = cargar_configuracion()
    
    limpiar_pantalla()
    print("\n  Comprobando entorno portable...")
    
    while True:
        # Recolectamos el estado de los componentes cada vez que se pinta el menú.
        status_yt, status_ff, status_dn = obtener_estado_del_sistema()
        alerta_sistema = obtener_alerta(status_yt, status_ff, status_dn)

        mostrar_menu(destino, alerta_sistema)
        opcion = input(" Elige una opción [1-5]: ").strip()

        if opcion == "1":
            mostrar_menu_video()
            opcion_video = input("  Elige una opción [1-5]: ").strip()
            if opcion_video == "5":
                continue
            if opcion_video not in ["1", "2", "3", "4"]:
                mostrar_error("Opción inválida.")
                pausar()
                continue

            if "No instalado" in status_yt:
                mostrar_error("yt-dlp.exe no está instalado. Ve a la opción [4].")
                pausar()
                continue
            if "No instalado" in status_ff:
                mostrar_error("FFmpeg no está instalado. Ve a la opción [4].")
                pausar()
                continue

            if not validar_destino(destino):
                mostrar_error("No se puede escribir en la carpeta de destino.")
                pausar()
                continue

            while True:
                mostrar_configuracion_video(opcion_video)
                url = input("\n  Pega la URL: ").strip().replace('\x00', '')
                if not url:
                    continue

                # 1. Definimos los límites para la inspección según la opción elegida
                limites = {"1": "1080", "2": "720", "3": "480", "4": "360"}
                limite_res = limites.get(opcion_video, "1080")
                
                # 2. Inspeccionamos el codec antes de descargar nada
                print("\n  🔍 Verificando compatibilidad en el servidor...")
                tiene_h264, codec_detectado = verificar_codec_rapido(url, limite_res, YTDLP_PATH)
                if codec_detectado.startswith("error:"):
                    mostrar_error(f"No se pudo inspeccionar el video: {codec_detectado[6:]}")
                    continue
                modo_elegido = "compat"
                necesita_conversion = False  # <--- NUEVA BANDERA

                # 3. Lógica inteligente de decisión
                if tiene_h264:
                    print(f"  {VERDE}✓ Versión H.264 nativa encontrada. Descarga directa activada.{RESET}")
                    modo_elegido = "compat"
                    
                elif codec_detectado and "avc" not in codec_detectado and codec_detectado != "desconocido":
                    # Identificamos el nombre real para mostrárselo al usuario
                    if "av01" in codec_detectado:
                        nombre_codec = "AV1"
                    elif "vp09" in codec_detectado:
                        nombre_codec = "VP9"
                    elif "hevc" in codec_detectado or "h265" in codec_detectado:
                        nombre_codec = "H.265 (HEVC)"
                    else:
                        nombre_codec = codec_detectado.upper()
                    
                    print(f"\n  {AMARILLO}⚠️ ATENCIÓN: No hay H.264. El codec original es '{nombre_codec}'.{RESET}")
                    print("  ¿Qué deseas hacer?")
                    print("  [1] Convertir a H.264 (Recomendado - Máxima compatibilidad)")
                    print("  [2] Mantener el formato original (Más rápido)")
                    
                    while True:
                        resp = input("\n  Elige una opción [1 o 2]: ").strip()
                        if resp == "1":
                            modo_elegido = "nativo"        # Lo bajamos puro
                            necesita_conversion = True     # Le decimos a Python que lo convierta
                            break
                        elif resp == "2":
                            modo_elegido = "nativo"
                            break
                        print("  Opción inválida.")
                else:
                    print(f"  {CYAN}Iniciando descarga estándar...{RESET}")

                # 4. Lanzamos la descarga
                if necesita_conversion:
                    print(f"\n  Descargando archivo original para luego convertir...\n")
                else:
                    print(f"\n  Descargando en modo: {modo_elegido}...\n")
                    
                ok, mensaje, archivo_descargado = descargar_video(
                    url, opcion_video, destino, YTDLP_PATH, FFMPEG_DIR,
                    modo=modo_elegido
                )

                if not ok and detectar_error_codec(mensaje) and modo_elegido == "compat":
                    print("\n  El formato compatible no está disponible; reintentando con el mejor formato nativo...")
                    ok, mensaje, archivo_descargado = descargar_video(
                        url, opcion_video, destino, YTDLP_PATH, FFMPEG_DIR,
                        modo="nativo"
                    )
                
                if ok:
                    if necesita_conversion:
                        if archivo_descargado:
                            ok_conv, mensaje_conv = convertir_a_h264(archivo_descargado, FFMPEG_DIR)
                            if ok_conv:
                                eliminado = eliminar_si_existe(archivo_descargado)
                                print(f"\n  {VERDE}¡Finalizado con éxito!{RESET}")
                                if not eliminado:
                                    print("  El archivo convertido y el original permanecen en la carpeta.")
                            else:
                                mostrar_error(f"{mensaje_conv} El archivo original se conservó.")
                        else:
                            mostrar_error("No se pudo localizar el archivo descargado para convertirlo.")
                    else:
                        print(f"\n  {VERDE}¡Finalizado con éxito!{RESET}")
                else:
                    mostrar_error(mensaje)

                # ========================================================
                # AQUÍ QUEDA LA OPCIÓN DE REPETIR (Justo al final del bucle)
                # ========================================================
                verificar_archivos(destino)
                respuesta = input("\n  ¿Descargar otro video con la misma configuración? [S/N]: ").strip().upper()
                if respuesta != "S":
                    break
        
        elif opcion == "2":
            mostrar_menu_audio(destino)
            opcion_audio = input("  Elige una opción [1-5]: ").strip()
            if opcion_audio == "5":
                continue
            if opcion_audio not in ["1", "2", "3", "4"]:
                mostrar_error("Opción inválida.")
                pausar()
                continue

            if "No instalado" in status_yt:
                mostrar_error("yt-dlp.exe no está instalado. Ve a la opción [4].")
                pausar()
                continue
            if "No instalado" in status_ff:
                mostrar_error("FFmpeg no está instalado. Ve a la opción [4].")
                pausar()
                continue

            if not validar_destino(destino):
                mostrar_error("No se puede escribir en la carpeta de destino.")
                pausar()
                continue

            formato, calidad = obtener_formato_audio(opcion_audio)

            while True:
                mostrar_configuracion_audio(formato, calidad)
                url = input("\n  Pega la URL: ").strip().replace('\x00', '')
                if not url:
                    continue

                print(f"\n  Descargando audio en formato {formato.upper()}...\n")
                ok, mensaje = descargar_audio(url, destino, YTDLP_PATH, FFMPEG_DIR, formato=formato, calidad=calidad)
                if ok:
                    print("\n  ¡Finalizado!")
                else:
                    mostrar_error(mensaje)

                verificar_archivos(destino)
                respuesta = input("\n  ¿Descargar otro archivo con la misma configuración? [S/N]: ").strip().upper()
                if respuesta != "S":
                    break

        elif opcion == "3":
            limpiar_pantalla()
            nueva_ruta = input(f"\n Carpeta actual: {destino}\n\n Nueva ruta: ").strip().replace('"', '').replace('\x00', '')
            if nueva_ruta:
                try:
                    nueva_ruta = normalizar_ruta(nueva_ruta)
                    guardar_configuracion(nueva_ruta)
                    destino = nueva_ruta
                    print("\n Carpeta actualizada.")
                except Exception as e:
                    mostrar_error(str(e))
                time.sleep(1)

        elif opcion == "4":
            # Ejecuta el actualizador externo y luego vuelve a cargar la ruta guardada.
            updater.arrancar_actualizador()
            destino = cargar_configuracion()

        elif opcion == "5":
            print("\n ¡Hasta luego!")
            time.sleep(1)
            break
        else:
            mostrar_error("Opción inválida.")
            pausar()

if __name__ == "__main__":
    main()