/**
 * client_workflow_fixed.js - クライアントワークフローのJavaScript機能
 */

let clientId = null;
let currentStep = 1;
let selectedScriptId = null;
let processedVideoId = null;
let subtitleIds = [];
let selectedBgmId = null;

function loadSession() {
    try {
        const sessionData = localStorage.getItem('clientWorkflowSession');
        if (sessionData) {
            const data = JSON.parse(sessionData);
            clientId = data.clientId || null;
            currentStep = data.currentStep || 1;
            selectedScriptId = data.selectedScriptId || null;
            processedVideoId = data.processedVideoId || null;
            subtitleIds = data.subtitleIds || [];
            selectedBgmId = data.selectedBgmId || null;
            return true;
        }
    } catch (error) {
        console.error('セッションの読み込みに失敗しました:', error);
    }
    return false;
}

function saveSession() {
    try {
        const sessionData = {
            clientId,
            currentStep,
            selectedScriptId,
            processedVideoId,
            subtitleIds,
            selectedBgmId
        };
        localStorage.setItem('clientWorkflowSession', JSON.stringify(sessionData));
    } catch (error) {
        console.error('セッションの保存に失敗しました:', error);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    if (loadSession() && currentStep > 1) {
        goToStep(currentStep);
    } else {
        goToStep(1);
    }
    
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
                sns_platform: Array.from(document.querySelectorAll('.platform:checked')).map(el => el.value),
                description: document.getElementById('companyDescription').value,
                youtube_urls: document.getElementById('youtubeUrls').value.split('\n').filter(url => url.trim() !== '')
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
                    clientId = data.clientId; // グローバル変数に保存
                    saveSession(); // セッションに保存
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
    console.log('Fetching script proposals for clientId:', clientId);
    fetch(`/api/get-script-proposals?clientId=${clientId}`)
    .then(response => response.json())
    .then(data => {
        console.log('Script proposals response:', data);
        if (data.success) {
            displayScriptProposals(data.proposals);
            
            goToStep(3);
        } else {
            alert('台本提案の取得に失敗しました: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error fetching script proposals:', error);
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
                <div class="card-footer text-center">
                    <button class="btn btn-sm btn-outline-primary select-script-btn">選択</button>
                </div>
            </div>
        `;
        
        container.appendChild(proposalElement);
    });
    
    setTimeout(() => {
        document.querySelectorAll('.select-script-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const proposalCard = this.closest('.script-proposal');
                const proposalId = proposalCard.dataset.proposalId;
                
                console.log('Script proposal selected:', proposalId);
                showScriptDetailModal(proposalId);
            });
        });
    }, 100);
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

function showScriptDetailModal(proposalId) {
    console.log('showScriptDetailModal called with proposalId:', proposalId);
    const proposals = document.querySelectorAll('.script-proposal');
    let selectedProposal = null;
    
    proposals.forEach(proposal => {
        if (proposal.dataset.proposalId === proposalId) {
            selectedProposal = proposal;
            proposal.classList.add('selected');
        } else {
            proposal.classList.remove('selected');
        }
    });
    
    if (!selectedProposal) {
        console.error('No proposal found with ID:', proposalId);
        return;
    }
    
    console.log('Selected proposal:', selectedProposal);
    const title = selectedProposal.querySelector('.card-header h6').textContent;
    const content = selectedProposal.querySelector('.card-body p').textContent.replace('...', '');
    console.log('Title:', title, 'Content:', content);
    
    let modal = document.getElementById('scriptDetailModal');
    if (!modal) {
        console.log('Creating new modal');
        modal = document.createElement('div');
        modal.id = 'scriptDetailModal';
        modal.className = 'modal fade';
        modal.setAttribute('tabindex', '-1');
        modal.setAttribute('aria-hidden', 'true');
        
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">台本詳細</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <h6 id="modalScriptTitle"></h6>
                        <div class="mb-3">
                            <textarea id="modalScriptContent" class="form-control" rows="10"></textarea>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">閉じる</button>
                        <button type="button" class="btn btn-primary" id="selectThisScriptBtn">この台本を選択</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        document.getElementById('selectThisScriptBtn').addEventListener('click', function() {
            console.log('Script selected with ID:', proposalId);
            selectedScriptId = proposalId;
            saveSession();
            
            try {
                const bsModal = bootstrap.Modal.getInstance(document.getElementById('scriptDetailModal'));
                if (bsModal) {
                    bsModal.hide();
                } else {
                    console.error('Modal instance not found');
                    modal.style.display = 'none';
                    modal.classList.remove('show');
                    document.body.classList.remove('modal-open');
                    const backdrop = document.querySelector('.modal-backdrop');
                    if (backdrop) backdrop.remove();
                }
            } catch (error) {
                console.error('Error hiding modal:', error);
                modal.style.display = 'none';
                modal.classList.remove('show');
                document.body.classList.remove('modal-open');
                const backdrop = document.querySelector('.modal-backdrop');
                if (backdrop) backdrop.remove();
            }
            
            generateShootingInstructions(proposalId);
        });
    } else {
        console.log('Using existing modal');
    }
    
    document.getElementById('modalScriptTitle').textContent = title;
    document.getElementById('modalScriptContent').value = content;
    
    try {
        console.log('Showing modal');
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    } catch (error) {
        console.error('Error showing modal:', error);
        modal.style.display = 'block';
        modal.classList.add('show');
        document.body.classList.add('modal-open');
        const backdrop = document.createElement('div');
        backdrop.className = 'modal-backdrop fade show';
        document.body.appendChild(backdrop);
    }
}

window.goToStep = goToStep;
