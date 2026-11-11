import os
import subprocess
import urllib.request
import zipfile
import tempfile
import shutil
import hashlib
import re
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


def limpiar_directorio_temporal(ruta):
    try:
        shutil.rmtree(ruta)
    except FileNotFoundError:
        pass
    except OSError as e:
        print(f"\n  [AVISO] No se pudo limpiar '{ruta}': {e}")


def mostrar_progreso(actual, total, tiempo_inicio, prefijo="Descargando"):
    tiempo_transcurrido = time.time() - tiempo_inicio
    velocidad = actual / tiempo_transcurrido if tiempo_transcurrido > 0 else 0
    
    if velocidad > 1024 * 1024:
        txt_vel = f"{velocidad / (1024*1024):.2f} MB/s"
    else:
        txt_vel = f"{velocidad / 1024:.2f} KB/s"
        
    if total > 0:
        porcentaje = (actual / total) * 100
        porcentaje = min(porcentaje, 100)
        bloques = min(25, int(porcentaje // 4))
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


def descargar_a_archivo(url, ruta, etiqueta, sha256_esperado=None):
    req = urllib.request.Request(url, headers={"User-Agent": "SMDM"})
    sha256 = hashlib.sha256()
    with urllib.request.urlopen(req, timeout=30) as response:
        total_size = int(response.info().get("Content-Length", 0))
        bytes_descargados = 0
        tiempo_inicio = time.time()
        with open(ruta, "wb") as archivo:
            while True:
                chunk = response.read(256 * 1024)
                if not chunk:
                    break
                archivo.write(chunk)
                sha256.update(chunk)
                bytes_descargados += len(chunk)
                mostrar_progreso(bytes_descargados, total_size, tiempo_inicio, etiqueta)

    if not archivo_valido(ruta):
        raise RuntimeError(f"{etiqueta} está vacío.")
    if total_size and bytes_descargados != total_size:
        raise RuntimeError(
            f"Descarga incompleta de {etiqueta}: {bytes_descargados} de {total_size} bytes."
        )
    if sha256_esperado and sha256.hexdigest().lower() != sha256_esperado.lower():
        raise RuntimeError(f"No coincide el SHA-256 oficial de {etiqueta}.")


def obtener_asset_github(api_url, nombre_asset):
    req = urllib.request.Request(
        api_url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "SMDM"}
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        release = json.loads(response.read().decode("utf-8"))

    assets = [
        asset for asset in release.get("assets", [])
        if asset.get("name") == nombre_asset
    ]
    if len(assets) != 1 or not assets[0].get("browser_download_url"):
        raise RuntimeError(f"No se encontró el asset oficial {nombre_asset}.")

    digest = assets[0].get("digest", "")
    sha256 = digest.partition(":")[2] if digest.startswith("sha256:") else None
    return assets[0]["browser_download_url"], sha256


def obtener_sha256(url):
    req = urllib.request.Request(url, headers={"User-Agent": "SMDM"})
    with urllib.request.urlopen(req, timeout=15) as response:
        contenido = response.read().decode("ascii").strip()
    hash_publicado = contenido.split()[0] if contenido else ""
    if not re.fullmatch(r"[a-fA-F0-9]{64}", hash_publicado):
        raise RuntimeError("La fuente oficial no devolvió un SHA-256 válido.")
    return hash_publicado


def validar_ejecutable(ruta, argumentos, nombre):
    resultado = subprocess.run(
        [ruta, *argumentos],
        capture_output=True,
        text=True,
        timeout=20
    )
    salida = (resultado.stdout or resultado.stderr).strip()
    if resultado.returncode != 0 or not salida:
        raise RuntimeError(f"{nombre} descargado no superó la validación.")
    return salida


def instalar_transaccional(reemplazos):
    """Reemplaza varios archivos y restaura el estado anterior si una operación falla."""
    directorio_backup = tempfile.mkdtemp(prefix=".smdm-backup-", dir=BASE_DIR)
    respaldos = {}
    instalados = []
    try:
        for indice, destino in enumerate(reemplazos):
            if os.path.exists(destino):
                respaldo = os.path.join(directorio_backup, str(indice))
                os.replace(destino, respaldo)
                respaldos[destino] = respaldo
            else:
                respaldos[destino] = None

        for destino, origen in reemplazos.items():
            os.replace(origen, destino)
            instalados.append(destino)
    except Exception as error:
        errores_rollback = []
        for destino in instalados:
            try:
                os.remove(destino)
            except OSError as rollback_error:
                errores_rollback.append(f"No se pudo retirar {destino}: {rollback_error}")
        for destino, respaldo in respaldos.items():
            if respaldo and os.path.exists(respaldo):
                try:
                    os.replace(respaldo, destino)
                except OSError as rollback_error:
                    errores_rollback.append(f"No se pudo restaurar {destino}: {rollback_error}")
        if errores_rollback:
            raise RuntimeError(
                f"Falló la instalación y el rollback. Los respaldos se conservaron en "
                f"{directorio_backup}. {'; '.join(errores_rollback)}"
            ) from error
        limpiar_directorio_temporal(directorio_backup)
        raise
    else:
        limpiar_directorio_temporal(directorio_backup)

# ==========================================
# SECCIÓN DE COMPROBACIÓN DE VERSIONES
# ==========================================

def comprobar_estado_ytdlp():
    if not os.path.exists(YTDLP_PATH):
        return f"{ROJO}[ No instalado ]{RESET}"
    
    v_local = None
    try:
        res = subprocess.run(
            [YTDLP_PATH, "--version"], capture_output=True, text=True,
            timeout=5, check=True
        )
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
        res = subprocess.run(
            [FFMPEG_PATH, "-version"], capture_output=True, text=True,
            timeout=5, check=True
        )
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
        res = subprocess.run(
            [DENO_PATH, "--version"], capture_output=True, text=True,
            timeout=5, check=True
        )
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

    directorio_temporal = tempfile.mkdtemp(prefix=".smdm-ytdlp-", dir=BASE_DIR)
    ruta_temporal = os.path.join(directorio_temporal, "yt-dlp.exe")
    try:
        print("  >> Descargando yt-dlp en un archivo temporal...")
        url, sha256 = obtener_asset_github(
            "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest",
            "yt-dlp.exe"
        )
        descargar_a_archivo(
            url,
            ruta_temporal,
            "yt-dlp.exe",
            sha256
        )
        version = validar_ejecutable(ruta_temporal, ["--version"], "yt-dlp")
        instalar_transaccional({YTDLP_PATH: ruta_temporal})
        print(f"\n\n  [OK] yt-dlp.exe actualizado ({version}).")
        return True
    except Exception as e:
        print(f"\n  [ERROR] Falló la descarga: {e}")
        return False
    finally:
        limpiar_directorio_temporal(directorio_temporal)

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

    directorio_temporal = tempfile.mkdtemp(prefix=".smdm-ffmpeg-", dir=BASE_DIR)
    ruta_zip = os.path.join(directorio_temporal, "ffmpeg.zip")
    rutas_temporales = {
        FFMPEG_PATH: os.path.join(directorio_temporal, "ffmpeg.exe"),
        FFPROBE_PATH: os.path.join(directorio_temporal, "ffprobe.exe")
    }
    try:
        print("  >> Descargando el paquete oficial de FFmpeg...")
        url_ffmpeg = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        sha256 = obtener_sha256(url_ffmpeg + ".sha256")
        descargar_a_archivo(
            url_ffmpeg,
            ruta_zip,
            "FFmpeg Pack",
            sha256
        )
        print("\n\n  >> Extrayendo y validando binarios...")
        with zipfile.ZipFile(ruta_zip) as archivo_zip:
            miembros = {
                os.path.basename(nombre).lower(): nombre
                for nombre in archivo_zip.namelist()
                if os.path.basename(nombre).lower() in ("ffmpeg.exe", "ffprobe.exe")
            }
            if set(miembros) != {"ffmpeg.exe", "ffprobe.exe"}:
                raise RuntimeError("El paquete ZIP no contiene ffmpeg.exe y ffprobe.exe.")
            for nombre, destino in (
                ("ffmpeg.exe", rutas_temporales[FFMPEG_PATH]),
                ("ffprobe.exe", rutas_temporales[FFPROBE_PATH])
            ):
                with archivo_zip.open(miembros[nombre]) as origen, open(destino, "wb") as salida:
                    shutil.copyfileobj(origen, salida)

        version = validar_ejecutable(rutas_temporales[FFMPEG_PATH], ["-version"], "FFmpeg")
        validar_ejecutable(rutas_temporales[FFPROBE_PATH], ["-version"], "FFprobe")
        instalar_transaccional(rutas_temporales)
        print(f"\n  ¡FFmpeg y FFprobe actualizados correctamente! {version.splitlines()[0]}")
        return True
    except Exception as e:
        print(f"\n  [ERROR] Ocurrió un fallo: {e}")
        return False
    finally:
        limpiar_directorio_temporal(directorio_temporal)

def actualizar_deno():
    mostrar_encabezado("ACTUALIZAR DENO")

    if comprobar_bloqueo(DENO_PATH):
        print("  [ERROR] deno.exe está bloqueado.")
        return False
    if "Al día" in ESTADOS["deno"]:
        print("  [INFO] Omitiendo descarga de Deno (Ya está actualizado).")
        return True

    directorio_temporal = tempfile.mkdtemp(prefix=".smdm-deno-", dir=BASE_DIR)
    ruta_zip = os.path.join(directorio_temporal, "deno.zip")
    ruta_temporal = os.path.join(directorio_temporal, "deno.exe")
    try:
        print("  >> Descargando el paquete oficial de Deno...")
        url, sha256 = obtener_asset_github(
            "https://api.github.com/repos/denoland/deno/releases/latest",
            "deno-x86_64-pc-windows-msvc.zip"
        )
        descargar_a_archivo(
            url,
            ruta_zip,
            "deno.zip",
            sha256
        )
        with zipfile.ZipFile(ruta_zip) as archivo_zip:
            miembros = [
                nombre for nombre in archivo_zip.namelist()
                if os.path.basename(nombre).lower() == "deno.exe"
            ]
            if len(miembros) != 1:
                raise RuntimeError("El paquete ZIP no contiene un único deno.exe.")
            with archivo_zip.open(miembros[0]) as origen, open(ruta_temporal, "wb") as destino:
                shutil.copyfileobj(origen, destino)

        version = validar_ejecutable(ruta_temporal, ["--version"], "Deno")
        instalar_transaccional({DENO_PATH: ruta_temporal})
        print(f"\n  [OK] deno.exe actualizado ({version.splitlines()[0]}).")
        return True
    except Exception as e:
        print(f"\n  [ERROR] Falló la descarga de Deno: {e}")
        return False
    finally:
        limpiar_directorio_temporal(directorio_temporal)

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