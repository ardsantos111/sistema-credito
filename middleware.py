from functools import wraps
from flask import abort, session, redirect, url_for, flash
from auth import user_has_permission

def require_permission(permission_name):
    """
    Decorator para verificar se o usuário tem uma permissão específica
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Verificar se usuário está logado
            if 'user_id' not in session:
                flash('Você precisa estar logado para acessar esta página.', 'error')
                return redirect(url_for('login'))
            
            user_id = session['user_id']
            
            # Verificar permissão
            if not user_has_permission(user_id, permission_name):
                flash('Você não tem permissão para acessar esta página.', 'error')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_role(required_role):
    """
    Decorator para verificar se o usuário tem um role específico
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Verificar se usuário está logado
            if 'user_id' not in session:
                flash('Você precisa estar logado para acessar esta página.', 'error')
                return redirect(url_for('login'))
            
            # Aqui você pode adicionar lógica para verificar o role do usuário
            # Por enquanto, vamos deixar como placeholder
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_company_selection(f):
    """
    Decorator para verificar se o usuário selecionou uma empresa
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verificar se usuário está logado
        if 'user_id' not in session:
            flash('Você precisa estar logado para acessar esta página.', 'error')
            return redirect(url_for('login'))
        
        # Verificar se empresa foi selecionada
        if 'empresa_id' not in session:
            # Redirecionar para seleção de empresa
            return redirect(url_for('select_company'))
        
        return f(*args, **kwargs)
    return decorated_function

def is_master_user(user_id):
    """
    Verifica se o usuário é um master user
    """
    from auth import load_user
    user = load_user(user_id)
    return user and user.role == 'master'

def require_master(f):
    """
    Decorator para verificar se o usuário é master
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verificar se usuário está logado
        if 'user_id' not in session:
            flash('Você precisa estar logado para acessar esta página.', 'error')
            return redirect(url_for('login'))
        
        # Verificar se é master user
        if not is_master_user(session['user_id']):
            flash('Acesso negado. Apenas usuários master podem acessar esta página.', 'error')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function