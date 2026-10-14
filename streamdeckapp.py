# Controle do PC via celular — botões definidos em botoes.json
# Roda em segundo plano (use iniciar.bat / parar.bat)
# Requisitos: pip install flask pynput
# Manual:     python controle.py   (mostra o endereço no terminal)
# Segundo plano: iniciar.bat       (sem terminal, log em log.txt)

from flask import Flask, jsonify
import json, os, sys, subprocess, socket

from pynput.keyboard import Key, Controller
teclado = Controller()

app = Flask(__name__)

PASTA = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_JSON = os.path.join(PASTA, "botoes.json")
ARQUIVO_LOG = os.path.join(PASTA, "log.txt")

# ==========================================================
# Leitura do JSON — recarrega a cada pedido, então dá pra
# editar os botões com o servidor rodando (só recarregar a página)
# ==========================================================
def carregar_botoes():
    try:
        with open(ARQUIVO_JSON, "r", encoding="utf-8") as f:
            dados = json.load(f)
        return dados.get("botoes", [])
    except FileNotFoundError:
        print(f"AVISO: {ARQUIVO_JSON} não encontrado. Usando lista vazia.")
        return []
    except json.JSONDecodeError as e:
        print(f"AVISO: JSON inválido ({e}). Corrija o arquivo botoes.json.")
        return []

TECLAS_MIDIA = {
    "play_pause":  Key.media_play_pause,
    "volume_up":   Key.media_volume_up,
    "volume_down": Key.media_volume_down,
    "mute":        Key.media_volume_mute,
}

def executar(acao):
    tipo = acao["tipo"]
    if tipo == "tecla":
        t = TECLAS_MIDIA[acao["valor"]]
        teclado.press(t); teclado.release(t)
    elif tipo == "comando":
        subprocess.Popen(acao["valor"], shell=True)
    elif tipo == "texto":
        teclado.type(acao["valor"])
    elif tipo == "combinacao":
        teclas = acao["valor"]
        mods = []
        for m in teclas[:-1]:
            k = Key[m.lower()] if len(m) > 1 else m
            mods.append(k)
            teclado.press(k)
        ultima = teclas[-1]
        if len(ultima) == 1:
            teclado.press(ultima); teclado.release(ultima)
        else:
            k = Key[ultima.lower()]
            teclado.press(k); teclado.release(k)
        for k in mods:
            teclado.release(k)

PAGINA = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Controle do PC</title>
<style>
  body { font-family: system-ui; background:#111; color:#eee; margin:0; padding:16px; }
  h1 { text-align:center; font-size:1.3em; }
  #grade { display:grid; grid-template-columns:1fr 1fr; gap:12px; max-width:500px; margin:0 auto; }
  button { padding:26px 8px; font-size:1.05em; border:none; border-radius:14px;
           background:#2b7de9; color:#fff; cursor:pointer; transition:.1s; }
  button:active { transform:scale(.94); background:#1e5fb8; }
  .status { text-align:center; margin-top:14px; font-size:.85em; color:#8f8; height:1.2em; }
  .vazio { text-align:center; color:#999; margin-top:30px; }
</style>
</head>
<body>
<h1>📱 Controle do PC</h1>
<div id="grade"></div>
<div class="status" id="status"></div>
<script>
const botoes = __BOTOES__;
const grade = document.getElementById("grade");

if (botoes.length === 0) {
  grade.innerHTML = '<div class="vazio">Nenhum botão no botoes.json</div>';
}

botoes.forEach(b => {
  const btn = document.createElement("button");
  btn.textContent = b.nome;
  btn.onclick = () => fetch("/acao/" + b.id)
      .then(r => r.json())
      .then(d => mostrar(d.ok ? "✓ " + b.nome : "✗ falhou"))
      .catch(() => mostrar("✗ falhou"));
  grade.appendChild(btn);
});

function mostrar(txt) {
  const s = document.getElementById("status");
  s.textContent = txt;
  setTimeout(() => s.textContent = "", 1500);
}
</script>
</body>
</html>"""

@app.route("/")
def index():
    botoes = carregar_botoes()
    return PAGINA.replace("__BOTOES__", json.dumps(botoes, ensure_ascii=False))

@app.route("/acao/<id_botao>")
def acao(id_botao):
    botoes = carregar_botoes()
    acao = next((b for b in botoes if b["id"] == id_botao), None)
    if not acao:
        return jsonify(ok=False)
    try:
        executar(acao)
        return jsonify(ok=True)
    except Exception as e:
        print("Erro:", e)
        return jsonify(ok=False)

if __name__ == "__main__":
    # Detecta como o programa foi iniciado:
    #  - pythonw (via iniciar.bat) = segundo plano -> loga em log.txt
    #  - python (manual/duplo clique) = terminal -> mostra na tela
    em_segundo_plano = "pythonw" in sys.executable.lower()

    if em_segundo_plano:
        class Log:
            def write(self, txt):
                with open(ARQUIVO_LOG, "a", encoding="utf-8") as f:
                    f.write(txt)
            def flush(self):
                pass
        sys.stdout = Log()
        sys.stderr = Log()

    ip = socket.gethostbyname(socket.gethostname())
    print(f"Servidor iniciado em http://{ip}:5000\n")
    app.run(host="0.0.0.0", port=5000)