/**
 * 手動カット調整用JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
  const videoPlayer = document.getElementById('videoPlayer') || document.getElementById('videoPreview');
  
  const startSlider = document.getElementById('startTimeSlider');
  const endSlider = document.getElementById('endTimeSlider');
  const startTimeInput = document.getElementById('startTimeInput');
  const endTimeInput = document.getElementById('endTimeInput');
  
  function initSliders() {
    if (!videoPlayer || !startSlider || !endSlider) return;
    
    function setupSliders() {
      const duration = videoPlayer.duration;
      
      startSlider.min = 0;
      startSlider.max = duration;
      startSlider.value = 0;
      
      endSlider.min = 0;
      endSlider.max = duration;
      endSlider.value = duration;
      
      startTimeInput.value = formatTime(0);
      endTimeInput.value = formatTime(duration);
      
      updateRangeHighlight();
    }
    
    document.addEventListener('video-selected', function() {
      console.log('Video selected event received');
    });
    
    document.addEventListener('video-loaded', function() {
      console.log('Video loaded event received');
      if (videoPlayer.readyState >= 1) {
        setupSliders();
      }
    });
    
    videoPlayer.addEventListener('loadedmetadata', function() {
      console.log('Video metadata loaded');
      setupSliders();
    });
    
    startSlider.addEventListener('input', function() {
      const startTime = parseFloat(startSlider.value);
      if (startTime >= parseFloat(endSlider.value)) {
        startSlider.value = endSlider.value - 0.1;
      }
      startTimeInput.value = formatTime(startSlider.value);
      updateRangeHighlight();
    });
    
    endSlider.addEventListener('input', function() {
      const endTime = parseFloat(endSlider.value);
      if (endTime <= parseFloat(startSlider.value)) {
        endSlider.value = parseFloat(startSlider.value) + 0.1;
      }
      endTimeInput.value = formatTime(endSlider.value);
      updateRangeHighlight();
    });
    
    startTimeInput.addEventListener('change', function() {
      const time = parseTimeInput(startTimeInput.value);
      startSlider.value = time;
      updateRangeHighlight();
    });
    
    endTimeInput.addEventListener('change', function() {
      const time = parseTimeInput(endTimeInput.value);
      endSlider.value = time;
      updateRangeHighlight();
    });
  }
  
  function formatTime(seconds) {
    const min = Math.floor(seconds / 60);
    const sec = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 10);
    return `${min.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}.${ms}`;
  }
  
  function parseTimeInput(timeStr) {
    const parts = timeStr.split(':');
    if (parts.length !== 2) return 0;
    
    const minSec = parts[1].split('.');
    const min = parseInt(parts[0], 10);
    const sec = parseInt(minSec[0], 10);
    const ms = minSec.length > 1 ? parseInt(minSec[1], 10) / 10 : 0;
    
    return min * 60 + sec + ms;
  }
  
  function updateRangeHighlight() {
    const startVal = parseFloat(startSlider.value);
    const endVal = parseFloat(endSlider.value);
    const duration = parseFloat(videoPlayer.duration);
    
    const startPercent = (startVal / duration) * 100;
    const endPercent = (endVal / duration) * 100;
    
    document.documentElement.style.setProperty('--start-percent', `${startPercent}%`);
    document.documentElement.style.setProperty('--end-percent', `${endPercent}%`);
  }
  
  document.getElementById('previewRangeBtn')?.addEventListener('click', function() {
    videoPlayer.currentTime = parseFloat(startSlider.value);
    videoPlayer.play();
    
    const previewEnd = parseFloat(endSlider.value);
    const checkEnd = function() {
      if (videoPlayer.currentTime >= previewEnd) {
        videoPlayer.pause();
        videoPlayer.removeEventListener('timeupdate', checkEnd);
      }
    };
    
    videoPlayer.addEventListener('timeupdate', checkEnd);
  });
  
  document.getElementById('applyRangeBtn')?.addEventListener('click', function() {
    const startTime = parseFloat(startSlider.value);
    const endTime = parseFloat(endSlider.value);
    let videoId = document.getElementById('videoId')?.value;
    
    if (!videoId) {
      console.error('videoId not found, checking selectedVideoId from voice-edit.js');
      if (window.selectedVideoId) {
        console.log('Using selectedVideoId from voice-edit.js:', window.selectedVideoId);
        videoId = window.selectedVideoId;
      } else {
        showMessage('エラー: 動画IDが見つかりません', 'error');
        return;
      }
    }
    
    console.log('Applying range edit with videoId:', videoId);
    
    const editCommand = {
      type: 'cut',
      start_time: startTime,
      end_time: endTime,
      video_id: videoId
    };
    
    fetch('/api/edit-range', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(editCommand)
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        showMessage('範囲の編集が適用されました', 'success');
        if (data.processed_video_url) {
          videoPlayer.src = data.processed_video_url;
          
          const videoIdInput = document.getElementById('videoId');
          if (videoIdInput && data.edit_id) {
            videoIdInput.value = 'history_' + data.edit_id;
          }
        }
      } else {
        showMessage('エラー: ' + (data.message || '不明なエラー'), 'error');
      }
    })
    .catch(error => {
      showMessage('エラー: ' + error.message, 'error');
    });
  });
  
  function showMessage(message, type) {
    const messagesElement = document.getElementById('statusMessages');
    if (!messagesElement) return;
    
    const messageElement = document.createElement('div');
    messageElement.className = `alert alert-${type === 'success' ? 'success' : 'danger'}`;
    messageElement.innerText = message;
    messagesElement.appendChild(messageElement);
    
    setTimeout(() => {
      messagesElement.removeChild(messageElement);
    }, 5000);
  }
  
  initSliders();
});
