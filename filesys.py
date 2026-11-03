# -*- coding: utf-8 -*-
import os
import sys
import tkinter as tk
from tkinter import filedialog

class FileEntry:
    
    TYPE_FILE   = 0x00
    TYPE_FOLDER = 0x01
    
    def __init__(self, type, filename):
        self.serializer = {
            FileEntry.TYPE_FILE     : FileEntry.__file_str__ ,
            FileEntry.TYPE_FOLDER   : FileEntry.__folder_str__ ,
        }.get(type, FileEntry.__file_str__)
        self.type       = type
        self.selected   = False 
        self.filename   = filename
         
    def __file_str__(self)     : return f'🗎 { self.filename }'
    def __folder_str__(self)   : return f'🗁 { self.filename }' if self.selected else f'🗀 { self.filename }'
    

class ScrollBar:
    def __init__(self, pygame, x, y, height, max_val):
        self.value  = 0
        self.height = height
        self.x      = x
        self.y      = y
        self.min    = 0
        self.max    = max_val
        self.pygame = pygame
        self.knob   = pygame.Rect(x, y, 26, 27) 
        self.rect   = pygame.Rect(x, y, 26, height) 
        self.drag   = False
        self.last   = 0 
        
    def update(self):
        rango       = self.max - self.min
        proporcion  = (self.value - self.min) / rango if rango != 0 else 0
        self.knob.y = self.rect.y + int(proporcion * (self.height - 27))

    def handle(self, evento):
        if evento.type == self.pygame.MOUSEBUTTONDOWN and evento.button == 1:
            if self.knob.collidepoint(evento.pos) or self.rect.collidepoint(evento.pos):
                self.drag   = True
                self.last   = evento.pos[1]
                
                if not self.knob.collidepoint(evento.pos):
                    proporcion = (evento.pos[1] - self.rect.y) / (self.height - 27)
                    self.value = self.min + proporcion * (self.max - self.min)
                    self.update()
                return True
                
        elif evento.type == self.pygame.MOUSEBUTTONUP and evento.button == 1:
            self.drag = False
            
        elif evento.type == self.pygame.MOUSEMOTION and self.drag:
            y_actual    = evento.pos[1]
            delta       = y_actual - self.last
            self.last   = y_actual
            
            if self.pygame.key.get_mods() & self.pygame.KMOD_SHIFT:
                factor_sensibilidad = 0.1
            else:
                factor_sensibilidad = 1.0
                
            unidades_por_pixel = (self.max - self.min) / (self.height - 27) if (self.height - 27) != 0 else 0
            self.value += delta * unidades_por_pixel * factor_sensibilidad
            
            if self.value < self.min: self.value = self.min
            if self.value > self.max: self.value = self.max
            
            self.update()
            return True
            
        return False

class FileMan:
    root        = '.'
    width       = 672
    height      = 222
    color       = (64,255,245)
    y           = 617
    file_x      = 439
    file_lines  = ['' for _ in range(8)]
    file_index  = 0
    file_scroll = 0
    file_box    = None
    file_knob   = None
    dir_x       = 50
    dir_lines   = ['' for _ in range(8)]
    dir_index   = 0
    dir_scroll  = 0
    entries     = []
    dir_box     = None
    dir_knob    = None
    scrollbars  = {}
    
    ultimo_clic_tiempo = 0
    ultimo_clic_index  = -1
    
    def init( pygame ):
        FileMan.scrollbars['file'    ]= ScrollBar(pygame, FileMan.file_x+FileMan.width-14, FileMan.y - 9, 204, 0)
        FileMan.scrollbars['dir'     ]= ScrollBar(pygame, FileMan.file_x-39              , FileMan.y + 2, 192, 0)
        FileMan.file_box    = pygame.Rect(FileMan.file_x, FileMan.y-3, FileMan.width-20, 27) 
        FileMan.dir_box     = pygame.Rect(FileMan.file_x-389, FileMan.y-3, 344, 27) 
        FileMan.navigate( FileMan.root )
                     
    def navigate(folder):
        FileMan.root = folder
        FileMan.entries = []
        
        ruta_absoluta = os.path.abspath(FileMan.root)
        ruta_padre = os.path.dirname(ruta_absoluta)
        if ruta_padre != ruta_absoluta:
            FileMan.entries.append(FileEntry(FileEntry.TYPE_FOLDER, ".."))
            
        try:
            for elemento in os.scandir(FileMan.root):
                if elemento.is_dir():
                    FileMan.entries.append(FileEntry(FileEntry.TYPE_FOLDER, elemento.name))
                elif elemento.is_file():
                    FileMan.entries.append(FileEntry(FileEntry.TYPE_FILE, elemento.name))
            
            FileMan.entries.sort(key=lambda x: (x.filename != "..", x.type != FileEntry.TYPE_FOLDER, x.filename.lower()))
        except PermissionError:
            pass
            
        FileMan.scrollbars['file'].value = 0
        FileMan.scrollbars['dir'].value = 0
        FileMan.file_index = 0
        FileMan.dir_index = 0
        FileMan.file_scroll = 0
        FileMan.dir_scroll = 0
        
        FileMan.update()
    
    def update():
        carpetas = [x for x in FileMan.entries if x.type == FileEntry.TYPE_FOLDER]
        archivos = [x for x in FileMan.entries if x.type == FileEntry.TYPE_FILE]
        
        FileMan.scrollbars['dir'].max  = max(0, len(carpetas) - 8)
        FileMan.scrollbars['file'].max = max(0, len(archivos) - 8)
        
        FileMan.scrollbars['dir'].update()
        FileMan.scrollbars['file'].update()
        
        FileMan.dir_scroll  = int(FileMan.scrollbars['dir'].value)
        FileMan.file_scroll = int(FileMan.scrollbars['file'].value)
        
        FileMan.dir_lines   = ['' for _ in range(8)]
        FileMan.file_lines  = ['' for _ in range(8)]
        
        # Sincronización del recuadro de carpetas basándose en la línea visible
        FileMan.dir_box.y = (FileMan.y - 3) + (27 * FileMan.dir_index)
        # Sincronización del recuadro de archivos basándose en la línea visible
        FileMan.file_box.y = (FileMan.y - 3) + (27 * FileMan.file_index)
        
        for i in range(8):
            indice_real = FileMan.dir_scroll + i
            if indice_real < len(carpetas):
                entry = carpetas[indice_real]
                entry.selected = True if i == FileMan.dir_index else False
                FileMan.dir_lines[i] = entry.serializer(entry)
                
        for i in range(8):
            indice_real = FileMan.file_scroll + i
            if indice_real < len(archivos):
                entry = archivos[indice_real]
                entry.selected = True if i == FileMan.file_index else False
                FileMan.file_lines[i] = entry.serializer(entry)
                
    def render(app):
        renderer    = app.fonts.ocr.render
        blitter     = app.screen.blit
        color       = FileMan.color
        
        # Renderizado de la caja de fondo para carpetas
        carpetas = [x for x in FileMan.entries if x.type == FileEntry.TYPE_FOLDER]
        if len(carpetas) > 0 and 0 <= FileMan.dir_index < 8:
            indice_real = FileMan.dir_scroll + FileMan.dir_index
            if indice_real < len(carpetas):
                app.pygame.draw.rect(app.screen, (31, 229, 186), FileMan.dir_box)
                
        # Renderizado de la caja de fondo para archivos
        archivos = [x for x in FileMan.entries if x.type == FileEntry.TYPE_FILE]
        if len(archivos) > 0 and 0 <= FileMan.file_index < 8:
            indice_real = FileMan.file_scroll + FileMan.file_index
            if indice_real < len(archivos):
                app.pygame.draw.rect(app.screen, (31, 229, 186), FileMan.file_box)
                        
        for key, scrollbar in FileMan.scrollbars.items():
            app.pygame.draw.rect(app.screen, (31, 229, 186), scrollbar.knob)
                        
        y_file = FileMan.y
        for index in range(len(FileMan.file_lines)):
            line = FileMan.file_lines[index]
            surface = renderer(line, True, (0,0,0) if index == FileMan.file_index else color)
            blitter(surface, (FileMan.file_x, y_file))
            y_file += 27
            
        y_dir = FileMan.y                
        for index in range(len(FileMan.dir_lines)):
            line = FileMan.dir_lines[index]
            surface = renderer(line, True, (0,0,0) if index == FileMan.dir_index else color)
            blitter(surface, (FileMan.dir_x, y_dir))
            y_dir += 27

    def handle(app, evento):
        se_movio_scroll = False
        for scrollbar in FileMan.scrollbars.values():
            if scrollbar.handle(evento):
                se_movio_scroll = True
                
        if se_movio_scroll:
            FileMan.update()
            return True
            
        if evento.type == app.pygame.MOUSEBUTTONDOWN and evento.button == 1:
            x_mouse, y_mouse = evento.pos
            
            # Clic en la sección de carpetas
            if 50 <= x_mouse <= 400 and FileMan.y <= y_mouse < FileMan.y + (8 * 27):
                linea_clicada = (y_mouse - FileMan.y) // 27
                carpetas = [x for x in FileMan.entries if x.type == FileEntry.TYPE_FOLDER]
                indice_real = FileMan.dir_scroll + linea_clicada
                
                if indice_real < len(carpetas):
                    FileMan.dir_index = linea_clicada
                    
                    tiempo_actual = app.pygame.time.get_ticks()
                    if linea_clicada == FileMan.ultimo_clic_index and (tiempo_actual - FileMan.ultimo_clic_tiempo) < 500:
                        carpeta_seleccionada = carpetas[indice_real].filename
                        
                        if carpeta_seleccionada == "..":
                            nueva_ruta = os.path.dirname(os.path.abspath(FileMan.root))
                        else:
                            nueva_ruta = os.path.join(FileMan.root, carpeta_seleccionada)
                            
                        FileMan.navigate(nueva_ruta)
                        FileMan.ultimo_clic_index = -1
                    else:
                        FileMan.ultimo_clic_index = linea_clicada
                        FileMan.ultimo_clic_tiempo = tiempo_actual
                        FileMan.update()
                    return True
                    
            # Clic en la sección de archivos
            elif FileMan.file_x <= x_mouse <= (FileMan.file_x + FileMan.width - 20) and FileMan.y <= y_mouse < FileMan.y + (8 * 27):
                linea_clicada = (y_mouse - FileMan.y) // 27
                archivos = [x for x in FileMan.entries if x.type == FileEntry.TYPE_FILE]
                indice_real = FileMan.file_scroll + linea_clicada
                
                if indice_real < len(archivos):
                    FileMan.file_index = linea_clicada
                    print([x for x in FileMan.entries if x.type == FileEntry.TYPE_FILE][FileMan.file_index+FileMan.file_scroll].filename)
                    FileMan.update()
                    return True
                    
        return False
        
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
    root_tk = tk.Tk()
    root_tk.withdraw()
    
    if tipos_archivo is None:
        tipos_archivo = [("Todos los archivos", "*.*")]
    
    ruta_completa = filedialog.askopenfilename(
        title=titulo,
        filetypes=tipos_archivo
    )
    
    root_tk.destroy()
    
    if ruta_completa:
        nombre_fichero = os.path.basename(ruta_completa)
        return nombre_fichero, ruta_completa
    
    return None, None
