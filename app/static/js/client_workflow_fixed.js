/**
 * client_workflow_fixed.js - クライアントワークフローのJavaScript機能
 */

document.addEventListener('DOMContentLoaded', function() {
    setupStepNavigation();
    
    setupFormHandlers();
    
    setupScriptProposalSelection();
    
    setupBGMSelection();
    
    setupVideoUpload();
    
    setupSubtitleEditing();
});

function setupStepNavigation() {
    document.querySelectorAll('.step-container').forEach(container => {
        container.style.display = 'none';
    });
    
    const firstStep = document.querySelector('.step-container');
    if (firstStep) {
        firstStep.style.display = 'block';
    }
    
    document.querySelectorAll('.next-step-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const currentStep = this.closest('.step-container');
            const nextStep = currentStep.nextElementSibling;
            
            if (nextStep && nextStep.classList.contains('step-container')) {
                currentStep.style.display = 'none';
                nextStep.style.display = 'block';
                
                updateStepIndicator(nextStep.id);
            }
        });
    });
    
    document.querySelectorAll('.prev-step-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const currentStep = this.closest('.step-container');
            const prevStep = currentStep.previousElementSibling;
            
            if (prevStep && prevStep.classList.contains('step-container')) {
                currentStep.style.display = 'none';
                prevStep.style.display = 'block';
                
                updateStepIndicator(prevStep.id);
            }
        });
    });
    
    document.querySelectorAll('.step-indicator .step').forEach((step, index) => {
        step.addEventListener('click', function() {
            const stepId = `step-${index + 1}`;
            const targetStep = document.getElementById(stepId);
            
            if (targetStep) {
                document.querySelectorAll('.step-container').forEach(container => {
                    container.style.display = 'none';
                });
                
                targetStep.style.display = 'block';
                updateStepIndicator(stepId);
            }
        });
    });
}

function updateStepIndicator(activeStepId) {
    if (!activeStepId) return;
    
    const stepNumber = parseInt(activeStepId.replace('step-', ''));
    
    document.querySelectorAll('.step-indicator .step').forEach((step, index) => {
        step.classList.remove('active', 'completed');
        
        if (index + 1 < stepNumber) {
            step.classList.add('completed');
        } else if (index + 1 === stepNumber) {
            step.classList.add('active');
        }
    });
}

function goToStep(stepNumber) {
    const stepId = `step-${stepNumber}`;
    const targetStep = document.getElementById(stepId);
    
    if (targetStep) {
        document.querySelectorAll('.step-container').forEach(container => {
            container.style.display = 'none';
        });
        
        targetStep.style.display = 'block';
        updateStepIndicator(stepId);
    }
}

function setupFormHandlers() {
    const clientInfoForm = document.getElementById('clientInfoForm');
    if (clientInfoForm) {
        clientInfoForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const clientData = {
                name: document.getElementById('clientName').value,
                email: document.getElementById('clientEmail').value,
                purposes: Array.from(document.querySelectorAll('.purpose:checked')).map(el => el.value),
                targetAttributes: Array.from(document.querySelectorAll('.target-attr:checked')).map(el => el.value),
                targetInterests: document.getElementById('targetInterests').value,
                platforms: Array.from(document.querySelectorAll('.platform:checked')).map(el => el.value),
                companyDescription: document.getElementById('companyDescription').value,
                youtubeUrls: document.getElementById('youtubeUrls').value
            };
            
            fetch('/api/save-client-info', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(clientData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    goToStep(2);
                    
                    startAutoResearch(data.clientId);
                } else {
                    alert('エラーが発生しました: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('エラーが発生しました。もう一度お試しください。');
            });
        });
    }
}

function startAutoResearch(clientId) {
    const progressBar = document.getElementById('researchProgressBar');
    const statusElement = document.getElementById('researchStatus');
    
    let progress = 0;
    const interval = setInterval(() => {
        progress += 5;
        if (progress > 100) {
            clearInterval(interval);
            
            getScriptProposals(clientId);
            return;
        }
        
        progressBar.style.width = `${progress}%`;
        progressBar.textContent = `${progress}%`;
        
        if (progress < 30) {
            statusElement.innerHTML = '<p><i class="bi bi-search"></i> 競合分析を実行中...</p>';
        } else if (progress < 60) {
            statusElement.innerHTML = '<p><i class="bi bi-graph-up"></i> エンゲージメント調査中...</p>';
        } else if (progress < 90) {
            statusElement.innerHTML = '<p><i class="bi bi-lightning"></i> トレンド分析中...</p>';
        } else {
            statusElement.innerHTML = '<p><i class="bi bi-check-circle"></i> 分析完了！台本提案を生成中...</p>';
        }
    }, 200);
}

function getScriptProposals(clientId) {
    fetch(`/api/get-script-proposals?clientId=${clientId}`)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            displayScriptProposals(data.proposals);
            
            goToStep(3);
        } else {
            alert('台本提案の取得に失敗しました: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('台本提案の取得中にエラーが発生しました。');
    });
}

function displayScriptProposals(proposals) {
    const container = document.getElementById('scriptProposalsContainer');
    if (!container) return;
    
    container.innerHTML = '';
    
    proposals.forEach((proposal, index) => {
        const proposalElement = document.createElement('div');
        proposalElement.className = 'col-md-4 mb-3';
        proposalElement.innerHTML = `
            <div class="card script-proposal" data-proposal-id="${proposal.id}">
                <div class="card-header">
                    <h6 class="mb-0">${proposal.title}</h6>
                </div>
                <div class="card-body">
                    <p>${proposal.content.substring(0, 150)}...</p>
                </div>
                <div class="card-footer">
                    <button class="btn btn-sm btn-outline-primary view-script-btn">詳細を見る</button>
                </div>
            </div>
        `;
        
        container.appendChild(proposalElement);
    });
    
    document.querySelectorAll('.view-script-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const proposalCard = this.closest('.script-proposal');
            const proposalId = proposalCard.dataset.proposalId;
            
            showScriptDetailModal(proposalId);
        });
    });
}

function setupScriptProposalSelection() {
    document.addEventListener('click', function(e) {
        if (e.target.closest('.script-proposal')) {
            const proposalCard = e.target.closest('.script-proposal');
            
            document.querySelectorAll('.script-proposal').forEach(card => {
                card.classList.remove('selected');
            });
            
            proposalCard.classList.add('selected');
        }
    });
    
    const selectScriptBtn = document.getElementById('selectScriptBtn');
    if (selectScriptBtn) {
        selectScriptBtn.addEventListener('click', function() {
            const selectedProposal = document.querySelector('.script-proposal.selected');
            if (!selectedProposal) {
                alert('台本を選択してください');
                return;
            }
            
            const proposalId = selectedProposal.dataset.proposalId;
            
            generateShootingInstructions(proposalId);
        });
    }
}

function generateShootingInstructions(proposalId) {
    fetch(`/api/generate-shooting-instructions?proposalId=${proposalId}`)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById('shootingInstructionsContent').innerHTML = data.instructions;
            
            goToStep(4);
        } else {
            alert('撮影指示書の生成に失敗しました: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('撮影指示書の生成中にエラーが発生しました。');
    });
}

function setupVideoUpload() {
    const videoUploadForm = document.getElementById('videoUploadForm');
    if (videoUploadForm) {
        videoUploadForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            
            document.getElementById('uploadSpinner').style.display = 'block';
            
            fetch('/api/upload-video', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('uploadSpinner').style.display = 'none';
                
                if (data.success) {
                    document.getElementById('uploadedVideoPreview').src = data.videoUrl;
                    document.getElementById('uploadedVideoContainer').style.display = 'block';
                    
                    document.getElementById('goToEditBtn').disabled = false;
                } else {
                    alert('動画アップロードに失敗しました: ' + data.message);
                }
            })
            .catch(error => {
                document.getElementById('uploadSpinner').style.display = 'none';
                console.error('Error:', error);
                alert('動画アップロード中にエラーが発生しました。');
            });
        });
    }
}

function setupBGMSelection() {
    document.addEventListener('click', function(e) {
        if (e.target.closest('.bgm-item')) {
            const bgmItem = e.target.closest('.bgm-item');
            
            document.querySelectorAll('.bgm-item').forEach(item => {
                item.classList.remove('selected');
            });
            
            bgmItem.classList.add('selected');
            
            const audioPreview = document.getElementById('bgmAudioPreview');
            if (audioPreview) {
                audioPreview.src = bgmItem.dataset.audioUrl;
                audioPreview.play();
            }
        }
    });
    
    const selectBGMBtn = document.getElementById('selectBGMBtn');
    if (selectBGMBtn) {
        selectBGMBtn.addEventListener('click', function() {
            const selectedBGM = document.querySelector('.bgm-item.selected');
            if (!selectedBGM) {
                alert('BGMを選択してください');
                return;
            }
            
            const bgmId = selectedBGM.dataset.bgmId;
            
            applyBGMToVideo(bgmId);
        });
    }
}

function setupSubtitleEditing() {
    document.addEventListener('input', function(e) {
        if (e.target.classList.contains('subtitle-text-input')) {
            const subtitleId = e.target.dataset.subtitleId;
            const newText = e.target.value;
            
            updateSubtitlePreview(subtitleId, newText);
        }
    });
    
    const saveSubtitlesBtn = document.getElementById('saveSubtitlesBtn');
    if (saveSubtitlesBtn) {
        saveSubtitlesBtn.addEventListener('click', function() {
            const subtitles = [];
            
            document.querySelectorAll('.subtitle-text-input').forEach(input => {
                subtitles.push({
                    id: input.dataset.subtitleId,
                    text: input.value
                });
            });
            
            saveSubtitles(subtitles);
        });
    }
}

window.goToStep = goToStep;
