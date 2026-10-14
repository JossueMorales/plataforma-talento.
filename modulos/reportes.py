import streamlit as st
import pandas as pd
import google.generativeai as genai

def renderizar_reportes(df_completo, df_pdi, df_mla):
    st.markdown("## 📊 Reportes e Inteligencia Artificial")
    st.write("Bienvenido al módulo de análisis estratégico de talento.")
    
    # Validar si el usuario es "admin"
    if str(st.session_state.get("id_usuario")).strip().lower() == "admin":
        
        # Validar que exista la llave de Gemini en los secretos
        if "GEMINI_API_KEY" in st.secrets:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### 👑 Panel de Inteligencia de RH (Analista de Datos IA)")
            
            with st.expander("🤖 Pregúntale a Gemini sobre Sucesión, PDI y Evaluaciones", expanded=True):
                st.info("El motor de Gemini procesará los Excel completos de la empresa (Mapa de talento, PDI y Evaluaciones) para darte estadísticas, cruces de datos y resúmenes directivos.")
                
                pregunta_admin = st.text_area(
                    "¿Qué quieres saber sobre los datos de la empresa?", 
                    placeholder="Ej. ¿Cuántas personas son Sucesores Inmediatos y no tienen un PDI iniciado? o ¿Cuáles son las 3 competencias más bajas de la Dirección de Manufactura?",
                    height=100
                )
                
                if st.button("📊 Analizar Base de Datos con IA", type="primary"):
                    if pregunta_admin.strip() == "":
                        st.warning("Por favor, escribe una pregunta primero.")
                    else:
                        with st.spinner("🧠 Leyendo bases de datos y calculando métricas... (Puede tomar unos segundos)"):
                            try:
                                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                                modelo_analista = genai.GenerativeModel('gemini-1.5-flash')
                                
                                # Convertimos a CSV para pasarlo al modelo
                                csv_completo = df_completo.to_csv(index=False) if not df_completo.empty else "Sin datos"
                                csv_pdi = df_pdi.to_csv(index=False) if not df_pdi.empty else "Sin datos"
                                csv_mla = df_mla.to_csv(index=False) if not df_mla.empty else "Sin datos"
                                
                                prompt_analista = f"""
                                Eres el Director de Data Analytics de Recursos Humanos de la empresa Ayvi.
                                Se te proporcionan las bases de datos en vivo de la empresa en formato CSV.
                                
                                Tus instrucciones estrictas:
                                1. Cruza la información de Sucesión (Plantilla), Avance de PDI y Resultados MLA para responder.
                                2. Responde ÚNICAMENTE basándote en los datos adjuntos. No inventes información.
                                3. Calcula porcentajes, conteos o listas exactas si la pregunta lo requiere.
                                4. Da tu respuesta en un formato claro, directivo y profesional.
                                
                                Pregunta del Director de RH: {pregunta_admin}
                                
                                Bases de Datos:
                                === DATOS DE PLANTILLA Y SUCESIÓN ===
                                {csv_completo[:15000]}
                                
                                === ESTATUS DE PDI ===
                                {csv_pdi[:15000]}
                                
                                === RESULTADOS EVALUACIÓN MLA ===
                                {csv_mla[:15000]}
                                """
                                
                                respuesta_analista = modelo_analista.generate_content(prompt_analista)
                                
                                st.success("✅ Análisis completado:")
                                st.markdown(respuesta_analista.text)
                                
                            except Exception as e:
                                st.error(f"❌ Ocurrió un error en el análisis de datos: {e}")
        else:
            st.error("No se encontró la llave GEMINI_API_KEY en los secretos de Streamlit.")
            
    else:
        # Qué ven los usuarios normales que NO son el admin
        st.warning("🔒 **Acceso Restringido**")
        st.info("Esta sección contiene métricas confidenciales y herramientas de Inteligencia Artificial exclusivas para la administración de Recursos Humanos.")
