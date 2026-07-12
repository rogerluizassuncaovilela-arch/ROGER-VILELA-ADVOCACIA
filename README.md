# Roger Vilela Advocacia — Site Institucional

Stack: Python (Flask) + PostgreSQL + HTML/CSS/JS

---

## Passo a passo completo via CMD (Windows)

### 1. Abrir o CMD na pasta do projeto

```
cd "C:\Users\User\Downloads\ROGER VILELA ADVOCACIA"
```

---

### 2. Clonar o repositório (apenas na primeira vez)

```
git clone https://github.com/rogerluizassuncaovilela-arch/ROGER-VILELA-ADVOCACIA.git .
```

> O ponto no final clona dentro da pasta atual.

---

### 3. Criar o ambiente virtual Python

```
python -m venv venv
```

### 4. Ativar o ambiente virtual

```
venv\Scripts\activate
```

> O terminal ficará assim: `(venv) C:\Users\User\Downloads\ROGER VILELA ADVOCACIA>`

---

### 5. Instalar as dependências

```
pip install -r requirements.txt
```

---

### 6. Configurar o arquivo .env

Copie o arquivo de exemplo:

```
copy .env.example .env
```

Abra o `.env` no VS Code ou Bloco de Notas e preencha:

```
DB_NAME=rogervilela
DB_USER=postgres
DB_PASSWORD=SUA_SENHA_DO_POSTGRES
DB_HOST=localhost
DB_PORT=5432

GMAIL_USER=rogerluizassuncaovilela@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx

ADMIN_PASSWORD=escolha_uma_senha
SECRET_KEY=qualquer_string_longa_aleatoria
```

> **Como gerar a Senha de App do Gmail:**
> 1. Acesse myaccount.google.com
> 2. Segurança > Verificação em duas etapas (ative se não estiver ativa)
> 3. Segurança > Senhas de app
> 4. Selecione "Outro" > nomeie como "Site Roger Vilela" > Gerar
> 5. Copie os 16 caracteres para GMAIL_APP_PASSWORD

---

### 7. Criar o banco de dados no PostgreSQL

Abra o pgAdmin ou o psql e crie o banco:

```sql
CREATE DATABASE rogervilela;
```

Depois, com o ambiente virtual ativo, rode:

```
python init_db.py
```

Você verá: `✅ Tabela 'contatos' criada com sucesso!`

---

### 8. Rodar o servidor local

```
python app.py
```

Acesse no navegador: **http://localhost:5000**

Painel admin: **http://localhost:5000/admin**

---

### 9. Subir para o GitHub

```
git add .
git commit -m "primeiro commit - site roger vilela"
git push origin main
```

---

## Uso diário

Sempre que quiser rodar o projeto:

```
cd "C:\Users\User\Downloads\ROGER VILELA ADVOCACIA"
venv\Scripts\activate
python app.py
```

---

## Estrutura do projeto

```
ROGER VILELA ADVOCACIA/
├── app.py              ← Servidor Flask (rotas, banco, e-mail)
├── init_db.py          ← Cria a tabela no PostgreSQL (rode 1 vez)
├── requirements.txt    ← Dependências Python
├── .env                ← Configurações (NÃO sobe para o Git)
├── .env.example        ← Modelo do .env
├── .gitignore          ← Arquivos ignorados pelo Git
├── README.md           ← Este arquivo
└── templates/
    ├── index.html      ← Site principal
    ├── admin_login.html← Login do painel
    └── admin.html      ← Painel de mensagens
```

---

## Painel Admin

Acesse `/admin` com a senha definida em `ADMIN_PASSWORD`.

Funcionalidades:
- Ver todas as mensagens recebidas
- Destacar mensagens não lidas
- Marcar como lida
- Deletar mensagem
- Link direto para responder por e-mail
