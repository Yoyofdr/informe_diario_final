from datetime import datetime

def generar_informe_html(publicaciones, fecha=None, valores_monedas=None, documentos_analizados=None, tiempo_lectura=None, url_informe_completo=None):
    """
    Genera un informe HTML visualmente atractivo y profesional, inspirado en lovable, sin emojis, con todos los hechos relevantes, badges, bloques destacados y valores de monedas. Ahora ocupa todo el ancho disponible (full-width) y el header está bien ordenado.
    """
    if fecha is None:
        fecha = datetime.now().strftime('%d-%m-%Y')
    if documentos_analizados is None:
        documentos_analizados = len(publicaciones) if publicaciones else 0
    if tiempo_lectura is None:
        tiempo_lectura = max(1, documentos_analizados // 4)
    if url_informe_completo is None:
        url_informe_completo = "https://informediario.cl/informe-completo"  # Placeholder

    # Función para color de borde según categoría
    def color_categoria(cat):
        if cat == 'laboral':
            return '#2563eb'  # azul
        elif cat == 'salud':
            return '#22c55e'  # verde
        elif cat == 'educacion':
            return '#fbbf24'  # amarillo
        else:
            return '#a21caf'  # morado

    html = f"""
    <html>
    <body style='margin:0; padding:0; background:#f6f8fb; font-family: Segoe UI, Arial, sans-serif; color:#1e293b;'>
      <div style='width:100%; background:#f6f8fb;'>
        <div style='background:#fff; width:100%; max-width:100%; margin:0; border-radius:0; box-shadow:none; padding:0;'>
          <!-- Header sobrio -->
          <div style='padding:32px 0 18px 0; text-align:center;'>
            <div style="font-size:2.2em; font-weight:900; margin-bottom:8px; letter-spacing:-1.5px; color:#231D54;">Informe Diario Oficial</div>
            <div style="font-size:1.25em; color:#64748b; font-weight:600;">{fecha}</div>
          </div>
          <!-- Badges -->
          <div style='padding:20px 32px 0 32px;'>
            <div style='display:flex; gap:12px; margin-bottom:8px;'>
              <span style='display:inline-block; background:#e0e7ff; color:#2563eb; font-weight:700; border-radius:14px; padding:7px 18px; font-size:1em; box-shadow:0 2px 8px #2563eb11;'>
                {documentos_analizados} documentos analizados
              </span>
              <span style='display:inline-block; background:#d1fae5; color:#059669; font-weight:700; border-radius:14px; padding:7px 18px; font-size:1em; box-shadow:0 2px 8px #05966911;'>
                {tiempo_lectura} min de lectura
              </span>
            </div>
          </div>
          <!-- Separador -->
          <div style='height:1px; background:#e5e7eb; margin:18px 32px 0 32px;'></div>
          <!-- Lista de hechos -->
          <div style='padding:18px 32px 0 32px;'>
    """
    if not publicaciones:
        html += "<div style='padding: 24px 0 24px 0; color: #555; font-size: 1.08em; text-align:center;'>No hay publicaciones relevantes hoy.</div>"
    else:
        for pub in publicaciones:
            url = pub['url_pdf']
            if url.startswith('http'):
                url_final = url
            else:
                url_final = f'https://www.diariooficial.interior.gob.cl{url}'
            cat = pub.get('categoria', 'otros')
            # Extraer entidad y documento del título (asumiendo formato: 'ENTIDAD: Documento...')
            entidad = ''
            documento = pub['titulo']
            if ':' in pub['titulo']:
                partes = pub['titulo'].split(':', 1)
                entidad = partes[0].strip()
                documento = partes[1].strip()
            html += f"""
              <div style='border-left:5px solid {color_categoria(cat)}; padding-left:20px; margin-bottom:22px; background:#f8fafc; border-radius:10px; padding-top:14px; padding-bottom:14px; box-shadow:0 2px 12px #2563eb0a;'>
                <div style='font-size:1.08em; font-weight:700; color:#6366f1; margin-bottom:2px;'>{entidad}</div>
                <div style='font-size:1.18em; font-weight:800; margin-bottom:4px; color:#1e293b; letter-spacing:-0.5px;'>{documento}</div>
                <div style='color:#334155; font-size:1.04em; margin-bottom:7px; line-height:1.6;'>
                  <b>Resumen:</b> {pub['resumen']}
                </div>
                <a href='{url_final}' target='_blank' style='color:#2563eb; text-decoration:underline; font-size:1em; font-weight:600;'>Ver documento PDF</a>
              </div>
            """
    html += f"""
          </div>
          <!-- Separador -->
          <div style='height:1px; background:#e5e7eb; margin:18px 32px 0 32px;'></div>
          <!-- Valores de monedas -->
          <div style='padding:0 32px 0 32px;'>
    """
    if valores_monedas and (valores_monedas.get('dolar') or valores_monedas.get('euro')):
        html += f"<div style='margin-top:24px; margin-bottom:24px; padding:22px; background:#f8f9fa; border-radius:14px; border:1.5px solid #e0e0e0; color:#222; font-size:1.13em; font-weight:600; box-shadow:0 2px 12px #2563eb0a;'>"
        html += "<span style='color:#2563eb; font-weight:800;'>Valores de referencia publicados por el Banco Central de Chile:</span><br>"
        if valores_monedas.get('dolar'):
            html += f"Dólar observado: <b style='color:#2563eb; font-size:1.08em;'>${valores_monedas['dolar']}</b><br>"
        if valores_monedas.get('euro'):
            html += f"Euro: <b style='color:#059669; font-size:1.08em;'>${valores_monedas['euro']}</b><br>"
        html += "</div>"
    else:
        html += f"<div style='margin-top:24px; margin-bottom:24px; padding:22px; background:#f8f9fa; border-radius:14px; border:1.5px solid #e0e0e0; color:#222; font-size:1.13em; font-weight:600; box-shadow:0 2px 12px #2563eb0a;'>"
        html += "<span style='color:#2563eb; font-weight:800;'>Valores de dólar y euro:</span> No publicados en la edición de hoy."
        html += "</div>"
    html += f"""
          </div>
          <!-- Footer -->
          <div style='padding:24px 32px 0 32px;'>
            <div style='display:flex; align-items:center; justify-content:space-between; border-top:1px solid #e5e7eb; padding-top:18px; margin-top:10px;'>
              <div style='color:#64748b; font-size:1.05em; text-align:left; font-weight:500;'>
                Tiempo de lectura: {tiempo_lectura} minutos
              </div>
              <a href='{url_informe_completo}' style='background:#2563eb; color:#fff; font-weight:800; border-radius:10px; padding:13px 30px; text-decoration:none; font-size:1.08em; box-shadow:0 2px 12px 0 #2563eb33; border:0; display:inline-block; margin-left:auto;'>Ver informe completo →</a>
            </div>
          </div>
        </div>
      </div>
    </body>
    </html>
    """
    return html 