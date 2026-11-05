# Equipa de Agentes IA

Uma pequena "empresa" de agentes de IA (Gemini) que trabalham em conjunto, à semelhança do ChatDev, para:

- **Software** — construir uma ferramenta/aplicação a partir de um pedido (Coordenador → Programador → Revisor → Testador).
- **Relatório / análise técnica** — escrever um relatório completo (Coordenador → Analista → Redator → Revisor).

O progresso de cada agente é mostrado em tempo real numa página local no browser.

## Configuração

1. Crie um ambiente virtual e instale as dependências:

   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Copie `.env.example` para `.env` e preencha a sua chave da API do Gemini (gratuita, gerada em
   https://aistudio.google.com/apikey — é diferente da conta/assinatura Gemini Pro):

   ```
   copy .env.example .env
   ```

   Edite `.env` e coloque a sua `GEMINI_API_KEY`.

## Uso

```
python run.py
```

Isto abre automaticamente `http://127.0.0.1:8000` no browser. Escreva o pedido, escolha o tipo de equipa
("Software" ou "Relatório") e clique em "Iniciar equipa". Se o pedido for vago, o Coordenador faz
perguntas de clarificação antes de avançar.

No fim, os ficheiros produzidos ficam disponíveis para download num `.zip`, e também na pasta
`workspaces/<nome-da-execução>/`.

## Notas

- O servidor só escuta em `127.0.0.1` (não está acessível na rede).
- Usa o nível gratuito da API do Gemini (`GEMINI_MODEL` no `.env`, por omissão `gemini-3.1-flash-lite`),
  que tem limites de pedidos por minuto **e por dia** — bastante apertados (ex: só 20 pedidos/dia no
  modelo `gemini-3.5-flash` comum) — e os modelos mais recentes (3.5/3.6/3.8) ficam por vezes
  sobrecarregados ("503 UNAVAILABLE") por terem mais procura. Consulte os seus limites atuais em
  https://aistudio.google.com/rate-limit. Se esgotar a quota de um modelo ou ele estiver
  sobrecarregado, pode mudar `GEMINI_MODEL` para outro (cada modelo tem quota diária própria — modelos
  mais antigos como `gemini-3.1-flash-lite` tendem a estar mais livres). O número de iterações de
  revisão/correção também tem um limite próprio (`MAX_REVIEW_ITERATIONS` no `.env`, por omissão 3)
  para poupar pedidos.
- Pedidos de software mantêm-se propositadamente simples (um script Python ou uma página web
  autossuficiente) — tal como o ChatDev original, não é indicado para projetos grandes ou complexos.

## Publicar online (Render ou Railway)

A app tem um `Dockerfile` pronto (inclui Python, Node.js e PHP, necessários para a pré-visualização).
Passos gerais, válidos para Render ou Railway:

1. Crie um repositório no GitHub com este projeto (o `.gitignore` já exclui `.env`, `.venv/` e
   `workspaces/`) e publique-o (`git push`).
2. No Render ([render.com](https://render.com)) ou Railway ([railway.app](https://railway.app)), crie um
   novo serviço a partir desse repositório — ambos detetam o `Dockerfile` automaticamente.
3. Defina as variáveis de ambiente do serviço (iguais às do `.env`):
   - `GEMINI_API_KEY` (obrigatória)
   - `GEMINI_MODEL`, `MAX_REVIEW_ITERATIONS` (opcionais, usam o valor por omissão se não definir)
   - `REGISTO_CHAVE` e `SECRET_KEY` — **defina sempre estas duas ao publicar online** (ver secção
     "Contas de utilizador" abaixo). Sem elas, a app fica aberta a qualquer pessoa com o link.
4. A plataforma atribui a porta automaticamente através da variável `PORT` — o `Dockerfile` já lê isso,
   não precisa de configurar nada.

## Contas de utilizador (login)

Por omissão (uso local, sem `REGISTO_CHAVE` definida) a app fica aberta, sem pedir login — como sempre
foi. Ao definir `REGISTO_CHAVE` no `.env` (ou nas variáveis de ambiente do serviço online), a app passa a
exigir sessão iniciada para tudo:

- Cada pessoa cria a sua própria conta em `/registar`, indicando utilizador, password e a `REGISTO_CHAVE`
  — só quem souber essa chave consegue criar conta. Reparta a chave apenas com quem quiser convidar.
- As contas e as passwords (sempre em hash, nunca em texto simples) ficam guardadas em `data/users.json`.
- `SECRET_KEY` assina a sessão de login — defina um valor fixo ao publicar online, senão todos têm de
  voltar a entrar sempre que o serviço reiniciar.

Gere valores fortes e únicos para as duas (nunca reutilize os mesmos em instalações diferentes):

```
python -c "import secrets; print(secrets.token_urlsafe(24))"
```

**Importante sobre armazenamento:** nos planos gratuitos/básicos do Render/Railway, o disco não é
persistente — cada reinício ou novo deploy apaga as pastas `workspaces/` (histórico de projetos) **e**
`data/` (contas criadas, que teriam de ser recriadas). Para manter isto entre reinícios, é preciso
adicionar um disco persistente ("Disk" no Render, "Volume" no Railway) montado em `/app`, normalmente só
disponível em planos pagos. Sem isso, trate a versão online como algo que pode "esquecer" contas e
projetos a cada reinício, e descarregue o `.zip` de cada projeto importante.
