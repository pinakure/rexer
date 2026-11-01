import os
import sys
import time
import ctypes
import numpy as np
import sounddevice as sd
import pygame
from ctypes import c_int32, c_char_p, c_void_p, POINTER, Structure, c_float

from app import App

# 1. Estructuras de metadatos de REX.h (SDK Oficial)
class REXInfo(Structure):
    _fields_ = [
        ("fChannels", c_int32),
        ("fSampleRate", c_int32),
        ("fSliceCount", c_int32),
        ("fTempo", c_int32),         # Almacenado como BPM * 1000
        ("fOriginalTempo", c_int32),
        ("fPPQLength", c_int32),
        ("fTimeSignNom", c_int32),
        ("fTimeSignDenom", c_int32),
        ("fBitDepth", c_int32)
    ]

class REXSliceInfo(Structure):
    _fields_ = [
        ("fPPQPos", c_int32),
        ("fSampleLength", c_int32)
    ]

def init(ruta_archivo, bpm_inicial):
    try:
        rex_dll = ctypes.CDLL(".\\REX.dll")
    except OSError as E:
        print(f"Error cargando REX.dll: {E}")
        exit()

    # Definición estricta de Prototipos de la API de REX
    rex_dll.REXInitializeDLL.argtypes = []
    rex_dll.REXInitializeDLL.restype = c_int32

    rex_dll.REXCreate.argtypes = [POINTER(c_void_p), c_char_p, c_int32, c_void_p, c_void_p]
    rex_dll.REXCreate.restype = c_int32

    rex_dll.REXGetInfo.argtypes = [c_void_p, c_int32, POINTER(REXInfo)]
    rex_dll.REXGetInfo.restype = c_int32

    rex_dll.REXGetSliceInfo.argtypes = [c_void_p, c_int32, c_int32, POINTER(REXSliceInfo)]
    rex_dll.REXGetSliceInfo.restype = c_int32

    rex_dll.REXSetOutputSampleRate.argtypes = [c_void_p, c_int32]
    rex_dll.REXSetOutputSampleRate.restype = c_int32

    rex_dll.REXRenderSlice.argtypes = [c_void_p, c_int32, c_int32, POINTER(POINTER(c_float))]
    rex_dll.REXRenderSlice.restype = c_int32

    # Funciones de Preescucha (Preview Engine)
    rex_dll.REXStartPreview.argtypes = [c_void_p]
    rex_dll.REXStartPreview.restype = c_int32

    rex_dll.REXStopPreview.argtypes = [c_void_p]
    rex_dll.REXStopPreview.restype = c_int32

    rex_dll.REXSetPreviewTempo.argtypes = [c_void_p, c_int32]
    rex_dll.REXSetPreviewTempo.restype = c_int32

    rex_dll.REXRenderPreviewBatch.argtypes = [c_void_p, c_int32, POINTER(POINTER(c_float))]
    rex_dll.REXRenderPreviewBatch.restype = c_int32

    rex_dll.REXDelete.argtypes = [POINTER(c_void_p)]
    rex_dll.REXDelete.restype = None

    rex_dll.REXUninitializeDLL.argtypes = []
    rex_dll.REXUninitializeDLL.restype = None

    formas_de_onda  = []  
    
    if rex_dll.REXInitializeDLL() != 1:
        print("No se pudo inicializar la DLL.")
        return

    try:
        with open(ruta_archivo, "rb") as f:
            buffer_archivo = f.read()
    except FileNotFoundError:
        print(f"Archivo no encontrado: {ruta_archivo}")
        rex_dll.REXUninitializeDLL()
        return

    manejador_rex = c_void_p(0)
    tamaño_archivo = len(buffer_archivo)

    if rex_dll.REXCreate(ctypes.byref(manejador_rex), buffer_archivo, tamaño_archivo, None, None) != 1:
        print("Error al crear el objeto REX.")
        rex_dll.REXUninitializeDLL()
        return

    info = REXInfo()
    rex_dll.REXGetInfo(manejador_rex, ctypes.sizeof(REXInfo), ctypes.byref(info))
    
    samplerate      = info.fSampleRate
    canales         = info.fChannels
    tempo_original  = info.fTempo / 1000.0
    total_slices    = info.fSliceCount
    total_ppq       = info.fPPQLength

    rex_dll.REXSetOutputSampleRate(manejador_rex, samplerate)

    # --- EXTRACCIÓN GRÁFICA DE AUDIO POR SLICE ---
    print("Pre-renderizando formas de onda desde la DLL...")
    mapa_slices_ppq = []
    

    for i in range(total_slices):
        info_slice = REXSliceInfo()
        rex_dll.REXGetSliceInfo(manejador_rex, i, ctypes.sizeof(REXSliceInfo), ctypes.byref(info_slice))
        mapa_slices_ppq.append(info_slice.fPPQPos)
        
        length_samples = info_slice.fSampleLength
        slice_buf_l = np.zeros(length_samples, dtype=np.float32)
        slice_buf_r = np.zeros(length_samples, dtype=np.float32)
        
        ptr_l = slice_buf_l.ctypes.data_as(POINTER(c_float))
        ptr_r = slice_buf_r.ctypes.data_as(POINTER(c_float))
        
        arreglo_punteros = (POINTER(c_float) * 2)()
        arreglo_punteros[0] = ptr_l
        arreglo_punteros[1] = ptr_r if canales == 2 else None
        
        rex_dll.REXRenderSlice(manejador_rex, i, length_samples, arreglo_punteros)
        formas_de_onda.append(slice_buf_l.copy())

    # Configuración de tempo inicial
    if bpm_inicial is None:
        bpm_inicial = tempo_original
    
    bpm_actual = max(20.0, min(float(bpm_inicial), 450.0))
    rex_dll.REXSetPreviewTempo(manejador_rex, int(bpm_actual * 1000))
    rex_dll.REXStartPreview(manejador_rex)

    BLOCK_SIZE = 1024
    out_buf_l = np.zeros(BLOCK_SIZE, dtype=np.float32)
    out_buf_r = np.zeros(BLOCK_SIZE, dtype=np.float32)
    
    punteros_streaming = (POINTER(c_float) * 2)()
    punteros_streaming[0] = out_buf_l.ctypes.data_as(POINTER(c_float))
    punteros_streaming[1] = out_buf_r.ctypes.data_as(POINTER(c_float)) if canales == 2 else None

    global_acumulador_samples = 0
    pitch_semitones = 0  # Desviación de tono en semitonos (-12 a +12)

    def audio_callback(outdata, frames, time_info, status):
        nonlocal global_acumulador_samples
        if status:
            print(status)
        
        # Renderizar el batch desde la DLL
        rex_dll.REXRenderPreviewBatch(manejador_rex, frames, punteros_streaming)
        
        # Procesamiento del Pitch Shifting (Remuestreo por interpolación lineal)
        # Si el tono cambia, alteramos la velocidad de lectura del buffer devuelto por la DLL
        if pitch_semitones != 0:
            # Factor de velocidad: 2^(semitonos / 12)
            factor_pitch = 2.0 ** (pitch_semitones / 12.0)
            
            # Crear los índices de remuestreo
            indices = np.arange(0, frames) * factor_pitch
            indices = np.clip(indices, 0, BLOCK_SIZE - 1)
            
            # Interpolación lineal de los buffers
            idx_bajo = indices.astype(np.int32)
            idx_alto = np.clip(idx_bajo + 1, 0, BLOCK_SIZE - 1)
            frac = indices - idx_bajo
            
            buf_l_pitched = (1.0 - frac) * out_buf_l[idx_bajo] + frac * out_buf_l[idx_alto]
            if canales == 2:
                buf_r_pitched = (1.0 - frac) * out_buf_r[idx_bajo] + frac * out_buf_r[idx_alto]
            
            if canales == 2:
                outdata[:, 0] = buf_l_pitched
                outdata[:, 1] = buf_r_pitched
            else:
                outdata[:, 0] = buf_l_pitched
        else:
            if canales == 2:
                outdata[:, 0] = out_buf_l
                outdata[:, 1] = out_buf_r
            else:
                outdata[:, 0] = out_buf_l
            
        global_acumulador_samples += frames

    stream = sd.OutputStream(
        samplerate  = samplerate,
        channels    = canales,
        callback    = audio_callback,
        blocksize   = BLOCK_SIZE,
        dtype       = 'float32'
    )
    
   
    # Precalcular coordenadas proporcionales X para cada slice
    posiciones_x_bloques = []
    anchos_bloques = []

    for idx, ppq_inicio in enumerate(mapa_slices_ppq):
        x_start = (ppq_inicio / total_ppq) * App.width
        posiciones_x_bloques.append(x_start)
        
        if idx < total_slices - 1:
            ppq_fin = mapa_slices_ppq[idx + 1]
        else:
            ppq_fin = total_ppq
            
        duracion_ppq = ppq_fin - ppq_inicio
        x_width = (duracion_ppq / total_ppq) * App.width
        anchos_bloques.append(x_width)
    
    App.rex_dll = rex_dll
    App.stream  = stream
    return manejador_rex

    stream.start()
    ejecutando = True

    while ejecutando:
        mouse_x, mouse_y = pygame.mouse.get_pos()
        clicks_mouse = pygame.mouse.get_pressed()


        segundos_actuales = global_acumulador_samples / samplerate
        ppq_actual = int(segundos_actuales * (bpm_actual / 60.0) * 15360) % total_ppq

        slice_activo_idx = 0
        for i in range(len(mapa_slices_ppq)):
            if ppq_actual >= mapa_slices_ppq[i]:
                slice_activo_idx = i
            else:
                break

        pantalla.fill((20, 20, 22))
        y_centro = 160  
        alto_contenedor = 250

        # Dibujo de contenedores y ondas
        for idx, datos_audio in enumerate(formas_de_onda):
            x_inicio = posiciones_x_bloques[idx]
            ancho_bloque = anchos_bloques[idx]
            
            if idx == slice_activo_idx:
                color_fondo = (30, 45, 40)
                color_onda = (0, 255, 130)  
            else:
                color_fondo = (28, 28, 32)
                color_onda = (70, 110, 140)  

            pygame.draw.rect(
                pantalla, 
                color_fondo, 
                (int(x_inicio) + 1, int(y_centro - alto_contenedor/2), max(1, int(ancho_bloque) - 2), int(alto_contenedor)),
                border_radius=2
            )

            ancho_pixel_bloque = max(1, int(ancho_bloque) - 4)
            if ancho_pixel_bloque > 2 and len(datos_audio) > 0:
                chunks_audio = np.array_split(datos_audio, ancho_pixel_bloque)

                for px in range(ancho_pixel_bloque):
                    if len(chunks_audio[px]) > 0:
                        pico = np.max(np.abs(chunks_audio[px]))
                        amplitud_pixeles = int(pico * (alto_contenedor / 2) * 0.9)
                        x_pixel = int(x_inicio + 2 + px)
                        
                        pygame.draw.line(
                            pantalla,
                            color_onda,
                            (x_pixel, int(y_centro - amplitud_pixeles)),
                            (x_pixel, int(y_centro + amplitud_pixeles)),
                            1
                        )

        # Playhead global
        x_playhead_global = (ppq_actual / total_ppq) * App.width
        pygame.draw.line(
            pantalla,
            (255, 255, 255),
            (int(x_playhead_global), int(y_centro - alto_contenedor/2)),
            (int(x_playhead_global), int(y_centro + alto_contenedor/2)),
            2
        )

        # --- TEXTOS INFORMATIVOS EN PANTALLA ---
        txt_bpm = fuente.render(f"BPM Actual: {bpm_actual:.1f} (Original: {tempo_original:.1f})", True, (240, 240, 240))
        txt_pitch = fuente.render(f"Tono (Pitch): {pitch_semitones:+} semitonos", True, (240, 240, 240))
        txt_slice = fuente.render(f"Slice Sonando: {slice_activo_idx + 1} / {total_slices}", True, (0, 255, 130))
        
        pantalla.blit(txt_bpm, (20, 20))
        pantalla.blit(txt_pitch, (20, 45))
        pantalla.blit(txt_slice, (20, 70))

        # --- DIBUJO DEL INTERFAZ DEL SLIDER 1 (BPM) ---
        pygame.draw.rect(pantalla, (60, 60, 65), (SLIDER_X, SLIDER_BPM_Y, SLIDER_ANCHO, SLIDER_ALTO), border_radius=5)
        progreso_bpm = (bpm_actual - BPM_MIN) / (BPM_MAX - BPM_MIN)
        knob_bpm_x = int(SLIDER_X + progreso_bpm * SLIDER_ANCHO)
        color_kbpm = (255, 255, 255) if ARRASTRE_BPM else (180, 180, 185)
        pygame.draw.circle(pantalla, color_kbpm, (knob_bpm_x, SLIDER_BPM_Y + SLIDER_ALTO // 2), 10)
        
        lbl_bpm_slider = fuente.render("TEMPO (BPM)", True, (150, 150, 150))
        pantalla.blit(lbl_bpm_slider, (20, SLIDER_BPM_Y - 5))

        # --- DIBUJO DEL INTERFAZ DEL SLIDER 2 (PITCH) ---
        pygame.draw.rect(pantalla, (60, 60, 65), (SLIDER_X, SLIDER_PITCH_Y, SLIDER_ANCHO, SLIDER_ALTO), border_radius=5)
        progreso_pitch = (pitch_semitones - PITCH_MIN) / (PITCH_MAX - PITCH_MIN)
        knob_pitch_x = int(SLIDER_X + progreso_pitch * SLIDER_ANCHO)
        color_kpitch = (255, 255, 255) if ARRASTRE_PITCH else (180, 180, 185)
        pygame.draw.circle(pantalla, color_kpitch, (knob_pitch_x, SLIDER_PITCH_Y + SLIDER_ALTO // 2), 10)
        
        lbl_pitch_slider = fuente.render("TONO (PITCH)", True, (150, 150, 150))
        pantalla.blit(lbl_pitch_slider, (20, SLIDER_PITCH_Y - 5))

        pygame.display.flip()
        reloj_fps.tick(60)
