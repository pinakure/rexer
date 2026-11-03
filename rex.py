import  ctypes
import  pygame
import  numpy       as np
import  sounddevice as sd
from    ctypes      import c_int32, c_char_p, c_void_p, POINTER, Structure, c_float
from    app         import App

class REXInfo(Structure):
    _fields_ = [
        ("fChannels"        , c_int32),
        ("fSampleRate"      , c_int32),
        ("fSliceCount"      , c_int32),
        ("fTempo"           , c_int32),         # Almacenado como BPM * 1000
        ("fOriginalTempo"   , c_int32),
        ("fPPQLength"       , c_int32),
        ("fTimeSignNom"     , c_int32),
        ("fTimeSignDenom"   , c_int32),
        ("fBitDepth"        , c_int32)
    ]

class REXSliceInfo(Structure):
    _fields_ = [
        ("fPPQPos", c_int32),
        ("fSampleLength", c_int32)
    ]
    
class Slice(object):
    def __init__(self, x, width):
        self.x = x
        self.width = width
        # Añadimos contenedores gráficos para optimizar el dibujo
        self.surf_normal = None
        self.surf_active = None

class REXPlayer(object):    
    def __init__(self, filename, bpm):
        self.formas_de_onda             = []
        self.global_acumulador_samples  = 0
        self.bpm                        = float(bpm)
        self.pitch                      = 0
        self.total_ppq                  = 0
        self.mapa_slices_ppq            = []
        self.slices                     = []
        self.timer                      = 0
        self.data                       = None
        self.stylus                     = 0.0
        self.manager                    = None
        
        # Constantes estéticas fijas
        self.y_centro = 247  
        self.alto_contenedor = 328
        
        # Pre-asignación de buffers de audio para evitar el Garbage Collector en tiempo real
        self.BLOCK_SIZE = 1024
        self.idx_base                   = np.arange(0, self.BLOCK_SIZE, dtype=np.float32)
        self.buf_l_pitched              = np.zeros(self.BLOCK_SIZE, dtype=np.float32)
        self.buf_r_pitched              = np.zeros(self.BLOCK_SIZE, dtype=np.float32)
        
        self.loadDLL()
        self.load(filename)
        self.process()
        
    def loadDLL(self):
        try:
            print("Cargando DLL...")
            self.dll = ctypes.CDLL(".\\REX.dll")
            self.bind()            
        except OSError as E:
            print(f"Error cargando REX.dll: {E}")
            App.run = False                    
        
    def initDLL(self):
        try:
            print("Inicializando DLL...")
            if self.dll.REXInitializeDLL() != 1:
                print("No se pudo inicializar la DLL.")
                App.run = False
        except OSError as E:
            print(f"Error inicializando REX.dll: {E}")
            App.run = False
            
    def deinitDLL(self):
        try:
            print("Deinicializando DLL...")
            self.dll.REXUninitializeDLL()
        except OSError as E:
            print(f"Error desinicializando REX.dll: {E}")
            exit()
            
    def load(self, filename):
        self.filename = filename
        self.initDLL()
        try:
            with open( filename, "rb" ) as f:
                self.data       = f.read()        
                self.filesize   = len( self.data )

        except FileNotFoundError:
            print(f"Archivo no encontrado: {filename}")
            self.deinitDLL()
            return
        
    def process(self):
        if self.manager: 
            App.rex_dll.REXStopPreview(self.manager)
            App.rex_dll.REXDelete(ctypes.byref(self.manager))
        self.manager    = c_void_p(0)
    
        if self.dll.REXCreate(ctypes.byref(self.manager), self.data, self.filesize, None, None) != 1:
            print("Error al crear el objeto REX.")
            self.deinitDLL()
            return
    
        info = REXInfo()
        self.dll.REXGetInfo(self.manager, ctypes.sizeof(REXInfo), ctypes.byref(info))
        
        self.samplerate     = info.fSampleRate
        canales             = info.fChannels
        self.originalbpm    = info.fTempo / 1000.0
        self.total_slices   = info.fSliceCount
        self.total_ppq      = info.fPPQLength

        self.dll.REXSetOutputSampleRate(self.manager, self.samplerate)
    
        # --- EXTRACCIÓN GRÁFICA DE AUDIO POR SLICE ---
        print("Pre-renderizando formas de onda desde la DLL...")
        self.mapa_slices_ppq = []
        for i in range(self.total_slices):
            info_slice = REXSliceInfo()
            self.dll.REXGetSliceInfo(self.manager, i, ctypes.sizeof(REXSliceInfo), ctypes.byref(info_slice))
            self.mapa_slices_ppq.append(info_slice.fPPQPos)
            
            length_samples = info_slice.fSampleLength
            slice_buf_l = np.zeros(length_samples, dtype=np.float32)
            slice_buf_r = np.zeros(length_samples, dtype=np.float32)
            
            ptr_l = slice_buf_l.ctypes.data_as(POINTER(c_float))
            ptr_r = slice_buf_r.ctypes.data_as(POINTER(c_float))
            
            arreglo_punteros = (POINTER(c_float) * 2)()
            arreglo_punteros[0] = ptr_l
            arreglo_punteros[1] = ptr_r if canales == 2 else None
            
            self.dll.REXRenderSlice(self.manager, i, length_samples, arreglo_punteros)
            self.formas_de_onda.append(slice_buf_l.copy())
        
        # Configuración de tempo inicial
        if self.bpm is None:
            self.bpm = self.originalbpm
        
        self.bpm = max(20.0, min(float(self.bpm), 450.0))
        self.dll.REXSetPreviewTempo(self.manager, int(self.bpm * 1000))
        self.dll.REXStartPreview(self.manager)
    
        out_buf_l               = np.zeros(self.BLOCK_SIZE, dtype=np.float32)
        out_buf_r               = np.zeros(self.BLOCK_SIZE, dtype=np.float32)
        
        punteros_streaming      = (POINTER(c_float) * 2)()
        punteros_streaming[0]   = out_buf_l.ctypes.data_as(POINTER(c_float))
        punteros_streaming[1]   = out_buf_r.ctypes.data_as(POINTER(c_float)) if canales == 2 else None
        self.stylus             = punteros_streaming[0]
        self.global_acumulador_samples  = 0
        self.pitch                      = 0  # Desviación de tono en semitonos (-12 a +12)
    
        def audio_callback(outdata, frames, time_info, status):
            if status:
                print(status)
            
            # Renderizar el batch desde la DLL
            self.dll.REXRenderPreviewBatch(self.manager, frames, punteros_streaming)
            
            if self.pitch != 0:
                factor_pitch = 2.0 ** (self.pitch / 12.0)
                
                # Reutilizamos buffers pre-asignados modificando el slice correspondiente para evitar reallocs
                indices = self.idx_base[:frames] * factor_pitch
                np.clip(indices, 0, self.BLOCK_SIZE - 1, out=indices)
                
                idx_bajo = indices.astype(np.int32)
                idx_alto = idx_bajo + 1
                np.clip(idx_alto, 0, self.BLOCK_SIZE - 1, out=idx_alto)
                frac = indices - idx_bajo
                
                # Procesar canales sobre arrays pre-asignados
                self.buf_l_pitched[:frames] = (1.0 - frac) * out_buf_l[idx_bajo] + frac * out_buf_l[idx_alto]
                if canales == 2:
                    self.buf_r_pitched[:frames] = (1.0 - frac) * out_buf_r[idx_bajo] + frac * out_buf_r[idx_alto]
                    outdata[:, 0] = self.buf_l_pitched[:frames]
                    outdata[:, 1] = self.buf_r_pitched[:frames]
                else:
                    outdata[:, 0] = self.buf_l_pitched[:frames]
            else:
                if canales == 2:
                    outdata[:, 0] = out_buf_l[:frames]
                    outdata[:, 1] = out_buf_r[:frames]
                else:
                    outdata[:, 0] = out_buf_l[:frames]
                
            self.global_acumulador_samples += frames

        stream = sd.OutputStream(
            samplerate  = self.samplerate,
            channels    = canales,
            callback    = audio_callback,
            blocksize   = self.BLOCK_SIZE,
            dtype       = 'float32'
        )
        
        # Precalcular coordenadas proporcionales X para cada slice
        self.slices = []
        for idx, ppq_inicio in enumerate(self.mapa_slices_ppq):
            x_start = 71 + ((ppq_inicio / self.total_ppq) * 1513)
           
            if idx < self.total_slices - 1:
                ppq_fin = self.mapa_slices_ppq[idx + 1]
            else:
                ppq_fin = self.total_ppq
               
            duracion_ppq = ppq_fin - ppq_inicio
            x_width = (duracion_ppq / self.total_ppq) * 1513
            
            nuevo_slice = Slice(x_start, x_width)
            
            # Pre-renderizado estático de ondas
            ancho_pixel_bloque = max(1, int(x_width) - 4)
            datos_audio = self.formas_de_onda[idx]
            
            # Creamos dos superficies por slice (Normal y Activa) con fondo transparente
            surf_n = pygame.Surface((ancho_pixel_bloque + 4, self.alto_contenedor), pygame.SRCALPHA)
            surf_a = pygame.Surface((ancho_pixel_bloque + 4, self.alto_contenedor), pygame.SRCALPHA)
            
            if ancho_pixel_bloque > 2 and len(datos_audio) > 0:
                chunks_audio = np.array_split(datos_audio, ancho_pixel_bloque)
                y_centro_local = self.alto_contenedor // 2
                
                pygame.draw.line(surf_n, ( 27, 102,   0), (0, 10 ), (0, 340), 1)
                pygame.draw.line(surf_a, ( 52,  64,   0), (0, 10 ), (0, 340), 1)
                
                pygame.draw.line(surf_n, ( 52, 124,   0), (0, 40 ), (0, 310), 1)
                pygame.draw.line(surf_a, (105, 128,   0), (0, 40 ), (0, 310), 1)
                                                        
                pygame.draw.line(surf_n, (105, 188,   0), (0, 80 ), (0, 270), 1)
                pygame.draw.line(surf_a, (210, 255,   0), (0, 80 ), (0, 270), 1)
                                                        
                for px in range(ancho_pixel_bloque):
                    if len(chunks_audio[px]) > 0:
                        pico = np.max(np.abs(chunks_audio[px]))
                        amplitud_pixeles = int(pico * y_centro_local * 0.9)
                        x_pixel = 2 + px
                        
                        # Dibujamos de forma única en las superficies cacheadas
                        pygame.draw.line(surf_n, ( 15, 102,  65), (x_pixel, y_centro_local - amplitud_pixeles), (x_pixel, y_centro_local + amplitud_pixeles), 1)
                        pygame.draw.line(surf_a, ( 31, 205, 130), (x_pixel, y_centro_local - amplitud_pixeles), (x_pixel, y_centro_local + amplitud_pixeles), 1)
            
            nuevo_slice.surf_normal = surf_n
            nuevo_slice.surf_active = surf_a
            self.slices.append(nuevo_slice)

        App.rex_dll = self.dll
        App.stream  = stream
        
    def bind(self):
        self.dll.REXInitializeDLL.argtypes       = []
        self.dll.REXInitializeDLL.restype        = c_int32
        self.dll.REXCreate.argtypes              = [POINTER(c_void_p), c_char_p, c_int32, c_void_p, c_void_p]
        self.dll.REXCreate.restype               = c_int32
        self.dll.REXGetInfo.argtypes             = [c_void_p, c_int32, POINTER(REXInfo)]
        self.dll.REXGetInfo.restype              = c_int32
        self.dll.REXGetSliceInfo.argtypes        = [c_void_p, c_int32, c_int32, POINTER(REXSliceInfo)]
        self.dll.REXGetSliceInfo.restype         = c_int32
        self.dll.REXSetOutputSampleRate.argtypes = [c_void_p, c_int32]
        self.dll.REXSetOutputSampleRate.restype  = c_int32
        self.dll.REXRenderSlice.argtypes         = [c_void_p, c_int32, c_int32, POINTER(POINTER(c_float))]
        self.dll.REXRenderSlice.restype          = c_int32
        self.dll.REXStartPreview.argtypes        = [c_void_p]
        self.dll.REXStartPreview.restype         = c_int32
        self.dll.REXStopPreview.argtypes         = [c_void_p]
        self.dll.REXStopPreview.restype          = c_int32
        self.dll.REXSetPreviewTempo.argtypes     = [c_void_p, c_int32]
        self.dll.REXSetPreviewTempo.restype      = c_int32
        self.dll.REXRenderPreviewBatch.argtypes  = [c_void_p, c_int32, POINTER(POINTER(c_float))]
        self.dll.REXRenderPreviewBatch.restype   = c_int32
        self.dll.REXDelete.argtypes              = [POINTER(c_void_p)]
        self.dll.REXDelete.restype               = None
        self.dll.REXUninitializeDLL.argtypes     = []
        self.dll.REXUninitializeDLL.restype      = None

    def update(self):
        if not App.run: return 
        segundos_actuales   = self.global_acumulador_samples / self.samplerate
        ppq_actual          = int(segundos_actuales * (self.bpm / 60.0) * 15360) % self.total_ppq
        
        # Separar búsqueda de dibujo (Des-anidado)
        slice_activo_idx    = 0
        for i in range(len(self.mapa_slices_ppq)):
            if ppq_actual >= self.mapa_slices_ppq[i]:
                slice_activo_idx = i
            else:
                break
        
        # El dibujo se ejecuta UNA sola vez por frame, fuera de los bucles de lógica posicional
        y_esquina_render = self.y_centro - (self.alto_contenedor // 2)
        
        # Dibujo mediante Blit de texturas precalculadas
        for idx, s in enumerate(self.slices):
            if idx == slice_activo_idx:
                App.screen.blit(s.surf_active, (int(s.x), y_esquina_render))
            else:
                App.screen.blit(s.surf_normal, (int(s.x), y_esquina_render))
                
        # Playhead global
        x_playhead_global = 71 + ((ppq_actual / self.total_ppq) * 1513)
        pygame.draw.line(
            App.screen,
            ( 62, 255, 200),
            (int(x_playhead_global), int(self.y_centro - self.alto_contenedor/2)),
            (int(x_playhead_global), int(self.y_centro + self.alto_contenedor/2)),
            2
        )

        # --- TEXTOS INFORMATIVOS EN PANTALLA ---
        color = App.labels[  'bpm'].highlight if (self.timer % 1==0) else App.labels[  'bpm'].color
        self.timer+=1
        txt_bpm   = App.fonts.ocr.render(f"{self.bpm:.1f}"                                                  , True, color)
        txt_obpm  = App.fonts.ocr.render(f"{self.originalbpm:.1f})"                                         , True, color)
        txt_pitch = App.fonts.ocr.render(f"{self.pitch:+}"                                                  , True, color)
        txt_slice = App.fonts.ocr.render(f"{str(slice_activo_idx + 1).rjust(2,'0')} / {self.total_slices}"  , True, color)
        App.screen.blit(txt_bpm     , App.labels['bpm'  ].position)
        App.screen.blit(txt_obpm    , App.labels['obpm' ].position)
        App.screen.blit(txt_pitch   , App.labels['pitch'].position)
        App.screen.blit(txt_slice   , App.labels['slice'].position)

    def destroy(self):
        App.rex_dll.REXStopPreview(self.manager)
        App.rex_dll.REXDelete(ctypes.byref(self.manager))
        App.rex_dll.REXUninitializeDLL()
        App.stream.stop()
        App.stream.close()
