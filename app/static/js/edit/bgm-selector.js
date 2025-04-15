/**
 * bgm-selector.js - BGM提案と選択のための機能
 */

document.addEventListener('DOMContentLoaded', function() {
  let bgmSuggestionBtn;
  let bgmContainer;
  let bgmList;
  let bgmVolumeSlider;
  let bgmApplyBtn;
  let statusMessages;
  
  function initBgmUI() {
    const videoPreviewContainer = document.getElementById('videoPreviewContainer');
    if (!videoPreviewContainer) return;
    
    if (!document.getElementById('bgmSection')) {
      const bgmSection = document.createElement('div');
      bgmSection.id = 'bgmSection';
      bgmSection.className = 'card mt-3';
      bgmSection.innerHTML = `
        <div class="card-header">
          <h5>BGM提案と選択</h5>
        </div>
        <div class="card-body">
          <button id="bgmSuggestionBtn" class="btn btn-primary mb-3">BGMを提案</button>
          <div id="bgmContainer" class="d-none">
            <div id="bgmSuggestion" class="mb-3 p-3 bg-light rounded"></div>
            <h6>BGMサンプル:</h6>
            <div id="bgmList" class="list-group mb-3"></div>
            <div class="mb-3">
              <label for="bgmVolumeSlider" class="form-label">BGM音量: <span id="bgmVolumeValue">30%</span></label>
              <input type="range" class="form-range" id="bgmVolumeSlider" min="0" max="100" value="30">
            </div>
            <button id="bgmApplyBtn" class="btn btn-success" disabled>選択したBGMを適用</button>
          </div>
        </div>
      `;
      
      videoPreviewContainer.appendChild(bgmSection);
    }
    
    bgmSuggestionBtn = document.getElementById('bgmSuggestionBtn');
    bgmContainer = document.getElementById('bgmContainer');
    bgmList = document.getElementById('bgmList');
    bgmVolumeSlider = document.getElementById('bgmVolumeSlider');
    bgmApplyBtn = document.getElementById('bgmApplyBtn');
    statusMessages = document.getElementById('statusMessages');
    
    if (bgmSuggestionBtn) {
      bgmSuggestionBtn.addEventListener('click', requestBgmSuggestion);
    }
    
    if (bgmVolumeSlider) {
      bgmVolumeSlider.addEventListener('input', updateVolumeDisplay);
    }
    
    if (bgmApplyBtn) {
      bgmApplyBtn.addEventListener('click', applySelectedBgm);
    }
  }
  
  function requestBgmSuggestion() {
    const videoId = document.getElementById('videoId')?.value;
    
    if (!videoId) {
      showMessage('エラー: 動画IDが見つかりません', 'error');
      return;
    }
    
    bgmSuggestionBtn.disabled = true;
    bgmSuggestionBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 分析中...';
    
    fetch('/api/suggest-bgm', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        video_id: videoId
      })
    })
    .then(response => response.json())
    .then(data => {
      bgmSuggestionBtn.disabled = false;
      bgmSuggestionBtn.textContent = 'BGMを提案';
      
      if (data.success) {
        showBgmSuggestion(data.suggestion, data.bgm_samples);
      } else {
        showMessage('エラー: ' + (data.message || '不明なエラー'), 'error');
      }
    })
    .catch(error => {
      bgmSuggestionBtn.disabled = false;
      bgmSuggestionBtn.textContent = 'BGMを提案';
      showMessage('エラー: ' + error.message, 'error');
    });
  }
  
  function showBgmSuggestion(suggestion, bgmSamples) {
    const bgmSuggestionElement = document.getElementById('bgmSuggestion');
    if (bgmSuggestionElement) {
      bgmSuggestionElement.textContent = suggestion;
    }
    
    if (bgmList) {
      bgmList.innerHTML = '';
      
      bgmSamples.forEach(bgm => {
        const bgmItem = document.createElement('div');
        bgmItem.className = 'list-group-item';
        bgmItem.innerHTML = `
          <div class="d-flex justify-content-between align-items-center">
            <div>
              <input type="radio" name="bgmSelection" id="bgm_${bgm.id}" value="${bgm.id}" class="me-2">
              <label for="bgm_${bgm.id}">${bgm.name} (${bgm.genre})</label>
            </div>
            <audio src="${bgm.url}" controls preload="none" style="max-width: 200px;"></audio>
          </div>
        `;
        
        bgmList.appendChild(bgmItem);
        
        const radioBtn = bgmItem.querySelector(`#bgm_${bgm.id}`);
        if (radioBtn) {
          radioBtn.addEventListener('change', function() {
            bgmApplyBtn.disabled = false;
          });
        }
      });
    }
    
    if (bgmContainer) {
      bgmContainer.classList.remove('d-none');
    }
  }
  
  function updateVolumeDisplay() {
    const volumeValue = document.getElementById('bgmVolumeValue');
    if (volumeValue && bgmVolumeSlider) {
      volumeValue.textContent = `${bgmVolumeSlider.value}%`;
    }
  }
  
  function applySelectedBgm() {
    const videoId = document.getElementById('videoId')?.value;
    const selectedBgm = document.querySelector('input[name="bgmSelection"]:checked');
    const volume = bgmVolumeSlider ? parseFloat(bgmVolumeSlider.value) / 100 : 0.3;
    
    if (!videoId) {
      showMessage('エラー: 動画IDが見つかりません', 'error');
      return;
    }
    
    if (!selectedBgm) {
      showMessage('エラー: BGMが選択されていません', 'error');
      return;
    }
    
    bgmApplyBtn.disabled = true;
    bgmApplyBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 処理中...';
    
    fetch('/api/apply-bgm', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        video_id: videoId,
        bgm_id: selectedBgm.value,
        volume: volume
      })
    })
    .then(response => response.json())
    .then(data => {
      bgmApplyBtn.disabled = false;
      bgmApplyBtn.textContent = '選択したBGMを適用';
      
      if (data.success) {
        showMessage('BGMを適用しました', 'success');
        if (data.processed_video_url) {
          const videoPlayer = document.getElementById('videoPlayer') || document.getElementById('videoPreview');
          if (videoPlayer) {
            videoPlayer.src = data.processed_video_url;
          }
        }
      } else {
        showMessage('エラー: ' + (data.message || '不明なエラー'), 'error');
      }
    })
    .catch(error => {
      bgmApplyBtn.disabled = false;
      bgmApplyBtn.textContent = '選択したBGMを適用';
      showMessage('エラー: ' + error.message, 'error');
    });
  }
  
  function showMessage(message, type) {
    if (!statusMessages) return;
    
    const messageElement = document.createElement('div');
    messageElement.className = `alert alert-${type === 'success' ? 'success' : 'danger'}`;
    messageElement.innerText = message;
    statusMessages.appendChild(messageElement);
    
    setTimeout(() => {
      statusMessages.removeChild(messageElement);
    }, 5000);
  }
  
  initBgmUI();
});
