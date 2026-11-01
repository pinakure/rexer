import  pygame
import  logo
import  sys
import  ctypes
import  ui
import  filesys
import  audio
import  rex    
from    interface   import EventHandler
from    app         import App

def main(archivo_entrada, bpm=120.0):    
    ventana     = ui.init( archivo_entrada )
    mgr         = rex.init( archivo_entrada, bpm)
    ui          .create()
    App.stream.start()
    while App.run:
        App.clock.tick(60)
        mouse_x, mouse_y = pygame.mouse.get_pos()
        mouse_state      = pygame.mouse.get_pressed()

        for evento in pygame.event.get():
            App.run = EventHandler.handle( evento, mouse_x, mouse_y, mouse_state, mgr, ventana )

        ui.redraw([0.5, -0.5, 0.0], 1.0, 0, 100, audio.obtener_puntero_global())
       
    App.rex_dll.REXStopPreview(mgr)
    App.rex_dll.REXDelete(ctypes.byref(mgr))
    App.rex_dll.REXUninitializeDLL()
    App.stream.stop()
    App.stream.close()
    pygame.quit()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        ruta, fichero = filesys.obtener_nombre_fichero(tipos_archivo=[("REX Loops", "*.rx2")])
        if ruta is None or fichero is None:
            print("Missing parameter: < REX > [ BPM ]")
            exit(1)
        main(fichero)
    else:
        if len(sys.argv) < 3:
            main(sys.argv[1])
        elif len(sys.argv) < 4:
            main(sys.argv[1], sys.argv[2])