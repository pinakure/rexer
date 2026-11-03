import  pygame
from    pygame._sdl2    import Window
from    app             import App
import  interface
import  os
import  filesys

class SliderRaton:
    def __init__(self, x, y, val_min, val_max, val_inicial, etiqueta, width=1289):
        self.x = x  
        self.y          = y  
        self.alto       = 20
        self.min        = val_min
        self.max        = val_max
        self.val        = float(val_inicial)
        self.etiqueta   = etiqueta
        self.width      = width 
        self.rect       = pygame.Rect(x, y, self.width, self.alto) 
        self.tirador_ancho = 32
        self.tirador_rect = pygame.Rect(x, y, self.tirador_ancho, self.alto)
        self.arrastrando = False
        self.ultima_x_raton = 0
        self.actualizar_tirador_desde_val()

    def actualizar_tirador_desde_val(self):
        rango = self.max - self.min
        proporcion = (self.val - self.min) / rango if rango != 0 else 0
        self.tirador_rect.x = self.rect.x + int(proporcion * (self.rect.width - self.tirador_ancho))
        self.tirador_rect.y = self.y

    def manejar_evento(self, evento):
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            if self.tirador_rect.collidepoint(evento.pos) or self.rect.collidepoint(evento.pos):
                self.arrastrando = True
                # CORREGIDO: Guardar solo la coordenada X en lugar de la tupla (x,y)
                self.ultima_x_raton = evento.pos[0]
                
                if not self.tirador_rect.collidepoint(evento.pos):
                    proporcion = (evento.pos[0] - self.rect.x) / (self.rect.width - self.tirador_ancho)
                    self.val = self.min + proporcion * (self.max - self.min)
                    self.actualizar_tirador_desde_val()
                return True
                
        elif evento.type == pygame.MOUSEBUTTONUP and evento.button == 1:
            self.arrastrando = False
            
        elif evento.type == pygame.MOUSEMOTION and self.arrastrando:
            # CORREGIDO: Extraer la componente X de la posición actual del ratón
            x_actual = evento.pos[0]
            delta_x = x_actual - self.ultima_x_raton
            self.ultima_x_raton = x_actual
            
            if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                factor_sensibilidad = 0.1
            else:
                factor_sensibilidad = 1.0
                
            unidades_por_pixel = (self.max - self.min) / (self.rect.width - self.tirador_ancho)
            self.val += delta_x * unidades_por_pixel * factor_sensibilidad
            
            if self.val < self.min: self.val = self.min
            if self.val > self.max: self.val = self.max
            
            self.actualizar_tirador_desde_val()
            return True
            
        return False

    def dibujar(self, superficie, knob, fuente, fuente_lcd):
        # pygame.draw.rect(superficie, (60, 60, 75), self.rect, border_radius=4)
        color_tirador = (50, 220, 120,64) if self.arrastrando else (50, 120, 240)
        # pygame.draw.rect(superficie, color_tirador, self.tirador_rect, border_radius=4)
        superficie.blit(knob, (self.tirador_rect.x, self.tirador_rect.y-6))
        txt = fuente    .render(f"{self.etiqueta}", True, (255, 255, 255))
        val = fuente_lcd.render(f"{str(int(self.val)).rjust(8)}", True, (255, 55, 0))
        superficie.blit(txt, (self.rect.x-128, self.rect.y))
        superficie.blit(val, (self.rect.x+self.rect.w+13, self.rect.y - 1))

def carga_imagen(ruta_imagen):
    if ruta_imagen and os.path.exists(ruta_imagen):
        try:
            return pygame.image.load(ruta_imagen).convert_alpha()            
        except Exception as e:
            print(f"[Aviso] No se pudo cargar el backdrop: {e}")
            exit(1)
    
def splash():
    App.screen.fill((20, 20, 25))
    App.fonts.heading   = pygame.font.SysFont("Consolas", 28, bold=True)
    App.fonts.monospace = pygame.font.SysFont("Consolas", 16)
    App.screen.blit(App.backdrop, (0, 0))
    txt_titulo = App.fonts.heading.render(App.name.upper(), True, (130, 250, 50))
    txt_carga  = App.fonts.monospace .render("Decodificando audio y fijando geometría sólida estable... Espere.", True, (130, 250, 50))
    App.screen.blit(txt_titulo, (App.width // 2 - txt_titulo.get_width() // 2, App.height // 3 - 40))
    App.screen.blit( txt_carga, (App.width // 2 - txt_carga.get_width()  // 2, App.height // 3 + 10))
    pygame.display.flip()

def create():
    for key,sld in interface.SLIDERS.items():
        interface.WIDGETS[key] = SliderRaton(
            sld.x, sld.y,
            sld.min, sld.max,
            sld.value, sld.name,
            sld.width
        )
        
def init( archivo_entrada ):
    pygame          .init()
    pygame          .font.init()
    App.screen      = pygame.display.set_mode(( App.width, App.height ), pygame.NOFRAME)
    App.backdrop    = carga_imagen(filesys.path('deck.png'))
    App.knob        = carga_imagen(filesys.path('knob.png'))
    splash  ()
    
    pygame          .display.set_caption(f"{ App.name } - { archivo_entrada.split(os.path.sep)[-1] }")
    App.fonts.ocr   = pygame.font.Font(filesys.path("ocr.ttf"   ), 22)
    App.fonts.lcd   = pygame.font.Font(filesys.path("lcd.ttf"   ), 24)
    App.fonts.pbb   = pygame.font.Font(filesys.path("pbb.otf"   ), 16)
    App.fonts.pb    = pygame.font.Font(filesys.path("pb.otf"    ), 16)
    App.fonts.combi = pygame.font.Font(filesys.path("combi.otf" ), 16)
    App.fonts.m4g   = pygame.font.Font(filesys.path("m4g.ttf"   ), 16)

    # Pre-renderizar etiquetas estáticas    
    label_bpm   = App.fonts.ocr.render("  BPM", True, App.labels[  'bpm'].color)
    label_obpm  = App.fonts.ocr.render("O.BPM", True, App.labels[ 'obpm'].color)
    label_pitch = App.fonts.ocr.render(" Tone", True, App.labels['pitch'].color)
    label_slice = App.fonts.ocr.render("Slice", True, App.labels['slice'].color)    
    App.backdrop.blit(label_bpm     , (App.labels[  'bpm'].x,App.labels[  'bpm'].y))
    App.backdrop.blit(label_obpm    , (App.labels[ 'obpm'].x,App.labels[ 'obpm'].y))
    App.backdrop.blit(label_pitch   , (App.labels['pitch'].x,App.labels['pitch'].y))
    App.backdrop.blit(label_slice   , (App.labels['slice'].x,App.labels['slice'].y))
    
    App.clock       = pygame.time.Clock()
    return Window.from_display_module()
        
def redraw(audio_g, max_amplitud_global, inicio_muestras, muestras_actuales, posicion_aguja):
    App.screen.blit(App.backdrop, (0, 0))
    for _,w in interface.WIDGETS.items():
        w.dibujar( App.screen, App.knob, App.fonts.ocr, App.fonts.lcd )

