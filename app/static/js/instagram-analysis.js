
document.addEventListener('DOMContentLoaded', function() {
    console.log('Instagram分析機能の初期化');
    
    const instagramForm = document.getElementById('instagramAnalysisForm');
    if (instagramForm) {
        instagramForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            console.log('Instagram分析フォームが送信されました');
            
            const postUrl = document.getElementById('instagramPostUrl').value;
            const clientId = document.getElementById('instagramClientId').value || null;
            
            document.getElementById('instagramAnalysisSpinner').style.display = 'inline-block';
            
            try {
                const formData = new FormData();
                formData.append('post_url', postUrl);
                if (clientId) {
                    formData.append('client_id', clientId);
                }
                
                console.log('APIリクエスト送信: ', postUrl, clientId);
                const response = await fetch('/analyze-instagram-post/', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                console.log('API応答: ', result);
                
                if (result.success) {
                    displayInstagramResult(result);
                    fetchInstagramAnalysisResults();
                } else {
                    alert('エラー: ' + result.error);
                }
            } catch (error) {
                console.error('Instagram分析エラー:', error);
                alert('エラーが発生しました: ' + error);
            } finally {
                document.getElementById('instagramAnalysisSpinner').style.display = 'none';
            }
        });
    }
    
    const refreshButton = document.getElementById('instagramRefreshButton');
    if (refreshButton) {
        refreshButton.addEventListener('click', function() {
            console.log('更新ボタンがクリックされました');
            fetchInstagramAnalysisResults();
        });
    }
    
    const instagramTab = document.querySelector('[data-bs-target="#instagram-analysis"]');
    if (instagramTab) {
        instagramTab.addEventListener('click', function() {
            console.log('Instagram分析タブがクリックされました');
            
            const noDataElements = document.querySelectorAll('#instagram-analysis .no-data');
            noDataElements.forEach(function(element) {
                element.style.display = 'none';
            });
            
            const formCard = document.getElementById('instagramFormCard');
            if (formCard) {
                formCard.style.display = 'block';
            }
            
            fetchInstagramAnalysisResults();
        });
    }
    
    if (window.location.hash === '#instagram-analysis-tab') {
        if (instagramTab) {
            instagramTab.click();
        }
    }
    
    setTimeout(function() {
        fetchInstagramAnalysisResults();
    }, 500);
});

function fetchInstagramAnalysisResults() {
    console.log('Instagram分析結果一覧を取得します');
    const refreshSpinner = document.getElementById('instagramRefreshSpinner');
    if (refreshSpinner) {
        refreshSpinner.style.display = 'inline-block';
    }
    
    fetch('/get-instagram-analysis/')
        .then(response => response.json())
        .then(data => {
            console.log('Instagram分析データを取得しました:', data);
            displayInstagramAnalysis(data);
        })
        .catch(error => {
            console.error('Instagram分析データ取得エラー:', error);
        })
        .finally(() => {
            if (refreshSpinner) {
                refreshSpinner.style.display = 'none';
            }
        });
}

function displayInstagramAnalysis(data) {
    console.log('Instagram分析結果一覧を表示します:', data);
    const tableBody = document.getElementById('instagramAnalysisTable');
    if (!tableBody) {
        console.error('テーブルボディが見つかりません');
        return;
    }
    
    tableBody.innerHTML = '';
    
    if (data && data.length > 0) {
        data.forEach(item => {
            const row = document.createElement('tr');
            
            const idCell = document.createElement('td');
            idCell.textContent = item.id;
            row.appendChild(idCell);
            
            const urlCell = document.createElement('td');
            const urlLink = document.createElement('a');
            urlLink.href = item.post_url;
            urlLink.textContent = item.post_url.substring(0, 30) + '...';
            urlLink.target = '_blank';
            urlCell.appendChild(urlLink);
            row.appendChild(urlCell);
            
            const viewsCell = document.createElement('td');
            viewsCell.textContent = item.views ? item.views.toLocaleString() : 'N/A';
            row.appendChild(viewsCell);
            
            const engagementCell = document.createElement('td');
            const engagementRate = item.engagement_rate ? item.engagement_rate.toFixed(2) + '%' : 'N/A';
            engagementCell.textContent = engagementRate;
            if (item.high_engagement) {
                engagementCell.classList.add('engagement-high');
            } else {
                engagementCell.classList.add('engagement-low');
            }
            row.appendChild(engagementCell);
            
            const highEngagementCell = document.createElement('td');
            highEngagementCell.textContent = item.high_engagement ? '✓' : '✗';
            highEngagementCell.classList.add(item.high_engagement ? 'engagement-high' : 'engagement-low');
            row.appendChild(highEngagementCell);
            
            const transcriptCell = document.createElement('td');
            transcriptCell.textContent = item.transcript ? '✓' : '✗';
            transcriptCell.classList.add(item.transcript ? 'engagement-high' : 'engagement-low');
            row.appendChild(transcriptCell);
            
            const actionCell = document.createElement('td');
            const detailButton = document.createElement('button');
            detailButton.textContent = '詳細';
            detailButton.classList.add('btn', 'btn-sm', 'btn-outline-primary', 'view-details-btn');
            detailButton.setAttribute('data-id', item.id);
            detailButton.addEventListener('click', async () => {
                try {
                    const response = await fetch(`/get-instagram-analysis/${item.id}`);
                    const data = await response.json();
                    if (data) {
                        displayInstagramResult(data);
                    }
                } catch (error) {
                    console.error('詳細取得エラー:', error);
                }
            });
            actionCell.appendChild(detailButton);
            row.appendChild(actionCell);
            
            tableBody.appendChild(row);
        });
    } else {
        const row = document.createElement('tr');
        const cell = document.createElement('td');
        cell.colSpan = 7;
        cell.textContent = 'データがありません';
        cell.style.textAlign = 'center';
        row.appendChild(cell);
        tableBody.appendChild(row);
    }
}

function displayInstagramResult(data) {
    console.log('Instagram分析結果詳細を表示します:', data);
    document.getElementById('instagramResultUrl').textContent = data.post_url;
    document.getElementById('instagramResultViews').textContent = data.views ? data.views.toLocaleString() : 'N/A';
    document.getElementById('instagramResultLikes').textContent = data.likes ? data.likes.toLocaleString() : 'N/A';
    document.getElementById('instagramResultComments').textContent = data.comments ? data.comments.toLocaleString() : 'N/A';
    
    const engagementRate = data.engagement_rate ? data.engagement_rate.toFixed(2) + '%' : 'N/A';
    const engagementEl = document.getElementById('instagramResultEngagement');
    engagementEl.textContent = engagementRate;
    engagementEl.className = data.high_engagement ? 'engagement-high' : 'engagement-low';
    
    document.getElementById('instagramResultHighEngagement').textContent = data.high_engagement ? '✓ 高エンゲージメント' : '✗ 低エンゲージメント';
    document.getElementById('instagramResultHighEngagement').className = data.high_engagement ? 'engagement-high' : 'engagement-low';
    
    document.getElementById('instagramResultCaption').textContent = data.caption || 'N/A';
    document.getElementById('instagramResultHashtags').textContent = data.hashtags || 'N/A';
    document.getElementById('instagramResultPostedAt').textContent = data.posted_at || 'N/A';
    
    const transcriptSection = document.getElementById('instagramTranscriptSection');
    if (data.transcript) {
        document.getElementById('instagramResultTranscript').textContent = data.transcript;
        transcriptSection.style.display = 'block';
    } else {
        transcriptSection.style.display = 'none';
    }
    
    const rewrittenSection = document.getElementById('instagramRewrittenSection');
    if (data.rewritten_script) {
        document.getElementById('instagramResultRewritten').textContent = data.rewritten_script;
        rewrittenSection.style.display = 'block';
    } else {
        rewrittenSection.style.display = 'none';
    }
    
    document.getElementById('instagramResultCard').style.display = 'block';
    document.getElementById('instagramFormCard').style.display = 'none';
}

function backToInstagramForm() {
    document.getElementById('instagramResultCard').style.display = 'none';
    document.getElementById('instagramFormCard').style.display = 'block';
}

function addDetailButtonListeners() {
    const detailButtons = document.querySelectorAll('.view-details-btn');
    detailButtons.forEach(button => {
        button.addEventListener('click', async () => {
            const id = button.getAttribute('data-id');
            try {
                const response = await fetch(`/get-instagram-analysis/${id}`);
                const data = await response.json();
                if (data) {
                    displayInstagramResult(data);
                }
            } catch (error) {
                console.error('詳細取得エラー:', error);
            }
        });
    });
}
