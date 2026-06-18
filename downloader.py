import os
import subprocess
import sys

# Importamos el módulo local updater y sus variables de control visual
try:
    import updater
    from updater import VERDE, AMARILLO, ROJO, RESET
except ImportError:
    print("[ERROR] No se encontró 'updater.py' en la misma carpeta para compilar.")
    input("Presiona Enter para salir...")
    sys.exit(1)

CONFIG_FILE = "config.txt"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
YTDLP_PATH = updater.YTDLP_PATH
FFMPEG_DIR = BASE_DIR

def limpiar_pantalla():
    os.system("") # Inicializa soporte ANSI en Windows
    os.system("cls" if os.name == "nt" else "clear")

def cargar_configuracion():
    ruta_config = os.path.join(BASE_DIR, CONFIG_FILE)
    if os.path.exists(ruta_config):
        try:
            with open(ruta_config, "r", encoding="utf-8", errors="ignore") as f:
                contenido = f.read().replace('\x00', '').strip()
                if contenido: return contenido
        except Exception: pass
    ruta_defecto = os.path.join(os.path.expanduser("~"), "Downloads", "yt-dlp")
    guardar_configuracion(ruta_defecto)
    return ruta_defecto

def guardar_configuracion(nueva_ruta):
    nueva_ruta = nueva_ruta.replace('\x00', '').strip()
    os.makedirs(nueva_ruta, exist_ok=True)
    with open(os.path.join(BASE_DIR, CONFIG_FILE), "w", encoding="utf-8") as f:
        f.write(nueva_ruta)

def mostrar_menu(destino, alerta_sistema):
    limpiar_pantalla()
    print("\n  ╔══════════════════════════════════════════════════╗")
    print("  ║               DESCARGADOR PORTABLE               ║")
    print("  ╚══════════════════════════════════════════════════╝\n")
    
    # Alerta sutil integrada (Minimalismo puro)
    if alerta_sistema:
        print(f"  {alerta_sistema}")
        print("  " + "─"*50)

    print(f"   Ruta: {destino}\n")
    print("  ┌──────────────────────────────────────────────────┐")
    print("  │  [1]  Video MP4  -  1080p Nativo (H.264 + AAC)   │")
    print("  │  [2]  Video MP4  -   720p Nativo (H.264 + AAC)   │")
    print("  │  [3]  Audio MP3  -  192kbps (Extracción Rápida)  │")
    print("  │  [4]  Cambiar carpeta de descarga                │")
    print("  │  [5]  Actualizar / Reparar Componentes (.exe)    │")
    print("  │  [6]  Salir                                      │")
    print("  └──────────────────────────────────────────────────┘\n")

def verificar_archivos(destino):
    print("\n  Archivos disponibles en la carpeta de descarga:")
    print("  ─────────────────────────────────────────────────────")
    if os.path.exists(destino):
        archivos = [f for f in os.listdir(destino) if f.endswith(('.mp4', '.mp3'))]
        if archivos:
            for archivo in archivos: print(f"  {archivo}")
        else:
            print("  (No se encontraron archivos .mp4 o .mp3)")
    print("  ─────────────────────────────────────────────────────")

def main():
    destino = cargar_configuracion()
    
    limpiar_pantalla()
    print("\n  Comprobando entorno portable...")
    
    while True:
        # Consultamos las funciones de diagnóstico que ya programaste en updater
        status_yt = updater.comprobar_estado_ytdlp()
        status_ff = updater.comprobar_estado_ffmpeg()
        status_dn = updater.comprobar_estado_deno()

        alerta_sistema = ""
        if "No instalado" in status_yt or "No instalado" in status_ff or "No instalado" in status_dn:
            alerta_sistema = f"{ROJO}⚠️  [Alerta]: Faltan componentes. Ejecuta la opción [5] para reparar.{RESET}"
        elif "Disp." in status_yt or "Disp." in status_ff or "Disp." in status_dn:
            alerta_sistema = f"{AMARILLO}💡 [Info]: Hay actualizaciones disponibles. Revisa la opción [5].{RESET}"

        mostrar_menu(destino, alerta_sistema)
        opcion = input(" Elige una opción [1-6]: ").strip()
        
        if opcion in ["1", "2", "3"]:
            if "No instalado" in status_yt:
                print(f"\n  {ROJO}[ERROR] yt-dlp.exe no está instalado. Ve a la opción [5].{RESET}")
                input("\n  Presiona Enter para continuar...")
                continue

            url = input("\n Pega la URL: ").strip().replace('\x00', '')
            if not url: continue
            
            comando = [YTDLP_PATH, "--ffmpeg-location", FFMPEG_DIR, "--no-playlist", "--restrict-filenames", "--no-part"]
            
            if opcion == "1":
                comando.extend([
                    "--format", "bestvideo[height<=1080][vcodec^=avc]+bestaudio[ext=m4a]/best[height<=1080][vcodec^=avc]",
                    "--merge-output-format", "mp4", "--embed-chapters",
                    "--output", os.path.join(destino, "%(title)s_[1080p].%(ext)s")
                ])
            elif opcion == "2":
                comando.extend([
                    "--format", "bestvideo[height<=720][vcodec^=avc]+bestaudio[ext=m4a]/best[height<=720][vcodec^=avc]",
                    "--merge-output-format", "mp4", "--embed-chapters",
                    "--output", os.path.join(destino, "%(title)s_[720p].%(ext)s")
                ])
            elif opcion == "3":
                comando.extend([
                    "--format", "bestaudio/best", "--extract-audio", "--audio-format", "mp3", "--audio-quality", "192K",
                    "--output", os.path.join(destino, "%(title)s.%(ext)s")
                ])
            
            comando.append(url)
            print("\n  Descargando...\n")
            try:
                subprocess.run(comando)
                print("\n  ¡Finalizado!")
            except Exception as e:
                print(f"\n  {ROJO}[ERROR]: {e}{RESET}")
                
            verificar_archivos(destino)
            if input("\n ¿Otra descarga? [S/N]: ").strip().upper() != "S": break
                
        elif opcion == "4":
            limpiar_pantalla()
            nueva_ruta = input(f"\n Carpeta actual: {destino}\n\n Nueva ruta: ").strip().replace('"', '').replace('\x00', '')
            if nueva_ruta:
                guardar_configuracion(nueva_ruta)
                destino = nueva_ruta
                print("\n Carpeta actualizada.")
                os.system("timeout /t 1 >nul" if os.name == "nt" else "sleep 1")
                
        elif opcion == "5":
            # EJECUCIÓN INTERNA: Llamamos a la función nativa importada de updater.py
            updater.arrancar_actualizador()
            
            # Al salir del actualizador, refrescamos la ruta de descargas por si acaso
            destino = cargar_configuracion()
            
        elif opcion == "6":
            print("\n ¡Hasta luego!")
            os.system("timeout /t 1 >nul" if os.name == "nt" else "sleep 1")
            break

if __name__ == "__main__":
    main()