import  pygame
import  logo
import  sys
import  ctypes
import  ui
import  filesys
from filesys import FileMan
import  audio
from    rex         import REXPlayer
from    interface   import EventHandler
from    app         import App

def main(archivo_entrada, bpm=120.0):    
    ventana     = ui.init( archivo_entrada )
    App.init(pygame)
    App.rex     = REXPlayer(archivo_entrada, bpm)
    ui          .create()
    FileMan.init( pygame, App )
    App.stream.start()
    while App.run:
        App.update()
        for evento in pygame.event.get():
            App.run = EventHandler.handle( evento, App.mouse_x, App.mouse_y, App.mouse_state, App.rex.manager, ventana )
        App.rex.stylus = audio.obtener_puntero_global()
        ui.redraw([0.5, -0.5, 0.0], 1.0, 0, 100, App.rex.stylus)
        FileMan.update()
        FileMan.render(App)
        App.rex.update()
        pygame.display.flip()
    App.exit()
    
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