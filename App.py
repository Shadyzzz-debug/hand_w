import streamlit as st
import base64
import json
import requests # Requerido para la llamada HTTP
import time
import io
from PIL import Image
from streamlit_drawable_canvas import st_canvas

# --- Configuraciones del LLM para el entorno ---
GEMINI_CHAT_MODEL = "gemini-2.5-flash-preview-09-2025" 
# La clave se leerá desde el input, no desde el entorno.
# Se añade el 'requests' package para resolver el AttributeError

# --- CSS GÓTICO (Paleta Arcano-Escarlata) ---
gothic_css = """
<style>
/* Paleta base: Fondo #111111, Texto #E0E0E0 (Pergamino ligero), Acento #5A4832 (Bronce/Metal), Sangre #A50000 */
.stApp {
    background-color: #111111;
    color: #E0E0E0;
    font-family: 'Georgia', serif;
}

/* Título Principal (h1) */
h1 {
    color: #A50000; /* Rojo sangre */
    text-shadow: 3px 3px 8px #000000;
    font-size: 3.2em; 
    border-bottom: 5px solid #5A4832; /* Borde Bronce */
    padding-bottom: 10px;
    margin-bottom: 30px;
    text-align: center;
    letter-spacing: 2px;
}

/* Subtítulos (h2, h3): Énfasis en el bronce */
h2, h3 {
    color: #C0C0C0; /* Plata/gris claro */
    border-left: 5px solid #5A4832;
    padding-left: 10px;
    margin-top: 25px;
}

/* Input y TextArea (Pergamino de Inscripción) */
div[data-testid="stTextInput"], div[data-testid="stTextarea"], .stFileUploader, .stCameraInput {
    background-color: #1A1A1A;
    border: 1px solid #5A4832;
    padding: 10px;
    border-radius: 5px;
    color: #F5F5DC;
}

/* Botones (Sellos de Invocación) */
.stButton>button {
    background-color: #5A4832; /* Bronce Oscuro */
    color: #E0E0E0;
    border: 2px solid #A50000; /* Borde de Sangre */
    padding: 10px 20px;
    font-weight: bold;
    border-radius: 8px;
    transition: all 0.3s;
    box-shadow: 0 4px #2D2418;
}

.stButton>button:hover {
    background-color: #6C5B49;
    box-shadow: 0 6px #1A1A1A;
    transform: translateY(-2px);
}

.stButton>button:active {
    box-shadow: 0 2px #1A1A1A;
    transform: translateY(2px);
}

/* Toggle (Mecanismo Secreto) */
.stCheckbox, .stRadio, .stSelectbox {
    color: #C0C0C0;
}

/* Texto de Alertas (Revelaciones) */
.stSuccess { background-color: #20251B; color: #F5F5DC; border-left: 5px solid #5A4832; }
.stInfo { background-color: #1A1A25; color: #F5F5DC; border-left: 5px solid #5A4832; }
.stWarning { background-color: #352A1A; color: #F5F5DC; border-left: 5px solid #A50000; }
.stError { background-color: #4A1A1A; color: #F5F5DC; border-left: 5px solid #A50000; }

/* Placeholder para la respuesta */
div[data-testid="stMarkdownContainer"] {
    background-color: #1A1A1A;
    padding: 20px;
    border: 1px solid #5A4832;
    border-radius: 5px;
}
</style>
"""
st.markdown(gothic_css, unsafe_allow_html=True)


# --- Funciones de Utilidad (Uso de 'requests' para la API de Gemini) ---

def safe_fetch_request(url, api_key, method='POST', headers=None, body=None, max_retries=3, delay=1):
    """Realiza llamadas a la API con reintentos y retroceso exponencial usando 'requests'."""
    if headers is None:
        headers = {'Content-Type': 'application/json'}
    
    # Agregar la clave API a la URL
    url_with_key = f"{url}?key={api_key}"
    
    for attempt in range(max_retries):
        try:
            response = requests.request(method, url_with_key, headers=headers, data=body, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code in [429, 500, 503] and attempt < max_retries - 1:
                time.sleep(delay * (2 ** attempt))
                continue
            else:
                error_detail = response.text if response.text else f"Código de estado: {response.status_code}"
                raise Exception(f"Fallo en la llamada a la API ({response.status_code}). {error_detail}")
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(delay * (2 ** attempt))
                continue
            raise Exception(f"Error de red/conexión: {e}")
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(delay * (2 ** attempt))
                continue
            raise e
    raise Exception("Llamada a la API fallida después de múltiples reintentos.")


def get_gemini_vision_answer(base64_image: str, mime_type: str, user_prompt: str, api_key: str) -> str:
    """Invoca la API de Gemini para análisis de visión."""
    
    # Construcción del payload
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": user_prompt},
                    {
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": base64_image
                        }
                    }
                ]
            }
        ]
    }
    
    apiUrl = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_CHAT_MODEL}:generateContent"

    response_data = safe_fetch_request(apiUrl, api_key, body=json.dumps(payload))
    
    # Manejo de la respuesta
    candidate = response_data.get('candidates', [{}])[0]
    text = candidate.get('content', {}).get('parts', [{}])[0].get('text', None)

    if text:
        return text
    
    # Revisar si hay un mensaje de error explícito de la API
    error_message = response_data.get('error', {}).get('message', 'Respuesta incompleta o vacía del Oráculo.')
    raise Exception(f"Fallo de la Visión Arcana: {error_message}")


# --- Streamlit App Setup ---

st.title("👁️ El Ojo del Arcano: Códice de la Numerología Manual")
st.markdown("---")

# Input para la API Key (Sello Arcano)
ke = st.text_input('Ingresa el Sello Arcano (Clave API)', type="password", key="api_key_input")
if not ke:
    st.info("Introduce el Sello Arcano para dotar de Visión al Ojo.")


# --- Configuración del Canvas (El Papiro de la Inscripción) ---

st.subheader("Traza el Símbolo Numérico")
st.markdown("Dibuja un único dígito (0-9) en el papiro negro para invocar su significado numérico.")

# Parámetros del Canvas
drawing_mode = "freedraw"
stroke_width = st.slider('Define la Pluma del Símbolo (Ancho de Línea)', 1, 30, 15)
stroke_color = '#FFFFFF' # Color de trazo blanco (visible)
bg_color = '#000000' # Fondo negro (como la pizarra)

# Crear el componente Canvas
canvas_result = st_canvas(
    stroke_width=stroke_width,
    stroke_color=stroke_color,
    background_color=bg_color,
    height=200,
    width=200,
    key="canvas",
)


# Toggle para la pregunta específica (Invocación de Contexto)
show_details = st.toggle("Invocar Profundización de Análisis", value=False)

additional_details = ""
if show_details:
    additional_details = st.text_area(
        "Dicta la Pregunta Específica sobre el Dígito:",
        placeholder="Ej: ¿Qué posibles significados esotéricos podría tener este símbolo?",
        disabled=not show_details,
        key="context_area"
    )

# Button to trigger the analysis (Apertura del Ojo)
analyze_button = st.button("Abre el Ojo del Arcano (Analizar)", type="secondary")

# Check if conditions are met
if canvas_result.image_data is not None and analyze_button:
    
    # Advertencia del Sello Arcano
    if not ke:
        st.warning("El Sello Arcano es obligatorio para invocar la Visión. Por favor, ingrésalo.")
        st.stop()
        
    # Verificar si el dibujo está vacío
    if not canvas_result.image_data.any():
        st.warning("El papiro está en blanco. Por favor, traza un símbolo numérico.")
        st.stop()
        
    with st.spinner("El Ojo del Arcano se está abriendo para descifrar el símbolo..."):
        try:
            # 1. Preparar la Reliquia (Codificación Base64)
            input_numpy_array = canvas_result.image_data
            input_image = Image.fromarray(input_numpy_array.astype('uint8'), 'RGBA').convert('RGB')
            
            # Guardar en memoria como PNG para Base64
            buf = io.BytesIO()
            input_image.save(buf, format='PNG')
            file_bytes = buf.getvalue()
            
            base64_image = base64.b64encode(file_bytes).decode("utf-8")
            mime_type = 'image/png'

            # 2. Construir el Conjuro (Prompt)
            prompt_text = (
                "Analiza la imagen que contiene un dígito escrito a mano (0-9). "
                "Responde ÚNICAMENTE con el número que has identificado, y luego, en un párrafo separado, "
                "proporciona una descripción solemne y formal de tu hallazgo en español."
            )
            
            if show_details and additional_details:
                prompt_text += (
                    f"\n\n**INSTRUCCIÓN DE PROFUNDIZACIÓN INVOCADA:** {additional_details}"
                )
            
            # 3. Invocar la Visión
            response = get_gemini_vision_answer(base64_image, mime_type, prompt_text, ke)
            
            # 4. Mostrar la Revelación
            st.markdown("### 📜 La Revelación del Oráculo:")
            st.markdown(response)
            
        except Exception as e:
            st.error(f"Fallo en la Invocación. El Ojo no pudo abrirse: {e}")
            
else:
    # Mensajes de estado
    if analyze_button and canvas_result.image_data is None:
        st.warning("El Canvas no ha sido inicializado o no contiene datos.")


