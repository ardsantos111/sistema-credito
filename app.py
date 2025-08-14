import os
import io
import json
import pg8000.dbapi

from urllib.parse import urlparse, unquote
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, send_from_directory, jsonify
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

# Importar nossos módulos de autenticação
from auth import authenticate_user, load_user as auth_load_user, get_user_companies, update_last_access, AppUser
from middleware import require_permission, require_role, require_company_selection, require_master

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
# Usar a URL do banco de dados correta diretamente
app.config['DATABASE_URL'] = os.environ.get('DATABASE_URL', 'postgresql://postgres:Am461271%40am461271@db.guqrxjjrpmfbeftwmokz.supabase.co:5432/postgres')

# Inicializar Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor, faça login para acessar esta página.'

@login_manager.user_loader
def load_user(user_id):
    """Carrega um usuário pelo ID para o Flask-Login"""
    return auth_load_user(user_id)

def get_db_connection():
    try:
        # Usar a URL do banco de dados correta diretamente
        database_url = app.config['DATABASE_URL']
        
        # Analisar a URL do banco de dados
        url = urlparse(database_url)
        
        # Decodificar a senha para lidar com caracteres especiais
        decoded_password = unquote(url.password) if url.password else None
        
        # Criar contexto SSL
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Conectar ao banco de dados
        return pg8000.dbapi.connect(
            user=url.username,
            password=decoded_password,
            host=url.hostname,
            port=url.port,
            database=url.path[1:],
            timeout=30,
            ssl_context=ssl_context
        )
    except Exception as e:
        print(f"Erro na conexão com o banco: {str(e)}")
        return None

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
        
        # Autenticar usuário
        user = authenticate_user(email, password)
        if user:
            # Verificar se usuário está ativo
            if not user.is_active:
                flash('Usuário inativo. Contate o administrador.', 'error')
                return redirect(url_for('login'))
            
            # Fazer login com Flask-Login
            login_user(user)
            
            # Atualizar último acesso
            update_last_access(user.id)
            
            flash('Login realizado com sucesso!', 'success')
            
            # Verificar empresas do usuário
            companies = get_user_companies(user.id)
            if len(companies) == 1:
                # Se usuário só tem acesso a uma empresa, selecionar automaticamente
                session['empresa_id'] = companies[0][0]
                session['empresa_nome'] = companies[0][1]
                return redirect(url_for('dashboard'))
            elif len(companies) > 1:
                # Se usuário tem acesso a múltiplas empresas, ir para tela de seleção
                return redirect(url_for('select_company'))
            else:
                # Se usuário não tem acesso a nenhuma empresa (somente master)
                if user.role == 'master':
                    return redirect(url_for('master_dashboard'))
                else:
                    flash('Você não tem acesso a nenhuma empresa.', 'error')
                    return redirect(url_for('login'))
        else:
            flash('Email ou senha incorretos', 'error')
    
    return render_template('login.html')

@app.route('/select-company')
@login_required
def select_company():
    """Rota para seleção de empresa"""
    # Buscar empresas do usuário
    companies = get_user_companies(current_user.id)
    
    if len(companies) == 1:
        # Se só tem uma empresa, selecionar automaticamente
        session['empresa_id'] = companies[0][0]
        session['empresa_nome'] = companies[0][1]
        return redirect(url_for('dashboard'))
    elif len(companies) == 0:
        # Se não tem empresas, verificar se é master
        if current_user.role == 'master':
            return redirect(url_for('master_dashboard'))
        else:
            flash('Você não tem acesso a nenhuma empresa.', 'error')
            return redirect(url_for('logout'))
    
    return render_template('select_company.html', companies=companies)

@app.route('/select-company/<int:empresa_id>')
@login_required
def select_company_action(empresa_id):
    """Ação para selecionar uma empresa"""
    # Verificar se usuário tem acesso a esta empresa
    companies = get_user_companies(current_user.id)
    empresa_encontrada = None
    
    for company in companies:
        if company[0] == empresa_id:
            empresa_encontrada = company
            break
    
    if not empresa_encontrada:
        flash('Você não tem acesso a esta empresa.', 'error')
        return redirect(url_for('select_company'))
    
    # Salvar empresa na sessão
    session['empresa_id'] = empresa_id
    session['empresa_nome'] = empresa_encontrada[1]
    
    flash(f'Empresa {empresa_encontrada[1]} selecionada com sucesso!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/logout')
@login_required
def logout():
    """Rota de logout"""
    logout_user()
    session.clear()
    flash('Você foi desconectado com sucesso.', 'success')
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard da empresa selecionada"""
    # Verificar se empresa foi selecionada
    if 'empresa_id' not in session:
        return redirect(url_for('select_company'))
    
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados', 'error')
            return redirect(url_for('home'))
        
        cur = conn.cursor()
        
        # Buscar vendas recentes da empresa
        cur.execute("""
            SELECT v.id, c.nome, v.valor_total, v.data_venda, v.status 
            FROM vendas v 
            JOIN clientes c ON v.cliente_id = c.id 
            WHERE v.empresa_id = %s 
            ORDER BY v.data_venda DESC 
            LIMIT 10
        """, (session['empresa_id'],))
        vendas_recentes = cur.fetchall()
        
        # Buscar pagamentos pendentes da empresa
        cur.execute("""
            SELECT c.nome, p.valor, p.data_vencimento 
            FROM pagamentos p 
            JOIN vendas v ON p.venda_id = v.id 
            JOIN clientes c ON v.cliente_id = c.id 
            WHERE v.empresa_id = %s AND p.status = 'pendente' 
            ORDER BY p.data_vencimento
        """, (session['empresa_id'],))
        pagamentos_pendentes = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return render_template('dashboard.html', 
                             vendas_recentes=vendas_recentes,
                             pagamentos_pendentes=pagamentos_pendentes)
    except Exception as e:
        print(f"[ERRO] Erro no dashboard: {str(e)}")
        flash('Erro ao carregar dashboard', 'error')
        return redirect(url_for('home'))

@app.route('/master-dashboard')
@login_required
def master_dashboard():
    """Dashboard para usuários master"""
    # Verificar se é usuário master
    if current_user.role != 'master':
        flash('Acesso negado. Apenas usuários master podem acessar esta página.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados', 'error')
            return redirect(url_for('home'))
        
        cur = conn.cursor()
        
        # Buscar estatísticas globais
        cur.execute("SELECT COUNT(*) FROM empresas WHERE ativo = TRUE")
        empresas_ativas = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM app_users WHERE ativo = TRUE")
        usuarios_totais = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM vendas")
        vendas_totais = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        return render_template('master_dashboard.html',
                             empresas_ativas=empresas_ativas,
                             usuarios_totais=usuarios_totais,
                             vendas_totais=vendas_totais)
    except Exception as e:
        print(f"[ERRO] Erro no master dashboard: {str(e)}")
        flash('Erro ao carregar dashboard master', 'error')
        return redirect(url_for('home'))

@app.route('/vendas', methods=['GET', 'POST'])
@login_required
def vendas():
    """Rota para gerenciar vendas"""
    # Verificar se empresa foi selecionada
    if 'empresa_id' not in session:
        return redirect(url_for('select_company'))
    
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
            """, (cliente_id, session['empresa_id'], current_user.id, valor_total, valor_entrada,
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
            print(f"[ERRO] Erro ao registrar venda: {str(e)}")
            return redirect(url_for('vendas'))
    
    # GET request
    conn = get_db_connection()
    if not conn:
        flash('Erro ao conectar ao banco de dados', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, nome FROM clientes WHERE empresa_id = %s", (session['empresa_id'],))
        clientes = cur.fetchall()
        cur.close()
        conn.close()
        
        return render_template('vendas.html', clientes=clientes)
    except Exception as e:
        flash('Erro ao carregar página de vendas', 'error')
        print(f"[ERRO] Erro na página de vendas: {str(e)}")
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
            JOIN app_users u ON v.user_id = u.id
            WHERE v.id = %s AND v.empresa_id = %s
        """, (venda_id, session['empresa_id']))
        
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
        print(f"[ERRO] Erro ao gerar contrato: {str(e)}")
        import traceback
        traceback.print_exc()
        return redirect(url_for('vendas'))

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)