// Global state
const state = {
  token: localStorage.getItem('token') || null,
  user: null,
  patients: [],
  doctors: [],
  appointments: [],
};

// ===== UTILITIES =====

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
    const detail = data?.detail || `Error ${res.status}`;
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
  return d.toLocaleString('en-CA', {
    weekday: 'short', day: '2-digit', month: 'short',
    hour: '2-digit', minute: '2-digit',
  });
}

const STATUS_STYLE = {
  scheduled: { label: 'Scheduled', classes: 'bg-blue-100 text-blue-700' },
  confirmed: { label: 'Confirmed', classes: 'bg-emerald-100 text-emerald-700' },
  cancelled: { label: 'Cancelled', classes: 'bg-red-100 text-red-700' },
  completed: { label: 'Completed', classes: 'bg-slate-200 text-slate-700' },
};

// ===== AUTHENTICATION =====

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
  toast('Account created, please sign in', 'success');
  $('#tab-login').click();
}

async function loadUser() {
  try {
    state.user = await api('GET', '/auth/me');
    $('#user-email').textContent = state.user.email;
    $('#user-role').textContent = state.user.role === 'admin' ? 'Administrator' : 'Doctor';
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
  if (page === 'doctors') loadDoctors();
  if (page === 'appointments') loadAppointments();
  if (page === 'slots') loadSlotsPage();
}

// ===== DASHBOARD =====

async function loadDashboard() {
  try {
    const [patients, doctors, appointments] = await Promise.all([
      api('GET', '/patients'),
      api('GET', '/doctors'),
      api('GET', '/appointments'),
    ]);
    state.patients = patients;
    state.doctors = doctors;
    state.appointments = appointments;

    $('#stat-patients').textContent = patients.length;
    $('#stat-doctors').textContent = doctors.length;
    $('#stat-appointments').textContent = appointments.length;

    const upcoming = appointments
      .filter(a => a.status !== 'cancelled' && new Date(a.scheduled_at) >= new Date())
      .sort((a, b) => new Date(a.scheduled_at) - new Date(b.scheduled_at))
      .slice(0, 5);

    const container = $('#dashboard-upcoming');
    if (upcoming.length === 0) {
      container.innerHTML = '<p class="text-sm text-slate-400 italic">No upcoming appointments</p>';
    } else {
      container.innerHTML = upcoming.map(a => {
        const p = patients.find(x => x.id === a.patient_id);
        const d = doctors.find(x => x.id === a.doctor_id);
        const status = STATUS_STYLE[a.status];
        return `
          <div class="flex items-center justify-between p-3 rounded-lg hover:bg-slate-50 transition">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-primary-100 to-primary-500 flex items-center justify-center text-white font-semibold text-sm">
                ${p ? (p.first_name[0] + p.last_name[0]) : '?'}
              </div>
              <div>
                <p class="text-sm font-semibold text-slate-900">${p ? p.first_name + ' ' + p.last_name : 'Unknown patient'}</p>
                <p class="text-xs text-slate-500">With Dr ${d ? d.last_name : '?'} — ${d?.specialty || ''}</p>
              </div>
            </div>
            <div class="text-right">
              <p class="text-sm font-medium text-slate-700">${formatDateTime(a.scheduled_at)}</p>
              <span class="inline-block text-xs px-2 py-0.5 rounded-full ${status.classes} mt-0.5">${status.label}</span>
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
      list.innerHTML = emptyState('No patients', 'Start by creating one');
      return;
    }
    list.innerHTML = `
      <table class="w-full text-sm">
        <thead class="bg-slate-50 border-b border-slate-200">
          <tr>
            <th class="text-left px-6 py-3 font-semibold text-slate-700">Patient</th>
            <th class="text-left px-6 py-3 font-semibold text-slate-700">Age</th>
            <th class="text-left px-6 py-3 font-semibold text-slate-700">Health card</th>
            <th class="px-6 py-3"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          ${state.patients.map(p => `
            <tr class="hover:bg-slate-50 transition">
              <td class="px-6 py-3">
                <div class="flex items-center gap-3">
                  <div class="w-9 h-9 rounded-full bg-gradient-to-br from-blue-100 to-blue-500 flex items-center justify-center text-white font-semibold text-xs">${p.first_name[0]}${p.last_name[0]}</div>
                  <div>
                    <p class="font-semibold text-slate-900">${p.first_name} ${p.last_name}</p>
                  </div>
                </div>
              </td>
              <td class="px-6 py-3 text-slate-600">${p.age} yrs</td>
              <td class="px-6 py-3"><code class="text-xs font-mono bg-slate-100 px-2 py-0.5 rounded">${p.health_card_number}</code></td>
              <td class="px-6 py-3 text-right">
                <button onclick="deletePatient(${p.id})" class="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded transition" title="Delete">
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
  if (!confirm('Delete this patient? All their appointments will be deleted too.')) return;
  try {
    await api('DELETE', `/patients/${id}`);
    toast('Patient deleted', 'success');
    loadPatients();
  } catch (e) { toast(e.message, 'error'); }
}

// ===== DOCTORS =====

async function loadDoctors() {
  try {
    state.doctors = await api('GET', '/doctors');
    const list = $('#doctors-list');
    if (state.doctors.length === 0) {
      list.innerHTML = emptyState('No doctors', 'Start by creating one');
      return;
    }
    list.innerHTML = `
      <table class="w-full text-sm">
        <thead class="bg-slate-50 border-b border-slate-200">
          <tr>
            <th class="text-left px-6 py-3 font-semibold text-slate-700">Doctor</th>
            <th class="text-left px-6 py-3 font-semibold text-slate-700">Specialty</th>
            <th class="text-left px-6 py-3 font-semibold text-slate-700">License</th>
            <th class="px-6 py-3"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          ${state.doctors.map(d => `
            <tr class="hover:bg-slate-50 transition">
              <td class="px-6 py-3">
                <div class="flex items-center gap-3">
                  <div class="w-9 h-9 rounded-full bg-gradient-to-br from-emerald-100 to-emerald-500 flex items-center justify-center text-white font-semibold text-xs">${d.first_name[0]}${d.last_name[0]}</div>
                  <p class="font-semibold text-slate-900">Dr ${d.first_name} ${d.last_name}</p>
                </div>
              </td>
              <td class="px-6 py-3"><span class="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 text-xs font-medium">${d.specialty}</span></td>
              <td class="px-6 py-3"><code class="text-xs font-mono bg-slate-100 px-2 py-0.5 rounded">${d.license_number}</code></td>
              <td class="px-6 py-3 text-right">
                <button onclick="deleteDoctor(${d.id})" class="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded transition">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6M1 7h22M9 7V4a1 1 0 011-1h4a1 1 0 011 1v3"/></svg>
                </button>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>`;
  } catch (e) { toast(e.message, 'error'); }
}

async function deleteDoctor(id) {
  if (!confirm('Delete this doctor? All their appointments will be deleted too.')) return;
  try {
    await api('DELETE', `/doctors/${id}`);
    toast('Doctor deleted', 'success');
    loadDoctors();
  } catch (e) { toast(e.message, 'error'); }
}

// ===== APPOINTMENTS =====

async function loadAppointments() {
  try {
    const [appointments, patients, doctors] = await Promise.all([
      api('GET', '/appointments'),
      api('GET', '/patients'),
      api('GET', '/doctors'),
    ]);
    state.appointments = appointments;
    state.patients = patients;
    state.doctors = doctors;
    const list = $('#appointments-list');
    if (appointments.length === 0) {
      list.innerHTML = emptyState('No appointments', 'Create your first appointment');
      return;
    }
    list.innerHTML = `
      <table class="w-full text-sm">
        <thead class="bg-slate-50 border-b border-slate-200">
          <tr>
            <th class="text-left px-6 py-3 font-semibold text-slate-700">Date and time</th>
            <th class="text-left px-6 py-3 font-semibold text-slate-700">Patient</th>
            <th class="text-left px-6 py-3 font-semibold text-slate-700">Doctor</th>
            <th class="text-left px-6 py-3 font-semibold text-slate-700">Mode</th>
            <th class="text-left px-6 py-3 font-semibold text-slate-700">Status</th>
            <th class="px-6 py-3"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          ${appointments.map(a => {
            const p = patients.find(x => x.id === a.patient_id);
            const d = doctors.find(x => x.id === a.doctor_id);
            const status = STATUS_STYLE[a.status];
            const modeIcon = a.mode === 'virtual'
              ? '<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>'
              : '<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>';
            return `
              <tr class="hover:bg-slate-50 transition">
                <td class="px-6 py-3">
                  <p class="font-semibold text-slate-900">${formatDateTime(a.scheduled_at)}</p>
                  <p class="text-xs text-slate-500">${a.duration_minutes} min</p>
                </td>
                <td class="px-6 py-3 text-slate-700">${p ? p.first_name + ' ' + p.last_name : '—'}</td>
                <td class="px-6 py-3 text-slate-700">Dr ${d ? d.last_name : '—'}</td>
                <td class="px-6 py-3">
                  <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 text-xs font-medium">
                    ${modeIcon}
                    ${a.mode === 'virtual' ? 'Virtual' : 'In person'}
                  </span>
                </td>
                <td class="px-6 py-3"><span class="px-2 py-0.5 rounded-full text-xs font-medium ${status.classes}">${status.label}</span></td>
                <td class="px-6 py-3 text-right">
                  ${a.status !== 'cancelled' && a.status !== 'completed' ? `
                    <button onclick="cancelAppointment(${a.id})" class="text-xs text-slate-500 hover:text-red-600 mr-2">Cancel</button>
                  ` : ''}
                  <button onclick="deleteAppointment(${a.id})" class="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded transition" title="Delete">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6M1 7h22M9 7V4a1 1 0 011-1h4a1 1 0 011 1v3"/></svg>
                  </button>
                </td>
              </tr>`;
          }).join('')}
        </tbody>
      </table>`;
  } catch (e) { toast(e.message, 'error'); }
}

async function cancelAppointment(id) {
  const appt = state.appointments.find(a => a.id === id);
  if (!appt) return;
  if (!confirm('Cancel this appointment?')) return;
  try {
    await api('PUT', `/appointments/${id}`, { ...appt, status: 'cancelled' });
    toast('Appointment cancelled', 'success');
    loadAppointments();
  } catch (e) { toast(e.message, 'error'); }
}

async function deleteAppointment(id) {
  if (!confirm('Permanently delete this appointment?')) return;
  try {
    await api('DELETE', `/appointments/${id}`);
    toast('Appointment deleted', 'success');
    loadAppointments();
  } catch (e) { toast(e.message, 'error'); }
}

// ===== AVAILABLE SLOTS =====

async function loadSlotsPage() {
  try {
    state.doctors = await api('GET', '/doctors');
    const select = $('#slots-doctor');
    select.innerHTML = '<option value="">Choose a doctor...</option>' +
      state.doctors.map(d => `<option value="${d.id}">Dr ${d.first_name} ${d.last_name} — ${d.specialty}</option>`).join('');
    $('#slots-date').valueAsDate = new Date();
    $('#slots-result').innerHTML = '';
  } catch (e) { toast(e.message, 'error'); }
}

async function searchSlots() {
  const doctorId = $('#slots-doctor').value;
  const day = $('#slots-date').value;
  if (!doctorId || !day) {
    $('#slots-result').innerHTML = '';
    return;
  }
  try {
    const data = await api('GET', `/doctors/${doctorId}/slots?day=${day}`);
    const container = $('#slots-result');
    if (data.available_slots.length === 0) {
      container.innerHTML = `
        <div class="bg-white rounded-2xl p-12 border border-slate-200 shadow-sm text-center">
          <div class="inline-flex items-center justify-center w-12 h-12 rounded-full bg-slate-100 mb-3">
            <svg class="w-6 h-6 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728L5.636 5.636m12.728 12.728L18.364 5.636M5.636 18.364l12.728-12.728"/></svg>
          </div>
          <p class="font-semibold text-slate-900">No available slots</p>
          <p class="text-sm text-slate-500 mt-1">The doctor is not available on that day (weekend or fully booked).</p>
        </div>`;
      return;
    }
    container.innerHTML = `
      <div class="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
        <p class="text-sm text-slate-600 mb-4">${data.available_slots.length} available slots on ${data.date}</p>
        <div class="grid grid-cols-3 sm:grid-cols-5 md:grid-cols-6 gap-2">
          ${data.available_slots.map(h => `
            <button class="px-3 py-2 rounded-lg bg-gradient-to-br from-primary-50 to-primary-100 hover:from-primary-100 hover:to-primary-500 hover:text-white text-primary-700 font-semibold text-sm transition shadow-sm">
              ${h}
            </button>
          `).join('')}
        </div>
      </div>`;
  } catch (e) { toast(e.message, 'error'); }
}

// ===== UI HELPERS =====

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

function fillAppointmentSelects() {
  $('select[name="patient_id"]').innerHTML =
    '<option value="">Choose a patient...</option>' +
    state.patients.map(p => `<option value="${p.id}">${p.first_name} ${p.last_name}</option>`).join('');
  $('select[name="doctor_id"]').innerHTML =
    '<option value="">Choose a doctor...</option>' +
    state.doctors.map(d => `<option value="${d.id}">Dr ${d.first_name} ${d.last_name} — ${d.specialty}</option>`).join('');
}

// ===== EVENTS =====

document.addEventListener('DOMContentLoaded', () => {
  // Login/register tabs
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

  // Login/register submissions
  $('#form-login').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      await login(fd.get('email'), fd.get('password'));
      toast(`Welcome ${state.user.email}`, 'success');
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
    toast('Signed out', 'info');
  });

  // Navigation
  $$('.nav-link').forEach(b => b.addEventListener('click', () => navigate(b.dataset.page)));

  // New buttons
  $('#btn-new-patient').addEventListener('click', () => openModal('#modal-patient'));
  $('#btn-new-doctor').addEventListener('click', () => openModal('#modal-doctor'));
  $('#btn-new-appointment').addEventListener('click', () => {
    fillAppointmentSelects();
    openModal('#modal-appointment');
  });

  // Close modals
  $$('.modal-close').forEach(b => b.addEventListener('click', () => {
    $$('#modal-patient, #modal-doctor, #modal-appointment').forEach(m => m.classList.add('hidden'));
  }));

  // Form submissions
  $('#form-patient').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const data = {
      last_name: fd.get('last_name'),
      first_name: fd.get('first_name'),
      age: parseInt(fd.get('age')),
      health_card_number: fd.get('health_card_number').toUpperCase(),
    };
    try {
      await api('POST', '/patients', data);
      toast('Patient created', 'success');
      e.target.reset();
      closeModal('#modal-patient');
      loadPatients();
    } catch (err) { toast(err.message, 'error'); }
  });

  $('#form-doctor').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const data = {
      last_name: fd.get('last_name'),
      first_name: fd.get('first_name'),
      specialty: fd.get('specialty'),
      license_number: fd.get('license_number'),
    };
    try {
      await api('POST', '/doctors', data);
      toast('Doctor created', 'success');
      e.target.reset();
      closeModal('#modal-doctor');
      loadDoctors();
    } catch (err) { toast(err.message, 'error'); }
  });

  $('#form-appointment').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const data = {
      patient_id: parseInt(fd.get('patient_id')),
      doctor_id: parseInt(fd.get('doctor_id')),
      scheduled_at: fd.get('scheduled_at') + ':00',
      duration_minutes: parseInt(fd.get('duration_minutes')),
      reason: fd.get('reason') || null,
      mode: fd.get('mode'),
      status: 'scheduled',
    };
    try {
      await api('POST', '/appointments', data);
      toast('Appointment created', 'success');
      e.target.reset();
      closeModal('#modal-appointment');
      loadAppointments();
    } catch (err) { toast(err.message, 'error'); }
  });

  // Slots
  $('#slots-doctor').addEventListener('change', searchSlots);
  $('#slots-date').addEventListener('change', searchSlots);

  // Auto-login if token is valid
  if (state.token) {
    loadUser().then(() => {
      if (state.user) {
        showApp();
        navigate('dashboard');
      }
    });
  }
});

// Global exposure for inline onclick handlers
window.deletePatient = deletePatient;
window.deleteDoctor = deleteDoctor;
window.cancelAppointment = cancelAppointment;
window.deleteAppointment = deleteAppointment;
