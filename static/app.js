// État global
const state = {
  token: localStorage.getItem('token') || null,
  user: null,
  patients: [],
  medecins: [],
  rendezvous: [],
};

// ===== UTILITAIRES =====

function $(selector) { return document.querySelector(selector); }
function $$(selector) { return document.querySelectorAll(selector); }

async function api(method, path, body = null, isForm = false) {
  const headers = {};
  if (state.token) headers['Authorization'] = `Bearer ${state.token}`;
  let bodyData = null;
  if (body) {
    if (isForm) {
      bodyData = new URLSearchParams(body).toString();
      headers['Content-Type'] = 'application/x-www-form-urlencoded';
    } else {
      bodyData = JSON.stringify(body);
      headers['Content-Type'] = 'application/json';
    }
  }
  const res = await fetch(path, { method, headers, body: bodyData });
  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) {
    const detail = data?.detail || `Erreur ${res.status}`;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return data;
}

function toast(message, type = 'success') {
  const colors = {
    success: 'bg-emerald-50 border-emerald-200 text-emerald-800',
    error:   'bg-red-50 border-red-200 text-red-800',
    info:    'bg-blue-50 border-blue-200 text-blue-800',
  };
  const icons = {
    success: '<svg class="w-5 h-5 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>',
    error:   '<svg class="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>',
    info:    '<svg class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>',
  };
  const el = document.createElement('div');
  el.className = `toast-enter flex items-start gap-3 px-4 py-3 rounded-xl border shadow-lg max-w-sm ${colors[type]}`;
  el.innerHTML = `${icons[type]}<p class="text-sm font-medium flex-1">${message}</p>`;
  $('#toast-container').appendChild(el);
  setTimeout(() => {
    el.style.transition = 'opacity 0.3s';
    el.style.opacity = '0';
    setTimeout(() => el.remove(), 300);
  }, 3500);
}

function formatDateTime(iso) {
  const d = new Date(iso);
  return d.toLocaleString('fr-CA', {
    weekday: 'short', day: '2-digit', month: 'short',
    hour: '2-digit', minute: '2-digit',
  });
}

const STATUT_STYLE = {
  prevu:    { label: 'Prévu',     classes: 'bg-blue-100 text-blue-700' },
  confirme: { label: 'Confirmé',  classes: 'bg-emerald-100 text-emerald-700' },
  annule:   { label: 'Annulé',    classes: 'bg-red-100 text-red-700' },
  complete: { label: 'Complété',  classes: 'bg-slate-200 text-slate-700' },
};

// ===== AUTHENTIFICATION =====

async function login(email, password) {
  const data = await api('POST', '/auth/login', { username: email, password }, true);
  state.token = data.access_token;
  localStorage.setItem('token', state.token);
  await loadUser();
  showApp();
  navigate('dashboard');
}

async function register(email, password, role) {
  await api('POST', '/auth/register', { email, password, role });
  toast('Compte créé, connectez-vous', 'success');
  $('#tab-login').click();
}

async function loadUser() {
  try {
    state.user = await api('GET', '/auth/me');
    $('#user-email').textContent = state.user.email;
    $('#user-role').textContent = state.user.role === 'admin' ? 'Administrateur' : 'Médecin';
    $('#user-avatar').textContent = state.user.email[0].toUpperCase();
  } catch (e) {
    logout();
  }
}

function logout() {
  state.token = null;
  state.user = null;
  localStorage.removeItem('token');
  $('#app-screen').classList.add('hidden');
  $('#login-screen').classList.remove('hidden');
}

function showApp() {
  $('#login-screen').classList.add('hidden');
  $('#app-screen').classList.remove('hidden');
}

// ===== NAVIGATION =====

function navigate(page) {
  $$('section[id^="page-"]').forEach(s => s.classList.add('hidden'));
  $(`#page-${page}`).classList.remove('hidden');
  $$('.nav-link').forEach(b => b.classList.remove('active'));
  $(`.nav-link[data-page="${page}"]`)?.classList.add('active');

  if (page === 'dashboard') loadDashboard();
  if (page === 'patients') loadPatients();
  if (page === 'medecins') loadMedecins();
  if (page === 'rendezvous') loadRendezVous();
  if (page === 'creneaux') loadCreneauxPage();
}

// ===== TABLEAU DE BORD =====

async function loadDashboard() {
  try {
    const [patients, medecins, rdv] = await Promise.all([
      api('GET', '/patients'),
      api('GET', '/medecins'),
      api('GET', '/rendezvous'),
    ]);
    state.patients = patients;
    state.medecins = medecins;
    state.rendezvous = rdv;

    $('#stat-patients').textContent = patients.length;
    $('#stat-medecins').textContent = medecins.length;
    $('#stat-rdv').textContent = rdv.length;

    const upcoming = rdv
      .filter(r => r.statut !== 'annule' && new Date(r.date_heure) >= new Date())
      .sort((a, b) => new Date(a.date_heure) - new Date(b.date_heure))
      .slice(0, 5);

    const container = $('#dashboard-upcoming');
    if (upcoming.length === 0) {
      container.innerHTML = '<p class="text-sm text-slate-400 italic">Aucun rendez-vous à venir</p>';
    } else {
      container.innerHTML = upcoming.map(r => {
        const p = patients.find(x => x.id === r.patient_id);
        const m = medecins.find(x => x.id === r.medecin_id);
        const statut = STATUT_STYLE[r.statut];
        return `
          <div class="flex items-center justify-between p-3 rounded-lg hover:bg-slate-50 transition">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-primary-100 to-primary-500 flex items-center justify-center text-white font-semibold text-sm">
                ${p ? (p.prenom[0] + p.nom[0]) : '?'}
              </div>
              <div>
                <p class="text-sm font-semibold text-slate-900">${p ? p.prenom + ' ' + p.nom : 'Patient inconnu'}</p>
                <p class="text-xs text-slate-500">Avec Dr ${m ? m.nom : '?'} — ${m?.specialite || ''}</p>
              </div>
            </div>
            <div class="text-right">
              <p class="text-sm font-medium text-slate-700">${formatDateTime(r.date_heure)}</p>
              <span class="inline-block text-xs px-2 py-0.5 rounded-full ${statut.classes} mt-0.5">${statut.label}</span>
            </div>
          </div>`;
      }).join('');
    }
  } catch (e) { toast(e.message, 'error'); }
}

// ===== PATIENTS =====

async function loadPatients() {
  try {
    state.patients = await api('GET', '/patients');
    const list = $('#patients-list');
    if (state.patients.length === 0) {
      list.innerHTML = emptyState('Aucun patient', 'Commencez par en créer un');
      return;
    }
    list.innerHTML = `
      <table class="w-full text-sm">
        <thead class="bg-slate-50 border-b border-slate-200">
          <tr>
            <th class="text-left px-6 py-3 font-semibold text-slate-700">Patient</th>
            <th class="text-left px-6 py-3 font-semibold text-slate-700">Âge</th>
            <th class="text-left px-6 py-3 font-semibold text-slate-700">RAMQ</th>
            <th class="px-6 py-3"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          ${state.patients.map(p => `
            <tr class="hover:bg-slate-50 transition">
              <td class="px-6 py-3">
                <div class="flex items-center gap-3">
                  <div class="w-9 h-9 rounded-full bg-gradient-to-br from-blue-100 to-blue-500 flex items-center justify-center text-white font-semibold text-xs">${p.prenom[0]}${p.nom[0]}</div>
                  <div>
                    <p class="font-semibold text-slate-900">${p.prenom} ${p.nom}</p>
                  </div>
                </div>
              </td>
              <td class="px-6 py-3 text-slate-600">${p.age} ans</td>
              <td class="px-6 py-3"><code class="text-xs font-mono bg-slate-100 px-2 py-0.5 rounded">${p.numero_ramq}</code></td>
              <td class="px-6 py-3 text-right">
                <button onclick="deletePatient(${p.id})" class="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded transition" title="Supprimer">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6M1 7h22M9 7V4a1 1 0 011-1h4a1 1 0 011 1v3"/></svg>
                </button>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>`;
  } catch (e) { toast(e.message, 'error'); }
}

async function deletePatient(id) {
  if (!confirm('Supprimer ce patient ? Tous ses rendez-vous seront aussi supprimés.')) return;
  try {
    await api('DELETE', `/patients/${id}`);
    toast('Patient supprimé', 'success');
    loadPatients();
  } catch (e) { toast(e.message, 'error'); }
}

// ===== MÉDECINS =====

async function loadMedecins() {
  try {
    state.medecins = await api('GET', '/medecins');
    const list = $('#medecins-list');
    if (state.medecins.length === 0) {
      list.innerHTML = emptyState('Aucun médecin', 'Commencez par en créer un');
      return;
    }
    list.innerHTML = `
      <table class="w-full text-sm">
        <thead class="bg-slate-50 border-b border-slate-200">
          <tr>
            <th class="text-left px-6 py-3 font-semibold text-slate-700">Médecin</th>
            <th class="text-left px-6 py-3 font-semibold text-slate-700">Spécialité</th>
            <th class="text-left px-6 py-3 font-semibold text-slate-700">Permis</th>
            <th class="px-6 py-3"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          ${state.medecins.map(m => `
            <tr class="hover:bg-slate-50 transition">
              <td class="px-6 py-3">
                <div class="flex items-center gap-3">
                  <div class="w-9 h-9 rounded-full bg-gradient-to-br from-emerald-100 to-emerald-500 flex items-center justify-center text-white font-semibold text-xs">${m.prenom[0]}${m.nom[0]}</div>
                  <p class="font-semibold text-slate-900">Dr ${m.prenom} ${m.nom}</p>
                </div>
              </td>
              <td class="px-6 py-3"><span class="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 text-xs font-medium">${m.specialite}</span></td>
              <td class="px-6 py-3"><code class="text-xs font-mono bg-slate-100 px-2 py-0.5 rounded">${m.numero_permis}</code></td>
              <td class="px-6 py-3 text-right">
                <button onclick="deleteMedecin(${m.id})" class="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded transition">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6M1 7h22M9 7V4a1 1 0 011-1h4a1 1 0 011 1v3"/></svg>
                </button>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>`;
  } catch (e) { toast(e.message, 'error'); }
}

async function deleteMedecin(id) {
  if (!confirm('Supprimer ce médecin ? Tous ses rendez-vous seront aussi supprimés.')) return;
  try {
    await api('DELETE', `/medecins/${id}`);
    toast('Médecin supprimé', 'success');
    loadMedecins();
  } catch (e) { toast(e.message, 'error'); }
}

// ===== RENDEZ-VOUS =====

async function loadRendezVous() {
  try {
    const [rdv, patients, medecins] = await Promise.all([
      api('GET', '/rendezvous'),
      api('GET', '/patients'),
      api('GET', '/medecins'),
    ]);
    state.rendezvous = rdv;
    state.patients = patients;
    state.medecins = medecins;
    const list = $('#rdv-list');
    if (rdv.length === 0) {
      list.innerHTML = emptyState('Aucun rendez-vous', 'Créez votre premier rendez-vous');
      return;
    }
    list.innerHTML = `
      <table class="w-full text-sm">
        <thead class="bg-slate-50 border-b border-slate-200">
          <tr>
            <th class="text-left px-6 py-3 font-semibold text-slate-700">Date et heure</th>
            <th class="text-left px-6 py-3 font-semibold text-slate-700">Patient</th>
            <th class="text-left px-6 py-3 font-semibold text-slate-700">Médecin</th>
            <th class="text-left px-6 py-3 font-semibold text-slate-700">Mode</th>
            <th class="text-left px-6 py-3 font-semibold text-slate-700">Statut</th>
            <th class="px-6 py-3"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          ${rdv.map(r => {
            const p = patients.find(x => x.id === r.patient_id);
            const m = medecins.find(x => x.id === r.medecin_id);
            const statut = STATUT_STYLE[r.statut];
            const modeIcon = r.mode === 'virtuel'
              ? '<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>'
              : '<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>';
            return `
              <tr class="hover:bg-slate-50 transition">
                <td class="px-6 py-3">
                  <p class="font-semibold text-slate-900">${formatDateTime(r.date_heure)}</p>
                  <p class="text-xs text-slate-500">${r.duree_minutes} min</p>
                </td>
                <td class="px-6 py-3 text-slate-700">${p ? p.prenom + ' ' + p.nom : '—'}</td>
                <td class="px-6 py-3 text-slate-700">Dr ${m ? m.nom : '—'}</td>
                <td class="px-6 py-3">
                  <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 text-xs font-medium">
                    ${modeIcon}
                    ${r.mode === 'virtuel' ? 'Virtuel' : 'En personne'}
                  </span>
                </td>
                <td class="px-6 py-3"><span class="px-2 py-0.5 rounded-full text-xs font-medium ${statut.classes}">${statut.label}</span></td>
                <td class="px-6 py-3 text-right">
                  ${r.statut !== 'annule' && r.statut !== 'complete' ? `
                    <button onclick="annulerRdv(${r.id})" class="text-xs text-slate-500 hover:text-red-600 mr-2">Annuler</button>
                  ` : ''}
                  <button onclick="deleteRdv(${r.id})" class="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded transition" title="Supprimer">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6M1 7h22M9 7V4a1 1 0 011-1h4a1 1 0 011 1v3"/></svg>
                  </button>
                </td>
              </tr>`;
          }).join('')}
        </tbody>
      </table>`;
  } catch (e) { toast(e.message, 'error'); }
}

async function annulerRdv(id) {
  const rdv = state.rendezvous.find(r => r.id === id);
  if (!rdv) return;
  if (!confirm('Annuler ce rendez-vous ?')) return;
  try {
    await api('PUT', `/rendezvous/${id}`, { ...rdv, statut: 'annule' });
    toast('Rendez-vous annulé', 'success');
    loadRendezVous();
  } catch (e) { toast(e.message, 'error'); }
}

async function deleteRdv(id) {
  if (!confirm('Supprimer définitivement ce rendez-vous ?')) return;
  try {
    await api('DELETE', `/rendezvous/${id}`);
    toast('Rendez-vous supprimé', 'success');
    loadRendezVous();
  } catch (e) { toast(e.message, 'error'); }
}

// ===== CRÉNEAUX =====

async function loadCreneauxPage() {
  try {
    state.medecins = await api('GET', '/medecins');
    const select = $('#creneaux-medecin');
    select.innerHTML = '<option value="">Choisir un médecin...</option>' +
      state.medecins.map(m => `<option value="${m.id}">Dr ${m.prenom} ${m.nom} — ${m.specialite}</option>`).join('');
    $('#creneaux-date').valueAsDate = new Date();
    $('#creneaux-result').innerHTML = '';
  } catch (e) { toast(e.message, 'error'); }
}

async function chercherCreneaux() {
  const medecinId = $('#creneaux-medecin').value;
  const jour = $('#creneaux-date').value;
  if (!medecinId || !jour) {
    $('#creneaux-result').innerHTML = '';
    return;
  }
  try {
    const data = await api('GET', `/medecins/${medecinId}/creneaux?jour=${jour}`);
    const container = $('#creneaux-result');
    if (data.creneaux_disponibles.length === 0) {
      container.innerHTML = `
        <div class="bg-white rounded-2xl p-12 border border-slate-200 shadow-sm text-center">
          <div class="inline-flex items-center justify-center w-12 h-12 rounded-full bg-slate-100 mb-3">
            <svg class="w-6 h-6 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728L5.636 5.636m12.728 12.728L18.364 5.636M5.636 18.364l12.728-12.728"/></svg>
          </div>
          <p class="font-semibold text-slate-900">Aucun créneau disponible</p>
          <p class="text-sm text-slate-500 mt-1">Le médecin n'est pas disponible ce jour-là (week-end ou journée complète).</p>
        </div>`;
      return;
    }
    container.innerHTML = `
      <div class="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
        <p class="text-sm text-slate-600 mb-4">${data.creneaux_disponibles.length} créneaux disponibles le ${data.date}</p>
        <div class="grid grid-cols-3 sm:grid-cols-5 md:grid-cols-6 gap-2">
          ${data.creneaux_disponibles.map(h => `
            <button class="px-3 py-2 rounded-lg bg-gradient-to-br from-primary-50 to-primary-100 hover:from-primary-100 hover:to-primary-500 hover:text-white text-primary-700 font-semibold text-sm transition shadow-sm">
              ${h}
            </button>
          `).join('')}
        </div>
      </div>`;
  } catch (e) { toast(e.message, 'error'); }
}

// ===== HELPERS UI =====

function emptyState(title, subtitle) {
  return `
    <div class="p-12 text-center">
      <div class="inline-flex items-center justify-center w-12 h-12 rounded-full bg-slate-100 mb-3">
        <svg class="w-6 h-6 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
      </div>
      <p class="font-semibold text-slate-900">${title}</p>
      <p class="text-sm text-slate-500 mt-1">${subtitle}</p>
    </div>`;
}

function openModal(id) { $(id).classList.remove('hidden'); }
function closeModal(id) { $(id).classList.add('hidden'); }

function fillRdvSelects() {
  $('select[name="patient_id"]').innerHTML =
    '<option value="">Choisir un patient...</option>' +
    state.patients.map(p => `<option value="${p.id}">${p.prenom} ${p.nom}</option>`).join('');
  $('select[name="medecin_id"]').innerHTML =
    '<option value="">Choisir un médecin...</option>' +
    state.medecins.map(m => `<option value="${m.id}">Dr ${m.prenom} ${m.nom} — ${m.specialite}</option>`).join('');
}

// ===== ÉVÉNEMENTS =====

document.addEventListener('DOMContentLoaded', () => {
  // Onglets login/register
  $('#tab-login').addEventListener('click', () => {
    $('#tab-login').classList.add('bg-white', 'shadow-sm', 'text-slate-900');
    $('#tab-login').classList.remove('text-slate-600');
    $('#tab-register').classList.remove('bg-white', 'shadow-sm', 'text-slate-900');
    $('#tab-register').classList.add('text-slate-600');
    $('#form-login').classList.remove('hidden');
    $('#form-register').classList.add('hidden');
  });
  $('#tab-register').addEventListener('click', () => {
    $('#tab-register').classList.add('bg-white', 'shadow-sm', 'text-slate-900');
    $('#tab-register').classList.remove('text-slate-600');
    $('#tab-login').classList.remove('bg-white', 'shadow-sm', 'text-slate-900');
    $('#tab-login').classList.add('text-slate-600');
    $('#form-register').classList.remove('hidden');
    $('#form-login').classList.add('hidden');
  });

  // Soumissions login/register
  $('#form-login').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      await login(fd.get('email'), fd.get('password'));
      toast(`Bienvenue ${state.user.email}`, 'success');
    } catch (err) { toast(err.message, 'error'); }
  });
  $('#form-register').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      await register(fd.get('email'), fd.get('password'), fd.get('role'));
    } catch (err) { toast(err.message, 'error'); }
  });

  // Logout
  $('#btn-logout').addEventListener('click', () => {
    logout();
    toast('Déconnecté', 'info');
  });

  // Navigation
  $$('.nav-link').forEach(b => b.addEventListener('click', () => navigate(b.dataset.page)));

  // Boutons nouveau
  $('#btn-new-patient').addEventListener('click', () => openModal('#modal-patient'));
  $('#btn-new-medecin').addEventListener('click', () => openModal('#modal-medecin'));
  $('#btn-new-rdv').addEventListener('click', () => {
    fillRdvSelects();
    openModal('#modal-rdv');
  });

  // Fermeture des modales
  $$('.modal-close').forEach(b => b.addEventListener('click', () => {
    $$('#modal-patient, #modal-medecin, #modal-rdv').forEach(m => m.classList.add('hidden'));
  }));

  // Soumissions des formulaires
  $('#form-patient').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const data = {
      nom: fd.get('nom'),
      prenom: fd.get('prenom'),
      age: parseInt(fd.get('age')),
      numero_ramq: fd.get('numero_ramq').toUpperCase(),
    };
    try {
      await api('POST', '/patients', data);
      toast('Patient créé', 'success');
      e.target.reset();
      closeModal('#modal-patient');
      loadPatients();
    } catch (err) { toast(err.message, 'error'); }
  });

  $('#form-medecin').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const data = {
      nom: fd.get('nom'),
      prenom: fd.get('prenom'),
      specialite: fd.get('specialite'),
      numero_permis: fd.get('numero_permis'),
    };
    try {
      await api('POST', '/medecins', data);
      toast('Médecin créé', 'success');
      e.target.reset();
      closeModal('#modal-medecin');
      loadMedecins();
    } catch (err) { toast(err.message, 'error'); }
  });

  $('#form-rdv').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const data = {
      patient_id: parseInt(fd.get('patient_id')),
      medecin_id: parseInt(fd.get('medecin_id')),
      date_heure: fd.get('date_heure') + ':00',
      duree_minutes: parseInt(fd.get('duree_minutes')),
      motif: fd.get('motif') || null,
      mode: fd.get('mode'),
      statut: 'prevu',
    };
    try {
      await api('POST', '/rendezvous', data);
      toast('Rendez-vous créé', 'success');
      e.target.reset();
      closeModal('#modal-rdv');
      loadRendezVous();
    } catch (err) { toast(err.message, 'error'); }
  });

  // Créneaux
  $('#creneaux-medecin').addEventListener('change', chercherCreneaux);
  $('#creneaux-date').addEventListener('change', chercherCreneaux);

  // Auto-login si token valide
  if (state.token) {
    loadUser().then(() => {
      if (state.user) {
        showApp();
        navigate('dashboard');
      }
    });
  }
});

// Exposition globale pour les onclick inline
window.deletePatient = deletePatient;
window.deleteMedecin = deleteMedecin;
window.annulerRdv = annulerRdv;
window.deleteRdv = deleteRdv;
