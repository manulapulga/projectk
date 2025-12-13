// pwa-check.js - Railway PWA diagnostics
(function() {
  console.log('=== LitmusQ PWA Diagnostics ===');
  console.log('Domain:', window.location.origin);
  console.log('Protocol:', window.location.protocol);
  console.log('HTTPS:', window.location.protocol === 'https:');
  
  // Check PWA requirements
  function checkPWASupport() {
    const results = {
      https: window.location.protocol === 'https:',
      serviceWorker: 'serviceWorker' in navigator,
      manifest: document.querySelector('link[rel="manifest"]') !== null,
      beforeinstallprompt: false,
      standalone: window.matchMedia('(display-mode: standalone)').matches
    };
    
    console.log('PWA Support Check:', results);
    return results;
  }
  
  // Display install button if supported
  function showInstallButton() {
    const installBtn = document.createElement('button');
    installBtn.id = 'pwa-install-btn';
    installBtn.innerHTML = '📱 Install LitmusQ';
    installBtn.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      background: linear-gradient(135deg, #21918e, #dc56e8);
      color: white;
      border: none;
      padding: 12px 20px;
      border-radius: 25px;
      font-weight: bold;
      cursor: pointer;
      z-index: 10000;
      box-shadow: 0 4px 15px rgba(0,0,0,0.2);
      font-size: 14px;
    `;
    
    document.body.appendChild(installBtn);
    return installBtn;
  }
  
  // Check and setup PWA
  window.addEventListener('load', async () => {
    const pwaSupport = checkPWASupport();
    
    // Register service worker
    if (pwaSupport.serviceWorker && pwaSupport.https) {
      try {
        const registration = await navigator.serviceWorker.register('/service-worker.js', {
          scope: '/'
        });
        console.log('ServiceWorker registration successful:', registration);
        
        // Check for updates
        if (registration.waiting) {
          console.log('New service worker waiting');
        }
        
        if (registration.installing) {
          console.log('Service worker installing');
        }
        
        if (registration.active) {
          console.log('Service worker active');
        }
      } catch (error) {
        console.error('ServiceWorker registration failed:', error);
      }
    }
    
    // Handle install prompt
    let deferredPrompt;
    
    window.addEventListener('beforeinstallprompt', (e) => {
      console.log('beforeinstallprompt event fired');
      e.preventDefault();
      deferredPrompt = e;
      
      // Show install button
      const installBtn = showInstallButton();
      
      installBtn.addEventListener('click', async () => {
        if (!deferredPrompt) return;
        
        deferredPrompt.prompt();
        const { outcome } = await deferredPrompt.userChoice;
        console.log(`User response to the install prompt: ${outcome}`);
        
        if (outcome === 'accepted') {
          installBtn.style.display = 'none';
          console.log('PWA installed successfully');
        }
        
        deferredPrompt = null;
      });
    });
    
    // Check if already installed
    if (pwaSupport.standalone) {
      console.log('Already running as installed PWA');
      const installBtn = document.getElementById('pwa-install-btn');
      if (installBtn) installBtn.style.display = 'none';
    }
    
    // Online/offline detection
    window.addEventListener('online', () => {
      console.log('App is online');
      document.body.classList.remove('offline');
    });
    
    window.addEventListener('offline', () => {
      console.log('App is offline');
      document.body.classList.add('offline');
    });
  });
  
  // Add debug info to page (optional)
  if (window.location.search.includes('debug=pwa')) {
    const debugDiv = document.createElement('div');
    debugDiv.style.cssText = `
      position: fixed;
      top: 10px;
      left: 10px;
      background: rgba(0,0,0,0.8);
      color: white;
      padding: 10px;
      border-radius: 5px;
      font-family: monospace;
      font-size: 12px;
      z-index: 10000;
      max-width: 300px;
    `;
    debugDiv.id = 'pwa-debug';
    document.body.appendChild(debugDiv);
    
    setInterval(() => {
      const debugInfo = checkPWASupport();
      document.getElementById('pwa-debug').innerHTML = `
        <div>PWA Debug Info:</div>
        <div>HTTPS: ${debugInfo.https ? '✅' : '❌'}</div>
        <div>ServiceWorker: ${debugInfo.serviceWorker ? '✅' : '❌'}</div>
        <div>Manifest: ${debugInfo.manifest ? '✅' : '❌'}</div>
        <div>Standalone: ${debugInfo.standalone ? '✅' : '❌'}</div>
      `;
    }, 2000);
  }
})();