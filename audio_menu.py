import os


CYAN = "\033[96m"
RESET = "\033[0m"


def limpiar_pantalla():
    os.system("")
    os.system("cls" if os.name == "nt" else "clear")


def mostrar_menu_audio(destino):
    limpiar_pantalla()
    print(f"  {CYAN}┌──────────────────────────────────────────────────┐{RESET}")
    print(f"  {CYAN}│{RESET}             MENÚ DE DESCARGA DE AUDIO            {CYAN}│{RESET}")
    print(f"  {CYAN}└──────────────────────────────────────────────────┘{RESET}")
    print("")
    print(f"  {CYAN}Ruta actual:{RESET} {destino}")
    print("")
    print(f"  {CYAN}[1]{RESET} MP3 (calidad 192 kbps)")
    print(f"  {CYAN}[2]{RESET} WAV")
    print(f"  {CYAN}[3]{RESET} OGG")
    print(f"  {CYAN}[4]{RESET} M4A")
    print(f"  {CYAN}[5]{RESET} Volver al menú principal")
    print()


def obtener_formato_audio(opcion):
    formatos = {
        "1": ("mp3", "192K"),
        "2": ("wav", None),
        "3": ("ogg", None),
        "4": ("m4a", None),
    }
    return formatos.get(opcion)
