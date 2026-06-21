import os
import subprocess
import urllib.request
import zipfile
import io
import time
import json
import sys

# Evitar UnicodeEncodeError en Windows al imprimir caracteres especiales/box-drawing
if sys.platform.startswith('win') and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# --- Ruta base del proyecto ---
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Rutas de los ejecutables que el programa gestiona ---
YTDLP_PATH = os.path.join(BASE_DIR, "yt-dlp.exe")
DENO_PATH = os.path.join(BASE_DIR, "deno.exe")
FFMPEG_PATH = os.path.join(BASE_DIR, "ffmpeg.exe")
FFPROBE_PATH = os.path.join(BASE_DIR, "ffprobe.exe")

# --- Colores para mensajes en consola ---
VERDE = "\033[92m"
AMARILLO = "\033[93m"
ROJO = "\033[91m"
CYAN = "\033[96m"
RESET = "\033[0m"

# --- Estado visual del ecosistema (se actualiza según la comprobación) ---
ESTADOS = {
    "ytdlp": f"{CYAN}[ Comprobando... ]{RESET}",
    "ffmpeg": f"{CYAN}[ Comprobando... ]{RESET}",
    "deno": f"{CYAN}[ Comprobando... ]{RESET}"
}


def limpiar_pantalla():
    # Esto ayuda a que los colores ANSI funcionen correctamente en Windows.
    os.system("")
    os.system("cls" if os.name == "nt" else "clear")


def mostrar_encabezado(titulo):
    # Se usa un ancho fijo para que el texto quede bien centrado dentro del recuadro.
    ancho_texto = max(46, len(titulo) + 4)
    borde = "═" * (ancho_texto + 2)

    print(f"  ╔{borde}╗")
    print(f"  ║ {titulo.center(ancho_texto)} ║")
    print(f"  ╚{borde}╝\n")


def archivo_valido(ruta):
    # Evita aceptar archivos vacíos o incompletos tras una descarga.
    return os.path.isfile(ruta) and os.path.getsize(ruta) > 0


def mostrar_progreso(actual, total, tiempo_inicio, prefijo="Descargando"):
    tiempo_transcurrido = time.time() - tiempo_inicio
    velocidad = actual / tiempo_transcurrido if tiempo_transcurrido > 0 else 0
    
    if velocidad > 1024 * 1024:
        txt_vel = f"{velocidad / (1024*1024):.2f} MB/s"
    else:
        txt_vel = f"{velocidad / 1024:.2f} KB/s"
        
    if total > 0:
        porcentaje = (actual / total) * 100
        bloques = int(porcentaje // 4)
        barra = "█" * bloques + "-" * (25 - bloques)
        print(f"\r  >> {prefijo}: |{barra}| {porcentaje:.1f}% ({actual / (1024*1024):.1f}/{total / (1024*1024):.1f} MB) ─ {VERDE}{txt_vel}{RESET}", end="", flush=True)
    else:
        print(f"\r  >> {prefijo}: Descargando... ({actual / (1024*1024):.1f} MB) ─ {VERDE}{txt_vel}{RESET}", end="", flush=True)

def comprobar_bloqueo(ruta_archivo):
    # Comprueba si el archivo está siendo usado por otro proceso.
    if os.path.exists(ruta_archivo):
        try:
            with open(ruta_archivo, "ab"):
                pass
        except PermissionError:
            return True
    return False


def gestionar_backup(ruta, crear=True):
    ruta_bak = ruta + ".bak"
    if crear:
        try:
            if os.path.exists(ruta_bak): os.remove(ruta_bak)
            if os.path.exists(ruta): os.rename(ruta, ruta_bak)
            return True
        except Exception:
            return False
    else:
        try:
            if os.path.exists(ruta): os.remove(ruta)
            if os.path.exists(ruta_bak): os.rename(ruta_bak, ruta)
        except Exception:
            pass

def limpiar_backup(ruta):
    # Limpia el respaldo si la descarga se completó correctamente.
    ruta_bak = ruta + ".bak"
    if os.path.exists(ruta_bak):
        try:
            os.remove(ruta_bak)
        except Exception:
            pass

# ==========================================
# SECCIÓN DE COMPROBACIÓN DE VERSIONES
# ==========================================

def comprobar_estado_ytdlp():
    if not os.path.exists(YTDLP_PATH):
        return f"{ROJO}[ No instalado ]{RESET}"
    
    v_local = None
    try:
        res = subprocess.run([YTDLP_PATH, "--version"], capture_output=True, text=True, timeout=3)
        v_local = res.stdout.strip()
    except Exception:
        pass

    v_remota = None
    try:
        req = urllib.request.Request("https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4) as response:
            datos = json.loads(response.read().decode('utf-8'))
            v_remota = datos.get("tag_name", "").strip()
    except Exception:
        return f"{CYAN}[ Error de Red ]{RESET}"

    if v_local and v_remota and (v_local == v_remota):
        return f"{VERDE}[ Al día ({v_local}) ]{RESET}"
    elif v_local and v_remota:
        return f"{AMARILLO}[ Actualización Disp. ({v_remota}) ]{RESET}"
    return f"{AMARILLO}[ Requiere Verificar ]{RESET}"

def comprobar_estado_ffmpeg():
    if not os.path.exists(FFMPEG_PATH):
        return f"{ROJO}[ No instalado ]{RESET}"
        
    v_local_str = None
    try:
        res = subprocess.run([FFMPEG_PATH, "-version"], capture_output=True, text=True, timeout=3)
        lineas = res.stdout.splitlines()
        if lineas: v_local_str = lineas[0]
    except Exception:
        pass

    v_remota = None
    try:
        req = urllib.request.Request("https://www.gyan.dev/ffmpeg/builds/release-version", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4) as response:
            v_remota = response.read().decode('utf-8').strip()
    except Exception:
        return f"{CYAN}[ Error de Red ]{RESET}"

    if v_remota and v_local_str and (v_remota in v_local_str):
        return f"{VERDE}[ Al día ]{RESET}"
    elif v_remota and v_local_str:
        return f"{AMARILLO}[ Actualización Disp. (v{v_remota}) ]{RESET}"
    return f"{AMARILLO}[ Requiere Verificar ]{RESET}"

def comprobar_estado_deno():
    if not os.path.exists(DENO_PATH):
        return f"{ROJO}[ No instalado ]{RESET}"

    v_local = None
    try:
        res = subprocess.run([DENO_PATH, "--version"], capture_output=True, text=True, timeout=3)
        lineas = res.stdout.splitlines()
        if lineas:
            partes = lineas[0].split()
            if len(partes) >= 2 and partes[0].lower() == "deno":
                v_local = partes[1].lstrip('v')
    except Exception:
        pass

    v_remota = None
    try:
        req = urllib.request.Request("https://dl.deno.land/release-latest.txt", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4) as response:
            v_remota = response.read().decode('utf-8').strip().lstrip('v')
    except Exception:
        return f"{CYAN}[ Error de Red ]{RESET}"

    if v_local and v_remota and (v_local == v_remota):
        return f"{VERDE}[ Al día (v{v_local}) ]{RESET}"
    elif v_local and v_remota:
        return f"{AMARILLO}[ Actualización Disp. (v{v_remota}) ]{RESET}"
    return f"{AMARILLO}[ Requiere Verificar ]{RESET}"

def verificar_todo_el_ecosistema():
    # Revisa todos los componentes una vez antes de mostrar el menú.
    global ESTADOS
    ESTADOS["ytdlp"] = comprobar_estado_ytdlp()
    ESTADOS["ffmpeg"] = comprobar_estado_ffmpeg()
    ESTADOS["deno"] = comprobar_estado_deno()

# ==========================================
# PROCESAMIENTO DE DESCARGAS Y ACTUALIZACIONES
# ==========================================

def actualizar_ytdlp():
    mostrar_encabezado("ACTUALIZAR YT-DLP")

    if comprobar_bloqueo(YTDLP_PATH):
        print("  [ERROR] yt-dlp.exe está bloqueado. Cierra el gestor de descargas.")
        return False

    if "Al día" in ESTADOS["ytdlp"]:
        print("  [INFO] Omitiendo descarga de yt-dlp.exe (Ya está actualizado).")
        return True

    tiene_backup = gestionar_backup(YTDLP_PATH, crear=True)
    print("  >> Descargando ejecutable desde GitHub...")
    url_ytdlp = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
    try:
        req = urllib.request.Request(url_ytdlp, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            total_size = int(response.info().get('Content-Length', 0))
            bytes_descargados = 0
            tiempo_inicio = time.time()
            
            with open(YTDLP_PATH, "wb") as f:
                while True:
                    chunk = response.read(1024 * 64)
                    if not chunk:
                        break
                    f.write(chunk)
                    bytes_descargados += len(chunk)
                    mostrar_progreso(bytes_descargados, total_size, tiempo_inicio, "yt-dlp.exe")

            if not archivo_valido(YTDLP_PATH):
                raise Exception("el archivo descargado está vacío o incompleto")

            limpiar_backup(YTDLP_PATH)
            print("\n\n  [OK] yt-dlp.exe actualizado con éxito.")
            return True
    except Exception as e:
        print(f"\n  [ERROR] Falló la descarga: {e}")
        if tiene_backup: gestionar_backup(YTDLP_PATH, crear=False)
        return False

def actualizar_ffmpeg():
    # Descarga el paquete oficial de FFmpeg y sustituye ambos binarios.
    mostrar_encabezado("ACTUALIZAR FFMPEG Y FFPROBE")

    for ruta in [FFMPEG_PATH, FFPROBE_PATH]:
        if comprobar_bloqueo(ruta):
            print(f"  [ERROR] El archivo '{os.path.basename(ruta)}' está bloqueado.")
            return False

    if "Al día" in ESTADOS["ffmpeg"]:
        print("  [INFO] Omitiendo descarga del pack FFmpeg (Ya está actualizado).")
        return True

    backup_ffmpeg = gestionar_backup(FFMPEG_PATH, crear=True)
    backup_ffprobe = gestionar_backup(FFPROBE_PATH, crear=True)

    print("  >> Descargando paquete oficial (Essentials 103 MB)...")
    url_ffmpeg = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    
    try:
        req = urllib.request.Request(url_ffmpeg, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            total_size = int(response.info().get('Content-Length', 0))
            bytes_descargados = 0
            tiempo_inicio = time.time()
            zip_en_memoria = io.BytesIO()
            
            while True:
                chunk = response.read(1024 * 256)
                if not chunk: break
                zip_en_memoria.write(chunk)
                bytes_descargados += len(chunk)
                mostrar_progreso(bytes_descargados, total_size, tiempo_inicio, "FFmpeg Pack")
        
        print("\n\n  >> Extrayendo binarios en memoria...")
        zip_en_memoria.seek(0)
        
        with zipfile.ZipFile(zip_en_memoria) as archivo_zip:
            extraidos = 0
            for ruta_interna in archivo_zip.namelist():
                ruta_destino_final = None
                if ruta_interna.endswith("ffmpeg.exe"): ruta_destino_final = FFMPEG_PATH
                elif ruta_interna.endswith("ffprobe.exe"): ruta_destino_final = FFPROBE_PATH
                
                if ruta_destino_final:
                    nombre_binario = os.path.basename(ruta_interna)
                    with archivo_zip.open(ruta_interna) as origen, open(ruta_destino_final, "wb") as destino:
                        destino.write(origen.read())
                    print(f"  [OK] Reemplazado: {nombre_binario}")
                    extraidos += 1
            
            if extraidos == 2 and archivo_valido(FFMPEG_PATH) and archivo_valido(FFPROBE_PATH):
                limpiar_backup(FFMPEG_PATH)
                limpiar_backup(FFPROBE_PATH)
                print("\n  ¡FFmpeg y FFprobe actualizados correctamente!")
                return True
            else:
                raise Exception("Zip corrupto o incompleto")
                
    except Exception as e:
        print(f"\n  [ERROR] Ocurrió un fallo: {e}")
        if backup_ffmpeg: gestionar_backup(FFMPEG_PATH, crear=False)
        if backup_ffprobe: gestionar_backup(FFPROBE_PATH, crear=False)
        return False

def actualizar_deno():
    # Ejecuta el proceso nativo de actualización de Deno o lo descarga si no está instalado.
    mostrar_encabezado("ACTUALIZAR DENO")

    if comprobar_bloqueo(DENO_PATH):
        print("  [ERROR] deno.exe está bloqueado.")
        return False

    if not os.path.exists(DENO_PATH):
        print("  [INFO] deno.exe no está instalado. Descargándolo desde GitHub...")
        tiene_backup = gestionar_backup(DENO_PATH, crear=True)
        url_deno = "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip"
        try:
            req = urllib.request.Request(url_deno, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as response:
                total_size = int(response.info().get('Content-Length', 0))
                bytes_descargados = 0
                tiempo_inicio = time.time()
                zip_en_memoria = io.BytesIO()
                
                while True:
                    chunk = response.read(1024 * 64)
                    if not chunk:
                        break
                    zip_en_memoria.write(chunk)
                    bytes_descargados += len(chunk)
                    mostrar_progreso(bytes_descargados, total_size, tiempo_inicio, "deno.zip")
            
            print("\n\n  >> Extrayendo deno.exe...")
            zip_en_memoria.seek(0)
            with zipfile.ZipFile(zip_en_memoria) as archivo_zip:
                extraido = False
                for ruta_interna in archivo_zip.namelist():
                    if ruta_interna.endswith("deno.exe"):
                        with archivo_zip.open(ruta_interna) as origen, open(DENO_PATH, "wb") as destino:
                            destino.write(origen.read())
                        extraido = True
                        break
            
            if extraido and archivo_valido(DENO_PATH):
                limpiar_backup(DENO_PATH)
                print("\n  [OK] deno.exe instalado con éxito.")
                return True
            else:
                raise Exception("El archivo extraído está vacío o incompleto.")
        except Exception as e:
            print(f"\n  [ERROR] Falló la descarga de Deno: {e}")
            if tiene_backup:
                gestionar_backup(DENO_PATH, crear=False)
            return False
    else:
        print("  >> Ejecutando proceso de actualización nativo de Deno...")
        try:
            resultado = subprocess.run(
                [DENO_PATH, "upgrade"],
                capture_output=True,
                text=True,
                timeout=20
            )

            if resultado.stdout:
                print(resultado.stdout)
            if resultado.stderr:
                print(resultado.stderr)

            if resultado.returncode != 0:
                print(f"  [ERROR] La actualización de Deno terminó con código {resultado.returncode}.")
                return False

            return True
        except Exception as e:
            print(f"  [ERROR] Falló Deno: {e}")
            return False

# ==========================================
# INTERFAZ DE USUARIO PRINCIPAL
# ==========================================

def arrancar_actualizador():
    # Este es el menú principal del actualizador.
    """Función unificada que controla el menú de actualización."""
    limpiar_pantalla()
    print("\n  Conectando con servidores remotos...")
    verificar_todo_el_ecosistema()

    while True:
        limpiar_pantalla()
        print("\n  ╔══════════════════════════════════════════════════════════════╗")
        print("  ║               DASHBOARD GLOBAL DE ACTUALIZACIÓN              ║")
        print("  ╚══════════════════════════════════════════════════════════════╝")
        print(f"  1. Actualizar yt-dlp             -> {ESTADOS['ytdlp']}")
        print(f"  2. Actualizar FFmpeg y FFprobe   -> {ESTADOS['ffmpeg']}")
        print(f"  3. Actualizar Deno               -> {ESTADOS['deno']}")
        print("  4. Actualizar TODO el ecosistema (Lanzar ráfaga)")
        print("  5. Forzar re-escaneo de red (Volver a comprobar en la nube)")
        print("  6. Salir")
        print("  " + "─"*62)
        
        opcion = input("  Selecciona una opción (1-6): ").strip()
        
        if opcion == "1":
            limpiar_pantalla()
            if actualizar_ytdlp():
                ESTADOS["ytdlp"] = comprobar_estado_ytdlp()
            input("\n  Presiona Enter para volver...")
        elif opcion == "2":
            limpiar_pantalla()
            if actualizar_ffmpeg():
                ESTADOS["ffmpeg"] = comprobar_estado_ffmpeg()
            input("\n  Presiona Enter para volver...")
        elif opcion == "3":
            limpiar_pantalla()
            if actualizar_deno():
                ESTADOS["deno"] = comprobar_estado_deno()
            input("\n  Presiona Enter para volver...")
        elif opcion == "4":
            limpiar_pantalla()
            print("  === INICIANDO OPERACIÓN COMPLETA ===\n")
            actualizar_ytdlp()
            print("\n" + "─"*53 + "\n")
            actualizar_ffmpeg()
            print("\n" + "─"*53 + "\n")
            actualizar_deno()
            print("\n  >> Re-evaluando entorno post-descargas...")
            verificar_todo_el_ecosistema()
            print("\n  === ENTORNO SINCRONIZADO ===")
            input("\n  Presiona Enter para volver...")
        elif opcion == "5":
            limpiar_pantalla()
            print("\n  Re-evaluando las respuestas de las APIs públicas...")
            verificar_todo_el_ecosistema()
        elif opcion == "6":
            print("\n  Saliendo del actualizador...")
            time.sleep(0.5)
            break
        else:
            print(f"\n  {ROJO}[ALERTA] Opción incorrecta.{RESET}")
            time.sleep(1.2)

if __name__ == "__main__":
    arrancar_actualizador()