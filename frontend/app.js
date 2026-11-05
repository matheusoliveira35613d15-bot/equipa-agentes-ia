const form = document.getElementById("form-pedido");
const salaEl = document.getElementById("sala");
const equipaSelect = document.getElementById("equipa");
const log = document.getElementById("log");
const clarificacaoDiv = document.getElementById("clarificacao");
const resultadoDiv = document.getElementById("resultado");
const btnIniciar = document.getElementById("btn-iniciar");

let ws = null;

const CARGOS = {
  software: ["Coordenador", "Programador", "Revisor", "Testador"],
  relatorio: ["Coordenador", "Analista", "Redator", "Revisor"],
};

// Centro da sala: (400, 260). Secretárias nos 4 pontos cardeais do losango do chão.
const CENTRO = { x: 400, y: 260 };
const POSICOES = [
  { x: 400, y: 165 }, // norte
  { x: 565, y: 260 }, // este
  { x: 400, y: 355 }, // sul
  { x: 235, y: 260 }, // oeste
];
const CORES = ["laranja", "azul", "verde", "roxo"];

function desenharSecretaria(nome, cx, cy, corClasse, indice) {
  const ww = 42; // meia-largura do tampo
  const hh = 21; // meia-profundidade do tampo
  const slabH = 5; // espessura do tampo (fino, como mobília a sério)
  const legH = 20; // comprimento das pernas

  const N = { x: cx, y: cy - hh };
  const E = { x: cx + ww, y: cy };
  const S = { x: cx, y: cy + hh };
  const W = { x: cx - ww, y: cy };
  const p = (pt) => `${pt.x},${pt.y}`;

  const topo = `${p(N)} ${p(E)} ${p(S)} ${p(W)}`;
  const direita = `${p(E)} ${p(S)} ${S.x},${S.y + slabH} ${E.x},${E.y + slabH}`;
  const esquerda = `${p(S)} ${p(W)} ${W.x},${W.y + slabH} ${S.x},${S.y + slabH}`;
  const pernaBottomY = S.y + slabH + legH;

  const standH = 8, monW = 26, monH = 22, gap1 = 6, bodyW = 16, bodyH = 24, headR = 14, neckOverlap = 3;
  const monitorBottom = N.y - standH;
  const monitorTop = monitorBottom - monH;
  const monX = cx - monW / 2;
  const bodyBottom = monitorTop - gap1;
  const bodyTop = bodyBottom - bodyH;
  const cabecaY = bodyTop + neckOverlap - headR;

  const tipY = cabecaY - headR - 8;
  const bolhaBottom = tipY - 8;
  const bolhaTop = bolhaBottom - 44;
  const bolhaPrimeiraLinha = (bolhaTop + bolhaBottom) / 2 - 3;

  const atraso = (indice * 0.35).toFixed(2);

  return `
    <g id="desk-${nome}" class="desk cor-${corClasse}" style="--atraso:${atraso}s">
      <line class="desk-linha" x1="${CENTRO.x}" y1="${CENTRO.y}" x2="${cx}" y2="${cy}"></line>

      <circle class="ripple" cx="${cx}" cy="${cy}" r="46"></circle>

      <ellipse class="desk-glow" cx="${cx}" cy="${pernaBottomY - 2}" rx="32" ry="8"></ellipse>
      <line class="desk-perna" x1="${E.x - 4}" y1="${E.y + 2}" x2="${E.x - 4}" y2="${pernaBottomY}"></line>
      <line class="desk-perna" x1="${W.x + 4}" y1="${W.y + 2}" x2="${W.x + 4}" y2="${pernaBottomY}"></line>
      <polygon class="desk-esquerda" points="${esquerda}"></polygon>
      <polygon class="desk-direita" points="${direita}"></polygon>
      <polygon class="desk-topo" points="${topo}"></polygon>
      <polyline class="desk-trim" points="${p(W)} ${p(S)} ${p(E)}"></polyline>

      <g class="avatar-figure" style="transform-origin:${cx}px ${N.y}px; animation-delay:${atraso}">
        <ellipse class="monitor-base" cx="${cx}" cy="${N.y}" rx="12" ry="4"></ellipse>
        <line class="monitor-pe" x1="${cx}" y1="${N.y}" x2="${cx}" y2="${monitorBottom}"></line>
        <rect class="monitor" x="${monX}" y="${monitorTop}" width="${monW}" height="${monH}" rx="2"></rect>
        <rect class="monitor-linha monitor-linha-a" x="${monX + 4}" y="${monitorTop + 5}" width="14" height="2"></rect>
        <rect class="monitor-linha monitor-linha-b" x="${monX + 4}" y="${monitorTop + 10}" width="10" height="2"></rect>
        <rect class="monitor-linha monitor-linha-c" x="${monX + 4}" y="${monitorTop + 15}" width="16" height="2"></rect>

        <rect class="teclado" x="${cx - 17}" y="${N.y + 6}" width="34" height="12" rx="2"></rect>
        <line class="teclado-tecla" x1="${cx - 13}" y1="${N.y + 9}" x2="${cx + 13}" y2="${N.y + 9}"></line>
        <line class="teclado-tecla" x1="${cx - 13}" y1="${N.y + 13}" x2="${cx + 13}" y2="${N.y + 13}"></line>
        <circle class="rato" cx="${cx + 24}" cy="${N.y + 12}" r="3.5"></circle>

        <path class="avatar-corpo" d="M${cx - bodyW} ${bodyBottom}
                 C${cx - bodyW} ${bodyBottom - 15} ${cx - bodyW + 4} ${bodyTop + 6} ${cx - 7} ${bodyTop}
                 L${cx + 7} ${bodyTop}
                 C${cx + bodyW - 4} ${bodyTop + 6} ${cx + bodyW} ${bodyBottom - 15} ${cx + bodyW} ${bodyBottom} Z"></path>
        <path class="avatar-colarinho" d="M${cx - 6} ${bodyTop + 1} L${cx} ${bodyTop + 11} L${cx + 6} ${bodyTop + 1} Z"></path>

        <circle class="avatar-cabeca" cx="${cx}" cy="${cabecaY}" r="${headR}"></circle>
        <path class="avatar-cabelo" d="M${cx - headR} ${cabecaY - 1}
                 A${headR} ${headR} 0 0 1 ${cx + headR} ${cabecaY - 1}
                 C${cx + headR} ${cabecaY - headR - 4} ${cx - headR} ${cabecaY - headR - 4} ${cx - headR} ${cabecaY - 1} Z"></path>
        <circle class="avatar-olho" cx="${cx - 4.5}" cy="${cabecaY + 1}" r="1.4"></circle>
        <circle class="avatar-olho" cx="${cx + 4.5}" cy="${cabecaY + 1}" r="1.4"></circle>
        <path class="avatar-sorriso" d="M${cx - 4} ${cabecaY + 6} Q${cx} ${cabecaY + 8.5} ${cx + 4} ${cabecaY + 6}"></path>
        <ellipse class="avatar-brilho" cx="${cx - 4}" cy="${cabecaY - 5}" rx="4.5" ry="3"></ellipse>
      </g>

      <g class="badge" style="transform-origin:${cx + ww - 2}px ${N.y - 2}px">
        <circle class="badge-ok" cx="${cx + ww - 2}" cy="${N.y - 2}" r="9"></circle>
        <text class="badge-ok-texto" x="${cx + ww - 2}" y="${N.y + 2}" text-anchor="middle">&#10003;</text>
      </g>

      <g class="fala" id="fala-${nome}" style="transform-origin:${cx}px ${bolhaBottom}px">
        <rect class="fala-fundo" x="${cx - 90}" y="${bolhaTop}" width="180" height="44" rx="8"></rect>
        <polygon class="fala-seta" points="${cx - 7},${bolhaBottom} ${cx + 7},${bolhaBottom} ${cx},${bolhaBottom + 10}"></polygon>
        <text class="fala-texto" x="${cx}" y="${bolhaPrimeiraLinha}" text-anchor="middle"></text>
      </g>

      <text class="desk-label" x="${cx}" y="${pernaBottomY + 17}" text-anchor="middle">${nome}</text>
      <text class="desk-estado" x="${cx}" y="${pernaBottomY + 32}" text-anchor="middle">à espera</text>
    </g>`;
}

function estrelas() {
  const posicoes = [
    [60, 40], [740, 50], [120, 400], [700, 410], [40, 230],
    [760, 230], [400, 30], [400, 430], [180, 120], [600, 350],
  ];
  return posicoes
    .map(([x, y], i) => `<circle class="estrela" cx="${x}" cy="${y}" r="1.6" style="--atraso:${(i * 0.4).toFixed(2)}s"></circle>`)
    .join("");
}

function montarSala(equipa) {
  const cargos = CARGOS[equipa];
  const desks = cargos
    .map((nome, i) => desenharSecretaria(nome, POSICOES[i].x, POSICOES[i].y, CORES[i], i))
    .join("");

  salaEl.innerHTML = `
    <defs>
      <pattern id="textura-chao" width="36" height="36" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
        <line x1="0" y1="0" x2="0" y2="36" class="textura-linha"></line>
      </pattern>
    </defs>
    ${estrelas()}
    <polygon class="sala-chao" points="400,70 730,260 400,450 70,260"></polygon>
    <polygon class="sala-chao-textura" points="400,70 730,260 400,450 70,260" fill="url(#textura-chao)"></polygon>
    <circle class="sala-centro" cx="${CENTRO.x}" cy="${CENTRO.y}" r="16"></circle>
    ${desks}
  `;
}

const temporizadoresFala = {};
const NS_SVG = "http://www.w3.org/2000/svg";

function quebrarDuasLinhas(texto, maxPorLinha = 24) {
  const limpo = texto.trim().replace(/\s+/g, " ");
  if (limpo.length <= maxPorLinha) return [limpo];

  let corte = limpo.lastIndexOf(" ", maxPorLinha);
  if (corte <= 0) corte = maxPorLinha;
  const linha1 = limpo.slice(0, corte);
  let resto = limpo.slice(corte).trim();

  if (resto.length > maxPorLinha) {
    let corte2 = resto.lastIndexOf(" ", maxPorLinha - 1);
    if (corte2 <= 0) corte2 = maxPorLinha - 1;
    resto = `${resto.slice(0, corte2)}…`;
  }
  return [linha1, resto];
}

function mostrarFala(agente, texto) {
  const bolha = document.getElementById(`fala-${agente}`);
  if (!bolha) return;
  const textoEl = bolha.querySelector(".fala-texto");
  const x = textoEl.getAttribute("x");

  textoEl.textContent = "";
  quebrarDuasLinhas(texto).forEach((linha, i) => {
    const tspan = document.createElementNS(NS_SVG, "tspan");
    tspan.setAttribute("x", x);
    tspan.setAttribute("dy", i === 0 ? "0" : "15");
    tspan.textContent = linha;
    textoEl.appendChild(tspan);
  });

  bolha.classList.add("mostrar");
  clearTimeout(temporizadoresFala[agente]);
  temporizadoresFala[agente] = setTimeout(() => bolha.classList.remove("mostrar"), 5000);
}

function atualizarEstado(agente, estado) {
  const grupo = document.getElementById(`desk-${agente}`);
  if (!grupo) return;
  grupo.querySelector(".desk-estado").textContent = estado;
  const concluido = estado === "concluído";
  const emEspera = estado === "à espera";
  grupo.classList.toggle("ativo", !concluido && !emEspera);
  grupo.classList.toggle("concluido", concluido);
}

async function tentarPreviewEm(area, runId) {
  if (!area) return;
  area.innerHTML = `<p class="preview-a-carregar">A preparar pré-visualização…</p>`;
  try {
    const resp = await fetch(`/preview/${encodeURIComponent(runId)}`, { method: "POST" });
    const dados = await resp.json();
    if (!resp.ok || !dados.url) {
      area.innerHTML = "";
      return;
    }
    const urlFresca = `${dados.url}${dados.url.includes("?") ? "&" : "?"}t=${Date.now()}`;
    area.innerHTML = `
      <a href="${dados.url}" target="_blank" rel="noopener" class="link-preview">Abrir numa nova aba ↗</a>
      <iframe class="iframe-preview" src="${urlFresca}" title="Pré-visualização do resultado"></iframe>`;
  } catch (e) {
    area.innerHTML = "";
  }
}

async function tentarPreview(runId) {
  await tentarPreviewEm(document.getElementById("preview-area"), runId);
}

function criarPainelEdicao(runId, { onAtualizado } = {}) {
  const container = document.createElement("div");
  container.className = "painel-edicao";
  container.innerHTML = `
    <label class="edicao-label">Pedir uma alteração à IA</label>
    <textarea class="edicao-texto" rows="2" placeholder="Ex: muda a cor principal para azul, adiciona uma secção de contactos..."></textarea>
    <button type="button" class="botao-editar">Aplicar alteração</button>
    <p class="edicao-estado"></p>`;

  const textarea = container.querySelector(".edicao-texto");
  const botao = container.querySelector(".botao-editar");
  const estado = container.querySelector(".edicao-estado");

  botao.addEventListener("click", async () => {
    const pedido = textarea.value.trim();
    if (!pedido) return;
    botao.disabled = true;
    estado.textContent = "A aplicar alteração… (pode demorar, por causa dos limites do nível gratuito)";
    try {
      const resp = await fetch(`/editar/${encodeURIComponent(runId)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pedido }),
      });
      const dados = await resp.json();
      if (!resp.ok) {
        estado.textContent = `Erro: ${dados.erro || "não foi possível aplicar a alteração."}`;
      } else {
        estado.textContent = "Alteração aplicada.";
        textarea.value = "";
        if (onAtualizado) onAtualizado(dados);
      }
    } catch (e) {
      estado.textContent = "Erro de ligação ao aplicar a alteração.";
    } finally {
      botao.disabled = false;
    }
  });

  return container;
}

function adicionarLog(agente, conteudo) {
  const linha = document.createElement("div");
  linha.className = "log-linha";
  const forte = document.createElement("strong");
  forte.textContent = `${agente}:`;
  linha.appendChild(forte);
  linha.appendChild(document.createTextNode(` ${conteudo}`));
  log.appendChild(linha);
  log.scrollTop = log.scrollHeight;
}

equipaSelect.addEventListener("change", () => montarSala(equipaSelect.value));
montarSala(equipaSelect.value);

let ultimaEquipa = equipaSelect.value;

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const pedido = document.getElementById("pedido").value.trim();
  const equipa = equipaSelect.value;
  if (!pedido) return;
  ultimaEquipa = equipa;

  log.innerHTML = "";
  clarificacaoDiv.innerHTML = "";
  resultadoDiv.innerHTML = "";
  montarSala(equipa);
  btnIniciar.disabled = true;

  ws = new WebSocket(`ws://${location.host}/ws`);
  ws.onopen = () => ws.send(JSON.stringify({ tipo: "iniciar", equipa, pedido }));
  ws.onmessage = (ev) => tratarEvento(JSON.parse(ev.data));
  ws.onclose = () => {
    btnIniciar.disabled = false;
  };
});

function tratarEvento(evento) {
  switch (evento.tipo) {
    case "status":
      atualizarEstado(evento.agente, evento.estado);
      break;
    case "mensagem":
      adicionarLog(evento.agente, evento.conteudo);
      mostrarFala(evento.agente, String(evento.conteudo));
      break;
    case "clarificacao":
      mostrarClarificacao(evento.perguntas);
      break;
    case "ficheiros":
      adicionarLog("Sistema", `Ficheiros gerados: ${evento.ficheiros.join(", ")}`);
      break;
    case "concluido":
      resultadoDiv.innerHTML = `
        <p>Concluído.</p>
        <a class="botao-download" href="${evento.download}">Descarregar resultado (.zip)</a>
        <div id="preview-area"></div>`;
      btnIniciar.disabled = false;
      tentarPreview(evento.run_id);
      if (ultimaEquipa === "software") {
        resultadoDiv.appendChild(
          criarPainelEdicao(evento.run_id, {
            onAtualizado: () => tentarPreview(evento.run_id),
          })
        );
      }
      break;
    case "erro":
      adicionarLog("Erro", evento.mensagem);
      btnIniciar.disabled = false;
      break;
  }
}

function mostrarClarificacao(perguntas) {
  clarificacaoDiv.innerHTML = "<p>O Coordenador precisa de mais informação:</p>";
  const ids = perguntas.map((p, i) => {
    const id = `resp-${i}`;
    const label = document.createElement("label");
    label.textContent = p;
    const input = document.createElement("input");
    input.type = "text";
    input.id = id;
    clarificacaoDiv.appendChild(label);
    clarificacaoDiv.appendChild(input);
    return id;
  });
  const botao = document.createElement("button");
  botao.type = "button";
  botao.textContent = "Responder";
  botao.onclick = () => {
    const respostas = ids.map((id) => document.getElementById(id).value);
    ws.send(JSON.stringify({ respostas }));
    clarificacaoDiv.innerHTML = "<p>Respostas enviadas.</p>";
  };
  clarificacaoDiv.appendChild(botao);
}

// --- Menu (hambúrguer): "Novo pedido" / "Os meus projetos" ---

const btnMenu = document.getElementById("btn-menu");
const menuDropdown = document.getElementById("menu-dropdown");
const btnAbaNovo = document.getElementById("aba-novo");
const btnAbaProjetos = document.getElementById("aba-projetos");
const vistaNovo = document.getElementById("vista-novo");
const vistaProjetos = document.getElementById("vista-projetos");
const listaProjetos = document.getElementById("lista-projetos");

function abrirMenu(aberto) {
  btnMenu.classList.toggle("aberto", aberto);
  btnMenu.setAttribute("aria-expanded", String(aberto));
  menuDropdown.classList.toggle("escondido", !aberto);
}

btnMenu.addEventListener("click", (e) => {
  e.stopPropagation();
  abrirMenu(menuDropdown.classList.contains("escondido"));
});

document.addEventListener("click", (e) => {
  if (!menuDropdown.classList.contains("escondido") && !menuDropdown.contains(e.target)) {
    abrirMenu(false);
  }
});

function mostrarAba(aba) {
  const ehNovo = aba === "novo";
  vistaNovo.classList.toggle("escondido", !ehNovo);
  vistaProjetos.classList.toggle("escondido", ehNovo);
  btnAbaNovo.classList.toggle("ativa", ehNovo);
  btnAbaProjetos.classList.toggle("ativa", !ehNovo);
  if (!ehNovo) carregarProjetos();
  abrirMenu(false);
}

btnAbaNovo.addEventListener("click", () => mostrarAba("novo"));
btnAbaProjetos.addEventListener("click", () => mostrarAba("projetos"));

function formatarData(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleString("pt-PT", { dateStyle: "short", timeStyle: "short" });
  } catch (e) {
    return iso;
  }
}

async function carregarProjetos() {
  listaProjetos.innerHTML = "<p class='projetos-a-carregar'>A carregar…</p>";
  try {
    const resp = await fetch("/execucoes");
    const execucoes = await resp.json();
    if (!execucoes.length) {
      listaProjetos.innerHTML = "<p>Ainda não criou nenhum projeto.</p>";
      return;
    }
    listaProjetos.innerHTML = "";
    execucoes.forEach((exec) => listaProjetos.appendChild(criarCartaoProjeto(exec)));
  } catch (e) {
    listaProjetos.innerHTML = "<p>Não foi possível carregar os projetos.</p>";
  }
}

function criarCartaoProjeto(exec) {
  const card = document.createElement("article");
  card.className = "projeto-card";

  const titulo = document.createElement("h3");
  titulo.textContent = exec.pedido.length > 100 ? `${exec.pedido.slice(0, 100)}…` : exec.pedido;
  card.appendChild(titulo);

  const meta = document.createElement("p");
  meta.className = "projeto-meta";
  meta.textContent = `${exec.equipa_tipo === "software" ? "Software" : "Relatório"} · ${formatarData(exec.criado_em)}`;
  card.appendChild(meta);

  const acoes = document.createElement("div");
  acoes.className = "projeto-acoes";

  if (exec.download) {
    const linkDownload = document.createElement("a");
    linkDownload.href = exec.download;
    linkDownload.className = "botao-download botao-pequeno";
    linkDownload.textContent = "Descarregar";
    acoes.appendChild(linkDownload);
  }

  const previewArea = document.createElement("div");

  if (exec.editavel) {
    const btnPreview = document.createElement("button");
    btnPreview.type = "button";
    btnPreview.className = "botao-secundario";
    btnPreview.textContent = "Pré-visualizar";
    btnPreview.addEventListener("click", () => tentarPreviewEm(previewArea, exec.run_id));
    acoes.appendChild(btnPreview);
  }

  card.appendChild(acoes);
  card.appendChild(previewArea);

  if (exec.editavel) {
    card.appendChild(
      criarPainelEdicao(exec.run_id, {
        onAtualizado: (dados) => {
          const linkDownload = card.querySelector(".botao-download");
          if (linkDownload && dados.download) linkDownload.href = dados.download;
          if (previewArea.innerHTML.trim()) tentarPreviewEm(previewArea, exec.run_id);
        },
      })
    );
  }

  return card;
}
