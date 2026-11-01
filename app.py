class FontCache:
    lcd         = None
    display     = None 
    ocr         = None
    heading     = None
    monospace   = None
    small       = None

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
    rex_dll     = None
    waveforms   = []