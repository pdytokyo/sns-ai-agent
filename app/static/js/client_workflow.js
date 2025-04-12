/**
 * client_workflow.js - クライアント中心のワークフローを管理するJavaScript
 */

let clientId = null;
let currentStep = 1;
let selectedScriptId = null;
let processedVideoId = null;
let subtitleIds = [];
let selectedBgmId = null;

document.addEventListener('DOMContentLoaded', function() {
    const clientInfoForm = document.getElementById('clientInfoForm');
    if (clientInfoForm) {
        clientInfoForm.addEventListener('submit', submitClientInfo);
    }
    
    const submitScriptEditBtn = document.getElementById('submitScriptEditBtn');
    if (submitScriptEditBtn) {
        submitScriptEditBtn.addEventListener('click', submitScriptEdit);
    }
    
    if (loadSession() && currentStep > 1) {
        goToStep(currentStep);
    } else {
        goToStep(1);
    }
});

function goToStep(stepNumber) {
    document.querySelectorAll('.step-container').forEach(container => {
        container.classList.remove('active');
    });
    
    document.querySelectorAll('.step-indicator .step').forEach((step, index) => {
        step.classList.remove('active', 'completed');
        if (index + 1 < stepNumber) {
            step.classList.add('completed');
        } else if (index + 1 === stepNumber) {
            step.classList.add('active');
        }
    });
    
    const newStepContainer = document.getElementById(`step-${stepNumber}`);
    if (newStepContainer) {
        newStepContainer.classList.add('active');
        currentStep = stepNumber;
        
        switch (stepNumber) {
            case 2:
                startAutoResearch();
                break;
            case 3:
                loadScriptProposals();
                break;
            case 4:
                loadShootingInstructions();
                break;
            case 5:
                setupVideoUpload();
                break;
            case 6:
                setupVideoEditing();
                break;
            case 7:
                setupSubtitleGeneration();
                break;
            case 8:
                setupBgmSuggestion();
                break;
            case 9:
                setupBgmIntegration();
                break;
            case 10:
                setupFinalVideo();
                break;
            case 11:
                setupAnalytics();
                break;
        }
        
        saveSession();
    }
}

function submitClientInfo(event) {
    event.preventDefault();
    
    const clientName = document.getElementById('clientName').value;
    const clientEmail = document.getElementById('clientEmail').value;
    const companyDescription = document.getElementById('companyDescription').value;
    const youtubeUrls = document.getElementById('youtubeUrls').value;
    
    const purposes = [];
    document.querySelectorAll('.purpose:checked').forEach(checkbox => {
        purposes.push(checkbox.value);
    });
    
    const targetAttrs = [];
    document.querySelectorAll('.target-attr:checked').forEach(checkbox => {
        targetAttrs.push(checkbox.value);
    });
    const targetInterests = document.getElementById('targetInterests').value;
    if (targetInterests) {
        targetInterests.split(',').forEach(interest => {
            targetAttrs.push(interest.trim());
        });
    }
    
    const platforms = [];
    document.querySelectorAll('.platform:checked').forEach(checkbox => {
        platforms.push(checkbox.value);
    });
    
    const textFile = document.getElementById('textFile').files[0];
    const pdfFile = document.getElementById('pdfFile').files[0];
    
    const formData = new FormData();
    formData.append('client_name', clientName);
    formData.append('client_email', clientEmail);
    formData.append('company_description', companyDescription);
    formData.append('youtube_urls', youtubeUrls);
    formData.append('purposes', purposes.join(','));
    formData.append('target_attributes', targetAttrs.join(','));
    formData.append('platforms', platforms.join(','));
    
    if (textFile) {
        formData.append('text_file', textFile);
    }
    if (pdfFile) {
        formData.append('pdf_file', pdfFile);
    }
    
    fetch('/api/client/register', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            clientId = data.client_id;
            goToStep(2); // 自動リサーチステップへ
        } else {
            alert('エラーが発生しました: ' + data.message);
        }
    })
    .catch(error => {
        console.error('エラー:', error);
        alert('通信エラーが発生しました。もう一度お試しください。');
    });
}

function startAutoResearch() {
    if (!clientId) return;
    
    const progressBar = document.getElementById('researchProgressBar');
    progressBar.style.width = '0%';
    progressBar.textContent = '0%';
    
    const statusElement = document.getElementById('researchStatus');
    statusElement.innerHTML = '<p><i class="bi bi-hourglass-split"></i> 分析を開始しています...</p>';
    
    let progress = 0;
    const progressInterval = setInterval(() => {
        progress += 5;
        if (progress > 100) {
            clearInterval(progressInterval);
            progress = 100;
            
            setTimeout(() => {
                goToStep(3);
            }, 1000);
        }
        
        progressBar.style.width = `${progress}%`;
        progressBar.textContent = `${progress}%`;
        
        if (progress < 30) {
            statusElement.innerHTML = '<p><i class="bi bi-search"></i> 競合コンテンツを分析中...</p>';
        } else if (progress < 60) {
            statusElement.innerHTML = '<p><i class="bi bi-graph-up"></i> エンゲージメントデータを収集中...</p>';
        } else if (progress < 90) {
            statusElement.innerHTML = '<p><i class="bi bi-lightbulb"></i> 台本案を生成中...</p>';
        } else {
            statusElement.innerHTML = '<p><i class="bi bi-check-circle"></i> 分析完了！台本提案を準備中...</p>';
        }
    }, 300);
    
    fetch(`/api/research/start?client_id=${clientId}`, {
        method: 'GET'
    })
    .then(response => response.json())
    .then(data => {
        console.log('リサーチ開始レスポンス:', data);
    })
    .catch(error => {
        console.error('リサーチ開始エラー:', error);
    });
}

function loadScriptProposals() {
    if (!clientId) return;
    
    fetch(`/api/script/proposals?client_id=${clientId}`)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const container = document.getElementById('scriptProposalsContainer');
            container.innerHTML = '';
            
            data.proposals.forEach(proposal => {
                const proposalElement = createScriptProposalElement(proposal);
                container.appendChild(proposalElement);
            });
            
            document.querySelectorAll('.select-script-btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    const proposalCard = this.closest('.script-proposal');
                    const proposalId = proposalCard.dataset.proposalId;
                    selectScriptProposal(proposalId);
                });
            });
        } else {
            console.error('台本提案の読み込みに失敗しました:', data.message);
        }
    })
    .catch(error => {
        console.error('台本提案の読み込み中にエラーが発生しました:', error);
        
        const dummyProposals = [
            {
                id: 1,
                title: '心に響く〇〇の魅力',
                content: 'あなたは今、何を求めていますか？毎日の忙しさの中で、ふと立ち止まって考えることはありますか？私たちの〇〇は、そんなあなたの心に寄り添います...',
                style: 'エモーショナルスタイル'
            },
            {
                id: 2,
                title: '知っておきたい〇〇の基礎知識',
                content: 'こんにちは！今日は〇〇について知っておくべき3つのポイントをご紹介します。多くの方が見落としがちなこの情報を知ることで、あなたの生活は大きく変わるかもしれません...',
                style: '情報提供型スタイル'
            },
            {
                id: 3,
                title: '〇〇が私の人生を変えた日',
                content: '私がはじめて〇〇と出会ったのは3年前のことでした。当時の私は悩みを抱え、解決策を探していました。そんなとき、友人から紹介されたのが〇〇だったのです...',
                style: 'ストーリーテリング'
            }
        ];
        
        const container = document.getElementById('scriptProposalsContainer');
        container.innerHTML = '';
        
        dummyProposals.forEach(proposal => {
            const proposalElement = createScriptProposalElement(proposal);
            container.appendChild(proposalElement);
        });
        
        document.querySelectorAll('.select-script-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const proposalCard = this.closest('.script-proposal');
                const proposalId = proposalCard.dataset.proposalId;
                selectScriptProposal(proposalId);
            });
        });
    });
    
    const refreshBtn = document.getElementById('refreshProposalsBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            fetch(`/api/script/regenerate?client_id=${clientId}`, {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    loadScriptProposals();
                } else {
                    alert('新しい提案の生成に失敗しました: ' + data.message);
                }
            })
            .catch(error => {
                console.error('提案生成エラー:', error);
                alert('通信エラーが発生しました。もう一度お試しください。');
            });
        });
    }
}

function createScriptProposalElement(proposal) {
    const col = document.createElement('div');
    col.className = 'col-md-4 mb-3';
    
    col.innerHTML = `
        <div class="card script-proposal" data-proposal-id="${proposal.id}">
            <div class="card-header">
                <h6 class="mb-0">${proposal.style}</h6>
            </div>
            <div class="card-body">
                <h6 class="proposal-title">タイトル: ${proposal.title}</h6>
                <p class="proposal-content">${proposal.content.substring(0, 150)}...</p>
            </div>
            <div class="card-footer text-center">
                <button class="btn btn-sm btn-outline-primary select-script-btn">選択</button>
            </div>
        </div>
    `;
    
    return col;
}

function selectScriptProposal(proposalId) {
    selectedScriptId = proposalId;
    saveSession();
    
    fetch(`/api/script/get?id=${proposalId}`)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById('scriptTitle').value = data.proposal.title;
            document.getElementById('scriptContent').value = data.proposal.content;
            
            document.getElementById('scriptProposalsContainer').parentElement.style.display = 'none';
            document.getElementById('scriptEditCard').style.display = 'block';
        } else {
            console.error('台本データの取得に失敗しました:', data.message);
        }
    })
    .catch(error => {
        console.error('台本データの取得中にエラーが発生しました:', error);
        
        let dummyContent = '';
        if (proposalId == 1) {
            dummyContent = `# 心に響く〇〇の魅力

【オープニング】
あなたは今、何を求めていますか？毎日の忙しさの中で、ふと立ち止まって考えることはありますか？

【導入部】
私たちの〇〇は、そんなあなたの心に寄り添います。今日は、多くの方の人生を変えた〇〇の魅力についてお話しします。

【本編】
まず一つ目の魅力は、「心の安らぎ」です。〇〇を使うことで、日々のストレスから解放され、心が穏やかになります。
二つ目は、「新たな発見」です。〇〇によって、今まで気づかなかった自分自身の可能性に気づくことができます。
そして三つ目は、「人とのつながり」です。〇〇を通じて、同じ価値観を持つ仲間と出会い、かけがえのない絆を育むことができます。

【まとめ】
あなたも今日から〇〇を始めてみませんか？きっと人生が豊かに変わるはずです。`;
        } else if (proposalId == 2) {
            dummyContent = `# 知っておきたい〇〇の基礎知識

【オープニング】
こんにちは！今日は〇〇について知っておくべき3つのポイントをご紹介します。

【導入部】
多くの方が見落としがちなこの情報を知ることで、あなたの生活は大きく変わるかもしれません。

【本編】
ポイント1: 〇〇の選び方
良質な〇〇を選ぶためには、まず〇〇〇をチェックしましょう。次に、〇〇〇の状態を確認します。最後に、〇〇〇が適切かどうかを判断します。

ポイント2: 〇〇の使い方
効果的な使い方は3ステップです。まず〇〇〇します。次に〇〇〇します。最後に〇〇〇して完了です。

ポイント3: 〇〇のメンテナンス
長く使うためには、定期的なメンテナンスが重要です。月に一度は〇〇〇をし、半年に一度は〇〇〇をしましょう。

【まとめ】
これらのポイントを押さえることで、〇〇をより効果的に活用できます。ぜひ今日から実践してみてください！`;
        } else {
            dummyContent = `# 〇〇が私の人生を変えた日

【オープニング】
私がはじめて〇〇と出会ったのは3年前のことでした。

【導入部】
当時の私は悩みを抱え、解決策を探していました。そんなとき、友人から紹介されたのが〇〇だったのです。

【本編】
最初は半信半疑でした。「こんなもので本当に変わるのだろうか」と。
しかし、使い始めて1週間で変化を感じました。まず、〇〇〇が改善されました。
1ヶ月後には、周囲の人からも「最近変わったね」と言われるようになりました。
そして3ヶ月後、ついに私の長年の悩みだった〇〇〇が解消されたのです。

【転機】
しかし、すべてが順調だったわけではありません。ある日、〇〇〇というトラブルが発生しました。
でも、そこで諦めずに続けたことで、さらに大きな成果を得ることができました。

【まとめ】
今では〇〇は私の生活に欠かせないものとなっています。あなたも勇気を出して一歩踏み出してみませんか？`;
        }
        
        document.getElementById('scriptTitle').value = document.querySelector(`.script-proposal[data-proposal-id="${proposalId}"] .proposal-title`).textContent.replace('タイトル: ', '');
        document.getElementById('scriptContent').value = dummyContent;
        
        document.getElementById('scriptProposalsContainer').parentElement.style.display = 'none';
        document.getElementById('scriptEditCard').style.display = 'block';
    });
}

function submitScriptEdit(event) {
    event.preventDefault();
    
    const title = document.getElementById('scriptTitle').value;
    const content = document.getElementById('scriptContent').value;
    
    if (!title || !content) {
        alert('タイトルと台本内容を入力してください');
        return;
    }
    
    fetch(`/api/script/update`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            script_id: selectedScriptId,
            title: title,
            content: content
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            goToStep(4);
        } else {
            alert('台本の更新に失敗しました: ' + data.message);
        }
    })
    .catch(error => {
        console.error('台本更新エラー:', error);
        
        goToStep(4);
    });
}

function loadShootingInstructions() {
    if (!selectedScriptId) return;
    
    fetch(`/api/shooting-instructions/generate?script_id=${selectedScriptId}`)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById('shootingInstructionsTitle').innerHTML = `<i class="bi bi-camera-video"></i> 「${data.title}」の撮影指示書`;
            document.getElementById('shootingInstructionsContent').innerHTML = data.content;
        } else {
            console.error('撮影指示書の生成に失敗しました:', data.message);
        }
    })
    .catch(error => {
        console.error('撮影指示書の生成中にエラーが発生しました:', error);
        
        const scriptTitle = document.getElementById('scriptTitle').value || '台本タイトル';
        document.getElementById('shootingInstructionsTitle').innerHTML = `<i class="bi bi-camera-video"></i> 「${scriptTitle}」の撮影指示書`;
        
        const dummyInstructions = `
        <h3>撮影指示書</h3>
        
        <h4>1. 必要な撮影機材</h4>
        <ul>
            <li>スマートフォン（iPhone 12以上またはAndroid同等機種）</li>
            <li>三脚またはスマホスタンド</li>
            <li>リングライト</li>
            <li>ワイヤレスマイク（オプション）</li>
        </ul>
        
        <h4>2. 撮影場所の設定と準備</h4>
        <p>明るく、シンプルな背景の場所を選びましょう。自然光が入る窓際が理想的です。背景に余計なものが映り込まないよう整理してください。</p>
        
        <h4>3. 照明と音声の設定</h4>
        <p>リングライトを顔の正面に設置し、自然な明るさに調整します。周囲の雑音が入らないよう、静かな環境で撮影してください。</p>
        
        <h4>4. 各シーンの具体的な撮影方法</h4>
        <p><strong>オープニング（0:00-0:15）</strong>：カメラに向かって笑顔で挨拶。アイコンタクトを意識し、エネルギッシュに話しかけるように。</p>
        <p><strong>導入部（0:15-0:45）</strong>：問題提起をしながら、視聴者の共感を得るように話す。時折、手振りを交えて。</p>
        <p><strong>本編（0:45-2:30）</strong>：3つのポイントを順番に説明。各ポイントで具体例や実演を交えると効果的。</p>
        <p><strong>まとめ（2:30-3:00）</strong>：再度カメラに近づき、視聴者に直接呼びかけるように。行動を促す言葉で締めくくる。</p>
        
        <h4>5. 演出のポイント</h4>
        <ul>
            <li>話すスピードは早すぎず、遅すぎずを心がける</li>
            <li>重要なポイントでは少し間を取る</li>
            <li>表情豊かに、特に目と口元の動きを意識する</li>
            <li>身振り手振りを適度に取り入れる</li>
        </ul>
        
        <h4>6. タイムライン（撮影の時間配分）</h4>
        <p>全体の長さ：約3分</p>
        <ul>
            <li>オープニング：15秒</li>
            <li>導入部：30秒</li>
            <li>本編：1分45秒（各ポイント35秒程度）</li>
            <li>まとめ：30秒</li>
        </ul>
        
        <h4>7. 特殊効果や編集上の注意点</h4>
        <ul>
            <li>重要なキーワードはテロップで強調</li>
            <li>ポイントの切り替わり時に簡単なトランジションを入れる</li>
            <li>BGMは明るく前向きな曲を選ぶ</li>
            <li>最後にチャンネル登録やSNSフォローの案内を入れる</li>
        </ul>`;
        
        document.getElementById('shootingInstructionsContent').innerHTML = dummyInstructions;
    });
    
    const downloadBtn = document.getElementById('downloadInstructionsBtn');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', function() {
            const title = document.getElementById('shootingInstructionsTitle').textContent.replace('「', '').replace('」の撮影指示書', '');
            const content = document.getElementById('shootingInstructionsContent').innerHTML;
            
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = content;
            const textContent = tempDiv.textContent;
            
            const blob = new Blob([`# ${title}の撮影指示書\n\n${textContent}`], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${title}_撮影指示書.txt`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        });
    }
}
