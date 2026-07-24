import { useState } from 'react';

function App() {
  const [repoUrl, setRepoUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [loadingMessage, setLoadingMessage] = useState('Kuyruğa alınıyor...');

  // YENİ SİHİR: Backend'e 3 saniyede bir "İşim bitti mi?" diye soran fonksiyon
  const pollTaskStatus = async (taskId) => {
    try {
      const response = await fetch(`http://localhost:8000/status/${taskId}`);
      const data = await response.json();

      if (data.status === 'success') {
        // İşlem bitti, yeşil ekranı göster
        setResult(data);
        setLoading(false);
      } else if (data.status === 'error') {
        // İşlem sırasında hata çıktı
        setError(data.message || 'Deploy sırasında bir hata oluştu.');
        setLoading(false);
      } else {
        // İşlem hala devam ediyor (processing), 3 saniye bekle ve tekrar sor
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
    setLoadingMessage('Kuyruğa alınıyor...');

    try {
      // 1. Siparişi ver (Sadece birkaç milisaniye sürecek)
      const response = await fetch('http://localhost:8000/deploy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_url: repoUrl }),
      });

      const data = await response.json();

      if (data.status === 'processing') {
        setLoadingMessage('İnşa ediliyor (1-2 dakika sürebilir)...');
        // 2. Takip numarasını (task_id) aldık, yoklama (polling) sürecini başlat
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
    <div className="min-h-screen bg-gray-900 text-white flex flex-col items-center justify-center p-4 font-sans">
      
      <div className="text-center mb-10">
        <h1 className="text-5xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-500 mb-4">
          CloudForge
        </h1>
        <p className="text-gray-400 text-lg max-w-md mx-auto">
          Kodunuzu saniyeler içinde canlıya alın. GitHub linkinizi yapıştırın, gerisini bize bırakın.
        </p>
      </div>

      <form onSubmit={handleDeploy} className="w-full max-w-2xl bg-gray-800 p-6 rounded-xl shadow-2xl border border-gray-700">
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
                {loadingMessage}
              </span>
            ) : (
              'Deploy Et'
            )}
          </button>
        </div>
      </form>

      {error && (
        <div className="mt-8 w-full max-w-2xl bg-red-900/50 border border-red-500 text-red-200 p-4 rounded-lg">
          <p className="font-bold">❌ Hata Oluştu</p>
          <p className="text-sm mt-1">{error}</p>
        </div>
      )}

      {result && (
        <div className="mt-8 w-full max-w-2xl bg-green-900/30 border border-green-500 p-6 rounded-lg shadow-lg">
          <h2 className="text-2xl font-bold text-green-400 mb-2">🎉 Uygulama Canlıda!</h2>
          <p className="text-gray-300 mb-4">{result.details}</p>
          
          <div className="bg-gray-950 p-4 rounded-md font-mono text-sm mb-4 border border-gray-800">
            <p><span className="text-blue-400">Deploy ID:</span> {result.deploy_id}</p>
            <p><span className="text-blue-400">Konteyner:</span> {result.container_name}</p>
          </div>

          <a 
            href={result.url} 
            target="_blank" 
            rel="noreferrer"
            className="inline-block w-full text-center bg-green-600 hover:bg-green-500 text-white font-bold py-3 rounded-lg transition-all"
          >
            Uygulamaya Git 🚀 ({result.url})
          </a>
        </div>
      )}
    </div>
  );
}

export default App;