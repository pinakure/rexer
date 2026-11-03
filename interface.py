import pygame 
from filesys import FileMan
import audio
from app import App

class SliderDef:
    def __init__(self, name, x, y, min, max, value, width, height=20):
        self.x       = int(x)
        self.y       = int(y)
        self.min     = float(min)
        self.max     = float(max)
        self.value   = float(value)
        self.width   = int(width)
        self.height  = int(height)
        self.name    = name
        
SLIDERS = {
    'bpm'       : SliderDef( "", 240, 458, 40.0, 450.0, 120.0, 1348),
    'pitch'     : SliderDef( "", 240, 511,  -12,    12,     0, 1348),
}

WIDGETS = {}

move_window_offset_x = 0
move_window_offset_y = 0
move_window_x        = 0
move_window_y        = 0

class EventHandler:
    def handle( event , mouse_x, mouse_y, clicks_mouse, manejador_rex, ventana):
        global move_window_offset_x
        global move_window_offset_y
        global move_window_x
        global move_window_y

        for key,w in WIDGETS.items():
            if w.manejar_evento( event ) and w.arrastrando: 
                if   key=='bpm': 
                    x_limitada = max(w.x, min(mouse_x, w.x + SLIDERS[key].width))
                    porcentaje_slider = (x_limitada - w.x) / SLIDERS[key].width
                    App.rex.bpm = w.min + porcentaje_slider * (w.max - w.min)
                    App.rex_dll.REXSetPreviewTempo(manejador_rex, int(App.rex.bpm * 1000))
                    return True
                elif key=='pitch': 
                    x_limitada = max(w.x, min(mouse_x, w.x + SLIDERS[key].width))
                    porcentaje_slider = (x_limitada - w.x) / SLIDERS[key].width
                    App.rex.pitch = int(round(w.min + porcentaje_slider * (w.max - w.min)))
                    return True
                
        for key,w in FileMan.scrollbars.items():
            if w.handle( event ) and w.drag: 
                if key=='dir': 
                    return True
                elif key=='file': 
                    return True
                        
        if FileMan.handle(App, event ):
            return True
                        
        kind = event.type
        if   kind == pygame.QUIT: return False
        elif kind == pygame.VIDEORESIZE:
            w, h = event.size
            # do stuff
        elif kind == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Botón izquierdo
                if event.pos[1] <= 32:  # Solo en los primeros 32px
                    App.drag = True
                    # CLAVE PARA EVITAR SALTOS: Guardamos la posición actual de la ventana
                    move_window_x, move_window_y = ventana.position
                    
                    move_window_offset_x = event.pos[0]
                    move_window_offset_y = event.pos[1]
                else:
                    print(f"Click @ {event.pos}")
                return True
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1: 
                App.drag = False
        elif event.type == pygame.MOUSEMOTION:
            if App.drag:
                # 1. Obtenemos dónde está la ventana actualmente en la pantalla del PC
                move_window_x, move_window_y = ventana.position
                
                # 2. El evento.pos dentro de MOUSEMOTION nos da la posición actual del ratón.
                # Calculamos cuánto se ha desplazado respecto al punto de agarre inicial (offset)
                nueva_x = move_window_x + (event.pos[0] - move_window_offset_x)
                nueva_y = move_window_y + (event.pos[1] - move_window_offset_y)
                
                # 3. Movemos la ventana a la posición calculada de forma inmediata
                ventana.position = (nueva_x, nueva_y)
            else:
                # Tus otros eventos de movimiento aquí
                pass            
        elif event.type == pygame.KEYDOWN:
            paso_base = 0.1 if (pygame.key.get_mods() & pygame.KMOD_SHIFT) else 1.0

            #if event.key == pygame.K_SPACE:
            #    if audio.esta_reproduciendo():
            #        audio.stop()
            #    else:
            #        bucle = True if (pygame.key.get_mods() & pygame.KMOD_SHIFT) else False
            #        audio.play(0, muestras_actuales, loop=bucle)
                        
            if event.key == pygame.K_RETURN:
                return False
        return True                    