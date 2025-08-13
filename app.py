import os
import io
import json
import pg8000.dbapi

from urllib.parse import urlparse, unquote
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, send_from_directory, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

# Tornar a importação do weasyprint opcional para ambientes que não o suportam
try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    print("WeasyPrint não está disponível. A geração de PDFs será desativada.")

app = Flask(__name__)

# Configurações
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'chave_secreta_temporaria')
# Configurar parâmetros do banco de dados separadamente
app.config['DB_HOST'] = "db.guqrxjjrpmfbeftwmokz.supabase.co"
app.config['DB_PORT'] = 5432
app.config['DB_NAME'] = "postgres"
app.config['DB_USER'] = "postgres"
app.config['DB_PASSWORD'] = "Am461271@am461271"  # Senha decodificada diretamente

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

def get_db_connection():
    try:
        # Usar parâmetros separados para conexão
        host = app.config['DB_HOST']
        port = app.config['DB_PORT']
        database = app.config['DB_NAME']
        user = app.config['DB_USER']
        password = app.config['DB_PASSWORD']
        
        print(f"[LOG] Tentando conectar ao banco de dados:")
        print(f"[LOG] Host: {host}")
        print(f"[LOG] Port: {port}")
        print(f"[LOG] Database: {database}")
        print(f"[LOG] User: {user}")
        print(f"[LOG] Password: {'*' * len(password)}")
        
        # Conectar ao banco de dados com timeout e SSL
        conn = pg8000.dbapi.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database=database,
            timeout=30,
            ssl_context=True  # Forçar SSL
        )
        
        print("[LOG] Conexão com o banco de dados estabelecida com sucesso!")
        return conn
        
    except Exception as e:
        print(f"[ERRO] Erro na conexão com o banco: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

@app.route('/test-db')
def test_db():
    """Rota para testar a conexão com o banco de dados"""
    print("[LOG] Acessando rota de teste do banco de dados")
    try:
        # Usar parâmetros separados para conexão
        host = app.config['DB_HOST']
        port = app.config['DB_PORT']
        database = app.config['DB_NAME']
        user = app.config['DB_USER']
        password = app.config['DB_PASSWORD']
        
        print(f"[LOG] Tentando conectar ao banco de dados:")
        print(f"[LOG] Host: {host}")
        print(f"[LOG] Port: {port}")
        print(f"[LOG] Database: {database}")
        print(f"[LOG] User: {user}")
        print(f"[LOG] Password: {'*' * len(password)}")
        
        # Conectar ao banco de dados com timeout e SSL
        print("[LOG] Tentando conectar ao banco de dados...")
        conn = pg8000.dbapi.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database=database,
            timeout=30,
            ssl_context=True  # Forçar SSL
        )
        
        # Testar uma consulta simples
        print("[LOG] Executando consulta de teste...")
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        cur.close()
        conn.close()
        
        result = {
            "success": True,
            "message": "Conexão com o banco de dados estabelecida com sucesso!",
            "database_version": version[0] if version else "Desconhecida"
        }
        
        print(f"[LOG] Teste concluído com sucesso: {result}")
        return jsonify(result)
        
    except Exception as e:
        print(f"[ERRO] Erro no teste do banco de dados: {str(e)}")
        import traceback
        traceback.print_exc()
        
        result = {
            "success": False,
            "message": f"Erro na conexão com o banco de dados: {str(e)}",
            "error_type": type(e).__name__
        }
        return jsonify(result), 500

@login_manager.user_loader
def load_user(user_id):
    print(f"Carregando usuário com ID: {user_id}")
    conn = get_db_connection()
    if not conn:
        print("Falha ao conectar ao banco de dados em load_user")
        return None
    
    try:
        cur = conn.cursor()
        print("Executando consulta de usuário em load_user")
        cur.execute("SELECT id, email, password, empresa_id FROM users WHERE id = %s", (user_id,))
        user_data = cur.fetchone()
        print(f"Dados do usuário carregados: {user_data}")
        cur.close()
        conn.close()
        
        if user_data:
            print("Usuário encontrado, criando objeto User")
            return User(user_data[0], user_data[1], user_data[2], user_data[3])
        print("Usuário não encontrado")
        return None
    except Exception as e:
        print(f"Erro ao carregar usuário: {str(e)}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.close()
        return None

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'logo.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/')
def home():
    print("Acessando rota home")
    if current_user.is_authenticated:
        print("Usuário autenticado, redirecionando para dashboard")
        return redirect(url_for('dashboard'))
    print("Usuário não autenticado, mostrando página inicial")
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    print("[LOG] Acessando rota de login")
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        print(f"[LOG] Tentando login com email: {email}")
        
        conn = get_db_connection()
        if not conn:
            print("[ERRO] Falha ao conectar ao banco de dados")
            flash('Erro ao conectar ao banco de dados', 'error')
            return redirect(url_for('login'))
        
        try:
            cur = conn.cursor()
            print("[LOG] Executando consulta de usuário")
            cur.execute("SELECT id, email, password, empresa_id FROM users WHERE email = %s", (email,))
            user_data = cur.fetchone()
            print(f"[LOG] Dados do usuário encontrados: {user_data is not None}")
            cur.close()
            conn.close()
            
            if user_data and check_password_hash(user_data[2], password):
                user = User(user_data[0], user_data[1], user_data[2], user_data[3])
                login_user(user)
                print("[LOG] Login bem-sucedido")
                return redirect(url_for('dashboard'))
            
            print("[LOG] Email ou senha incorretos")
            flash('Email ou senha incorretos', 'error')
        except Exception as e:
            print(f"[ERRO] Erro no login: {str(e)}")
            import traceback
            traceback.print_exc()
            flash('Erro ao realizar login', 'error')
        
    print("[LOG] Renderizando página de login")
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    print("Acessando rota dashboard")
    conn = get_db_connection()
    if not conn:
        print("Falha ao conectar ao banco de dados no dashboard")
        flash('Erro ao conectar ao banco de dados', 'error')
        return redirect(url_for('home'))
    
    try:
        cur = conn.cursor()
        print("Executando consulta de vendas recentes")
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
        print(f"Vendas recentes encontradas: {len(vendas_recentes)}")
        
        print("Executando consulta de pagamentos pendentes")
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
        print(f"Pagamentos pendentes encontrados: {len(pagamentos_pendentes)}")
        
        cur.close()
        conn.close()
        
        print("Renderizando template do dashboard")
        return render_template('dashboard.html', 
                             vendas_recentes=vendas_recentes,
                             pagamentos_pendentes=pagamentos_pendentes)
    except Exception as e:
        print(f"Erro no dashboard: {str(e)}")
        import traceback
        traceback.print_exc()
        flash('Erro ao carregar dashboard', 'error')
        print("Redirecionando para home devido ao erro")
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
                INSERT INTO vendas (cliente_id, empresa_id, user_id, valor_total, valor_entrada, 
                                  num_parcelas, data_venda, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'ativa')
                RETURNING id
            """, (cliente_id, current_user.empresa_id, current_user.id, valor_total, valor_entrada,
                 num_parcelas, datetime.now()))
            
            venda_id = cur.fetchone()[0]
            
            # Criar parcelas
            valor_restante = valor_total - valor_entrada
            valor_parcela = valor_restante / num_parcelas if num_parcelas > 0 else 0
            
            for i in range(num_parcelas):
                data_vencimento = datetime.now() + timedelta(days=30 * (i + 1))
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

@app.route('/gerar_contrato/<int:venda_id>')
@login_required
def gerar_contrato(venda_id):
    # Verificar se WeasyPrint está disponível
    if not WEASYPRINT_AVAILABLE:
        flash('A geração de PDFs não está disponível neste ambiente.', 'error')
        return redirect(url_for('vendas'))
    
    conn = get_db_connection()
    if not conn:
        flash('Erro ao conectar ao banco de dados', 'error')
        return redirect(url_for('vendas'))
    
    try:
        cur = conn.cursor()
        # Buscar dados da venda
        cur.execute("""
            SELECT v.*, c.nome as nome_cliente, c.cpf, c.endereco as endereco_cliente, 
                   e.nome_empresa, e.cnpj, u.email as vendedor_nome
            FROM vendas v
            JOIN clientes c ON v.cliente_id = c.id
            JOIN empresas e ON v.empresa_id = e.id
            JOIN users u ON v.user_id = u.id
            WHERE v.id = %s AND v.empresa_id = %s
        """, (venda_id, current_user.empresa_id))
        
        venda_data = cur.fetchone()
        
        if not venda_data:
            flash('Venda não encontrada', 'error')
            return redirect(url_for('vendas'))
        
        # Buscar dados da loja
        cur.execute("SELECT nome, endereco FROM loja LIMIT 1")
        loja_data = cur.fetchone()
        
        if not loja_data:
            flash('Dados da loja não encontrados', 'error')
            return redirect(url_for('vendas'))
        
        # Buscar parcelas
        cur.execute("""
            SELECT valor, data_vencimento
            FROM pagamentos
            WHERE venda_id = %s
            ORDER BY data_vencimento
        """, (venda_id,))
        parcelas = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # Preparar dados para o template
        valor_total = venda_data[4]  # valor_total
        valor_entrada = venda_data[5]  # valor_entrada
        num_parcelas = venda_data[6]  # num_parcelas
        valor_restante = valor_total - valor_entrada
        valor_parcela = valor_restante / num_parcelas if num_parcelas > 0 else 0
        
        # Gerar datas de vencimento
        datas_vencimento = [p[1].strftime('%d/%m/%Y') for p in parcelas]
        
        # Cláusulas padrão
        clausulas = [
            "O COMPRADOR(A) declara ter plena capacidade legal para celebrar o presente contrato.",
            "O(A) COMPRADOR(A) recebeu os produtos conforme descrito neste contrato e os reconhece em perfeito estado.",
            "Fica acordado que o não pagamento de qualquer parcela implicará na rescisão automática do contrato e na exigibilidade imediata do saldo devedor.",
            "Em caso de inadimplência, o(a) COMPRADOR(A) pagará multa de 2% sobre o valor em atraso e juros de 1% ao mês.",
            "O(A) COMPRADOR(A) autoriza expressamente a compensação de quaisquer créditos em seu favor com débitos de sua responsabilidade perante o VENDEDOR(A)."
        ]
        
        # Gerar PDF
        html = render_template('contrato_pdf.html',
                             ov_numero=venda_id,
                             nome_loja=loja_data[0],
                             cnpj_loja=venda_data[12],  # cnpj
                             endereco_loja=loja_data[1],
                             nome_cliente=venda_data[8],  # nome_cliente
                             cpf_cliente=venda_data[9],   # cpf
                             endereco_completo=venda_data[10],  # endereco_cliente
                             descricao_venda="Produtos diversos",
                             valor_total=valor_total,
                             forma_pagamento="A prazo",
                             vendedor_nome=venda_data[13],  # vendedor_nome
                             observacoes="Nenhuma observação",
                             valor_entrada=valor_entrada,
                             num_parcelas=num_parcelas,
                             valor_parcela=valor_parcela,
                             datas_vencimento=datas_vencimento,
                             clausulas=clausulas)
        
        pdf = HTML(string=html).write_pdf()
        
        return send_file(
            io.BytesIO(pdf),
            mimetype='application/pdf',
            download_name=f'contrato_venda_{venda_id}.pdf',
            as_attachment=True
        )
        
    except Exception as e:
        flash('Erro ao gerar contrato', 'error')
        print(f"Erro ao gerar contrato: {str(e)}")
        return redirect(url_for('vendas'))

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