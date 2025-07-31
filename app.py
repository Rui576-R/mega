from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session
import random
import pandas as pd
import os
from fpdf import FPDF
import json
from werkzeug.utils import secure_filename
import re

app = Flask(__name__)
app.secret_key = 'um_segredo_aleatorio'

PASTA_ARQUIVOS = os.path.join(os.path.dirname(__file__), 'arquivos')
os.makedirs(PASTA_ARQUIVOS, exist_ok=True)

config_loterias = {
    'Mega-Sena': {'min': 6, 'max': 15, 'total': 60},
    'Lotofácil': {'min': 15, 'max': 20, 'total': 25},
    'Quina': {'min': 5, 'max': 15, 'total': 80},
    'Timemania': {'min': 10, 'max': 10, 'total': 80},
    'Dia de Sorte': {'min': 7, 'max': 15, 'total': 31},
    'Super Sete': {'min': 7, 'max': 7, 'total': 9}
}

def gerar_dezenas(loteria, qtd_jogos, qtd_dezenas):
    conf = config_loterias[loteria]
    min_d, max_d, total = conf['min'], conf['max'], conf['total']
    if not (min_d <= qtd_dezenas <= max_d):
        raise ValueError(f"{loteria} permite entre {min_d} e {max_d} dezenas.")
    jogos = []
    for _ in range(qtd_jogos):
        if loteria == 'Super Sete':
            jogo = [random.randint(0, 9) for _ in range(7)]
        else:
            jogo = sorted(random.sample(range(1, total + 1), qtd_dezenas))
        jogos.append(jogo)
    return jogos

def conferir(jogos, resultado):
    resultado_set = set(resultado)
    conferidos = []
    for jogo in jogos:
        acertos = len(set(jogo) & resultado_set)
        conferidos.append((jogo, acertos))
    return conferidos

def estatisticas(jogos):
    todos = [n for jogo in jogos for n in jogo]
    freq = pd.Series(todos).value_counts().sort_index()
    return freq

ALLOWED_EXTENSIONS = {'txt', 'csv', 'json'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/importar', methods=['GET', 'POST'])
def importar():
    jogos = []
    mensagem = ""
    loteria_selecionada = request.form.get('loteria', 'Mega-Sena')
    qtd_dezenas = config_loterias[loteria_selecionada]['min']
    if request.method == 'POST':
        if 'arquivo' not in request.files:
            mensagem = "Nenhum arquivo enviado."
        else:
            arquivo = request.files['arquivo']
            loteria_selecionada = request.form.get('loteria', 'Mega-Sena')
            qtd_dezenas = config_loterias[loteria_selecionada]['min']
            if arquivo and allowed_file(arquivo.filename):
                filename = secure_filename(arquivo.filename)
                ext = filename.rsplit('.', 1)[1].lower()
                conteudo = arquivo.read().decode('utf-8')
                try:
                    if ext in ['txt', 'csv']:
                        for linha in conteudo.strip().splitlines():
                            numeros = [int(n) for n in re.findall(r'\d+', linha)]
                            # Corrigido: se a linha possui índice tipo "Jogo N: [x, y, z...]", descarta o primeiro número (índice do jogo)
                            if len(numeros) > qtd_dezenas:
                                jogos.append(numeros[1:qtd_dezenas+1])
                            elif len(numeros) == qtd_dezenas:
                                jogos.append(numeros)
                    elif ext == 'json':
                        jogos_json = json.loads(conteudo)
                        # Garante que cada item é só as dezenas
                        for item in jogos_json:
                            if isinstance(item, list):
                                jogos.append(item[:qtd_dezenas])
                            elif isinstance(item, dict) and 'dezenas' in item:
                                jogos.append(item['dezenas'][:qtd_dezenas])
                    mensagem = f"{len(jogos)} jogos importados com sucesso!"
                    if jogos:
                        session['jogos_importados'] = jogos
                        session['loteria_importada'] = loteria_selecionada
                        session['qtd_dezenas_importada'] = qtd_dezenas
                except Exception as e:
                    mensagem = f"Erro ao importar: {e}"
            else:
                mensagem = "Tipo de arquivo não suportado."
    return render_template("importar.html",
        jogos=jogos,
        mensagem=mensagem,
        config_loterias=config_loterias,
        loteria_selecionada=loteria_selecionada,
        qtd_dezenas=qtd_dezenas
    )

@app.route('/conferir_importados', methods=['GET', 'POST'])
def conferir_importados():
    jogos = session.get('jogos_importados', [])
    loteria = session.get('loteria_importada', 'Mega-Sena')
    qtd_dezenas = session.get('qtd_dezenas_importada', config_loterias[loteria]['min'])
    resultado = []
    conferidos = []
    mensagem = ""
    if not jogos:
        mensagem = "Nenhum jogo importado disponível. Importe jogos primeiro."
        return render_template("conferir_importados.html", jogos=[], resultado=[], conferidos=[], mensagem=mensagem, qtd_dezenas=qtd_dezenas, loteria=loteria)
    if request.method == 'POST':
        resultado_raw = request.form['resultado']
        resultado = [int(n) for n in re.findall(r'\d+', resultado_raw)]
        conferidos = conferir([jogo[:qtd_dezenas] for jogo in jogos], resultado)
    return render_template("conferir_importados.html",
                           jogos=jogos,
                           resultado=resultado,
                           conferidos=conferidos,
                           mensagem=mensagem,
                           qtd_dezenas=qtd_dezenas,
                           loteria=loteria)

@app.route('/')
def index():
    return render_template('index.html', loterias=config_loterias.keys())

@app.route('/gerar', methods=['POST'])
def gerar():
    loteria = request.form['loteria']
    qtd_jogos = int(request.form['qtd_jogos'])
    qtd_dezenas = int(request.form['qtd_dezenas'])

    jogos = gerar_dezenas(loteria, qtd_jogos, qtd_dezenas)

    return render_template('index.html', loterias=config_loterias.keys(),
                           jogos=jogos, loteria_selecionada=loteria,
                           qtd_jogos=qtd_jogos, qtd_dezenas=qtd_dezenas)

@app.route('/resultado', methods=['POST'])
def resultado():
    loteria = request.form['loteria']
    jogos_raw = request.form.getlist('jogos')
    resultado_raw = request.form['resultado']

    jogos = [list(map(int, re.findall(r'\d+', j))) for j in jogos_raw]
    resultado_list = list(map(int, re.findall(r'\d+', resultado_raw)))

    conferidos = conferir(jogos, resultado_list)

    return render_template('resultado.html', conferidos=conferidos,
                           resultado=resultado_list, loteria=loteria)

@app.route('/estatisticas', methods=['POST'])
def estatisticas_route():
    loteria = request.form['loteria']
    jogos_raw = request.form.getlist('jogos')

    jogos = [list(map(int, re.findall(r'\d+', j))) for j in jogos_raw]

    freq = estatisticas(jogos)

    return render_template('estatisticas.html', frequencias=freq.items(),
                           loteria=loteria)

@app.route('/exportar', methods=['POST'])
def exportar():
    loteria = request.form['loteria']
    formato = request.form['formato']
    jogos_raw = request.form.getlist('jogos')

    jogos = [list(map(int, re.findall(r'\d+', j))) for j in jogos_raw]

    nome_base = f"Jogos_{loteria}"

    if formato == 'txt':
        caminho = salvar_txt(jogos, nome_base)
    elif formato == 'json':
        caminho = salvar_json(jogos, nome_base)
    elif formato == 'excel':
        caminho = salvar_excel(jogos, nome_base)
    elif formato == 'pdf':
        caminho = salvar_pdf(jogos, nome_base)
    else:
        return "Formato inválido", 400

    filename = os.path.basename(caminho)
    return redirect(url_for('download_arquivo', filename=filename))

@app.route('/exportar_conferencia', methods=['POST'])
def exportar_conferencia():
    loteria = request.form['loteria']
    formato = request.form['formato']
    resultado_raw = request.form['resultado']
    conferidos_raw = request.form.getlist('conferidos')

    resultado_list = list(map(int, re.findall(r'\d+', resultado_raw)))

    conferidos = []
    for item in conferidos_raw:
        jogo_str, acertos = item.split('|')
        jogo = list(map(int, re.findall(r'\d+', jogo_str)))
        conferidos.append({'jogo': jogo, 'acertos': int(acertos)})

    nome_base = f"Conferencia_{loteria}"

    if formato == 'txt':
        caminho = salvar_conferencia_txt(conferidos, resultado_list, nome_base)
    elif formato == 'json':
        caminho = salvar_conferencia_json(conferidos, resultado_list, nome_base)
    elif formato == 'excel':
        caminho = salvar_conferencia_excel(conferidos, resultado_list, nome_base)
    elif formato == 'pdf':
        caminho = salvar_conferencia_pdf(conferidos, resultado_list, nome_base)
    else:
        return "Formato inválido", 400

    filename = os.path.basename(caminho)
    return redirect(url_for('download_arquivo', filename=filename))

def salvar_txt(jogos, nome):
    caminho = os.path.join(PASTA_ARQUIVOS, f"{nome}.txt")
    with open(caminho, 'w') as f:
        for i, jogo in enumerate(jogos, 1):
            f.write(f"Jogo {i}: {jogo}\n")
    return caminho

def salvar_json(jogos, nome):
    caminho = os.path.join(PASTA_ARQUIVOS, f"{nome}.json")
    with open(caminho, 'w') as f:
        json.dump(jogos, f, indent=4)
    return caminho

def salvar_excel(jogos, nome):
    caminho = os.path.join(PASTA_ARQUIVOS, f"{nome}.xlsx")
    df = pd.DataFrame(jogos)
    df.index += 1
    df.to_excel(caminho, index_label="Jogo")
    return caminho

def salvar_pdf(jogos, nome):
    caminho = os.path.join(PASTA_ARQUIVOS, f"{nome}.pdf")
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(200, 10, txt=nome, ln=True, align='C')
    pdf.ln(10)
    for i, jogo in enumerate(jogos, 1):
        linha = f"Jogo {i}: {jogo}"
        pdf.cell(200, 10, txt=linha, ln=True, align='L')
    pdf.output(caminho)
    return caminho

def salvar_conferencia_txt(conferidos, resultado, nome):
    caminho = os.path.join(PASTA_ARQUIVOS, f"{nome}.txt")
    with open(caminho, 'w') as f:
        f.write(f"Resultado Oficial: {resultado}\n\n")
        for i, item in enumerate(conferidos, 1):
            f.write(f"Jogo {i}: {item['jogo']} - {item['acertos']} acerto(s)\n")
    return caminho

def salvar_conferencia_json(conferidos, resultado, nome):
    caminho = os.path.join(PASTA_ARQUIVOS, f"{nome}.json")
    dados = {
        'resultado_oficial': resultado,
        'conferidos': conferidos
    }
    with open(caminho, 'w') as f:
        json.dump(dados, f, indent=4)
    return caminho

def salvar_conferencia_excel(conferidos, resultado, nome):
    caminho = os.path.join(PASTA_ARQUIVOS, f"{nome}.xlsx")
    df = pd.DataFrame([{'Jogo': i + 1, 'Dezenas': str(item['jogo']), 'Acertos': item['acertos']}
                       for i, item in enumerate(conferidos)])
    df.to_excel(caminho, index=False)
    return caminho

def salvar_conferencia_pdf(conferidos, resultado, nome):
    caminho = os.path.join(PASTA_ARQUIVOS, f"{nome}.pdf")
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(200, 10, txt=f"Resultado Oficial: {resultado}", ln=True, align='C')
    pdf.ln(10)
    for i, item in enumerate(conferidos, 1):
        linha = f"Jogo {i}: {item['jogo']} - {item['acertos']} acerto(s)"
        pdf.cell(200, 10, txt=linha, ln=True, align='L')
    pdf.output(caminho)
    return caminho

@app.route('/download/<path:filename>')
def download_arquivo(filename):
    return send_from_directory(PASTA_ARQUIVOS, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)