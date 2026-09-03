# -*- coding: utf-8 -*-
"""Régénère le sidecar base64 du modèle 3D.

    python3 tools/render/mkdata.py

`assets/models/qbot.glb.data.js` réencode le GLB en URI `data:`. `main.js`
l'injecte par une balise `<script src>` quand `location.protocol === 'file:'` :
un `fetch()` de fichier local est refusé par la politique d'origine, un
`<script src>` non. C'est ce qui fait que la 3D fonctionne encore quand on
ouvre une page en double-cliquant dessus.

À LANCER À CHAQUE FOIS QUE `qbot.glb` CHANGE. Sinon le mode `file://` continue
d'afficher l'ANCIEN modèle, sans une ligne d'erreur : le sidecar est un second
exemplaire du fichier, et rien ne vérifie qu'ils concordent.
"""
import base64, os

HERE = os.path.dirname(os.path.abspath(__file__))
GLB = os.path.join(HERE, '..', '..', 'assets', 'models', 'qbot.glb')
OUT = GLB + '.data.js'

data = base64.b64encode(open(GLB, 'rb').read()).decode()
with open(OUT, 'w', encoding='utf-8') as f:
    f.write('window.QBOT_MODEL_DATA = window.QBOT_MODEL_DATA || {};\n')
    f.write(f'window.QBOT_MODEL_DATA["qbot.glb"] = "data:model/gltf-binary;base64,{data}";\n')
print(f"{os.path.basename(OUT)} : {os.path.getsize(OUT)/1e3:.0f} Ko "
      f"pour un GLB de {os.path.getsize(GLB)/1e3:.0f} Ko")
