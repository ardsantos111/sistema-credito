import os
import io
import pg8000.dbapi
import traceback
from urllib.parse import urlparse
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)

# Configurações
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'chave_secreta_temporaria')
app.config['DATABASE_URL'] = os.environ.get('DATABASE_URL')

# Configuração do Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, email, password, empresa_id):
        self.id = id
        self.email = email
        self.password = password
        self.empresa_id = empresa_id

from urllib.parse import urlparse

def get_db_connection():
    try:
        database_url = app.config['DATABASE_URL']
        url = urlparse(database_url)
        return pg8000.dbapi.connect(
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port,
            database=url.path[1:],
            ssl_context=True
        )
    except Exception as e:
        print(f"Erro na conexão com o banco: {str(e)}")
        print(traceback.format_exc())
        return None

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, email, password, empresa_id FROM users WHERE id = %s", (user_id,))
        user_data = cur.fetchone()
        cur.close()
        conn.close()
        
        if user_data:
            return User(user_data[0], user_data[1], user_data[2], user_data[3])
        return None
    except Exception as e:
        print(f"Erro ao carregar usuário: {str(e)}")
        if conn:
            conn.close()
        return None

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'logo.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados', 'error')
            return redirect(url_for('login'))
        
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, email, password, empresa_id FROM users WHERE email = %s", (email,))
            user_data = cur.fetchone()
            cur.close()
            conn.close()
            
            if user_data and check_password_hash(user_data[2], password):
                user = User(user_data[0], user_data[1], user_data[2], user_data[3])
                login_user(user)
                return redirect(url_for('dashboard'))
            
            flash('Email ou senha incorretos', 'error')
        except Exception as e:
            flash('Erro ao realizar login', 'error')
            print(f"Erro no login: {str(e)}")
        
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    if not conn:
        flash('Erro ao conectar ao banco de dados', 'error')
        return redirect(url_for('home'))
    
    try:
        cur = conn.cursor()
        # Buscar vendas recentes
        cur.execute("""
            SELECT v.id, c.nome, v.valor_total, v.data_venda, v.status 
            FROM vendas v 
            JOIN clientes c ON v.cliente_id = c.id 
            WHERE v.empresa_id = %s 
            ORDER BY v.data_venda DESC 
            LIMIT 10
        """, (current_user.empresa_id,))
        vendas_recentes = cur.fetchall()
        
        # Buscar pagamentos pendentes
        cur.execute("""
            SELECT c.nome, p.valor, p.data_vencimento 
            FROM pagamentos p 
            JOIN vendas v ON p.venda_id = v.id 
            JOIN clientes c ON v.cliente_id = c.id 
            WHERE v.empresa_id = %s AND p.status = 'pendente' 
            ORDER BY p.data_vencimento
        """, (current_user.empresa_id,))
        pagamentos_pendentes = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return render_template('dashboard.html', 
                             vendas_recentes=vendas_recentes,
                             pagamentos_pendentes=pagamentos_pendentes)
    except Exception as e:
        flash('Erro ao carregar dashboard', 'error')
        print(f"Erro no dashboard: {str(e)}")
        return redirect(url_for('home'))

@app.route('/vendas', methods=['GET', 'POST'])
@login_required
def vendas():
    if request.method == 'POST':
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados', 'error')
            return redirect(url_for('vendas'))
        
        try:
            # Dados do formulário
            cliente_id = request.form['cliente_id']
            valor_total = float(request.form['valor_total'])
            valor_entrada = float(request.form.get('valor_entrada', 0))
            num_parcelas = int(request.form['num_parcelas'])
            
            cur = conn.cursor()
            # Inserir venda
            cur.execute("""
                INSERT INTO vendas (cliente_id, empresa_id, valor_total, valor_entrada, 
                                  num_parcelas, data_venda, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'ativa')
                RETURNING id
            """, (cliente_id, current_user.empresa_id, valor_total, valor_entrada,
                 num_parcelas, datetime.now()))
            
            venda_id = cur.fetchone()[0]
            
            # Criar parcelas
            valor_restante = valor_total - valor_entrada
            valor_parcela = valor_restante / num_parcelas
            data_vencimento = datetime.now()
            
            for i in range(num_parcelas):
                data_vencimento += timedelta(days=30)
                cur.execute("""
                    INSERT INTO pagamentos (venda_id, valor, data_vencimento, status)
                    VALUES (%s, %s, %s, 'pendente')
                """, (venda_id, valor_parcela, data_vencimento))
            
            conn.commit()
            cur.close()
            conn.close()
            
            flash('Venda registrada com sucesso!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            flash('Erro ao registrar venda', 'error')
            print(f"Erro ao registrar venda: {str(e)}")
            return redirect(url_for('vendas'))
    
    # GET request
    conn = get_db_connection()
    if not conn:
        flash('Erro ao conectar ao banco de dados', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, nome FROM clientes WHERE empresa_id = %s", (current_user.empresa_id,))
        clientes = cur.fetchall()
        cur.close()
        conn.close()
        
        return render_template('vendas.html', clientes=clientes)
    except Exception as e:
        flash('Erro ao carregar página de vendas', 'error')
        print(f"Erro na página de vendas: {str(e)}")
        return redirect(url_for('dashboard'))

#@app.route('/gerar_contrato/<int:venda_id>')
#@login_required
#def gerar_contrato(venda_id):
#    conn = get_db_connection()
#    if not conn:
#        flash('Erro ao conectar ao banco de dados', 'error')
#        return redirect(url_for('vendas'))
#    
#    try:
#        cur = conn.cursor()
#        # Buscar dados da venda
#        cur.execute("""
#            SELECT v.*, c.nome, c.cpf, c.endereco, e.nome_empresa, e.cnpj
#            FROM vendas v
#            JOIN clientes c ON v.cliente_id = c.id
#            JOIN empresas e ON v.empresa_id = e.id
#            WHERE v.id = %s AND v.empresa_id = %s
#        """, (venda_id, current_user.empresa_id))
#        
#        venda_data = cur.fetchone()
#        
#        if not venda_data:
#            flash('Venda não encontrada', 'error')
#            return redirect(url_for('vendas'))
#        
#        # Buscar parcelas
#        cur.execute("""
#            SELECT valor, data_vencimento
#            FROM pagamentos
#            WHERE venda_id = %s
#            ORDER BY data_vencimento
#        """, (venda_id,))
#        parcelas = cur.fetchall()
#        
#        cur.close()
#        conn.close()
#        
#        # Gerar PDF
#        html = render_template('contrato_pdf.html',
#                             venda=venda_data,
#                             parcelas=parcelas)
#        
#        pdf = HTML(string=html).write_pdf()
#        
#        return send_file(
#            io.BytesIO(pdf),
#            mimetype='application/pdf',
#            download_name=f'contrato_venda_{venda_id}.pdf',
#            as_attachment=True
#        )
#        
#    except Exception as e:
#        flash('Erro ao gerar contrato', 'error')
#        print(f"Erro ao gerar contrato: {str(e)}")
#        return redirect(url_for('vendas'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)