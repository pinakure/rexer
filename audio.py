import os
import numpy as np
import sounddevice as sd
from pydub import AudioSegment

_audio_data = None
_inicio = 0
_duracion = 0
_puntero = 0
_reproduciendo = False
_bucle = False

def audio_callback(outdata, frames, time_info, status):
    global _audio_data, _inicio, _duracion, _puntero, _reproduciendo, _bucle
    if not _reproduciendo or _audio_data is None or _duracion <= 0:
        outdata.fill(0)
        return

    for i in range(frames):
        idx_global = _inicio + _puntero
        if idx_global < len(_audio_data):
            outdata[i] = _audio_data[idx_global]
        else:
            outdata[i] = 0
            
        _puntero += 1
        if _puntero >= _duracion:
            if _bucle:
                _puntero = 0
            else:
                _reproduciendo = False
                outdata[i:] = 0
                break

def cargar_audio(ruta):
    if isinstance(ruta, (list, tuple)): 
        ruta = ruta if len(ruta) > 1 else ruta
    ruta = str(ruta)
    ext = os.path.splitext(ruta)[1].lower()
    
    if ext == '.wav': audio_seg = AudioSegment.from_wav(ruta)
    elif ext == '.mp3': audio_seg = AudioSegment.from_mp3(ruta)
    else: raise ValueError(f"Formato no soportado: {ext}")
        
    ancho_muestra = audio_seg.sample_width
    if ancho_muestra == 2: dtype = np.int16
    elif ancho_muestra == 1: dtype = np.int8
    elif ancho_muestra == 4: dtype = np.int32
    else: raise ValueError("Profundidad de bits no soportada.")

    audio_data = np.frombuffer(audio_seg.raw_data, dtype=dtype)
    fps = audio_seg.frame_rate
    
    audio_float = audio_data.astype(np.float32) / np.iinfo(dtype).max
    if audio_seg.channels == 2:
        audio_reproduccion = audio_float.reshape(-1, 2)
        audio_grafica = audio_float[::2]  
    else:
        audio_reproduccion = audio_float.reshape(-1, 1)
        audio_grafica = audio_float
        
    return audio_grafica, audio_reproduccion, fps, audio_seg.channels, audio_seg

def inicializar_motor(audio_rep, fps, canales):
    global _audio_data
    _audio_data = audio_rep
    stream = sd.OutputStream(samplerate=fps, channels=canales, callback=audio_callback)
    stream.start()
    return stream

def play(inicio, duracion, loop=False):
    global _inicio, _duracion, _puntero, _bucle, _reproduciendo
    _inicio = int(inicio)
    _duracion = int(duracion)
    _puntero = 0
    _bucle = loop
    _reproduciendo = True

def stop():
    global _reproduciendo, _bucle
    _reproduciendo = False
    _bucle = False

def esta_reproduciendo():
    return _reproduciendo

def obtener_puntero_global():
    global _inicio, _puntero, _reproduciendo
    if _reproduciendo:
        return _inicio + _puntero
    return _inicio

def actualizar_parametros_dinamicos(inicio, duracion):
    global _inicio, _duracion
    _inicio = int(inicio)
    _duracion = int(duracion)

def exportar_loops(audio_seg, offset_muestras, duracion_muestras, fps):
    """Exporta los loops considerando el trozo descartado al inicio."""
    duracion_ms_loop = (duracion_muestras / fps) * 1000
    offset_ms = (offset_muestras / fps) * 1000
    
    # Recortamos el audio original para quitar el offset inicial antes de segmentar
    audio_recortado = audio_seg[offset_ms:]
    total_ms = len(audio_recortado)
    num_loops = int(total_ms // duracion_ms_loop)
    
    for i in range(num_loops):
        inicio_ms = i * duracion_ms_loop
        fin_ms = inicio_ms + duracion_ms_loop
        loop_segmento = audio_recortado[inicio_ms:fin_ms]
        nombre_salida = f"loop_{i+1:03d}.wav"
        loop_segmento.export(nombre_salida, format="wav")
    print(f"¡Éxito! Se han exportado {num_loops} loops descartando {offset_muestras} muestras iniciales.")
