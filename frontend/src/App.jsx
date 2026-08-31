import { useState, useEffect, useRef } from 'react';

const API_BASE = 'http://localhost:8000';

function App() {
  // Auth state
  const [token, setToken] = useState(localStorage.getItem('cf_token') || '');
  const [user, setUser] = useState(null);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authMode, setAuthMode] = useState('login'); // 'login' or 'register'
  const [authForm, setAuthForm] = useState({ username: '', email: '', password: '' });
  const [authError, setAuthError] = useState('');

  // Deploy state
  const [repoUrl, setRepoUrl] = useState('');
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [projects, setProjects] = useState([]);
  const [newProjectName, setNewProjectName] = useState('');
  const [showNewProjectForm, setShowNewProjectForm] = useState(false);

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [logs, setLogs] = useState([]);
  const logsEndRef = useRef(null);

  const [containers, setContainers] = useState([]);

  // Secrets management state
  const [envVars, setEnvVars] = useState([]);
  const [newEnv, setNewEnv] = useState({ key: '', value: '', environment: 'production', is_secret: true });
  const [envLoading, setEnvLoading] = useState(false);

  // Build settings state
  const emptyBuildSettings = {
    root_directory: '',
    install_command: '',
    build_command: '',
    start_command: '',
    output_directory: '',
    port: ''
  };
  const [buildSettings, setBuildSettings] = useState(emptyBuildSettings);
  const [buildSettingsLoading, setBuildSettingsLoading] = useState(false);
  const [buildSettingsSaved, setBuildSettingsSaved] = useState(false);

  // Initial load & Current user fetch
  useEffect(() => {
    if (token) {
      fetchCurrentUser();
    }
    fetchProjects();
    fetchContainers();
  }, [token]);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  useEffect(() => {
    if (selectedProjectId) {
      fetchEnvVars(selectedProjectId);
      fetchBuildSettings(selectedProjectId);
    } else {
      setEnvVars([]);
      setBuildSettings(emptyBuildSettings);
    }
  }, [selectedProjectId]);

  const fetchCurrentUser = async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const userData = await res.json();
        setUser(userData);
      } else {
        handleLogout();
      }
    } catch (err) {
      console.error("Auth hatası:", err);
    }
  };

  const handleLogout = () => {
    setToken('');
    setUser(null);
    localStorage.removeItem('cf_token');
  };

  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    setAuthError('');

    const endpoint = authMode === 'login' ? '/auth/login' : '/auth/register';
    const payload = authMode === 'login'
      ? { username_or_email: authForm.username, password: authForm.password }
      : { username: authForm.username, email: authForm.email, password: authForm.password };

    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (!res.ok) {
        setAuthError(data.detail || 'İşlem başarısız oldu.');
        return;
      }

      setToken(data.access_token);
      localStorage.setItem('cf_token', data.access_token);
      setUser(data.user);
      setShowAuthModal(false);
      setAuthForm({ username: '', email: '', password: '' });
    } catch (err) {
      setAuthError('Sunucuya ulaşılamadı.');
    }
  };

  const fetchProjects = async () => {
    try {
      const res = await fetch(`${API_BASE}/projects`);
      const data = await res.json();
      if (Array.isArray(data)) {
        setProjects(data);
      }
    } catch (err) {
      console.error('Projeler yüklenirken hata:', err);
    }
  };

  const handleCreateProject = async (e) => {
    e.preventDefault();
    if (!newProjectName || !repoUrl) return;

    try {
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const res = await fetch(`${API_BASE}/projects`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ name: newProjectName, repo_url: repoUrl })
      });
      const data = await res.json();
      if (res.ok) {
        setProjects([data, ...projects]);
        setSelectedProjectId(data.id);
        setNewProjectName('');
        setShowNewProjectForm(false);
      }
    } catch (err) {
      alert('Proje oluşturulamadı.');
    }
  };

  const fetchContainers = async () => {
    try {
      const response = await fetch(`${API_BASE}/containers`);
      const data = await response.json();
      if (data.status === 'success') {
        setContainers(data.containers);
      }
    } catch (err) {
      console.error('Konteynerler çekilirken hata oluştu:', err);
    }
  };

  const fetchEnvVars = async (projectId) => {
    setEnvLoading(true);
    try {
      const res = await fetch(`${API_BASE}/projects/${projectId}/env`);
      const data = await res.json();
      if (Array.isArray(data)) {
        setEnvVars(data);
      }
    } catch (err) {
      console.error('Ortam değişkenleri yüklenirken hata:', err);
    } finally {
      setEnvLoading(false);
    }
  };

  const handleAddEnv = async (e) => {
    e.preventDefault();
    if (!selectedProjectId || !newEnv.key || !newEnv.value) return;

    try {
      const res = await fetch(`${API_BASE}/projects/${selectedProjectId}/env`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newEnv)
      });
      if (res.ok) {
        fetchEnvVars(selectedProjectId);
        setNewEnv({ key: '', value: '', environment: 'production', is_secret: true });
      }
    } catch (err) {
      alert('Ortam değişkeni eklenirken hata oluştu.');
    }
  };

  const handleDeleteEnv = async (envId) => {
    try {
      const res = await fetch(`${API_BASE}/projects/${selectedProjectId}/env/${envId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        fetchEnvVars(selectedProjectId);
      }
    } catch (err) {
      alert('Silme hatası.');
    }
  };

  const fetchBuildSettings = async (projectId) => {
    setBuildSettingsLoading(true);
    setBuildSettingsSaved(false);
    try {
      const res = await fetch(`${API_BASE}/projects/${projectId}/build-settings`);
      if (res.status === 200) {
        const data = await res.json();
        if (data) {
          setBuildSettings({
            root_directory: data.root_directory || '',
            install_command: data.install_command || '',
            build_command: data.build_command || '',
            start_command: data.start_command || '',
            output_directory: data.output_directory || '',
            port: data.port ? String(data.port) : ''
          });
        } else {
          setBuildSettings(emptyBuildSettings);
        }
      }
    } catch (err) {
      console.error('Build ayarları yüklenirken hata:', err);
    } finally {
      setBuildSettingsLoading(false);
    }
  };

  const handleBuildSettingsChange = (field, value) => {
    setBuildSettingsSaved(false);
    setBuildSettings((prev) => ({ ...prev, [field]: value }));
  };

  const handleSaveBuildSettings = async (e) => {
    e.preventDefault();
    if (!selectedProjectId) return;

    const payload = {
      root_directory: buildSettings.root_directory.trim() || null,
      install_command: buildSettings.install_command.trim() || null,
      build_command: buildSettings.build_command.trim() || null,
      start_command: buildSettings.start_command.trim() || null,
      output_directory: buildSettings.output_directory.trim() || null,
      port: buildSettings.port ? Number(buildSettings.port) : null
    };

    setBuildSettingsLoading(true);
    setBuildSettingsSaved(false);
    try {
      const res = await fetch(`${API_BASE}/projects/${selectedProjectId}/build-settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok) {
        setBuildSettings({
          root_directory: data.root_directory || '',
          install_command: data.install_command || '',
          build_command: data.build_command || '',
          start_command: data.start_command || '',
          output_directory: data.output_directory || '',
          port: data.port ? String(data.port) : ''
        });
        setBuildSettingsSaved(true);
      } else {
        alert(data.detail || 'Build ayarları kaydedilemedi.');
      }
    } catch (err) {
      alert('Build ayarları kaydedilirken hata oluştu.');
    } finally {
      setBuildSettingsLoading(false);
    }
  };

  const handleStop = async (id) => {
    try {
      await fetch(`${API_BASE}/containers/${id}/stop`, { method: 'POST' });
      fetchContainers();
    } catch (err) {
      alert('Durdurma işlemi başarısız oldu.');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Bu uygulamayı tamamen silmek istediğinize emin misiniz?')) return;
    try {
      await fetch(`${API_BASE}/containers/${id}`, { method: 'DELETE' });
      fetchContainers();
    } catch (err) {
      alert('Silme işlemi başarısız oldu.');
    }
  };

  const connectToLogs = (deployId) => {
    const ws = new WebSocket(`ws://localhost:8000/ws/logs/${deployId}`);
    ws.onmessage = (event) => {
      if (event.data === "EOF") {
        ws.close();
        return;
      }
      setLogs((prev) => [...prev, event.data]);
    };
    ws.onerror = (err) => console.error("WebSocket Hatası:", err);
  };

  const pollTaskStatus = async (taskId) => {
    try {
      const response = await fetch(`${API_BASE}/status/${taskId}`);
      const data = await response.json();

      if (data.status === 'success') {
        setResult(data);
        setLoading(false);
        fetchContainers();
      } else if (data.status === 'error') {
        setError(data.message || 'Deploy sırasında bir hata oluştu.');
        setLoading(false);
      } else {
        setTimeout(() => pollTaskStatus(taskId), 3000);
      }
    } catch (err) {
      setError('Durum sorgulanırken sunucuya ulaşılamadı.');
      setLoading(false);
    }
  };

  const handleDeploy = async (e) => {
    e.preventDefault();
    if (!repoUrl) return;

    setLoading(true);
    setResult(null);
    setError('');
    setLogs([]);

    try {
      const response = await fetch(`${API_BASE}/deploy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo_url: repoUrl,
          project_id: selectedProjectId || undefined
        }),
      });

      const data = await response.json();

      if (data.status === 'processing') {
        connectToLogs(data.deploy_id);
        pollTaskStatus(data.task_id);
      } else if (data.status === 'error') {
        setError(data.message);
        setLoading(false);
      }
    } catch (err) {
      setError('Backend sunucusuna ulaşılamadı.');
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col items-center py-8 px-4 font-sans">
      
      {/* HEADER / AUTH STATUS */}
      <header className="w-full max-w-5xl flex justify-between items-center pb-6 border-b border-gray-800 mb-8">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-purple-600 flex items-center justify-center font-extrabold text-xl shadow-lg">
            CF
          </div>
          <span className="text-2xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-400">
            CloudForge
          </span>
        </div>

        <div>
          {user ? (
            <div className="flex items-center gap-4">
              <span className="text-sm font-semibold text-gray-300 bg-gray-900 border border-gray-800 px-3 py-1.5 rounded-full flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-green-500 animate-pulse"></span>
                👤 {user.username}
              </span>
              <button
                onClick={handleLogout}
                className="text-xs bg-red-950/60 hover:bg-red-900/80 text-red-400 border border-red-800/50 px-3 py-1.5 rounded-lg transition-colors font-medium"
              >
                Çıkış Yap
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowAuthModal(true)}
              className="bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold px-5 py-2 rounded-lg transition-all shadow-md hover:shadow-blue-500/20"
            >
              Giriş Yap / Kaydol 🔑
            </button>
          )}
        </div>
      </header>

      {/* AUTH MODAL */}
      {showAuthModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-2xl w-full max-w-md p-6 shadow-2xl relative">
            <button
              onClick={() => setShowAuthModal(false)}
              className="absolute top-4 right-4 text-gray-400 hover:text-white text-lg font-bold"
            >
              ✕
            </button>

            <div className="flex border-b border-gray-800 mb-6">
              <button
                onClick={() => setAuthMode('login')}
                className={`flex-1 pb-3 text-center text-sm font-bold border-b-2 transition-all ${
                  authMode === 'login' ? 'border-blue-500 text-blue-400' : 'border-transparent text-gray-500'
                }`}
              >
                Giriş Yap
              </button>
              <button
                onClick={() => setAuthMode('register')}
                className={`flex-1 pb-3 text-center text-sm font-bold border-b-2 transition-all ${
                  authMode === 'register' ? 'border-blue-500 text-blue-400' : 'border-transparent text-gray-500'
                }`}
              >
                Hesap Oluştur
              </button>
            </div>

            {authError && (
              <div className="mb-4 bg-red-950/60 border border-red-700/50 text-red-300 text-xs p-3 rounded-lg">
                ⚠️ {authError}
              </div>
            )}

            <form onSubmit={handleAuthSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-400 mb-1">
                  Kullanıcı Adı {authMode === 'login' && '/ E-Posta'}
                </label>
                <input
                  type="text"
                  required
                  placeholder="Kullanıcı adı"
                  className="w-full bg-gray-950 border border-gray-700 rounded-lg px-4 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500"
                  value={authForm.username}
                  onChange={(e) => setAuthForm({ ...authForm, username: e.target.value })}
                />
              </div>

              {authMode === 'register' && (
                <div>
                  <label className="block text-xs font-semibold text-gray-400 mb-1">E-Posta Adresi</label>
                  <input
                    type="email"
                    required
                    placeholder="ornek@cloudforge.dev"
                    className="w-full bg-gray-950 border border-gray-700 rounded-lg px-4 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500"
                    value={authForm.email}
                    onChange={(e) => setAuthForm({ ...authForm, email: e.target.value })}
                  />
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-gray-400 mb-1">Parola</label>
                <input
                  type="password"
                  required
                  placeholder="••••••••"
                  className="w-full bg-gray-950 border border-gray-700 rounded-lg px-4 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500"
                  value={authForm.password}
                  onChange={(e) => setAuthForm({ ...authForm, password: e.target.value })}
                />
              </div>

              <button
                type="submit"
                className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 rounded-lg transition-all mt-2 shadow-lg shadow-blue-600/20"
              >
                {authMode === 'login' ? 'Giriş Yap' : 'Kayıt Ol'}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* DEPLOY FORM */}
      <div className="w-full max-w-4xl bg-gray-900 border border-gray-800 p-6 rounded-2xl shadow-xl mb-8">
        <h2 className="text-xl font-extrabold text-gray-100 mb-2">🚀 Yeni Uygulama Deploy Et</h2>
        <p className="text-gray-400 text-xs mb-6">GitHub repository URL'nizi girin ve seçili projenizin secrets değerleriyle canlıya alın.</p>

        <form onSubmit={handleDeploy} className="space-y-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <input
              type="url"
              required
              placeholder="https://github.com/kullanici/repo"
              className="flex-1 bg-gray-950 border border-gray-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              disabled={loading}
            />

            <select
              className="bg-gray-950 border border-gray-700 text-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={selectedProjectId}
              onChange={(e) => setSelectedProjectId(e.target.value)}
            >
              <option value="">-- Proje Seçilmedi (Bağımsız) --</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>📁 {p.name}</option>
              ))}
            </select>

            <button
              type="submit"
              disabled={loading}
              className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-bold py-3 px-8 rounded-xl transition-all disabled:opacity-50 flex items-center justify-center min-w-[180px] shadow-lg shadow-blue-600/20"
            >
              {loading ? 'Deploying...' : 'Deploy Et 🚀'}
            </button>
          </div>

          <div className="flex justify-between items-center pt-2">
            <button
              type="button"
              onClick={() => setShowNewProjectForm(!showNewProjectForm)}
              className="text-xs text-blue-400 hover:text-blue-300 transition-colors font-medium flex items-center gap-1"
            >
              ➕ Yeni Proje Kaydı Oluştur
            </button>
          </div>
        </form>

        {/* PROJE OLUŞTURMA İÇ FORMU */}
        {showNewProjectForm && (
          <form onSubmit={handleCreateProject} className="mt-4 pt-4 border-t border-gray-800 flex gap-3">
            <input
              type="text"
              required
              placeholder="Proje Adı (örn: E-Ticaret API)"
              className="flex-1 bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
            />
            <button
              type="submit"
              className="bg-green-600 hover:bg-green-500 text-white text-xs font-bold px-4 py-2 rounded-lg transition-colors"
            >
              Kaydet
            </button>
          </form>
        )}
      </div>

      {/* SECRETS / ORTAM DEĞİŞKENLERİ YÖNETİM PANELİ */}
      {selectedProjectId && (
        <div className="w-full max-w-4xl bg-gray-900 border border-gray-800 p-6 rounded-2xl shadow-xl mb-8">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h3 className="text-lg font-bold text-gray-100 flex items-center gap-2">
                🔒 Güvenli Ortam Değişkenleri (Secrets)
              </h3>
              <p className="text-xs text-gray-400">
                Seçili projeye ait hassas şifreler (DATABASE_URL, API_KEY vb.) AES ile veritabanında şifrelenir.
              </p>
            </div>
            <span className="text-xs bg-purple-950/60 text-purple-400 border border-purple-800/50 px-2.5 py-1 rounded-full font-mono">
              Proje ID: {selectedProjectId.substring(0, 8)}...
            </span>
          </div>

          {/* Yeni Secret Ekleme Formu */}
          <form onSubmit={handleAddEnv} className="grid grid-cols-1 sm:grid-cols-4 gap-3 mb-6 bg-gray-950 p-4 rounded-xl border border-gray-800">
            <input
              type="text"
              required
              placeholder="KEY (örn: DATABASE_URL)"
              className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-xs text-white uppercase tracking-wider font-mono focus:outline-none focus:border-blue-500"
              value={newEnv.key}
              onChange={(e) => setNewEnv({ ...newEnv, key: e.target.value.toUpperCase() })}
            />
            <input
              type="password"
              required
              placeholder="VALUE (örn: postgres://...)"
              className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-blue-500"
              value={newEnv.value}
              onChange={(e) => setNewEnv({ ...newEnv, value: e.target.value })}
            />
            <select
              className="bg-gray-900 border border-gray-700 text-gray-300 rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-blue-500"
              value={newEnv.environment}
              onChange={(e) => setNewEnv({ ...newEnv, environment: e.target.value })}
            >
              <option value="production">production</option>
              <option value="preview">preview</option>
              <option value="all">all environments</option>
            </select>
            <button
              type="submit"
              className="bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold py-2 px-4 rounded-lg transition-colors shadow-md"
            >
              Secret Ekle 🔑
            </button>
          </form>

          {/* Secret Tablosu */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-gray-400 font-mono">
              <thead className="bg-gray-950 text-gray-500 uppercase font-sans">
                <tr>
                  <th className="px-4 py-2.5">Key</th>
                  <th className="px-4 py-2.5">Değer (Maskelenmiş)</th>
                  <th className="px-4 py-2.5">Ortam</th>
                  <th className="px-4 py-2.5 text-right">İşlem</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {envLoading ? (
                  <tr><td colSpan="4" className="py-4 text-center text-gray-500">Yükleniyor...</td></tr>
                ) : envVars.length === 0 ? (
                  <tr><td colSpan="4" className="py-4 text-center text-gray-600">Tanımlanmış ortam değişkeni yok.</td></tr>
                ) : (
                  envVars.map((env) => (
                    <tr key={env.id} className="hover:bg-gray-800/40">
                      <td className="px-4 py-3 font-bold text-gray-200">{env.key}</td>
                      <td className="px-4 py-3 text-purple-400 tracking-widest">{env.value_masked}</td>
                      <td className="px-4 py-3">
                        <span className="px-2 py-0.5 rounded bg-gray-800 text-gray-300 font-sans font-semibold">
                          {env.environment}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => handleDeleteEnv(env.id)}
                          className="text-red-400 hover:text-red-300 font-sans font-medium"
                        >
                          Sil
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* CUSTOM BUILD SETTINGS */}
      {selectedProjectId && (
        <div className="w-full max-w-4xl bg-gray-900 border border-gray-800 p-6 rounded-2xl shadow-xl mb-8">
          <div className="flex justify-between items-start gap-4 mb-5">
            <div>
              <h3 className="text-lg font-bold text-gray-100">⚙️ Custom Build Settings</h3>
              <p className="text-xs text-gray-400">
                Boş bıraktığın alanlarda CloudForge otomatik framework tespitini kullanır.
              </p>
            </div>
            {buildSettingsSaved && (
              <span className="text-xs text-green-400 bg-green-950/60 border border-green-800/50 px-2.5 py-1 rounded-full">
                Kaydedildi
              </span>
            )}
          </div>

          <form onSubmit={handleSaveBuildSettings} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-400 mb-1">Root Directory</label>
              <input
                type="text"
                placeholder="frontend veya apps/web"
                className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-blue-500"
                value={buildSettings.root_directory}
                onChange={(e) => handleBuildSettingsChange('root_directory', e.target.value)}
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 mb-1">Port</label>
              <input
                type="number"
                min="1"
                max="65535"
                placeholder="3000, 5173, 8000"
                className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-blue-500"
                value={buildSettings.port}
                onChange={(e) => handleBuildSettingsChange('port', e.target.value)}
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 mb-1">Install Command</label>
              <input
                type="text"
                placeholder="npm install veya pip install -r requirements.txt"
                className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-blue-500"
                value={buildSettings.install_command}
                onChange={(e) => handleBuildSettingsChange('install_command', e.target.value)}
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 mb-1">Build Command</label>
              <input
                type="text"
                placeholder="npm run build"
                className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-blue-500"
                value={buildSettings.build_command}
                onChange={(e) => handleBuildSettingsChange('build_command', e.target.value)}
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 mb-1">Start Command</label>
              <input
                type="text"
                placeholder="npm start veya uvicorn main:app --host 0.0.0.0 --port 8000"
                className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-blue-500"
                value={buildSettings.start_command}
                onChange={(e) => handleBuildSettingsChange('start_command', e.target.value)}
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 mb-1">Output Directory</label>
              <input
                type="text"
                placeholder="dist veya build"
                className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-blue-500"
                value={buildSettings.output_directory}
                onChange={(e) => handleBuildSettingsChange('output_directory', e.target.value)}
              />
            </div>

            <div className="md:col-span-2 flex justify-end">
              <button
                type="submit"
                disabled={buildSettingsLoading}
                className="bg-blue-600 hover:bg-blue-500 text-white text-sm font-bold py-2.5 px-5 rounded-lg transition-colors disabled:opacity-60"
              >
                {buildSettingsLoading ? 'Kaydediliyor...' : 'Build Ayarlarını Kaydet'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* BUILD LOG TERMINAL */}
      {(loading || logs.length > 0) && (
        <div className="w-full max-w-4xl mb-8 bg-black rounded-2xl shadow-2xl border border-gray-800 overflow-hidden font-mono text-sm">
          <div className="bg-gray-900 px-4 py-2.5 flex items-center gap-2 border-b border-gray-800">
            <div className="w-3 h-3 rounded-full bg-red-500"></div>
            <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
            <span className="text-gray-400 text-xs ml-2 font-bold tracking-widest">BUILD & DEPLOY LOGS</span>
          </div>
          
          <div className="p-4 h-64 overflow-y-auto text-green-400 whitespace-pre-wrap leading-relaxed">
            {logs.map((log, index) => (
              <span key={index}>{log}</span>
            ))}
            <div ref={logsEndRef} />
          </div>
        </div>
      )}

      {error && (
        <div className="mb-8 w-full max-w-4xl bg-red-950/50 border border-red-500/50 text-red-200 p-4 rounded-xl">
          <p className="font-bold">❌ Hata Oluştu</p>
          <p className="text-sm mt-1">{error}</p>
        </div>
      )}

      {result && (
        <div className="mb-8 w-full max-w-4xl bg-green-950/30 border border-green-500/50 p-6 rounded-2xl shadow-xl">
          <h2 className="text-2xl font-bold text-green-400 mb-2">🎉 Uygulama Canlıda!</h2>
          <p className="text-gray-300 text-sm mb-4">{result.details}</p>
          <div className="flex gap-4">
            <a 
              href={result.url} 
              target="_blank" 
              rel="noreferrer"
              className="flex-1 text-center bg-green-600 hover:bg-green-500 text-white font-bold py-3 rounded-xl transition-all shadow-lg shadow-green-600/20"
            >
              Uygulamaya Git 🚀
            </a>
          </div>
        </div>
      )}

      {/* KONTROL PANELİ */}
      <div className="w-full max-w-4xl bg-gray-900 rounded-2xl shadow-2xl border border-gray-800 overflow-hidden">
        <div className="bg-gray-950 px-6 py-4 border-b border-gray-800 flex justify-between items-center">
          <h2 className="text-lg font-bold text-gray-200">Aktif Uygulamalarınız</h2>
          <button onClick={fetchContainers} className="text-xs text-blue-400 hover:text-blue-300 font-semibold transition-colors">
            🔄 Yenile
          </button>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-gray-400">
            <thead className="bg-gray-900/50 text-xs uppercase text-gray-500">
              <tr>
                <th className="px-6 py-3">Uygulama Adı</th>
                <th className="px-6 py-3">Durum</th>
                <th className="px-6 py-3">Port & Link</th>
                <th className="px-6 py-3 text-right">İşlemler</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {containers.length === 0 ? (
                <tr>
                  <td colSpan="4" className="px-6 py-8 text-center text-gray-500">
                    Şu an çalışan veya kayıtlı bir uygulama yok.
                  </td>
                </tr>
              ) : (
                containers.map((container) => (
                  <tr key={container.id} className="hover:bg-gray-800/30">
                    <td className="px-6 py-4 font-mono text-gray-300 font-medium">
                      {container.name}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${
                        container.status === 'running' ? 'bg-green-950 text-green-400 border border-green-800/50' : 'bg-red-950 text-red-400 border border-red-800/50'
                      }`}>
                        {container.status === 'running' ? '🟢 Çalışıyor' : '🔴 Durdu'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {container.status === 'running' && container.port !== 'Bilinmiyor' ? (
                        <a 
                          href={`http://localhost:${container.port}`} 
                          target="_blank" 
                          rel="noreferrer"
                          className="text-blue-400 hover:text-blue-300 hover:underline font-mono font-semibold"
                        >
                          :{container.port} ↗
                        </a>
                      ) : (
                        <span className="text-gray-600">-</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right space-x-2">
                      {container.status === 'running' && (
                        <button 
                          onClick={() => handleStop(container.id)}
                          className="px-3 py-1 bg-yellow-950/60 text-yellow-500 hover:bg-yellow-900/80 rounded-lg border border-yellow-800/50 text-xs font-semibold transition-colors"
                        >
                          Durdur
                        </button>
                      )}
                      <button 
                        onClick={() => handleDelete(container.id)}
                        className="px-3 py-1 bg-red-950/60 text-red-400 hover:bg-red-900/80 rounded-lg border border-red-800/50 text-xs font-semibold transition-colors"
                      >
                        Sil
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}

export default App;
