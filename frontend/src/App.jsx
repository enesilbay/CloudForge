import { useState, useEffect, useRef } from 'react';

function App() {
  const [repoUrl, setRepoUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [loadingMessage, setLoadingMessage] = useState('Kuyruğa alınıyor...');
  
  const [containers, setContainers] = useState([]);
  
  // YENİ SİHİR: Canlı logları tutacağımız state ve otomatik kaydırma referansı
  const [logs, setLogs] = useState([]);
  const logsEndRef = useRef(null);

  // Loglar her güncellendiğinde en aşağıya otomatik kaydır
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const fetchContainers = async () => {
    try {
      const response = await fetch('http://localhost:8000/containers');
      const data = await response.json();
      if (data.status === 'success') {
        setContainers(data.containers);
      }
    } catch (err) {
      console.error('Konteynerler çekilirken hata oluştu:', err);
    }
  };

  useEffect(() => {
    fetchContainers();
  }, []);

  const handleStop = async (id) => {
    try {
      await fetch(`http://localhost:8000/containers/${id}/stop`, { method: 'POST' });
      fetchContainers();
    } catch (err) {
      alert('Durdurma işlemi başarısız oldu.');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Bu uygulamayı tamamen silmek istediğinize emin misiniz?')) return;
    try {
      await fetch(`http://localhost:8000/containers/${id}`, { method: 'DELETE' });
      fetchContainers();
    } catch (err) {
      alert('Silme işlemi başarısız oldu.');
    }
  };

  // YENİ: WebSocket bağlantısını kuran fonksiyon
  const connectToLogs = (deployId) => {
    // Backend'deki WebSocket rotamıza bağlanıyoruz
    const ws = new WebSocket(`ws://localhost:8000/ws/logs/${deployId}`);
    
    ws.onmessage = (event) => {
      // Eğer backend yayını bitirdiğini (EOF) söylerse bağlantıyı kapat
      if (event.data === "EOF") {
        ws.close();
        return;
      }
      // Gelen log satırını eski logların sonuna ekle
      setLogs((prev) => [...prev, event.data]);
    };

    ws.onerror = (err) => {
      console.error("WebSocket Hatası:", err);
    };
  };

  const pollTaskStatus = async (taskId) => {
    try {
      const response = await fetch(`http://localhost:8000/status/${taskId}`);
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
    setLogs([]); // Yeni deploy başlarken eski logları temizle
    setLoadingMessage('Kuyruğa alınıyor...');

    try {
      const response = await fetch('http://localhost:8000/deploy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_url: repoUrl }),
      });

      const data = await response.json();

      if (data.status === 'processing') {
        setLoadingMessage('İnşa ediliyor...');
        
        // YENİ: Deploy başlar başlamaz Log Radyosuna (WebSocket) bağlan!
        connectToLogs(data.deploy_id);
        
        // İşin bitip bitmediğini sormaya devam et
        pollTaskStatus(data.task_id);
      } else if (data.status === 'error') {
        setError(data.message);
        setLoading(false);
      }
    } catch (err) {
      setError('Backend sunucusuna ulaşılamadı. Uvicorn çalışıyor mu?');
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col items-center py-10 px-4 font-sans">
      
      <div className="text-center mb-10">
        <h1 className="text-5xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-500 mb-4">
          CloudForge
        </h1>
        <p className="text-gray-400 text-lg max-w-md mx-auto">
          Kodunuzu saniyeler içinde canlıya alın.
        </p>
      </div>

      <form onSubmit={handleDeploy} className="w-full max-w-3xl bg-gray-800 p-6 rounded-xl shadow-2xl border border-gray-700 mb-8">
        <div className="flex flex-col sm:flex-row gap-4">
          <input
            type="url"
            required
            placeholder="https://github.com/kullanici/repo"
            className="flex-1 bg-gray-900 border border-gray-600 rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-8 rounded-lg transition-all disabled:opacity-50 flex items-center justify-center min-w-[200px]"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin h-5 w-5 text-white" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                Deploying
              </span>
            ) : (
              'Deploy Et'
            )}
          </button>
        </div>
      </form>

      {/* YENİ SİHİR: CANLI LOG TERMİNALİ */}
      {(loading || logs.length > 0) && (
        <div className="w-full max-w-3xl mb-8 bg-black rounded-xl shadow-2xl border border-gray-700 overflow-hidden font-mono text-sm">
          {/* Terminal Üst Çubuğu (Mac Görünümü) */}
          <div className="bg-gray-800 px-4 py-2 flex items-center gap-2 border-b border-gray-700">
            <div className="w-3 h-3 rounded-full bg-red-500"></div>
            <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
            <span className="text-gray-400 text-xs ml-2 uppercase font-bold tracking-widest">Build Logs</span>
          </div>
          
          {/* Logların Aktığı Alan */}
          <div className="p-4 h-64 overflow-y-auto text-green-400 whitespace-pre-wrap">
            {logs.map((log, index) => (
              <span key={index}>{log}</span>
            ))}
            {/* Sürekli en alta kaydırmak için görünmez bir çapa (anchor) */}
            <div ref={logsEndRef} />
          </div>
        </div>
      )}

      {error && (
        <div className="mb-8 w-full max-w-3xl bg-red-900/50 border border-red-500 text-red-200 p-4 rounded-lg">
          <p className="font-bold">❌ Hata Oluştu</p>
          <p className="text-sm mt-1">{error}</p>
        </div>
      )}

      {result && (
        <div className="mb-8 w-full max-w-3xl bg-green-900/30 border border-green-500 p-6 rounded-lg shadow-lg">
          <h2 className="text-2xl font-bold text-green-400 mb-2">🎉 Uygulama Canlıda!</h2>
          <p className="text-gray-300 mb-4">{result.details}</p>
          <div className="flex gap-4">
            <a 
              href={result.url} 
              target="_blank" 
              rel="noreferrer"
              className="flex-1 text-center bg-green-600 hover:bg-green-500 text-white font-bold py-3 rounded-lg transition-all"
            >
              Uygulamaya Git 🚀
            </a>
          </div>
        </div>
      )}

      {/* KONTROL PANELİ */}
      <div className="w-full max-w-4xl bg-gray-800 rounded-xl shadow-2xl border border-gray-700 overflow-hidden mt-4">
        <div className="bg-gray-900 px-6 py-4 border-b border-gray-700 flex justify-between items-center">
          <h2 className="text-xl font-bold text-gray-200">Aktif Uygulamalarınız</h2>
          <button onClick={fetchContainers} className="text-sm text-blue-400 hover:text-blue-300 transition-colors">
            🔄 Yenile
          </button>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-gray-400">
            <thead className="bg-gray-800/50 text-xs uppercase text-gray-500">
              <tr>
                <th className="px-6 py-3">Uygulama Adı</th>
                <th className="px-6 py-3">Durum</th>
                <th className="px-6 py-3">Port & Link</th>
                <th className="px-6 py-3 text-right">İşlemler</th>
              </tr>
            </thead>
            <tbody>
              {containers.length === 0 ? (
                <tr>
                  <td colSpan="4" className="px-6 py-8 text-center text-gray-500">
                    Şu an çalışan veya kayıtlı bir uygulama yok.
                  </td>
                </tr>
              ) : (
                containers.map((container) => (
                  <tr key={container.id} className="border-b border-gray-700 hover:bg-gray-750">
                    <td className="px-6 py-4 font-mono text-gray-300 font-medium">
                      {container.name}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-bold ${
                        container.status === 'running' ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'
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
                          className="text-blue-400 hover:text-blue-300 hover:underline font-mono"
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
                          className="px-3 py-1 bg-yellow-600/20 text-yellow-500 hover:bg-yellow-600/40 rounded border border-yellow-700/50 transition-colors"
                        >
                          Durdur
                        </button>
                      )}
                      <button 
                        onClick={() => handleDelete(container.id)}
                        className="px-3 py-1 bg-red-600/20 text-red-500 hover:bg-red-600/40 rounded border border-red-700/50 transition-colors"
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