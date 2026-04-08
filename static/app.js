// ── State ──
let resultados = [];
let lbl1 = '';
let lbl2 = '';
let filtroAtual = 'todos';

// ── DOM refs ──
const arquivo1 = document.getElementById('arquivo1');
const arquivo2 = document.getElementById('arquivo2');
const label1 = document.getElementById('label1');
const label2 = document.getElementById('label2');
const dropZone1 = document.getElementById('dropZone1');
const dropZone2 = document.getElementById('dropZone2');
const btnEnviar = document.getElementById('btnEnviar');
const btnLimpar = document.getElementById('btnLimpar');
const btnDownload = document.getElementById('btnDownload');
const loading = document.getElementById('loading');
const resumoSection = document.getElementById('resumoSection');
const filtrosSection = document.getElementById('filtrosSection');
const tabelaSection = document.getElementById('tabelaSection');
const tabelaHead = document.getElementById('tabelaHead');
const tabelaBody = document.getElementById('tabelaBody');
const chatPanel = document.getElementById('chatPanel');
const chatMessages = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');
const btnChatToggle = document.getElementById('btnChatToggle');
const btnChatSend = document.getElementById('btnChatSend');
const btnClear1 = document.getElementById('btnClear1');
const btnClear2 = document.getElementById('btnClear2');
const mainContent = document.getElementById('mainContent');

// ── File upload ──
function setupUpload(input, label, dropZone, btnClear, defaultText) {
    input.addEventListener('change', () => {
        if (input.files.length) {
            label.textContent = input.files[0].name;
            dropZone.classList.add('has-file');
            btnClear.hidden = false;
        } else {
            label.textContent = defaultText;
            dropZone.classList.remove('has-file');
            btnClear.hidden = true;
        }
        checkReady();
    });

    // Botão X para limpar arquivo individual
    btnClear.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        input.value = '';
        label.textContent = defaultText;
        dropZone.classList.remove('has-file');
        btnClear.hidden = true;
        checkReady();
    });

    dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('dragover'); });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
    dropZone.addEventListener('drop', e => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            input.files = e.dataTransfer.files;
            input.dispatchEvent(new Event('change'));
        }
    });
}

setupUpload(arquivo1, label1, dropZone1, btnClear1, 'Arquivo Flytour');
setupUpload(arquivo2, label2, dropZone2, btnClear2, 'Arquivo Wintour');

function checkReady() {
    btnEnviar.disabled = !(arquivo1.files.length && arquivo2.files.length);
}

// ── Processar ──
btnEnviar.addEventListener('click', async () => {
    const formData = new FormData();
    formData.append('arquivo1', arquivo1.files[0]);
    formData.append('arquivo2', arquivo2.files[0]);

    loading.classList.add('visible');
    resumoSection.hidden = true;
    filtrosSection.hidden = true;
    tabelaSection.hidden = true;
    btnEnviar.disabled = true;

    try {
        const res = await fetch('/api/processar', { method: 'POST', body: formData });
        const data = await res.json();

        if (data.error) {
            alert(data.error);
            return;
        }

        lbl1 = data.lbl1;
        lbl2 = data.lbl2;
        resultados = data.resultado;

        renderResumo(data.resumo);
        renderTabela();

        resumoSection.hidden = false;
        filtrosSection.hidden = false;
        tabelaSection.hidden = false;
    } catch (err) {
        alert('Erro ao processar: ' + err.message);
    } finally {
        loading.classList.remove('visible');
        btnEnviar.disabled = false;
    }
});

// ── Limpar ──
btnLimpar.addEventListener('click', () => {
    arquivo1.value = '';
    arquivo2.value = '';
    label1.textContent = 'Arquivo Flytour';
    label2.textContent = 'Arquivo Wintour';
    dropZone1.classList.remove('has-file');
    dropZone2.classList.remove('has-file');
    btnEnviar.disabled = true;
    resumoSection.hidden = true;
    filtrosSection.hidden = true;
    tabelaSection.hidden = true;
    resultados = [];
    filtroAtual = 'todos';
    setActiveChip('todos');
});

// ── Resumo ──
function renderResumo(resumo) {
    document.getElementById('lblLocs1').textContent = resumo.lbl1;
    document.getElementById('valLocs1').textContent = resumo.locs_1;
    document.getElementById('lblLocs2').textContent = resumo.lbl2;
    document.getElementById('valLocs2').textContent = resumo.locs_2;
    document.getElementById('valOk').textContent = resumo.ok;
    document.getElementById('valDiv').textContent = resumo.divergentes;
    document.getElementById('valSomF').textContent = resumo.somente_fornecedor;
    document.getElementById('valSomW').textContent = resumo.somente_wintour;
}

// ── Tabela ──
const STATUS_ORDER = { 'Divergente': 0, 'Somente Fornecedor': 1, 'Somente Wintour': 2, 'Ok': 3 };

function renderTabela() {
    // Header
    // Colgroup para larguras fixas (total = 100%) – 15 colunas
    const existingColgroup = document.querySelector('#tabelaResultado colgroup');
    if (existingColgroup) existingColgroup.remove();
    const colgroup = document.createElement('colgroup');
    //  Loc  Pax   Stat  LiqF  LiqS  Dif   OrigDif OverW IncF  DifOv DifT  DifTx Venda Cli   Emis  Mark
    [5,  10,  6,   5,    5,    5,    8,     5,    5,    5,    5,    5,    6,    8,    6,    5].forEach(w => {
        const col = document.createElement('col');
        col.style.width = w + '%';
        colgroup.appendChild(col);
    });
    document.getElementById('tabelaResultado').prepend(colgroup);

    tabelaHead.innerHTML = `
        <th title="Localizador">Loc.</th><th>Passageiro</th><th>Status</th>
        <th title="Liq. ${esc(lbl1)}">Liq. ${esc(lbl1)}</th><th title="Liq. ${esc(lbl2)}">Liq. ${esc(lbl2)}</th>
        <th>Diferença</th><th title="Origem da Diferença">Origem Dif.</th>
        <th title="Over Agência (Wintour)">Over (Win.)</th>
        <th title="Incentivo (Fornecedor)">Incentivo (Forn.)</th>
        <th title="Diferença Over/Incentivo">Dif. Over</th>
        <th title="Diferença Tarifa">Dif. Tarifa</th>
        <th title="Diferença Taxa de Embarque">Dif. Taxa Emb.</th>
        <th title="Número Venda">Nº Venda</th><th>Cliente</th><th>Emissor</th>
        <th>Markup</th>
    `;

    // Sort: divergentes primeiro
    const sorted = [...resultados].sort((a, b) => {
        const oa = STATUS_ORDER[a.status] ?? 99;
        const ob = STATUS_ORDER[b.status] ?? 99;
        return oa - ob;
    });

    // Filter
    const filtered = filtroAtual === 'todos'
        ? sorted
        : sorted.filter(r => r.status === filtroAtual);

    // Render
    tabelaBody.innerHTML = '';
    for (const r of filtered) {
        const tr = document.createElement('tr');
        const v1 = r[`liq_${lbl1}`];
        const v2 = r[`liq_${lbl2}`];
        const liq1 = fmt(v1);
        const liq2 = fmt(v2);
        const dif = fmt(r.dif);

        // Classe da célula de diferença
        const numDif = parseFloat(r.dif) || 0;
        let difClass = '';
        if (r.status === 'Divergente') difClass = 'cel-dif-positiva';
        else if (numDif > 0) difClass = 'cel-dif-positiva';
        else if (numDif < 0) difClass = 'cel-dif-negativa';
        else if (r.status === 'Ok') difClass = 'cel-dif-zero';

        // Origem da diferença vem do backend (comparação campo a campo)
        const origemDif = r.origem_dif || '';
        const origemDetalhe = r.origem_dif_detalhe || origemDif;
        const n1 = parseFloat(v1) || 0;
        const n2 = parseFloat(v2) || 0;
        let liq1Class = '';
        let liq2Class = '';

        if (r.status === 'Divergente' || r.status === 'Somente Fornecedor' || r.status === 'Somente Wintour') {
            if (n1 > 0 && n2 === 0) {
                liq1Class = 'cel-valor-presente';
                liq2Class = 'cel-valor-ausente';
            } else if (n2 > 0 && n1 === 0) {
                liq1Class = 'cel-valor-ausente';
                liq2Class = 'cel-valor-presente';
            } else if (n1 > n2) {
                liq1Class = 'cel-valor-maior';
                liq2Class = 'cel-valor-menor';
            } else if (n2 > n1) {
                liq1Class = 'cel-valor-menor';
                liq2Class = 'cel-valor-maior';
            }
        }

        const overWin  = fmt(r.over_agencia);
        const incForn  = fmt(r.incentivo_fornecedor);
        const difOver  = fmt(r.over_dif);

        // Classe da célula Dif. Over
        const numOver = parseFloat(r.over_dif) || 0;
        const overOk = (r.over_agencia !== '' || r.incentivo_fornecedor !== '') && Math.abs(numOver) <= 0.01;
        const difOverClass = (r.over_agencia !== '' || r.incentivo_fornecedor !== '')
            ? (overOk ? 'cel-dif-zero' : (numOver > 0 ? 'cel-dif-positiva' : 'cel-dif-negativa'))
            : '';

        const difTar  = fmt(r.tarifa_dif);
        const numTar  = parseFloat(r.tarifa_dif) || 0;
        const difTarClass = r.tarifa_dif !== ''
            ? (Math.abs(numTar) <= 0.01 ? 'cel-dif-zero' : (numTar > 0 ? 'cel-dif-positiva' : 'cel-dif-negativa'))
            : '';

        const difTax  = fmt(r.taxa_dif);
        const numTax  = parseFloat(r.taxa_dif) || 0;
        const difTaxClass = r.taxa_dif !== ''
            ? (Math.abs(numTax) <= 0.01 ? 'cel-dif-zero' : (numTax > 0 ? 'cel-dif-positiva' : 'cel-dif-negativa'))
            : '';

        tr.innerHTML = `
            <td title="${esc(r.loc)}"><strong>${esc(r.loc)}</strong></td>
            <td title="${esc(r.pax)}">${esc(r.pax)}</td>
            <td>${badgeStatus(r.status)}</td>
            <td title="${liq1}" class="${liq1Class}">${liq1}</td>
            <td title="${liq2}" class="${liq2Class}">${liq2}</td>
            <td title="${dif}" class="${difClass}">${dif}</td>
            <td title="${esc(origemDetalhe)}" class="${origemDif ? 'cel-origem-dif' : ''}">${esc(origemDif) || '—'}</td>
            <td title="${overWin}">${overWin}</td>
            <td title="${incForn}">${incForn}</td>
            <td title="${difOver}" class="${difOverClass}">${difOver}</td>
            <td title="${difTar}" class="${difTarClass}">${difTar}</td>
            <td title="${difTax}" class="${difTaxClass}">${difTax}</td>
            <td title="${esc(r.venda || '')}">${esc(r.venda || '')}</td>
            <td title="${esc(r.cliente || '')}">${esc(r.cliente || '')}</td>
            <td title="${esc(r.emissor || '')}">${esc(r.emissor || '')}</td>
            <td title="${esc(r.markup || '')}">${esc(r.markup || '')}</td>
        `;
        tabelaBody.appendChild(tr);
    }
}

function badgeStatus(status) {
    const map = {
        'Ok': 'badge-ok',
        'Divergente': 'badge-divergente',
        'Somente Fornecedor': 'badge-somente-f',
        'Somente Wintour': 'badge-somente-w',
    };
    return `<span class="badge ${map[status] || ''}">${esc(status)}</span>`;
}

function fmt(v) {
    if (v === '' || v === null || v === undefined) return '';
    if (typeof v === 'number') return v.toFixed(2);
    return esc(String(v));
}

function esc(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}

// ── Filtros ──
document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
        filtroAtual = chip.dataset.filter;
        setActiveChip(filtroAtual);
        renderTabela();
    });
});

function setActiveChip(filter) {
    document.querySelectorAll('.chip').forEach(c => {
        c.classList.toggle('active', c.dataset.filter === filter);
        // Remove default active class for "todos"
        if (c.dataset.filter === 'todos') {
            c.classList.toggle('chip-active', filter === 'todos');
        }
    });
}

// ── Download ──
btnDownload.addEventListener('click', () => {
    window.location.href = '/api/download';
});

// ── Home (scroll to top) ──
document.getElementById('btnHome').addEventListener('click', (e) => {
    e.preventDefault();
    document.getElementById('mainContent').scrollTo({ top: 0, behavior: 'smooth' });
});

// ── Chat toggle (abre/fecha com mesmo botão) ──
btnChatToggle.addEventListener('click', () => {
    const isOpen = chatPanel.classList.contains('open');
    toggleChat(!isOpen);
});


function toggleChat(open) {
    chatPanel.classList.toggle('open', open);
    // Muda texto do botão
    const label = btnChatToggle.querySelector('span');
    if (label) label.textContent = open ? 'Fechar Chat' : 'Chat IA';
    if (open) chatInput.focus();
}

// ── Chat send ──
btnChatSend.addEventListener('click', sendChat);
chatInput.addEventListener('keydown', e => { if (e.key === 'Enter') sendChat(); });

async function sendChat() {
    const msg = chatInput.value.trim();
    if (!msg) return;

    appendMsg('user', msg);
    chatInput.value = '';

    // Typing indicator
    const typing = document.createElement('div');
    typing.className = 'chat-typing';
    typing.innerHTML = '<span></span><span></span><span></span>';
    chatMessages.appendChild(typing);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mensagem: msg }),
        });
        const data = await res.json();
        typing.remove();
        appendMsg('assistant', data.resposta);
    } catch (err) {
        typing.remove();
        appendMsg('assistant', 'Erro ao enviar mensagem: ' + err.message);
    }
}

function appendMsg(role, text) {
    // Remove welcome message
    const welcome = chatMessages.querySelector('.chat-welcome');
    if (welcome) welcome.remove();

    const div = document.createElement('div');
    div.className = `chat-msg chat-msg-${role}`;
    div.textContent = text;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}
