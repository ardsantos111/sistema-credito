import os
import psycopg2
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import pdfkit
from datetime import datetime

app = Flask(__name__)

# Configuração de ambiente da Vercel
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config['DATABASE_URL'] = os.environ.get('DATABASE_URL')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, email, password, empresa_id):
        self.id = id
        self.email = email
        self.password = password
        self.empresa_id = empresa_id

def get_db_connection():
    conn = psycopg2.connect(app.config['DATABASE_URL'])
    return conn

# A Vercel procura por esta variável 'app' para rodar
# Garanta que esta linha existe!
# app = Flask(__name__)

# --- Funções de Usuário para Flask-Login ---
@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, email, password, empresa_id FROM users WHERE id = %s;", (user_id,))
    user_data = cur.fetchone()
    cur.close()
    conn.close()
    if user_data:
        return User(user_data[0], user_data[1], user_data[2], user_data[3])
    return None

def get_user_by_email(email):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, email, password, empresa_id FROM users WHERE email = %s;", (email,))
    user_data = cur.fetchone()
    cur.close()
    conn.close()
    if user_data:
        return User(user_data[0], user_data[1], user_data[2], user_data[3])
    return None

# --- Rotas da Aplicação ---
@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('user_dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = get_user_by_email(email)
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('user_dashboard'))
        flash('Email ou senha incorretos.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def user_dashboard():
    # Obtém o ID da empresa do usuário logado
    empresa_id = current_user.empresa_id
    
    # Lógica para obter vendas e clientes da empresa específica
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM vendas WHERE empresa_id = %s ORDER BY data_venda DESC;", (empresa_id,))
    vendas = cur.fetchall()
    cur.execute("SELECT id, nome_cliente FROM clientes WHERE empresa_id = %s;", (empresa_id,))
    clientes = cur.fetchall()
    cur.close()
    conn.close()
    
    return render_template('user_dashboard.html', vendas=vendas, clientes=clientes)

@app.route('/nova_venda', methods=['POST'])
@login_required
def nova_venda():
    empresa_id = current_user.empresa_id
    if request.method == 'POST':
        cliente_id = request.form.get('cliente')
        valor = request.form['valor']
        parcelas = request.form['parcelas']
        data_venda = datetime.now()
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO vendas (cliente_id, valor, parcelas, data_venda, empresa_id) VALUES (%s, %s, %s, %s, %s);",
                    (cliente_id, valor, parcelas, data_venda, empresa_id))
        conn.commit()
        cur.close()
        conn.close()
        flash('Venda adicionada com sucesso!', 'success')
    return redirect(url_for('user_dashboard'))

@app.route('/vendas')
@login_required
def vendas():
    empresa_id = current_user.empresa_id
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT v.id, c.nome_cliente, v.valor, v.parcelas, v.data_venda FROM vendas v JOIN clientes c ON v.cliente_id = c.id WHERE v.empresa_id = %s ORDER BY v.data_venda DESC;", (empresa_id,))
    vendas_com_cliente = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('vendas.html', vendas=vendas_com_cliente)

# --- Gerar Contrato PDF (Requer WeasyPrint) ---
@app.route('/contrato/<int:venda_id>')
@login_required
def gerar_contrato(venda_id):
    empresa_id = current_user.empresa_id
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT v.id, c.nome_cliente, e.nome_empresa, v.valor, v.parcelas, v.data_venda FROM vendas v JOIN clientes c ON v.cliente_id = c.id JOIN empresas e ON v.empresa_id = e.id WHERE v.id = %s AND v.empresa_id = %s;", (venda_id, empresa_id))
    venda_data = cur.fetchone()
    cur.close()
    conn.close()
    
    if not venda_data:
        flash('Venda não encontrada ou você não tem permissão para acessá-la.', 'danger')
        return redirect(url_for('vendas'))
        
    venda = {
        'id': venda_data[0],
        'nome_cliente': venda_data[1],
        'nome_empresa': venda_data[2],
        'valor': venda_data[3],
        'parcelas': venda_data[4],
        'data_venda': venda_data[5]
    }
    
    html_template = render_template('contrato_pdf.html', venda=venda)
    
    # Configuração do WeasyPrint
    config = pdfkit.configuration(wkhtmltopdf='C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe') # Altere o caminho se necessário
    
    pdf = pdfkit.from_string(html_template, False, configuration=config)
    
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=contrato_venda_{venda["id"]}.pdf'
    return response

# Ponto de entrada padrão para desenvolvimento local
# Isso é o que a Vercel usa para encontrar sua aplicação
if __name__ == "__main__":
    app.run(debug=True)