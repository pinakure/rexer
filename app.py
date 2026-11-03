class FontCache:
    lcd         = None
    display     = None 
    ocr         = None
    heading     = None
    monospace   = None
    small       = None
    pbb         = None
    pb          = None
    combi       = None
    m4g         = None

class Label: 
    def __init__(self, name, x, y, color = ( 31, 229, 186)):
        self.name       = name
        self.x          = x
        self.y          = y
        self.color      = color
        self.highlight  = (min(255, int(color[0]*1.5)), min(255, int(color[1]*1.5)), min(255, int(color[2]*1.5)))
        self.position   = (x+(len(name)*15),y)

class App:
    name        = "Rexer"
    version     = "1.0"
    description = "REX Loop Player and Exporter"
    width       = 1650
    height      = 928
    fonts       = FontCache
    backdrop    = None
    clock       = None
    drag        = False
    run         = True
    screen      = None
    stream      = None
    rex_dll     = None # rex_dll ctype instance
    rex         = None # REXPlayer
    waveforms   = []
    mouse_x     = 0
    mouse_y     = 0
    mouse_state = [0,0,0,0,0,0]
    pygame      = None
    labels      = {
        'bpm'   : Label('  BPM', 1185, 611 + (18*0)),
        'obpm'  : Label('O.BPM', 1185, 611 + (18*1)),
        'pitch' : Label('PITCH', 1185, 611 + (18*2)),
        'slice' : Label('SLICE', 1185, 611 + (18*3)),
    }
    
    def init( pygame ):
        App.pygame = pygame
    
    def update():
        App.clock.tick(60)
        App.mouse_x, App.mouse_y = App.pygame.mouse.get_pos()
        App.mouse_state          = App.pygame.mouse.get_pressed()

    def exit():
        App.rex.destroy()
        App.pygame.quit()
    