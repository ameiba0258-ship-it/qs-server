/**
 * 商家 POI 信息查询工具 — 高德地图
 */
const API_BASE = '';
const MUNICIPALITIES = ['北京市', '天津市', '上海市', '重庆市'];

const state = {
    config: { provider: 'amap', api_configured: false, max_results: 100, page_size: 20 },
    regions: { provinces: [] },
    poiTypes: [],
    filters: { keyword: '', province: '', city: '', poi_type: '' },
    results: { total: 0, page: 1, page_size: 20, data: [] },
    loading: false,
    batch: { task_id: null, status: '', progress: 0, total: 0, count: 0 },
    batchPolling: null,
    lastCompletedTaskId: null,
    lastCompletedCount: 0,
};

const $ = (id) => document.getElementById(id);

// --- Init ---
async function init() {
    await Promise.all([loadConfig(), loadRegions(), loadPoiTypes()]);
    checkAuth();
    setupListeners();
    updatePoiTypeSelect();
    setupMobile();
}

async function loadConfig() {
    try {
        const res = await fetch(`${API_BASE}/api/config`);
        Object.assign(state.config, await res.json());
        updateBadge();
    } catch (e) { console.error('loadConfig:', e); }
}

async function loadRegions() {
    try {
        const res = await fetch(`${API_BASE}/api/regions`);
        state.regions = await res.json();
        populateSelects();
    } catch (e) { console.error('loadRegions:', e); }
}

async function loadPoiTypes() {
    try {
        const res = await fetch(`${API_BASE}/api/poi-types`);
        const data = await res.json();
        state.poiTypes = data.poi_types || [];
    } catch (e) { console.error('loadPoiTypes:', e); }
}

// --- UI ---
function updateBadge() {
    const badge = $('apiBadge');
    const conf = state.config.api_configured || {};
    const currentProvider = ($('filterProvider')?.value) || 'amap';
    if (conf[currentProvider]) {
        const labels = { amap: '高德', baidumap: '百度', tencentmap: '腾讯' };
        badge.textContent = `${labels[currentProvider] || ''} API 已配置`;
        badge.className = 'api-badge configured';
    } else {
        const labels = { amap: '高德', baidumap: '百度', tencentmap: '腾讯' };
        badge.textContent = `${labels[currentProvider] || ''} 未配置 API`;
        badge.className = 'api-badge unconfigured';
    }
}

// Listen for provider switch to update badge
document.addEventListener('change', function(e) {
    if (e.target && e.target.id === 'filterProvider') {
        updateBadge();
    }
});

function populateSelects() {
    const provHtml = '<option value="">省份</option>' +
        state.regions.provinces.map(p => `<option value="${p.name}">${p.name}</option>`).join('');
    $('filterProvince').innerHTML = provHtml;
    $('filterCity').innerHTML = '<option value="">城市</option>';
    $('filterDistrict').innerHTML = '<option value="">区县</option>';
}

function updatePoiTypeSelect() {
    $('filterPoiType').innerHTML = state.poiTypes.map(t =>
        `<option value="${t.code}">${t.name}</option>`
    ).join('');
}

function updateCityOptions() {
    const sel = $('filterCity');
    const distSel = $('filterDistrict');
    const provinceName = $('filterProvince').value;
    
    // Default options
    sel.innerHTML = '<option value="">城市</option>';
    distSel.innerHTML = '<option value="">区县</option>';
    
    if (!provinceName) return;
    const p = state.regions.provinces.find(x => x.name === provinceName);
    if (!p || !p.cities) return;
    
    if (MUNICIPALITIES.includes(provinceName)) {
        // Municipality: cities ARE districts, move them to district level
        sel.innerHTML = '<option value="' + provinceName + '">' + provinceName + '</option>';
        distSel.innerHTML = '<option value="">区县</option>' +
            p.cities.map(c => `<option value="${c}">${c}</option>`).join('');
    } else {
        // Regular province: show cities normally
        sel.innerHTML = '<option value="">城市</option>' +
            p.cities.map(c => `<option value="${c}">${c}</option>`).join('');
    }
}

// --- Search ---
async function doSearch(page) {
    const keyword = $('filterKeyword').value.trim();
    if (!keyword) { showToast('请输入关键词（商家名称或品类）', 'error'); return; }

    state.loading = true;
    $('btnSearch').disabled = true;
    $('btnSearch').innerHTML = '<span class="spinner"></span> 搜索中...';

    // Collect additional keywords
    const kwText = $('filterKeywords')?.value.trim() || '';
    const extraKeywords = kwText ? kwText.split('\n').map(s => s.trim()).filter(s => s.length > 0) : [];

    const district = document.getElementById('filterDistrict')?.value || '';
    const params = {
        provider: 'all',
        keyword: keyword,
        keywords: extraKeywords,
        province: $('filterProvince').value,
        city: $('filterCity').value,
        district: district,
        industry: $('filterPoiType').value,
        reg_capital_min: null, reg_capital_max: null,
        reg_date_start: '', reg_date_end: '',
        page: page || 1, page_size: 20,
    };

    try {
        const res = await fetch(`${API_BASE}/api/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (!data.success) throw new Error(data.error || '搜索失败');

        state.results = {
            total: data.total, page: data.page || params.page,
            page_size: data.page_size || 20, data: data.data || [],
        };
        renderResults();
        renderPagination();
        updateHeader();
    } catch (e) {
        showToast('搜索出错: ' + e.message, 'error');
        state.results = { total: 0, page: 1, page_size: 20, data: [] };
        renderResults();
        renderPagination();
        updateHeader();
    } finally {
        state.loading = false;
        $('btnSearch').disabled = false;
        $('btnSearch').innerHTML = '🔍 搜索';
    }
}

function goToPage(page) { doSearch(page); }

function resetFilters() {
    $('filterKeyword').value = '';
    $('filterProvince').value = '';
    updateCityOptions();
    $('filterCity').value = '';
    $('filterPoiType').value = '';
    doSearch(1);
}

// --- Results ---
function renderResults() {
    const tbody = $('resultsBody');
    const empty = $('emptyState');
    const actions = $('resultActions');

    if (!state.results.data || state.results.data.length === 0) {
        tbody.innerHTML = '';
        empty.style.display = 'block';
        if (actions) actions.style.display = 'none';
        return;
    }
    empty.style.display = 'none';
    if (actions) actions.style.display = 'flex';

    let filtered = state.results.data.filter(item => item.mobile_phone);
    tbody.innerHTML = filtered.map((item, i) => `
        <tr>
            <td title="${esc(item.company_name)}"><strong>${esc(item.company_name)}</strong></td>
            <td title="${esc(item.industry)}">${esc(item.industry) || '-'}</td>
            <td title="${esc(item.mobile_phone || '')}" style="color:${item.mobile_phone ? 'var(--success)' : 'var(--gray-400)'};font-weight:${item.mobile_phone ? '600' : '400'}">
                ${item.mobile_phone ? esc(item.mobile_phone) : '-'}
            </td>
            <td title="${esc(item.landline_phone || '')}" style="color:${item.landline_phone ? 'inherit' : 'var(--gray-400)'}">
                ${item.landline_phone ? esc(item.landline_phone) : '-'}
            </td>
            <td title="${esc(item.address)}">${esc(item.address) || '-'}</td>
            <td>${esc(item.city) || '-'}</td>
            <td>${esc(item.district) || '-'}</td>
            <td>${esc(item.province) || '-'}</td>
        </tr>
    `).join('');
}

function renderPagination() {
    const { total, page, page_size } = state.results;
    const totalPages = Math.max(1, Math.ceil(total / (page_size || 1)));
    const container = $('pagination');
    if (total === 0) { container.innerHTML = ''; return; }

    let html = `<button class="page-btn" onclick="goToPage(${page - 1})" ${page <= 1 ? 'disabled' : ''}>‹</button>`;
    const start = Math.max(1, page - 2);
    const end = Math.min(totalPages, page + 2);
    if (start > 1) {
        html += `<button class="page-btn" onclick="goToPage(1)">1</button>`;
        if (start > 2) html += `<span class="page-info">...</span>`;
    }
    for (let i = start; i <= end; i++)
        html += `<button class="page-btn ${i === page ? 'active' : ''}" onclick="goToPage(${i})">${i}</button>`;
    if (end < totalPages) {
        if (end < totalPages - 1) html += `<span class="page-info">...</span>`;
        html += `<button class="page-btn" onclick="goToPage(${totalPages})">${totalPages}</button>`;
    }
    html += `<button class="page-btn" onclick="goToPage(${page + 1})" ${page >= totalPages ? 'disabled' : ''}>›</button>`;
    container.innerHTML = html;
}

function updateHeader() {
    const { total, page, page_size, data } = state.results;
    const start = data.length > 0 ? (page - 1) * page_size + 1 : 0;
    const end = Math.min(page * page_size, total);
    let info = total > 0
        ? `共 <strong>${total.toLocaleString()}</strong> 条，显示第 ${start}-${end} 条`
        : '暂无数据';
    $('resultsInfo').innerHTML = info;
}

// --- Export Functions ---
function exportCSV() {
    let data = state.results.data;
    if (!data || data.length === 0) { showToast('没有数据可导出', 'error'); return; }
    data = data.filter(item => item.mobile_phone);
    if (data.length === 0) { showToast('没有有手机号的数据', 'error'); return; }

    const headers = ['商家名称', '经营类型', '手机号', '座机', '地址', '城市', '区县', '省份'];
    const rows = data.map(item => [
        item.company_name || '',
        item.industry || '',
        item.mobile_phone || '',
        item.landline_phone || '',
        item.address || '',
        item.city || '',
        item.district || '',
        item.province || '',
    ]);

    let csv = '\uFEFF'; // BOM so Excel opens UTF-8 correctly
    csv += headers.join(',') + '\n';
    for (const row of rows) {
        csv += row.map(v => `"${(v || '').replace(/"/g, '""')}"`).join(',') + '\n';
    }

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const keyword = $('filterKeyword').value.trim() || '搜索结果';
    a.href = url;
    a.download = `${keyword}_${state.results.total}条.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast(`已下载 CSV (${data.length} 条)`, 'success');
}

function copyTable() {
    let data = state.results.data;
    if (!data || data.length === 0) { showToast('没有数据可复制', 'error'); return; }
    data = data.filter(item => item.mobile_phone);
    if (data.length === 0) { showToast('没有有手机号的数据', 'error'); return; }

    const headers = ['商家名称', '经营类型', '手机号', '座机', '地址', '城市', '区县', '省份'];
    const rows = data.map(item => [
        item.company_name || '',
        item.industry || '',
        item.mobile_phone || '',
        item.landline_phone || '',
        item.address || '',
        item.city || '',
        item.district || '',
        item.province || '',
    ]);

    // Tab-separated for easy paste into Excel
    let text = headers.join('\t') + '\n';
    for (const row of rows) {
        text += row.join('\t') + '\n';
    }

    navigator.clipboard.writeText(text).then(() => {
        showToast(`已复制 ${data.length} 条到剪贴板，可直接粘贴到 Excel`, 'success');
    }).catch(() => {
        // Fallback
        const ta = document.createElement('textarea');
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        showToast(`已复制 ${data.length} 条（兼容模式）`, 'success');
    });
}

// --- Batch ---
async function startBatchSearch() {
    if (!state.config.api_configured) {
        showToast('请先配置高德 API Key', 'error');
        return;
    }
    const keyword = $('filterKeyword').value.trim();
    if (!keyword) { showToast('请输入关键词', 'error'); return; }

    $('batchProgress').classList.add('show');
    $('batchProgressText').textContent = '准备中...';
    $('batchProgressFill').style.width = '0%';
    $('batchProgressFill').classList.remove('complete');
    $('btnBatch').disabled = true;
    $('btnBatch').innerHTML = '<span class="spinner"></span> 批量搜索中...';
    $('downloadActions').innerHTML = '';

    try {
        const kwTextB = $('filterKeywords')?.value.trim() || '';
        const extraKwB = kwTextB ? kwTextB.split('\n').map(s => s.trim()).filter(s => s.length > 0) : [];
        const bodyJson = JSON.stringify({
            provider: $('filterProvider')?.value || 'amap',
            keyword: keyword,
            keywords: extraKwB,
            province: $('filterProvince').value,
            city: $('filterCity').value,
            industry: $('filterPoiType').value,
            page_size: 25,
        });
        const res = await fetch(`${API_BASE}/api/batch-search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: bodyJson,
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const d = await res.json();
        state.batch.task_id = d.task_id;
        state.batch.status = 'running';
        pollProgress();
    } catch (e) {
        showToast('批量搜索失败: ' + e.message, 'error');
        resetBatch();
    }
}

function pollProgress() {
    if (state.batchPolling) clearInterval(state.batchPolling);
    state.batchPolling = setInterval(async () => {
        if (!state.batch.task_id) { clearInterval(state.batchPolling); return; }
        try {
            const res = await fetch(`${API_BASE}/api/batch-progress/${state.batch.task_id}`);
            if (!res.ok) throw new Error('gone');
            const d = await res.json();
            state.batch.status = d.status;
            state.batch.progress = d.progress || 0;
            state.batch.count = d.count || 0;
            const total = d.total || d.progress || 1;
            const pct = Math.min(100, Math.round((d.progress / total) * 100));
            const progressMsg = d.progress_text || `已获取 ${d.count || 0} 条${d.total ? ` / 共 ${d.total} 条` : ''}`;
            $('batchProgressText').textContent = progressMsg;
            $('batchProgressFill').style.width = pct + '%';

            if (d.status === 'completed') {
                clearInterval(state.batchPolling);
                state.batchPolling = null;
                $('batchProgressFill').classList.add('complete');
                $('batchProgressText').textContent = `✅ 已完成！共获取 ${d.count} 条数据`;
                const _tid = state.batch.task_id;  // save before reset
                resetBatch();
                showDownloads(d.count, _tid);
            } else if (d.status === 'error') {
                clearInterval(state.batchPolling);
                state.batchPolling = null;
                showToast('批量搜索出错: ' + (d.error || '未知错误'), 'error');
                resetBatch();
            }
        } catch (e) { /* keep polling */ }
    }, 1000);
}

function showDownloads(count, taskId) {
    if (!taskId) return;
    $('downloadActions').innerHTML = `
        <button class="btn btn-success btn-sm" onclick="downloadFile('${taskId}', 'xlsx')">📊 Excel (${count}条)</button>
        <button class="btn btn-outline btn-sm" onclick="downloadFile('${taskId}', 'csv')">📄 CSV</button>
        <button class="btn btn-outline btn-sm" onclick="downloadFile('${taskId}', 'json')">📋 JSON</button>
    `;
}

function downloadFile(taskId, fmt) {
    if (!taskId) return;
    window.open(`${API_BASE}/api/download/${taskId}?fmt=${fmt}`, '_blank');
    showToast('正在下载...', 'info');
}

function resetBatch() {
    $('btnBatch').disabled = false;
    $('btnBatch').innerHTML = '📥 批量搜索 <span style="font-size:11px;opacity:0.8">(最高100条)</span>';
    state.batch = { task_id: null, status: '', progress: 0, total: 0, count: 0 };
    if (state.batchPolling) { clearInterval(state.batchPolling); state.batchPolling = null; }
}

// --- Config ---
function showConfigModal() {
    $('configModal').classList.add('active');
    $('configAmapKey').value = '';
    $('configBaiduKey').value = '';
    if ($('configTencentKey')) $('configTencentKey').value = '';
    const conf = state.config.api_configured || {};
    const cur = ($('filterProvider')?.value) || 'amap';
    const labels = { amap: '高德地图', baidumap: '百度地图' };

    // Add/update helper text
    let helper = document.getElementById('configHelpText');
    if (!helper) {
        helper = document.createElement('p');
        helper.id = 'configHelpText';
        helper.style.cssText = 'font-size:13px;padding:8px 12px;border-radius:4px;margin-bottom:12px;font-weight:500';
        document.querySelector('#configModal .modal').insertBefore(helper, document.querySelector('#configModal .modal h2').nextSibling);
    }
    if (conf[cur]) {
        helper.textContent = '✅ 当前数据源「' + labels[cur] + '」API 已配置';
        helper.style.background = '#ecfdf5';
    } else {
        helper.textContent = '⚠ 当前数据源为「' + labels[cur] + '」，请填写下方对应的 API Key';
        helper.style.background = '#fffbeb';
    }

    // Update status indicators
    const amapStat = document.getElementById('amapStatus');
    const baiduStat = document.getElementById('baiduStatus');
    const tencentStat = document.getElementById('tencentStatus');
    if (tencentStat) {
        tencentStat.textContent = conf.tencentmap ? '✅ 已配置' : '❌ 未配置';
        tencentStat.style.color = conf.tencentmap ? 'var(--success)' : 'var(--danger)';
    }
    if (amapStat) {
        amapStat.textContent = conf.amap ? '✅ 已配置' : '❌ 未配置';
        amapStat.style.color = conf.amap ? 'var(--success)' : 'var(--danger)';
    }
    if (baiduStat) {
        baiduStat.textContent = conf.baidumap ? '✅ 已配置' : '❌ 未配置';
        baiduStat.style.color = conf.baidumap ? 'var(--success)' : 'var(--danger)';
    }

    // Highlight the current provider's field
    const amapGroup = $('configAmapKey').closest('.form-group');
    const baiduGroup = $('configBaiduKey').closest('.form-group');
    if (amapGroup) { amapGroup.style.border = 'none'; amapGroup.style.padding = ''; }
    if (baiduGroup) { baiduGroup.style.border = 'none'; baiduGroup.style.padding = ''; }

    if (cur === 'baidumap') {
        if (baiduGroup) { baiduGroup.style.border = '2px solid var(--success)'; baiduGroup.style.borderRadius = 'var(--radius)'; baiduGroup.style.padding = '12px'; }
        setTimeout(() => $('configBaiduKey')?.focus(), 100);
    } else if (cur === 'tencentmap') {
        const tencentGroup = $('configTencentKey').closest('.form-group');
        if (tencentGroup) { tencentGroup.style.border = '2px solid var(--success)'; tencentGroup.style.borderRadius = 'var(--radius)'; tencentGroup.style.padding = '12px'; }
        setTimeout(() => $('configTencentKey')?.focus(), 100);
    } else {
        if (amapGroup) { amapGroup.style.border = '2px solid var(--success)'; amapGroup.style.borderRadius = 'var(--radius)'; amapGroup.style.padding = '12px'; }
        setTimeout(() => $('configAmapKey')?.focus(), 100);
    }
}

function hideConfigModal() { $('configModal').classList.remove('active'); }

async function saveConfig() {
    const amapKey = $('configAmapKey').value.trim();
    const baiduKey = $('configBaiduKey').value.trim();
    const tencentKey = $('configTencentKey')?.value.trim();
    if (!amapKey && !baiduKey && !tencentKey) { showToast('请输入至少一个 API Key', 'error'); return; }
    const body = {};
    if (amapKey) body.amap_api_key = amapKey;
    if (baiduKey) body.baidu_api_key = baiduKey;
    if (tencentKey) body.tencent_api_key = tencentKey;
    try {
        const res = await fetch(`${API_BASE}/api/config/save`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!res.ok) throw new Error('保存失败');
        showToast('API Key 已保存并生效', 'success');
        hideConfigModal();
        await loadConfig();
    } catch (e) {
        showToast('保存失败: ' + e.message, 'error');
    }
}

// --- Toast ---
function showToast(msg, type = 'info') {
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.textContent = msg;
    $('toastContainer').appendChild(el);
    setTimeout(() => {
        el.style.opacity = '0';
        el.style.transition = 'opacity 0.3s';
        setTimeout(() => el.remove(), 300);
    }, 3000);
}

// --- Utils ---
function esc(s) { if (!s) return ''; const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

// --- Auth ---
async function checkAuth() {
    const token = localStorage.getItem('qs_token');
    const menuWrap = document.getElementById('userMenuWrap');
    const loginLink = document.getElementById('loginLink');
    if (!menuWrap) return;
    
    if (!token) {
        window.location.href = '/';
        return;
    }
    try {
        const res = await fetch('/api/auth/profile', {
            headers: {'Authorization': 'Bearer ' + token}
        });
        const data = await res.json();
        if (data.success) {
            const u = data.user;
            const tierLabels = {free:'免费版',premium:'会员版',enterprise:'企业版',admin:'管理员'};
            
            // Populate dropdown
            document.getElementById('dropdownEmail').textContent = u.username;
            document.getElementById('dropdownTier').textContent = tierLabels[u.tier] || u.tier;
                        document.getElementById('userDisplayName').textContent = u.username.split('@')[0];
            
            // Load avatar
            const avatarEl = document.getElementById('userAvatarSmall');
            if (avatarEl && u.id) {
                const img = new Image();
                img.onload = function() { avatarEl.innerHTML = ''; avatarEl.appendChild(img); };
                img.src = '/api/avatar/' + u.id + '?t=' + Date.now();
                img.style.cssText = 'width:24px;height:24px;border-radius:6px;object-fit:cover';
            }
            
            const used = u.today_searches || 0;
            const limit = u.daily_limit || 50;
            const remaining = limit - used;
            const usageEl = document.getElementById('dropdownUsage');
            if (limit > 9999) {
                usageEl.textContent = used + ' / ∞ 次';
            } else {
                usageEl.textContent = used + ' / ' + limit + ' 次';
                if (remaining <= 10) usageEl.style.color = '#dc2626';
                else usageEl.style.color = '#059669';
            }
            
            // Show menu, hide login
            menuWrap.style.display = 'inline-flex';
            if (loginLink) loginLink.style.display = 'none';
        } else {
            localStorage.removeItem('qs_token');
            window.location.href = '/';
        }
    } catch(e) {
        window.location.href = '/';
    }
}

// === User Dropdown Toggle ===
let dropOpen = false;
function toggleDropdown(e) {
    if (e) e.stopPropagation();
    const dd = document.getElementById('userDropdown');
    const trigger = document.getElementById('userTrigger');
    dropOpen = !dropOpen;
    dd.classList.toggle('open', dropOpen);
    trigger.classList.toggle('active', dropOpen);
}

// Close dropdown on click outside
document.addEventListener('click', function(e) {
    if (dropOpen) {
        const wrap = document.getElementById('userMenuWrap');
        if (wrap && !wrap.contains(e.target)) {
            const dd = document.getElementById('userDropdown');
            const trigger = document.getElementById('userTrigger');
            dropOpen = false;
            dd.classList.remove('open');
            trigger.classList.remove('active');
        }
    }
});

function logout() {
    localStorage.removeItem('qs_token');
    localStorage.removeItem('qs_user');
    window.location.href = '/';
}

// --- Listeners ---
function setupListeners() {
    $('filterProvince').addEventListener('change', function () {
        updateCityOptions();
        $('filterCity').value = '';
    });
    $('filterKeyword').addEventListener('keydown', function (e) {
        if (e.key === 'Enter') doSearch();
    });
}

function exportAllResults() {
    // 一键导出全部结果
    const keyword = document.getElementById('filterKeyword').value.trim();
    if (!keyword) { showToast('请先输入关键词', 'error'); return; }
    if (!state.config.api_configured) { showToast('请先配置高德 API Key', 'error'); return; }

    // 展开并滚动到进度区域
    const prog = document.getElementById('batchProgress');
    prog.classList.add('show');
    document.getElementById('batchProgressText').textContent = '正在拉取全部数据（深度搜索模式，可能较慢）...';
    document.getElementById('batchProgressFill').style.width = '0%';
    document.getElementById('batchProgressFill').classList.remove('complete');
    document.getElementById('downloadActions').innerHTML = '';
    prog.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    // 调用批量搜索
    startBatchSearch();
}

// --- Nearby Search ---
let nearbyMode = false;

function toggleNearbySection() {
    const body = document.getElementById('nearbyBody');
    const arrow = document.getElementById('nearbyArrow');
    if (!body) return;
    const isOpen = body.style.display !== 'none';
    body.style.display = isOpen ? 'none' : 'block';
    if (arrow) arrow.classList.toggle('open', !isOpen);
}

function setDistance(val) {
    document.querySelectorAll('.dist-btn').forEach(b => b.classList.remove('active'));
    document.querySelector('.dist-btn[data-dist="' + val + '"]')?.classList.add('active');
    document.getElementById('nearbyRadius').value = val;
}

let nearbyMode = false;
function toggleNearby() {
    // Legacy - handled by switchSearchMode already
    toggleNearbySection();
}

async function doNearbySearch() {
    const address = document.getElementById('nearbyAddress').value.trim();
    const keyword = document.getElementById('nearbyKeyword').value.trim();
    const radius = parseInt(document.getElementById('nearbyRadius').value) || 1000;
    
    if (!address) { showToast('请输入地址或小区名称', 'error'); return; }
    if (!keyword) { showToast('请输入关键词', 'error'); return; }
    
    const btn = document.getElementById('btnNearbySearch');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> 解析地址中...';
    
    try {
        // Step 1: Geocode address
        const geoRes = await fetch('/api/geocode?address=' + encodeURIComponent(address));
        const geoData = await geoRes.json();
        if (!geoData.success) {
            showToast('地址解析失败: ' + (geoData.error || ''), 'error');
            btn.disabled = false; btn.innerHTML = '📍 开始搜索附近';
            return;
        }
        
        btn.innerHTML = '<span class="spinner"></span> 搜索周边商家...';
        
        // Step 2: Search nearby
        const provider = 'amap'; // Nearby search uses default provider
        const searchRes = await fetch('/api/nearby-search', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                location: geoData.location,
                keyword: keyword,
                radius: parseInt(radius),
                provider: provider,
                page: 1,
                page_size: 20,
            })
        });
        const searchData = await searchRes.json();
        
        if (!searchData.success) {
            showToast('搜索失败: ' + (searchData.error || ''), 'error');
            btn.disabled = false; btn.innerHTML = '📍 开始搜索附近';
            return;
        }
        
        // Display results
        state.results = {
            total: searchData.total,
            page: 1,
            page_size: 20,
            data: searchData.data || [],
        };
        
        // Update header
        document.getElementById('currentSourceLabel').textContent = '📍 周边搜索';
        renderResults();
        renderPagination();
        updateHeader();
        
        showToast('✅ 找到 ' + searchData.total + ' 条附近商家', 'success');
        
    } catch(e) {
        showToast('请求失败: ' + e.message, 'error');
    }
    
    btn.disabled = false;
    btn.innerHTML = '📍 开始搜索附近';
}

// Override header display for nearby results
const origUpdateHeader = updateHeader;

function setupMobile() {
    // Mobile filter toggle
    const toggle = document.getElementById('filterToggleMobile');
    if (toggle) {
        toggle.addEventListener('click', function() {
            document.querySelector('.filter-section.collapsible')?.classList.toggle('open');
        });
    }
    // Card view header fix
    window.addEventListener('resize', function() {
        if (state.results.data && state.results.data.length > 0) renderResults();
    });
}

function toggleAdvanced() {
    const panel = document.getElementById('advPanel');
    const link = document.getElementById('advToggleLink');
    if (!panel) return;
    const isOpen = panel.classList.contains('open');
    panel.classList.toggle('open');
    if (link) link.textContent = isOpen ? '+ 多关键词搜索（每行一个）' : '− 收起高级筛选';
}


// === Email Export ===
function showEmailModal() {
    if (!state.lastCompletedTaskId) {
        showToast('请先进行批量搜索后再发送', 'error');
        return;
    }
    // Auto-fill saved email
    const saved = localStorage.getItem('qs_saved_email');
    if (saved) document.getElementById('emailTarget').value = saved;
    document.getElementById('emailExportInfo').textContent = 
        '发送 ' + state.lastCompletedCount + ' 条数据至您的邮箱';
    document.getElementById('emailModal').classList.add('active');
    document.getElementById('emailTarget').focus();
}

function closeEmailModal() {
    document.getElementById('emailModal').classList.remove('active');
}

async function sendToEmail() {
    const email = document.getElementById('emailTarget').value.trim().toLowerCase();
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        showToast('请输入有效的邮箱地址', 'error');
        return;
    }
    const taskId = state.lastCompletedTaskId;
    if (!taskId) {
        showToast('没有可发送的结果', 'error');
        closeEmailModal();
        return;
    }
    
    const btn = document.getElementById('emailSendBtn');
    btn.disabled = true;
    btn.textContent = '发送中...';
    
    try {
        const r = await fetch('/api/export-email', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + localStorage.getItem('qs_token')
            },
            body: JSON.stringify({ task_id: taskId, email: email })
        });
        const d = await r.json();
        if (d.success) {
            showToast('✅ ' + d.message, 'success');
            closeEmailModal();
        } else {
            showToast('❌ ' + (d.error || '发送失败'), 'error');
        }
    } catch(e) {
        showToast('❌ 网络错误: ' + e.message, 'error');
    }
    
    btn.disabled = false;
    btn.textContent = '发送';
}


document.addEventListener('DOMContentLoaded', init);
