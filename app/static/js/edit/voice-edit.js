
let mediaRecorder;
let audioChunks = [];
let recordingTimer;
let recordingSeconds = 0;
let selectedVideoId = null;
let currentEditCommands = null;
let clientId = localStorage.getItem('clientId') || 'test-client';

window.selectedVideoId = null;

document.addEventListener('DOMContentLoaded', function() {
    initializeUI();
    loadVideos();
    
    document.getElementById('startRecording').addEventListener('click', startRecording);
    document.getElementById('stopRecording').addEventListener('click', stopRecording);
    document.getElementById('submitText').addEventListener('click', submitText);
    document.getElementById('applyEdits').addEventListener('click', applyEdits);
    document.getElementById('rejectEdits').addEventListener('click', resetEditProposal);
    document.getElementById('videoUpload').addEventListener('change', handleVideoUpload);
    document.getElementById('videoSelect').addEventListener('change', handleVideoSelect);
});

function initializeUI() {
    document.getElementById('stopRecording').disabled = true;
    document.getElementById('editProposalContainer').classList.add('d-none');
    document.getElementById('resultContainer').classList.add('d-none');
    
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        console.log('マイクアクセスをサポートしています');
    } else {
        console.error('このブラウザはマイクアクセスをサポートしていません');
        document.getElementById('startRecording').disabled = true;
        document.getElementById('startRecording').textContent = 'マイク非対応';
    }
}

function loadVideos() {
    fetch('/api/get-processed-videos')
        .then(response => response.json())
        .then(videos => {
            const videoSelect = document.getElementById('videoSelect');
            videoSelect.innerHTML = '<option value="">動画を選択してください</option>';
            
            videos.forEach(video => {
                const option = document.createElement('option');
                option.value = video.id;
                option.textContent = video.filename || `動画 #${video.id}`;
                videoSelect.appendChild(option);
            });
        })
        .catch(error => {
            console.error('動画リストの取得に失敗しました:', error);
        });
}

function handleVideoSelect(event) {
    const videoId = event.target.value;
    if (!videoId || typeof videoId !== 'string') return;
    
    selectedVideoId = videoId;
    window.selectedVideoId = videoId;
    
    const videoPreview = document.getElementById('videoPreview') || document.getElementById('videoPlayer');
    const videoPreviewContainer = document.getElementById('videoPreviewContainer');
    
    const videoIdInput = document.getElementById('videoId');
    if (videoIdInput) {
        videoIdInput.value = videoId;
        console.log('videoId set to:', videoId); // デバッグ用
    } else {
        console.error('videoId input field not found');
        const hiddenInput = document.createElement('input');
        hiddenInput.type = 'hidden';
        hiddenInput.id = 'videoId';
        hiddenInput.value = videoId;
        document.body.appendChild(hiddenInput);
        console.log('Created videoId input field with value:', videoId);
    }
    
    const videoLoadedEvent = new Event('video-selected');
    document.dispatchEvent(videoLoadedEvent);
    
    let videoPath = '';
    console.log('処理するビデオID:', videoId);
    
    if (videoId.startsWith('upload_')) {
        const filename = videoId.replace('upload_', '');
        videoPath = `/uploaded_videos/${filename}`;
        console.log('アップロードビデオパス設定:', videoPath);
    } else if (videoId.startsWith('output_')) {
        const filename = videoId.replace('output_', '');
        videoPath = `/static/output/${filename}`;
        console.log('出力ビデオパス設定:', videoPath);
    } else if (videoId.startsWith('history_')) {
        fetch(`/api/edit-commands?id=${videoId.replace('history_', '')}`)
            .then(response => response.json())
            .then(data => {
                if (data && data.length > 0 && data[0].result_path) {
                    const filename = data[0].result_path.split('/').pop();
                    videoPreview.src = `/static/output/${filename}`;
                    videoPreviewContainer.classList.remove('d-none');
                    videoPreview.load();
                    
                    if (videoIdInput) videoIdInput.value = videoId;
                    
                    const videoLoadedEvent = new Event('video-loaded');
                    document.dispatchEvent(videoLoadedEvent);
                }
            })
            .catch(error => {
                console.error('編集履歴の取得に失敗しました:', error);
            });
        return;
    } else if (/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(videoId)) {
        videoPath = `/uploaded_videos/${videoId}.mp4`;
        console.log('UUID形式のビデオID検出、パス設定:', videoPath);
    } else if (videoId.includes('.mp4')) {
        if (videoId.includes('-')) {
            videoPath = `/uploaded_videos/${videoId}`;
            console.log('MP4ファイル名検出、アップロードディレクトリに設定:', videoPath);
        } else {
            videoPath = `/static/uploaded_videos/${videoId}`;
            console.log('その他のMP4ファイル名検出、静的ディレクトリに設定:', videoPath);
        }
    } else {
        fetch(`/video_info/${videoId}`)
            .then(response => response.json())
            .then(data => {
                if (data.video_url) {
                    videoPreview.src = data.video_url;
                    videoPreviewContainer.classList.remove('d-none');
                    videoPreview.load();
                    
                    if (videoIdInput) videoIdInput.value = videoId;
                    
                    const videoLoadedEvent = new Event('video-loaded');
                    document.dispatchEvent(videoLoadedEvent);
                }
            })
            .catch(error => {
                console.error('動画情報の取得に失敗しました:', error);
            });
        return;
    }
    
    videoPreview.src = videoPath;
    videoPreviewContainer.classList.remove('d-none');
    videoPreview.load();
    
    videoPreview.addEventListener('loadedmetadata', function() {
        const videoLoadedEvent = new Event('video-loaded');
        document.dispatchEvent(videoLoadedEvent);
    });
}

function handleVideoUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    if (!file.name.toLowerCase().endsWith('.mp4')) {
        alert('mp4形式の動画ファイルのみアップロード可能です');
        return;
    }
    
    const maxSize = 500 * 1024 * 1024; // 500MB
    if (file.size > maxSize) {
        alert('ファイルサイズは500MB以下にしてください');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('client_id', parseInt(clientId) || 1); // Convert to integer or default to 1
    formData.append('aspect_ratio', '16:9');
    formData.append('margin_seconds', 0.5);
    
    const uploadStatusEl = document.createElement('div');
    uploadStatusEl.className = 'alert alert-info mt-2';
    uploadStatusEl.innerHTML = '<div class="spinner-border spinner-border-sm" role="status"></div> アップロード中...';
    document.getElementById('videoPreviewContainer').before(uploadStatusEl);
    
    fetch('/upload_video/', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        uploadStatusEl.remove();
        
        if (data.video_id) {
            selectedVideoId = data.video_id;
            
            const videoPreview = document.getElementById('videoPreview');
            const videoPreviewContainer = document.getElementById('videoPreviewContainer');
            
            const successEl = document.createElement('div');
            successEl.className = 'alert alert-success mt-2 mb-2';
            successEl.innerHTML = `<strong>アップロード成功:</strong> ${file.name} (ID: ${data.video_id})`;
            videoPreviewContainer.before(successEl);
            
            setTimeout(() => successEl.remove(), 3000);
            
            videoPreview.src = data.video_url;
            videoPreviewContainer.classList.remove('d-none');
            
            loadVideos();
            
            const videoSelect = document.getElementById('videoSelect');
            videoSelect.value = selectedVideoId;
        }
    })
    .catch(error => {
        uploadStatusEl.remove();
        console.error('動画アップロードに失敗しました:', error);
        alert('動画アップロードに失敗しました。');
    });
}

function startRecording() {
    if (!selectedVideoId) {
        alert('先に動画を選択してください');
        return;
    }
    
    audioChunks = [];
    recordingSeconds = 0;
    
    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
            mediaRecorder = new MediaRecorder(stream);
            
            mediaRecorder.ondataavailable = event => {
                audioChunks.push(event.data);
            };
            
            mediaRecorder.onstop = () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                sendAudioForTranscription(audioBlob);
            };
            
            mediaRecorder.start();
            
            document.getElementById('startRecording').disabled = true;
            document.getElementById('stopRecording').disabled = false;
            document.getElementById('recordingStatus').classList.remove('d-none');
            document.getElementById('recordingTime').classList.remove('d-none');
            document.getElementById('startRecording').classList.remove('btn-primary');
            document.getElementById('startRecording').classList.add('btn-secondary');
            document.getElementById('stopRecording').classList.add('recording-active');
            
            startRecordingTimer();
        })
        .catch(error => {
            console.error('マイクアクセスに失敗しました:', error);
            alert('マイクへのアクセスに失敗しました。マイクの使用を許可してください。');
        });
}

function startRecordingTimer() {
    recordingTimer = setInterval(() => {
        recordingSeconds++;
        const minutes = Math.floor(recordingSeconds / 60);
        const seconds = recordingSeconds % 60;
        document.getElementById('recordingTime').textContent = 
            `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }, 1000);
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        mediaRecorder.stream.getTracks().forEach(track => track.stop());
    }
    
    clearInterval(recordingTimer);
    
    document.getElementById('startRecording').disabled = false;
    document.getElementById('stopRecording').disabled = true;
    document.getElementById('recordingStatus').classList.add('d-none');
    document.getElementById('startRecording').classList.remove('btn-secondary');
    document.getElementById('startRecording').classList.add('btn-primary');
    document.getElementById('stopRecording').classList.remove('recording-active');
}

function sendAudioForTranscription(audioBlob) {
    const formData = new FormData();
    formData.append('audio', audioBlob);
    formData.append('client_id', clientId);
    
    fetch('/api/transcribe-audio', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.text) {
            const transcriptionResult = document.getElementById('transcriptionResult');
            transcriptionResult.textContent = data.text;
            transcriptionResult.classList.remove('d-none');
            
            convertToEditCommands(data.text);
        }
    })
    .catch(error => {
        console.error('文字起こしに失敗しました:', error);
        alert('文字起こしに失敗しました。');
    });
}

function submitText() {
    const text = document.getElementById('textInput').value.trim();
    if (!text) {
        alert('テキストを入力してください');
        return;
    }
    
    if (!selectedVideoId) {
        alert('先に動画を選択してください');
        return;
    }
    
    const transcriptionResult = document.getElementById('transcriptionResult');
    transcriptionResult.textContent = text;
    transcriptionResult.classList.remove('d-none');
    
    convertToEditCommands(text);
}

function convertToEditCommands(text) {
    let videoMetadata = null;
    
    if (selectedVideoId && typeof selectedVideoId === 'string') {
        if (selectedVideoId.startsWith('upload_') || selectedVideoId.startsWith('output_') || selectedVideoId.startsWith('history_')) {
            const videoPath = document.getElementById('videoPreview').src;
            videoMetadata = {
                video_path: videoPath,
                original_duration: 0, // 実際の値は不明なので0をデフォルトとする
                processed_duration: 0,
                reduction_percentage: 0,
                aspect_ratio: '16:9'
            };
            sendEditRequest(text, videoMetadata);
        } else {
            fetch(`/video_info/${selectedVideoId}`)
                .then(response => response.json())
                .then(data => {
                    videoMetadata = data;
                    sendEditRequest(text, videoMetadata);
                })
                .catch(error => {
                    console.error('動画情報の取得に失敗しました:', error);
                    sendEditRequest(text, null);
                });
        }
    } else {
        sendEditRequest(text, null);
    }
}

function sendEditRequest(text, videoMetadata) {
    const requestData = {
        text: text,
        video_id: selectedVideoId,
        video_metadata: videoMetadata
    };
    
    fetch('/api/text-to-edit-commands', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.commands) {
            displayEditProposal(data.commands);
            currentEditCommands = data.commands;
        } else {
            throw new Error('編集コマンドの生成に失敗しました');
        }
    })
    .catch(error => {
        console.error('編集コマンドの生成に失敗しました:', error);
        alert('編集コマンドの生成に失敗しました。');
    });
}

function displayEditProposal(commands) {
    const editProposal = document.getElementById('editProposal');
    const editProposalContainer = document.getElementById('editProposalContainer');
    const noProposalMessage = document.getElementById('noProposalMessage');
    
    editProposal.innerHTML = '';
    
    if (commands.edits && commands.edits.length > 0) {
        commands.edits.forEach(edit => {
            const editElement = document.createElement('div');
            editElement.classList.add('edit-command');
            
            switch (edit.type) {
                case 'cut':
                    editElement.classList.add('edit-cut');
                    editElement.innerHTML = `<strong>カット:</strong> ${edit.start}秒から${edit.end}秒までを削除`;
                    break;
                case 'subtitle':
                    editElement.classList.add('edit-subtitle');
                    editElement.innerHTML = `<strong>テロップ:</strong> "${edit.text}" を${edit.start}秒から${edit.end}秒まで表示`;
                    break;
                case 'bgm_replace':
                    editElement.classList.add('edit-bgm');
                    editElement.innerHTML = `<strong>BGM変更:</strong> "${edit.mood}" ムードの音楽に置き換え`;
                    break;
                case 'speed':
                    editElement.classList.add('edit-speed');
                    editElement.innerHTML = `<strong>速度変更:</strong> ${edit.start}秒から${edit.end}秒までを${edit.rate}倍速に`;
                    break;
                case 'trim':
                    editElement.classList.add('edit-trim');
                    editElement.innerHTML = `<strong>トリム:</strong> ${edit.start}秒から${edit.end}秒までを残して他をカット`;
                    break;
                default:
                    editElement.innerHTML = `<strong>${edit.type}:</strong> ${JSON.stringify(edit)}`;
            }
            
            editProposal.appendChild(editElement);
        });
        
        editProposalContainer.classList.remove('d-none');
        noProposalMessage.classList.add('d-none');
    } else {
        editProposal.innerHTML = '<div class="alert alert-warning">有効な編集コマンドが生成されませんでした。別の指示を試してください。</div>';
        editProposalContainer.classList.remove('d-none');
        noProposalMessage.classList.add('d-none');
    }
}

function applyEdits() {
    if (!currentEditCommands || !selectedVideoId) {
        alert('編集コマンドまたは動画が選択されていません');
        return;
    }
    
    const processingMessage = document.getElementById('processingMessage');
    const resultContainer = document.getElementById('resultContainer');
    const noResultMessage = document.getElementById('noResultMessage');
    
    processingMessage.classList.remove('d-none');
    resultContainer.classList.add('d-none');
    noResultMessage.classList.add('d-none');
    
    let videoPath = '';
    let videoInfoPromise;
    
    if (selectedVideoId.startsWith('upload_')) {
        const filename = selectedVideoId.replace('upload_', '');
        videoPath = `/uploaded_videos/${filename}`;
        videoInfoPromise = Promise.resolve({ video_path: videoPath });
    } else if (selectedVideoId.startsWith('output_')) {
        const filename = selectedVideoId.replace('output_', '');
        videoPath = `/static/output/${filename}`;
        videoInfoPromise = Promise.resolve({ video_path: videoPath });
    } else if (selectedVideoId.startsWith('history_')) {
        videoInfoPromise = fetch(`/api/edit-commands?id=${selectedVideoId.replace('history_', '')}`)
            .then(response => response.json())
            .then(data => {
                if (data && data.length > 0 && data[0].result_path) {
                    return { video_path: data[0].result_path };
                } else {
                    throw new Error("編集履歴から動画パスが見つかりません");
                }
            });
    } else {
        videoInfoPromise = fetch(`/video_info/${selectedVideoId}`)
            .then(response => response.json());
    }
    
    videoInfoPromise
        .then(videoInfo => {
            console.log("currentEditCommands type:", typeof currentEditCommands);
            console.log("currentEditCommands value:", currentEditCommands);
            
            let commandJson;
            if (typeof currentEditCommands === 'string') {
                try {
                    const parsed = JSON.parse(currentEditCommands);
                    commandJson = JSON.stringify(parsed);
                } catch (e) {
                    commandJson = JSON.stringify(currentEditCommands);
                }
            } else {
                commandJson = JSON.stringify(currentEditCommands);
            }
            
            console.log("commandJson after processing:", commandJson);
            
            const videoPath = videoInfo.video_path || videoInfo.original_path;
            if (!videoPath) {
                throw new Error("動画パスが見つかりません");
            }
            
            return fetch('/api/process-edit', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    video_path: videoPath,
                    client_id: parseInt(clientId) || 1,
                    command_json: commandJson,
                    script_id: null
                })
            });
        })
    .then(response => response.json())
    .then(data => {
        processingMessage.classList.add('d-none');
        
        if (data.download_url) {
            const resultVideo = document.getElementById('resultVideo');
            const downloadLink = document.getElementById('downloadLink');
            
            resultVideo.src = data.download_url;
            downloadLink.href = data.download_url;
            downloadLink.download = data.filename || 'edited_video.mp4';
            
            resultContainer.classList.remove('d-none');
            noResultMessage.classList.add('d-none');
            
            resultVideo.load();
        } else {
            throw new Error('動画処理に失敗しました');
        }
    })
    .catch(error => {
        console.error('動画処理に失敗しました:', error);
        alert('動画処理に失敗しました。');
        processingMessage.classList.add('d-none');
        noResultMessage.classList.remove('d-none');
    });
}

function resetEditProposal() {
    const editProposalContainer = document.getElementById('editProposalContainer');
    const noProposalMessage = document.getElementById('noProposalMessage');
    const transcriptionResult = document.getElementById('transcriptionResult');
    
    editProposalContainer.classList.add('d-none');
    noProposalMessage.classList.remove('d-none');
    transcriptionResult.classList.add('d-none');
    transcriptionResult.textContent = '';
    document.getElementById('textInput').value = '';
    
    currentEditCommands = null;
}
