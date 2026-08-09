const { createApp } = Vue;

function authHeaders() {
  const token = localStorage.getItem('token');
  return token ? { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' };
}

createApp({
  data() {
    return {
      tab: 'home',
      email: '', password: '', name: '', message: '',
      drives: [], title:'', description:'', deadline:'', eligibility:'', pending: [], pending_drives: [],
      stats: {counts: {}}, companies: [], students: [], applications: [], company_search_q: '', student_search_q: '',
      showCompanies: false, showStudents: false,
      currentRole: localStorage.getItem('role') || '',
      isActive: localStorage.getItem('is_active') === 'true',
      cgpa: '', contact_number: '', resume_path: '',
      toasts: [],
      showRegisterChooser: false,
      showLoginChooser: false,
      myApplications: [],
      appStatusByDrive: {},

      // company-specific
      companyJobs: { pending: [], approved: [], rejected: [] },
      companyApplications: [], selectedDriveId: null
    }
  },

  methods: {
    showToast(msg, variant='info'){
      const id = Date.now() + Math.floor(Math.random()*1000);
      this.toasts.push({id, msg, variant});
      setTimeout(()=>{ this.toasts = this.toasts.filter(t=>t.id!==id) }, 4500);
    },
    removeToast(id){ this.toasts = this.toasts.filter(t=>t.id!==id) },
    openRegisterChooser(){ this.showRegisterChooser = true; this.showLoginChooser = false; },
    openLoginChooser(){ this.showLoginChooser = true; this.showRegisterChooser = false; },

    async registerStudent(){
      // client-side validation
      if(!this.email || !this.password || !this.name || this.cgpa === '' || this.cgpa === null || isNaN(Number(this.cgpa)) || !this.contact_number){
        this.showToast('Please fill email, password, name, numeric CGPA and contact number','warning');
        return;
      }
      const body = {email:this.email,password:this.password,name:this.name,cgpa:parseFloat(this.cgpa),contact_number:this.contact_number,resume_path:this.resume_path || null};
      const res = await fetch('/api/auth/register/student',{method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
      const j = await res.json(); this.showToast(j.msg || JSON.stringify(j), res.ok ? 'success' : 'danger');
      if(res.ok){
        // clear form
        this.email=''; this.password=''; this.name=''; this.cgpa=''; this.contact_number=''; this.resume_path='';
      }
    },

    async registerCompany(){
      // client-side validation to avoid backend 400
      if(!this.email || !this.password || !this.name){
        this.showToast('Please fill email, password and company name','warning');
        return;
      }
      try{
        const res = await fetch('/api/auth/register/company',{method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({email:this.email,password:this.password,name:this.name,hr_contact: '', website: ''})});
        let j = null;
        try{ j = await res.json(); } catch(e){ j = { msg: 'Invalid response from server' }; }
        this.showToast(j.msg || JSON.stringify(j), res.ok ? 'success' : 'danger');
        if(res.ok){ this.email=''; this.password=''; this.name=''; }
      } catch(err){
        console.error('registerCompany error', err);
        this.showToast('Network error during registration','danger');
      }
    },

    async login(){
      const res = await fetch('/api/auth/login',{method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({email:this.email,password:this.password})});
      const j = await res.json();
      if(res.ok && j.access_token){
        localStorage.setItem('token', j.access_token);
        localStorage.setItem('role', j.role);
        localStorage.setItem('is_active', j.is_active ? 'true' : 'false');
        this.currentRole = j.role;
        this.isActive = !!j.is_active;
        this.showToast('Logged in as ' + j.role, 'success');
        if(!this.isActive){
          this.tab = 'deactivated';
          this.showToast('Account deactivated. Contact admin.','danger');
          return;
        }
        if(j.role === 'admin'){
          this.tab='admin';
          setTimeout(()=> { this.loadPendingCompanies(); this.loadPendingDrives(); this.loadAdminStats(); }, 300);
        } else if(j.role === 'company'){
          this.tab='company';
          setTimeout(()=> { this.loadCompanyDrives(); }, 300);
        } else {
          this.tab='student';
          setTimeout(()=> { this.loadMyApplications(); }, 300);
        }
      }else{
        this.showToast(j.msg || 'login failed','danger');
      }
    },
    logout(){ localStorage.removeItem('token'); localStorage.removeItem('role'); this.currentRole=''; this.tab='home'; this.showToast('logged out','info'); },
    async loadDrives(){
      const res = await fetch('/api/drives/');
      const j = await res.json();
      this.drives = j.drives || [];
    },
    async createDrive(){
      const body = {title:this.title, description:this.description, application_deadline:this.deadline, eligibility:this.eligibility};
      const res = await fetch('/api/drives/create',{method:'POST', headers: authHeaders(), body: JSON.stringify(body)});
      const j = await res.json();
      // friendly message if company not approved
      if(res.status === 403 && j && /not approved/i.test(j.msg || '')){
        this.showToast('You can only create drives after admin approves your company','warning');
      } else {
        this.showToast(j.msg || JSON.stringify(j), res.ok ? 'success' : 'danger');
      }
      if(res.ok) { this.title=''; this.loadDrives(); }
    },
    async openAdmin(){
      // verify auth and admin role first
      const meRes = await fetch('/api/auth/me', { headers: authHeaders() });
      if(!meRes.ok){
        this.showToast('Unauthorized — please login as admin','danger');
        return;
      }
      const me = await meRes.json();
      if(!me.user || me.user.role !== 'admin'){
        this.showToast('Access denied — admin only','danger');
        return;
      }
      this.tab='admin';
      // load admin data
      await this.loadPendingCompanies();
      await this.loadPendingDrives();
      await this.loadAdminStats();
      await this.loadApplications();
    },

    async loadPendingCompanies(){
      const res = await fetch('/api/admin/companies/pending', { headers: authHeaders() });
      if(!res.ok){ this.showToast('Failed to load pending companies','danger'); return }
      const j = await res.json();
      this.pending = j.pending || [];
    },
    async approveCompany(id){
      const res = await fetch(`/api/admin/companies/${id}/approve`, { method:'POST', headers: authHeaders() });
      const j = await res.json(); this.message = j.msg || JSON.stringify(j); this.loadPendingCompanies();
    },
    async rejectCompany(id){
      const res = await fetch(`/api/admin/companies/${id}/reject`, { method:'POST', headers: authHeaders() });
      const j = await res.json(); this.message = j.msg || JSON.stringify(j); this.loadPendingCompanies();
    },
    async loadPendingDrives(){
      const res = await fetch('/api/admin/drives/pending', { headers: authHeaders() });
      if(!res.ok){ this.message='Failed to load pending drives'; return }
      const j = await res.json();
      this.pending_drives = j.pending_drives || [];
    },
    async loadAdminStats(){
      const res = await fetch('/api/health', { headers: authHeaders() });
      if(!res.ok){ this.showToast('Failed to load admin stats','danger'); return }
      const j = await res.json(); this.stats = j;
    },

    async loadAllCompanies(){
      const res = await fetch('/api/admin/companies', { headers: authHeaders() });
      if(!res.ok){ this.message='Failed to load companies'; return }
      const j = await res.json(); this.companies = j.companies || []; this.showCompanies = true;
    },
    async loadAllStudents(){
      const res = await fetch('/api/admin/students', { headers: authHeaders() });
      if(!res.ok){ this.message='Failed to load students'; return }
      const j = await res.json(); this.students = j.students || []; this.showStudents = true;
    },
    async toggleCompanies(){
      if(this.showCompanies){
        this.showCompanies = false;
        this.companies = [];
      } else {
        await this.loadAllCompanies();
      }
    },
    async toggleStudents(){
      if(this.showStudents){
        this.showStudents = false;
        this.students = [];
      } else {
        await this.loadAllStudents();
      }
    },
    async searchCompanies(){
      const q = encodeURIComponent(this.company_search_q || '');
      const res = await fetch('/api/admin/search/companies?q='+q, { headers: authHeaders() });
      if(!res.ok){ this.message='Search failed'; return }
      const j = await res.json(); this.companies = j.companies || []; this.showCompanies = true;
    },
    async searchStudents(){
      const q = encodeURIComponent(this.student_search_q || '');
      const res = await fetch('/api/admin/search/students?q='+q, { headers: authHeaders() });
      if(!res.ok){ this.message='Search failed'; return }
      const j = await res.json(); this.students = j.students || []; this.showStudents = true;
    },
    async deactivateCompany(id){
      const res = await fetch(`/api/admin/companies/${id}/deactivate`, { method:'POST', headers: authHeaders() });
      const j = await res.json(); this.message = j.msg || JSON.stringify(j); if(this.showCompanies) this.loadAllCompanies();
    },
    async deactivateStudent(id){
      const res = await fetch(`/api/admin/students/${id}/deactivate`, { method:'POST', headers: authHeaders() });
      const j = await res.json(); this.message = j.msg || JSON.stringify(j); if(this.showStudents) this.loadAllStudents();
    },
    async loadCompanyApplications(id){
      this.applicationsMessage = '';
      const res = await fetch(`/api/admin/companies/${id}/applications`, { headers: authHeaders() });
      if(!res.ok){ this.applications = []; this.applicationsMessage='Failed to load applications'; return }
      const j = await res.json(); this.applications = j.applications || []; if(this.applications.length===0){ this.applicationsMessage='No applications found'; } else { this.applicationsMessage=''; }
    },
    async loadCompanyDrives(){
      const res = await fetch('/api/drives/company/drives', { headers: authHeaders() });
      if(!res.ok){ this.message='Failed to load company drives'; return }
      const j = await res.json(); this.companyJobs = j; // {pending,approved,rejected}
    },
    async viewCompanyDriveApplications(driveId){
      this.selectedDriveId = driveId;
      const res = await fetch(`/api/drives/company/drives/${driveId}/applications`, { headers: authHeaders() });
      if(!res.ok){ this.companyApplications = []; this.showToast('Failed to load drive applications','danger'); return }
      const j = await res.json(); this.companyApplications = j.applications || [];
    },
    async decideApplication(appId, decision){
      const res = await fetch(`/api/drives/company/applications/${appId}/decide`, { method:'POST', headers: authHeaders(), body: JSON.stringify({decision}) });
      const j = await res.json(); this.showToast(j.msg || JSON.stringify(j), (typeof res !== 'undefined' && res.ok) ? 'success' : 'danger');
      if(res.ok){
        // refresh current drive apps
        if(this.selectedDriveId) this.viewCompanyDriveApplications(this.selectedDriveId);
      }
    },
    async loadApplications(){
      const res = await fetch('/api/admin/applications', { headers: authHeaders() });
      if(!res.ok){ this.applications = []; this.showToast('Failed to load applications','danger'); return }
      const j = await res.json(); this.applications = j.applications || [];
      if(this.applications.length===0){ this.showToast('No applications found','info'); }
    },

    async approveDrive(id){
      const res = await fetch(`/api/admin/drives/${id}/approve`, { method:'POST', headers: authHeaders() });
      const j = await res.json(); this.showToast(j.msg || JSON.stringify(j), (typeof res !== 'undefined' && res.ok) ? 'success' : 'danger'); this.loadPendingDrives(); this.loadDrives();
    },
    async rejectDrive(id){
      const res = await fetch(`/api/admin/drives/${id}/reject`, { method:'POST', headers: authHeaders() });
      const j = await res.json(); this.showToast(j.msg || JSON.stringify(j), (typeof res !== 'undefined' && res.ok) ? 'success' : 'danger'); this.loadPendingDrives();
    },
    async loadMyApplications(){
      const res = await fetch('/api/student/applications', { headers: authHeaders() });
      if(!res.ok){ this.myApplications = []; this.appStatusByDrive = {}; this.showToast('Failed to load your applications','danger'); return }
      const j = await res.json();
      const apps = j.applications || [];
      this.myApplications = apps.map(a=>a.drive_id);
      this.appStatusByDrive = {};
      apps.forEach(a => { if(a.drive_id) this.appStatusByDrive[a.drive_id] = a.status; });
    },

    async applyToDrive(driveId){
      if(this.myApplications.includes(driveId)){
        this.showToast('Already applied','info');
        return;
      }
      // ensure student has resume, fetch profile
      const meRes = await fetch('/api/auth/me', { headers: authHeaders() });
      if(!meRes.ok){ this.showToast('Failed to fetch profile','danger'); return }
      const me = await meRes.json();
      const user = me.user || {};
      // if user is deactivated, show toast/message and stop
      if(user.is_active === false){ this.showToast('You are deactivated','danger'); return }
      const student = user.student || null;
      let resume = student ? student.resume_path : null;
      if(!resume){
        const entered = prompt('Please provide resume path or URL (required to apply):');
        if(!entered){ this.showToast('Resume required to apply','warning'); return }
        resume = entered;
      }
      const res = await fetch(`/api/drives/${driveId}/apply`, { method: 'POST', headers: authHeaders(), body: JSON.stringify({resume_path: resume}) });
      const j = await res.json();
      if(!res.ok){ this.showToast(j.msg || 'Failed to apply','danger'); return }
      this.showToast(j.msg || 'Application submitted','success');
      this.myApplications.push(driveId);
      // set status mapping
      this.appStatusByDrive[driveId] = 'Applied';
    }
  },
  watch: {
    message(newVal){ if(newVal){ this.showToast(newVal,'info'); this.message=''; } },
    studentMessage(n){ if(n){ this.showToast(n,'info'); this.studentMessage=''; } },
    applicationsMessage(n){ if(n){ this.showToast(n,'info'); this.applicationsMessage=''; } }
  },
  mounted(){ this.loadDrives(); this.loadAdminStats(); this.loadApplications(); if(this.currentRole==='student') this.loadMyApplications(); },
  template: `\
  <div class="container mt-4">\
    <h1>Placement Portal</h1>\
    <div class="mb-3">\
      <button class="btn btn-sm btn-outline-primary me-1" @click="tab='home'">Home</button>\
      <button class="btn btn-sm btn-outline-secondary me-1" @click="openRegisterChooser">Register</button>\
      <button v-if="!currentRole" class="btn btn-sm btn-outline-success me-1" @click="openLoginChooser">Login</button>\
      <button v-else class="btn btn-sm btn-outline-danger" @click="logout">Logout</button>\
    </div>\
    <div v-if="showRegisterChooser" class="mb-2">\
      <div class="btn-group" role="group">\
        <button class="btn btn-sm btn-outline-primary" @click="showRegisterChooser=false; tab='register_student'">Student</button>\
        <button class="btn btn-sm btn-outline-primary" @click="showRegisterChooser=false; tab='register_company'">Company</button>\
        <button class="btn btn-sm btn-outline-secondary" @click="showRegisterChooser=false">Cancel</button>\
      </div>\
    </div>\
    <div v-if="showLoginChooser" class="mb-2">\
      <div class="btn-group" role="group">\
        <button class="btn btn-sm btn-outline-success" @click="showLoginChooser=false; tab='login'">Student</button>\
        <button class="btn btn-sm btn-outline-success" @click="showLoginChooser=false; tab='login'">Company</button>\
        <button class="btn btn-sm btn-outline-success" @click="showLoginChooser=false; tab='login'">Admin</button>\
        <button class="btn btn-sm btn-outline-secondary" @click="showLoginChooser=false">Cancel</button>\
      </div>\
    </div>\
\
    <div v-if="tab==='home'">\
      <h4>Available Drives</h4>\
      <div v-if="drives.length===0" class="text-muted">No drives available</div>\
      <ul class="list-group">\
        <li class="list-group-item" v-for="d in drives" :key="d.id">\
          <strong>{{ d.title }}</strong> — <em>{{ d.company_name }}</em><br/>\
          <small class="text-muted">Deadline: {{ d.application_deadline }}</small>\
        </li>\
      </ul>\
    </div>\
\
    <div v-if="tab==='register_student'">\
      <h4>Student Register</h4>\
      <input class="form-control mb-2" v-model="email" placeholder="email"/>\
      <input class="form-control mb-2" v-model="password" type="password" placeholder="password"/>\
      <input class="form-control mb-2" v-model="name" placeholder="full name"/>\
      <input class="form-control mb-2" v-model="cgpa" placeholder="CGPA (e.g. 8.5)"/>\
      <input class="form-control mb-2" v-model="contact_number" placeholder="Contact number"/>\
      <input class="form-control mb-2" v-model="resume_path" placeholder="Resume path or URL"/>\
      <button class="btn btn-primary" @click="registerStudent">Register</button>\
    </div>\
\
    <div v-if="tab==='register_company'">\
      <h4>Company Register</h4>\
      <input class="form-control mb-2" v-model="email" placeholder="email"/>\
      <input class="form-control mb-2" v-model="password" type="password" placeholder="password"/>\
      <input class="form-control mb-2" v-model="name" placeholder="company name"/>\
      <button class="btn btn-primary" @click="registerCompany">Register</button>\
    </div>\
\
    <div v-if="tab==='login'">\
      <h4>Login</h4>\
      <input class="form-control mb-2" v-model="email" placeholder="email"/>\
      <input class="form-control mb-2" v-model="password" type="password" placeholder="password"/>\
      <button class="btn btn-success" @click="login">Login</button>\
    </div>\
\
    <div v-if="tab==='deactivated'">\
      <div class="alert alert-danger">Your account has been deactivated. Please contact the institute admin for reactivation.</div>\
    </div>\
\
    <div v-if="tab==='company'">\
      <h4>Company Dashboard</h4>\
      <div class="mb-2">\
        <div class="alert alert-warning" v-if="!isActive">Your company account is deactivated. Contact admin.</div>\
        <h5>Create Placement Drive</h5>\
        <input class="form-control mb-2" v-model="title" placeholder="Job Title" :disabled="!isActive"/>\
        <input class="form-control mb-2" v-model="description" placeholder="Description" :disabled="!isActive"/>\
        <input class="form-control mb-2" v-model="eligibility" placeholder="Eligibility" :disabled="!isActive"/>\
        <input class="form-control mb-2" v-model="deadline" placeholder="YYYY-MM-DDTHH:MM:SS" :disabled="!isActive"/>\
        <button class="btn btn-primary" @click="createDrive" :disabled="!isActive">Create Drive</button>\
      </div>\
\
      <div class="mb-3">\
        <button class="btn btn-sm btn-outline-secondary me-1" @click="loadCompanyDrives">Refresh Drives</button>\
      </div>\
\
      <div class="row">\
        <div class="col-md-4">\
          <h6>Pending Drives</h6>\
          <ul class="list-group">\
            <li class="list-group-item" v-for="d in companyJobs.pending" :key="d.id">\
              <strong>{{ d.title }}</strong><br/>\
              <small class="text-muted">Deadline: {{ d.application_deadline }}</small>\
              <div class="mt-2">\
                <button class="btn btn-sm btn-info" @click="viewCompanyDriveApplications(d.id)">View Applications</button>\
              </div>\
            </li>\
          </ul>\
        </div>\
        <div class="col-md-4">\
          <h6>Approved Drives</h6>\
          <ul class="list-group">\
            <li class="list-group-item" v-for="d in companyJobs.approved" :key="d.id">\
              <strong>{{ d.title }}</strong><br/>\
              <small class="text-muted">Deadline: {{ d.application_deadline }}</small>\
              <div class="mt-2">\
                <button class="btn btn-sm btn-info" @click="viewCompanyDriveApplications(d.id)">View Applications</button>\
              </div>\
            </li>\
          </ul>\
        </div>\
        <div class="col-md-4">\
          <h6>Rejected Drives</h6>\
          <ul class="list-group">\
            <li class="list-group-item" v-for="d in companyJobs.rejected" :key="d.id">\
              <strong>{{ d.title }}</strong><br/>\
              <small class="text-muted">Deadline: {{ d.application_deadline }}</small>\
              <div class="mt-2">\
                <button class="btn btn-sm btn-info" @click="viewCompanyDriveApplications(d.id)">View Applications</button>\
              </div>\
            </li>\
          </ul>\
        </div>\
      </div>\
\
      <div v-if="companyApplications.length>0" class="mt-3">\
        <h5>Applications for Drive</h5>\
        <ul class="list-group">\
          <li class="list-group-item" v-for="a in companyApplications" :key="a.id">\
            <strong>{{ a.student_name }}</strong> — CGPA: {{ a.student_cgpa }} — Contact: {{ a.student_contact }}<br/>\
            <a :href="a.resume_path" target="_blank">Resume</a> — <small>{{ a.applied_at }}</small>\
            <div class="mt-2" v-if="isActive">\
              <button class="btn btn-sm btn-success" @click="decideApplication(a.id,'Accepted')">Accept</button>
              <button class="btn btn-sm btn-warning ms-1" @click="decideApplication(a.id,'Shortlisted')">Shortlist</button>
              <button class="btn btn-sm btn-danger ms-1" @click="decideApplication(a.id,'Rejected')">Reject</button>
            </div>\
          </li>\
        </ul>\
      </div>\
    </div>\
\
    <div v-if="tab==='student'">\
      <h4>Available Drives (Student)</h4>\
      <div v-if="drives.length===0" class="text-muted">No drives available</div>\
      <ul class="list-group">\
        <li class="list-group-item" v-for="d in drives" :key="d.id">\
          <strong>{{ d.title }}</strong>\
          <span v-if="appStatusByDrive[d.id]" class="badge ms-2" :class="{ 'bg-success': appStatusByDrive[d.id]==='Accepted', 'bg-warning': appStatusByDrive[d.id]==='Shortlisted', 'bg-danger': appStatusByDrive[d.id]==='Rejected', 'bg-secondary': appStatusByDrive[d.id]==='Applied' }">{{ appStatusByDrive[d.id] }}</span> — <em>{{ d.company_name }}</em><br/>\
          <small class="text-muted">Deadline: {{ d.application_deadline }}</small>\
          <div class="mt-2">\
            <button :class="myApplications.includes(d.id) ? 'btn btn-sm btn-secondary' : 'btn btn-sm btn-primary'" @click="applyToDrive(d.id)" :disabled="myApplications.includes(d.id) || appStatusByDrive[d.id]==='Rejected'">\
              {{ myApplications.includes(d.id) ? 'Applied' : 'Apply' }}\
            </button>\
          </div>\
        </li>\
      </ul>\
    </div>\
\
    <div v-if="tab==='admin'">\"}
      <h4>Admin Dashboard</h4>\
      <div class="row mb-3">\
        <div class="col-3"><div class="card p-2"><div class="h5">Students</div><div>{{ stats.counts.students ?? 'N/A' }}</div></div></div>\
        <div class="col-3"><div class="card p-2"><div class="h5">Companies</div><div>{{ stats.counts.companies ?? 'N/A' }}</div></div></div>\
        <div class="col-3"><div class="card p-2"><div class="h5">Drives</div><div>{{ stats.counts.drives ?? 'N/A' }}</div></div></div>\
        <div class="col-3"><div class="card p-2"><div class="h5">Applications</div><div>{{ stats.counts.applications ?? 'N/A' }}</div></div></div>\
      </div>\
\
      <div class="mb-3">\
        <button class="btn btn-sm btn-outline-primary me-1" @click="loadPendingCompanies">Pending Companies</button>\
        <button class="btn btn-sm btn-outline-primary me-1" @click="loadPendingDrives">Pending Drives</button>\
        <button class="btn btn-sm btn-outline-secondary" @click="loadApplications">Refresh Applications</button>\
      </div>\
\
      <div v-if="pending.length>0" class="mb-3">\
        <h5>Pending Companies</h5>\
        <ul class="list-group mb-2">\
          <li class="list-group-item" v-for="p in pending" :key="p.id">\
            <strong>{{ p.name }}</strong> — <small>{{ p.hr_contact || '' }} {{ p.website || '' }}</small>\
            <div class="mt-2">\
              <button class="btn btn-sm btn-success" @click="approveCompany(p.id)">Approve</button>\
              <button class="btn btn-sm btn-danger ms-1" @click="rejectCompany(p.id)">Reject</button>\
            </div>\
          </li>\
        </ul>\
      </div>\
\
      <div v-if="pending_drives.length>0" class="mb-3">\
        <h5>Pending Drives</h5>\
        <ul class="list-group mb-2">\
          <li class="list-group-item" v-for="d in pending_drives" :key="d.id">\
            <strong>{{ d.title }}</strong> — <em>{{ d.company_name }}</em><br/>\
            <small class="text-muted">Deadline: {{ d.application_deadline }}</small>\
            <div class="mt-2">\
              <button class="btn btn-sm btn-success" @click="approveDrive(d.id)">Approve</button>\
              <button class="btn btn-sm btn-danger ms-1" @click="rejectDrive(d.id)">Reject</button>\
            </div>\
          </li>\
        </ul>\
      </div>\
\
      <div class="mb-3">\
        <input class="form-control mb-2" v-model="company_search_q" placeholder="Search companies by name or website" @keyup.enter="searchCompanies"/>\
        <button class="btn btn-sm btn-primary me-1" @click="searchCompanies">Search Companies</button>\
        <button class="btn btn-sm btn-outline-secondary" @click="toggleCompanies">{{ showCompanies ? 'Hide All Companies' : 'Show All Companies' }}</button>\
      </div>\
      <ul class="list-group mb-3">\
        <li class="list-group-item" v-for="c in companies" :key="c.id">\
          <strong>{{ c.name }}</strong> — <small>Approved: {{ c.approved }}</small>\
          <div class="mt-2">\
            <button class="btn btn-sm btn-danger" @click="deactivateCompany(c.id)">Deactivate</button>\
            <button class="btn btn-sm btn-info ms-1" @click="loadCompanyApplications(c.id)">View Applications</button>\
          </div>\
        </li>\
      </ul>\
\
      <div class="mb-3">\
        <input class="form-control mb-2" v-model="student_search_q" placeholder="Search students by name" @keyup.enter="searchStudents"/>\
        <button class="btn btn-sm btn-primary me-1" @click="searchStudents">Search Students</button>\
        <button class="btn btn-sm btn-outline-secondary" @click="toggleStudents">{{ showStudents ? 'Hide All Students' : 'Show All Students' }}</button>\
      </div>\
      <ul class="list-group mb-3" v-if="showStudents">\
        <li class="list-group-item" v-for="s in students" :key="s.student_id">\
          <strong>{{ s.name }}</strong> — <small>{{ s.branch }} CGPA: {{ s.cgpa }}</small>\
          <div class="mt-2">\
            <button class="btn btn-sm btn-danger" @click="deactivateStudent(s.student_id)">Deactivate</button>\
          </div>\
        </li>\
      </ul>\
\
      <h5>Recent Applications</h5>\
\
      <ul class="list-group" v-if="applications.length>0">\
        <li class="list-group-item" v-for="a in applications" :key="a.id">\
          <strong>{{ a.student_name }}</strong> applied to <em>{{ a.drive_title }}</em> — <small>{{ a.status }}</small>\
        </li>\
      </ul>\
    </div>\
\
    <div aria-live="polite" aria-atomic="true" style="position: fixed; top: 1rem; right: 1rem; z-index: 1060;">\
      <div v-for="t in toasts" :key="t.id" class="toast show" role="alert" aria-live="assertive" aria-atomic="true" style="min-width:240px; margin-bottom:0.5rem;">\
        <div :class="['toast-header', t.variant==='danger' ? 'bg-danger text-white' : t.variant==='success' ? 'bg-success text-white' : 'bg-info text-white']">\
          <strong class="me-auto">{{ t.variant }}</strong>\
          <button type="button" class="btn-close btn-close-white" @click="removeToast(t.id)"></button>\
        </div>\
        <div class="toast-body">{{ t.msg }}</div>\
      </div>\
    </div>\
  </div>`
}).mount('#app');
