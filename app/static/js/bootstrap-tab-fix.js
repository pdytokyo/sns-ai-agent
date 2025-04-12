document.addEventListener('DOMContentLoaded', function() {
    window.addDetailButtonListeners = function() {
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
    };

    var triggerTabList = [].slice.call(document.querySelectorAll('button[data-bs-toggle="tab"]'))
    triggerTabList.forEach(function (triggerEl) {
        try {
            var tabTrigger = new bootstrap.Tab(triggerEl)
            
            triggerEl.addEventListener('click', function (event) {
                event.preventDefault()
                tabTrigger.show()
                
                if (triggerEl.getAttribute('data-bs-target') === '#instagram-analysis') {
                    console.log('Instagram分析タブがクリックされました');
                    
                    const noDataElements = document.querySelectorAll('#instagram-analysis .no-data');
                    noDataElements.forEach(function(element) {
                        element.style.display = 'none';
                    });
                    
                    const formCard = document.getElementById('instagramFormCard');
                    if (formCard) {
                        formCard.style.display = 'block';
                    }
                    
                    const instagramForm = document.getElementById('instagramAnalysisForm');
                    if (instagramForm) {
                        instagramForm.style.display = 'block';
                    }
                    
                    const resultCard = document.getElementById('instagramResultCard');
                    if (resultCard) {
                        resultCard.style.display = 'none';
                    }
                    
                    const resultsTable = document.getElementById('instagramResultsTable');
                    if (resultsTable) {
                        const tableContainer = resultsTable.closest('.card');
                        if (tableContainer) {
                            tableContainer.style.display = 'block';
                        }
                    }
                    
                    fetch('/get-instagram-analysis/')
                        .then(response => response.json())
                        .then(data => {
                            console.log('Instagram分析データを取得しました:', data);
                            if (data && data.length > 0) {
                                if (typeof displayInstagramAnalysis === 'function') {
                                    displayInstagramAnalysis(data);
                                } else {
                                    console.error('displayInstagramAnalysis関数が定義されていません');
                                }
                            }
                        })
                        .catch(error => console.error('Instagram分析データ取得エラー:', error));
                }
            });
        } catch (e) {
            console.error('タブ初期化エラー:', e);
        }
    });
    
    if (window.location.hash === '#instagram') {
        const instagramTab = document.getElementById('instagram-analysis-tab');
        if (instagramTab) {
            instagramTab.click();
        }
    }
    
    setTimeout(function() {
        const instagramTabContent = document.getElementById('instagram-analysis');
        if (instagramTabContent) {
            const noDataElements = document.querySelectorAll('#instagram-analysis .no-data');
            noDataElements.forEach(function(element) {
                element.style.display = 'none';
            });
            
            const formCard = document.getElementById('instagramFormCard');
            if (formCard) {
                formCard.style.display = 'block';
            }
        }
    }, 500);
});
