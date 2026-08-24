# Publicar en GitHub Pages

El proyecto ya incluye `index.html`, `style.css`, `app.js` y `data/` en la raíz.

En GitHub: **Settings → Pages → Build and deployment → Source: Deploy from a branch → main → /(root) → Save**.

Después de unos minutos, GitHub mostrará la URL pública de la aplicación.

Para probar localmente:

```bash
python -m http.server 8000
```

Abre `http://localhost:8000/`.
