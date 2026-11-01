import os
import sys
import tkinter as tk
from tkinter import filedialog

def path(ruta_relativa):
    """ Obtiene la ruta absoluta de los recursos, compatible con PyInstaller """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, ruta_relativa, ruta_relativa)
    return os.path.join(os.path.abspath("."), ruta_relativa)

def obtener_nombre_fichero(titulo="Seleccionar archivo", tipos_archivo=None):
    """
    Abre un diálogo del sistema para seleccionar un archivo.
    Funciona en Windows y Linux.
    """
    # 1. Crear una ventana raíz oculta para que no aparezca una ventana vacía
    root = tk.Tk()
    root.withdraw()
    
    # Configurar filtros de archivo por defecto si no se especifican
    if tipos_archivo is None:
        tipos_archivo = [("Todos los archivos", "*.*")]
    
    # 2. Abrir el diálogo del sistema y capturar la ruta completa
    ruta_completa = filedialog.askopenfilename(
        title=titulo,
        filetypes=tipos_archivo
    )
    
    # 3. Destruir la ventana raíz para liberar memoria inmediatamente
    root.destroy()
    
    # Si el usuario cancela, ruta_completa será una cadena vacía ''
    if ruta_completa:
        nombre_fichero = os.path.basename(ruta_completa)
        return nombre_fichero, ruta_completa
    
    return None, None

# --- Ejemplo de uso ---
if __name__ == "__main__":
    print("Abriendo diálogo de selección...")
    
    # Opcional: Filtrar por extensiones específicas, por ejemplo, archivos de texto
    mis_filtros = [
        ("Archivos de texto", "*.txt"),
        ("Documentos PDF", "*.pdf"),
        ("Todos los archivos", "*.*")
    ]
    
    nombre, ruta = obtener_nombre_fichero("Elige tu archivo de configuración", mis_filtros)
    
    if nombre:
        print(f"\n¡Archivo seleccionado con éxito!")
        print(f"Nombre del fichero: {nombre}")
        print(f"Ruta completa:      {ruta}")
    else:
        print("\nSelección cancelada por el usuario.")