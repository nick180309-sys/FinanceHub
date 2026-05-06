#!/usr/bin/env python3
"""
Script para testar a funcionalidade de adicionar transações
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, init_db
import sqlite3

def test_add_transaction():
    """Testa a funcionalidade de adicionar transação"""
    print("🧪 Testando funcionalidade de adicionar transação...")

    # Inicializar banco
    init_db()

    # Verificar se tabela existe
    conn = db()
    c = conn.cursor()

    try:
        # Verificar estrutura da tabela
        c.execute("PRAGMA table_info(transacoes)")
        columns = c.fetchall()
        print(f"✅ Tabela transacoes tem {len(columns)} colunas")

        # Tentar inserir uma transação de teste
        c.execute("""
            INSERT INTO transacoes (family_id, user_id, valor, descricao, categoria, data, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (1, 1, -50.0, "Teste de transação", "Alimentação", "2024-01-01", "test_user", "2024-01-01T00:00:00"))

        conn.commit()
        print("✅ Inserção de transação funcionou!")

        # Verificar se foi inserida
        c.execute("SELECT COUNT(*) FROM transacoes")
        count = c.fetchone()[0]
        print(f"✅ Total de transações na tabela: {count}")

    except Exception as e:
        print(f"❌ Erro: {e}")
        return False
    finally:
        conn.close()

    print("✅ Teste concluído com sucesso!")
    return True

if __name__ == "__main__":
    test_add_transaction()