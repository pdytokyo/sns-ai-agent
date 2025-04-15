/**
 * subtitle-templates.js - テロップスタイルテンプレート選択のための機能
 */

document.addEventListener('DOMContentLoaded', function() {
  const templatesContainer = document.getElementById('subtitleTemplates');
  const applySubtitleBtn = document.getElementById('applySubtitleBtn');
  
  let selectedTemplateId = 'default';
  
  function loadSubtitleTemplates() {
    fetch('/api/subtitle-templates')
      .then(response => response.json())
      .then(data => {
        if (data.templates && Array.isArray(data.templates)) {
          displayTemplates(data.templates);
        } else {
          console.error('テンプレートデータが正しい形式ではありません');
        }
      })
      .catch(error => {
        console.error('テンプレート取得エラー:', error);
        displayDefaultTemplates();
      });
  }
  
  function displayDefaultTemplates() {
    const defaultTemplates = [
      {
        id: 'default',
        name: '標準',
        font: 'Arial',
        color: 'white',
        bg_color: 'rgba(0, 0, 0, 0.5)'
      },
      {
        id: 'pop',
        name: 'ポップ',
        font: 'Comic Sans MS',
        color: 'yellow',
        bg_color: 'rgba(0, 0, 150, 0.7)'
      },
      {
        id: 'minimal',
        name: 'ミニマル',
        font: 'Helvetica',
        color: 'white',
        bg_color: 'transparent'
      },
      {
        id: 'stylish',
        name: 'スタイリッシュ',
        font: 'Georgia',
        color: '#e0e0e0',
        bg_color: 'rgba(40, 40, 40, 0.9)'
      },
      {
        id: 'bold',
        name: 'ボールド',
        font: 'Impact',
        color: 'white',
        bg_color: 'rgba(220, 53, 69, 0.8)'
      }
    ];
    
    displayTemplates(defaultTemplates);
  }
  
  function displayTemplates(templates) {
    if (!templatesContainer) return;
    
    templatesContainer.innerHTML = '';
    
    templates.forEach(template => {
      const templateCol = document.createElement('div');
      templateCol.className = 'col-md-4 mb-3';
      
      const templateCard = document.createElement('div');
      templateCard.className = 'card h-100 template-card';
      templateCard.dataset.templateId = template.id;
      
      if (template.id === selectedTemplateId) {
        templateCard.classList.add('selected');
      }
      
      const previewStyle = `
        background-color: ${template.bg_color};
        color: ${template.color};
        font-family: ${template.font}, sans-serif;
        padding: 10px;
        text-align: center;
        border-radius: 4px;
      `;
      
      templateCard.innerHTML = `
        <div class="card-body">
          <h6 class="card-title">${template.name}</h6>
          <div class="template-preview" style="${previewStyle}">
            サンプルテキスト
          </div>
        </div>
      `;
      
      templateCard.addEventListener('click', function() {
        document.querySelectorAll('.template-card.selected').forEach(card => {
          card.classList.remove('selected');
        });
        
        this.classList.add('selected');
        selectedTemplateId = this.dataset.templateId;
      });
      
      templateCol.appendChild(templateCard);
      templatesContainer.appendChild(templateCol);
    });
  }
  
  if (applySubtitleBtn) {
    applySubtitleBtn.addEventListener('click', function() {
      const videoId = document.getElementById('videoId')?.value;
      
      if (!videoId) {
        showMessage('エラー: 動画IDが見つかりません', 'error');
        return;
      }
      
      fetch('/api/generate-subtitles', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          video_id: videoId,
          template_id: selectedTemplateId
        })
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          showMessage('テロップを生成しました', 'success');
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
        showMessage('エラー: ' + error.message, 'error');
      });
    });
  }
  
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
  
  loadSubtitleTemplates();
  
  const style = document.createElement('style');
  style.textContent = `
    .template-card {
      cursor: pointer;
      transition: all 0.2s ease;
    }
    .template-card:hover {
      transform: translateY(-5px);
      box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .template-card.selected {
      border: 2px solid #0d6efd;
      box-shadow: 0 0 0 3px rgba(13, 110, 253, 0.25);
    }
    .template-preview {
      margin-top: 10px;
      min-height: 40px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
  `;
  document.head.appendChild(style);
});
