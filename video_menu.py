import os


CYAN = "\033[96m"
RESET = "\033[0m"


def limpiar_pantalla():
    os.system("")
    os.system("cls" if os.name == "nt" else "clear")


def mostrar_menu_video():
    limpiar_pantalla()
    print(f"  {CYAN}┌──────────────────────────────────────────────────┐{RESET}")
    print(f"  {CYAN}│{RESET}             MENÚ DE DESCARGA DE VIDEO            {CYAN}│{RESET}")
    print(f"  {CYAN}└──────────────────────────────────────────────────┘{RESET}")
    print("")
    print(f"  {CYAN}[1]{RESET} 1080p  (por defecto, H.264 + AAC)")
    print(f"  {CYAN}[2]{RESET} 720p   (H.264 + AAC)")
    print(f"  {CYAN}[3]{RESET} 480p   (H.264 + AAC)")
    print(f"  {CYAN}[4]{RESET} 360p   (H.264 + AAC)")
    print(f"  {CYAN}[5]{RESET} Volver al menú principal")
    print()
