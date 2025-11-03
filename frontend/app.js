// API設定
const API_BASE_URL = 'http://localhost:8000/api';
let authToken = localStorage.getItem('authToken');
let currentSessionId = null;
let currentReportId = null;

// ページロード時の処理
window.onload = function() {
    // ロガーを初期化（logger.jsで自動的に初期化される）
    if (window.logger) {
        window.logger.info('SalesMindアプリケーションが起動しました');
    }
    checkAuth();
};

// 認証状態の確認
function checkAuth() {
    if (authToken) {
        document.getElementById('loginForm').style.display = 'none';
        document.getElementById('userInfo').style.display = 'block';
        document.getElementById('usernameDisplay').textContent = localStorage.getItem('username') || 'ユーザー';
        // Tokenが有効か確認（実際の実装ではAPIで確認）
    }
}

// ログインタブ表示
function showLoginTab() {
    document.getElementById('loginForm').style.display = 'block';
    document.getElementById('registerForm').style.display = 'none';
    document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
}

// 登録タブ表示
function showRegisterTab() {
    document.getElementById('loginForm').style.display = 'none';
    document.getElementById('registerForm').style.display = 'block';
    document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
}

// ユーザー登録
async function register() {
    if (window.logger) {
        window.logger.info('ユーザー登録を開始');
    }
    const username = document.getElementById('registerUsername').value.trim();
    const email = document.getElementById('registerEmail').value.trim();
    const password = document.getElementById('registerPassword').value;
    
    if (!username || !password) {
        showError('registerError', 'ユーザー名とパスワードは必須です');
        return;
    }
    
    if (username.length < 3) {
        showError('registerError', 'ユーザー名は3文字以上で入力してください');
        return;
    }
    
    if (password.length < 6) {
        showError('registerError', 'パスワードは6文字以上で入力してください');
        return;
    }
    
    // エラーメッセージをクリア
    document.getElementById('registerError').style.display = 'none';
    
    try {
        const response = await fetch(`${API_BASE_URL}/auth/register/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username,
                email: email || '',
                password
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // 登録成功 - Tokenを保存
            authToken = data.token;
            localStorage.setItem('authToken', authToken);
            localStorage.setItem('username', data.user.username);
            
            showSuccess('ユーザー登録が完了しました');
            
            // ログイン状態にする
            document.getElementById('loginForm').style.display = 'none';
            document.getElementById('registerForm').style.display = 'none';
            document.getElementById('userInfo').style.display = 'block';
            document.getElementById('usernameDisplay').textContent = data.user.username;
        } else {
            // エラー表示
            let errorMsg = 'ユーザー登録に失敗しました';
            if (data.details) {
                const errors = Object.values(data.details).flat();
                errorMsg = errors.join('\n');
            } else if (data.message) {
                errorMsg = data.message;
            }
            showError('registerError', errorMsg);
        }
    } catch (error) {
        showError('registerError', 'エラーが発生しました: ' + error.message);
    }
}

// ログイン
async function login() {
    if (window.logger) {
        window.logger.info('ログインを開始');
    }
    const username = document.getElementById('loginUsername').value.trim();
    const password = document.getElementById('loginPassword').value;
    
    if (!username || !password) {
        showError('loginError', 'ユーザー名とパスワードを入力してください');
        return;
    }
    
    // エラーメッセージをクリア
    document.getElementById('loginError').style.display = 'none';
    
    try {
        const response = await fetch(`${API_BASE_URL}/auth/login/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username,
                password
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // ログイン成功 - Tokenを保存
            authToken = data.token;
            localStorage.setItem('authToken', authToken);
            localStorage.setItem('username', data.user.username);
            
            showSuccess('ログインに成功しました');
            
            // ログイン状態にする
            document.getElementById('loginForm').style.display = 'none';
            document.getElementById('registerForm').style.display = 'none';
            document.getElementById('userInfo').style.display = 'block';
            document.getElementById('usernameDisplay').textContent = data.user.username;
        } else {
            // エラー表示
            let errorMsg = 'ログインに失敗しました';
            if (data.message) {
                errorMsg = data.message;
            }
            showError('loginError', errorMsg);
        }
    } catch (error) {
        showError('loginError', 'エラーが発生しました: ' + error.message);
    }
}

// ログアウト
function logout() {
    authToken = null;
    localStorage.removeItem('authToken');
    localStorage.removeItem('username');
    document.getElementById('loginForm').style.display = 'block';
    document.getElementById('userInfo').style.display = 'none';
    resetToStep1();
}

// ステップ1: SPIN質問生成
async function generateSpinQuestions() {
    // SPIN質問生成は認証不要
    
    const industry = document.getElementById('industry').value;
    const value_proposition = document.getElementById('value_proposition').value;
    const customer_persona = document.getElementById('customer_persona').value;
    const customer_pain = document.getElementById('customer_pain').value;
    
    if (window.logger) {
        window.logger.info('SPIN質問生成を開始', { industry, value_proposition, customer_persona, customer_pain });
    }
    
    if (!industry || !value_proposition) {
        if (window.logger) {
            window.logger.warning('SPIN質問生成: 必須項目が不足しています', { industry, value_proposition });
        }
        alert('業界と価値提案は必須です');
        return;
    }
    
    showLoading('spinQuestionsResult');
    
    const requestData = {
        industry,
        value_proposition,
        customer_persona: customer_persona || undefined,
        customer_pain: customer_pain || undefined
    };
    
    if (window.logger) {
        window.logger.apiRequest('POST', `${API_BASE_URL}/spin/generate/`, requestData);
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/spin/generate/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        let data;
        let responseText;
        try {
            responseText = await response.text();
            if (window.logger) {
                window.logger.debug('レスポンステキストを取得', { 
                    length: responseText.length,
                    text: responseText.substring(0, 500) 
                });
            }
            
            try {
                data = JSON.parse(responseText);
                if (window.logger) {
                    window.logger.debug('JSON解析成功', { 
                        hasQuestions: !!data.questions,
                        dataKeys: Object.keys(data)
                    });
                }
            } catch (parseError) {
                if (window.logger) {
                    window.logger.error('JSON解析エラー', { 
                        text: responseText, 
                        error: parseError.message,
                        errorStack: parseError.stack
                    });
                }
                throw new Error('レスポンスのJSON解析に失敗しました: ' + parseError.message);
            }
        } catch (jsonError) {
            if (window.logger) {
                window.logger.error('レスポンス取得エラー', { error: jsonError.message, stack: jsonError.stack });
            }
            showError('spinQuestionsResult', 'レスポンスの処理に失敗しました: ' + jsonError.message);
            return;
        }
        
        if (window.logger) {
            window.logger.apiResponse('POST', `${API_BASE_URL}/spin/generate/`, response.status, data);
        }
        
        if (response.ok) {
            if (window.logger) {
                window.logger.debug('レスポンスデータの内容', { data, hasQuestions: !!data.questions });
            }
            
            if (data.questions) {
                if (window.logger) {
                    window.logger.info('質問データを検出、表示処理を開始', { 
                        questionKeys: Object.keys(data.questions),
                        questionCount: Object.keys(data.questions).length 
                    });
                }
                
                // まず親要素を表示してから、子要素にアクセス
                const resultElement = document.getElementById('spinQuestionsResult');
                if (resultElement) {
                    // ローディングをクリア
                    const loadingElement = resultElement.querySelector('.loading');
                    if (loadingElement) {
                        loadingElement.remove();
                    }
                    
                    // 親要素を表示
                    resultElement.style.display = 'block';
                    
                    // すぐに表示処理を実行（要素は既に存在している）
                    displaySpinQuestions(data.questions);
                    
                    // コンテンツが表示されているか確認
                    const contentElement = document.getElementById('spinQuestionsContent');
                    if (!contentElement || contentElement.innerHTML.trim() === '') {
                        if (window.logger) {
                            window.logger.warning('コンテンツ要素が空です。再試行します。', { 
                                questions: data.questions,
                                contentElement: !!contentElement,
                                parentHTML: resultElement.innerHTML.substring(0, 300)
                            });
                        }
                        // 少し待ってからもう一度表示を試みる
                        setTimeout(() => {
                            displaySpinQuestions(data.questions);
                        }, 100);
                    } else {
                        if (window.logger) {
                            window.logger.info('コンテンツが正常に表示されました', { 
                                contentLength: contentElement.innerHTML.length 
                            });
                        }
                    }
                } else {
                    if (window.logger) {
                        window.logger.error('spinQuestionsResult要素が見つかりません');
                    }
                    // 要素が見つからない場合でも、とにかく表示を試みる
                    displaySpinQuestions(data.questions);
                }
                
                if (window.logger) {
                    window.logger.info('SPIN質問生成が完了しました', { questionCount: Object.keys(data.questions).length });
                }
            } else {
                if (window.logger) {
                    window.logger.error('質問データが存在しません', { 
                        data,
                        dataKeys: data ? Object.keys(data) : [],
                        responseText: responseText ? responseText.substring(0, 500) : 'N/A'
                    });
                }
                showError('spinQuestionsResult', '質問データの形式が正しくありません。レスポンス: ' + JSON.stringify(data));
            }
        } else {
            if (window.logger) {
                window.logger.error('SPIN質問生成に失敗しました', { status: response.status, data });
            }
            showError('spinQuestionsResult', '質問生成に失敗しました: ' + (data.message || data.error || '不明なエラー'));
        }
    } catch (error) {
        if (window.logger) {
            window.logger.error('SPIN質問生成エラー', { message: error.message, stack: error.stack });
        }
        showError('spinQuestionsResult', 'エラー: ' + error.message);
    }
}

// SPIN質問の表示
function displaySpinQuestions(questions) {
    if (window.logger) {
        window.logger.debug('displaySpinQuestions called with:', questions);
        window.logger.debug('質問データの構造', {
            hasQuestions: !!questions,
            isObject: typeof questions === 'object',
            keys: questions ? Object.keys(questions) : [],
            questionTypes: questions ? Object.keys(questions).map(key => ({
                key,
                isArray: Array.isArray(questions[key]),
                length: Array.isArray(questions[key]) ? questions[key].length : 0
            })) : []
        });
    }
    
    // 親要素を取得
    const parentElement = document.getElementById('spinQuestionsResult');
    if (!parentElement) {
        const errorMsg = 'spinQuestionsResult要素が見つかりません';
        if (window.logger) {
            window.logger.error(errorMsg);
        }
        console.error(errorMsg);
        alert('エラー: spinQuestionsResult要素が見つかりません。ページをリロードしてください。');
        return;
    }
    
    // 親要素を表示（非表示の場合）
    if (parentElement.style.display === 'none' || !parentElement.offsetParent) {
        if (window.logger) {
            window.logger.debug('親要素が非表示のため、表示します');
        }
        parentElement.style.display = 'block';
    }
    
    // 要素を探す（まず親要素内を検索、次に全体検索）
    let container = parentElement.querySelector('[id="spinQuestionsContent"]');
    
    // 見つからない場合は、全体検索
    if (!container) {
        container = document.getElementById('spinQuestionsContent');
    }
    
    // それでも見つからない場合は、親要素の子要素を直接検索
    if (!container && parentElement.children) {
        for (let i = 0; i < parentElement.children.length; i++) {
            const child = parentElement.children[i];
            if (child.id === 'spinQuestionsContent') {
                container = child;
                break;
            }
            // 孫要素も検索
            const grandChild = child.querySelector('[id="spinQuestionsContent"]');
            if (grandChild) {
                container = grandChild;
                break;
            }
        }
    }
    
    if (!container) {
        const errorMsg = 'spinQuestionsContent要素が見つかりません';
        if (window.logger) {
            window.logger.error(errorMsg, { 
                containerExists: !!document.getElementById('spinQuestionsContent'),
                parentExists: !!parentElement,
                parentDisplay: parentElement.style.display,
                parentInnerHTML: parentElement.innerHTML.length,
                parentChildren: Array.from(parentElement.children).map(el => ({
                    tag: el.tagName,
                    id: el.id,
                    className: el.className
                }))
            });
        }
        console.error(errorMsg);
        alert('エラー: spinQuestionsContent要素が見つかりません。ページをリロードしてください。');
        return;
    }
    
    if (!questions) {
        const errorMsg = '質問データがnullまたはundefinedです';
        if (window.logger) {
            window.logger.error(errorMsg);
        }
        container.innerHTML = '<p class="error-message">質問データが見つかりませんでした</p>';
        return;
    }
    
    if (typeof questions !== 'object') {
        const errorMsg = '質問データがオブジェクトではありません: ' + typeof questions;
        if (window.logger) {
            window.logger.error(errorMsg, { questions });
        }
        container.innerHTML = '<p class="error-message">質問データの形式が正しくありません</p>';
        return;
    }
    
    container.innerHTML = '';
    
    const categories = [
        { key: 'situation', label: 'Situation（状況確認）' },
        { key: 'problem', label: 'Problem（問題発見）' },
        { key: 'implication', label: 'Implication（示唆）' },
        { key: 'need', label: 'Need（ニーズ確認）' }
    ];
    
    let hasQuestions = false;
    const addedCategories = [];
    
    categories.forEach(cat => {
        if (window.logger) {
            window.logger.debug(`カテゴリ ${cat.key} をチェック`, {
                exists: questions.hasOwnProperty(cat.key),
                value: questions[cat.key],
                isArray: Array.isArray(questions[cat.key]),
                length: Array.isArray(questions[cat.key]) ? questions[cat.key].length : 'N/A'
            });
        }
        
        if (questions[cat.key] && Array.isArray(questions[cat.key]) && questions[cat.key].length > 0) {
            hasQuestions = true;
            addedCategories.push(cat.key);
            
            const categoryDiv = document.createElement('div');
            categoryDiv.className = 'spin-category';
            
            const questionsList = questions[cat.key].map(q => {
                if (typeof q !== 'string') {
                    if (window.logger) {
                        window.logger.warning(`質問が文字列ではありません: ${cat.key}`, { question: q, type: typeof q });
                    }
                    return `<li>${escapeHtml(String(q))}</li>`;
                }
                return `<li>${escapeHtml(q)}</li>`;
            }).join('');
            
            categoryDiv.innerHTML = `
                <h4>${cat.label}</h4>
                <ul>
                    ${questionsList}
                </ul>
            `;
            container.appendChild(categoryDiv);
            
            if (window.logger) {
                window.logger.debug(`カテゴリ ${cat.key} を追加`, { questionCount: questions[cat.key].length });
            }
        } else {
            if (window.logger) {
                window.logger.debug(`カテゴリ ${cat.key} はスキップ`, {
                    hasValue: !!questions[cat.key],
                    isArray: Array.isArray(questions[cat.key]),
                    length: Array.isArray(questions[cat.key]) ? questions[cat.key].length : 'N/A'
                });
            }
        }
    });
    
    if (!hasQuestions) {
        const warningMsg = '表示可能な質問がありません。データ構造: ' + JSON.stringify(questions);
        if (window.logger) {
            window.logger.warning(warningMsg, { 
                allKeys: Object.keys(questions),
                questionTypes: Object.keys(questions).map(key => ({
                    key,
                    type: typeof questions[key],
                    isArray: Array.isArray(questions[key]),
                    value: Array.isArray(questions[key]) ? questions[key] : questions[key]
                }))
            });
        }
        container.innerHTML = '<p class="error-message">質問データが見つかりませんでした<br><pre>' + escapeHtml(JSON.stringify(questions, null, 2)) + '</pre></p>';
    } else {
        if (window.logger) {
            window.logger.info('SPIN質問の表示が完了しました', { 
                addedCategories,
                totalCategories: addedCategories.length
            });
        }
    }
}

// HTMLエスケープ関数を追加
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// セッション開始に進む
function proceedToSessionStart() {
    // フォームデータをセッション開始フォームにコピー
    document.getElementById('session_industry').value = document.getElementById('industry').value;
    document.getElementById('session_value_proposition').value = document.getElementById('value_proposition').value;
    document.getElementById('session_customer_persona').value = document.getElementById('customer_persona').value;
    document.getElementById('session_customer_pain').value = document.getElementById('customer_pain').value;
    
    showStep(2);
}

// ステップ2: セッション開始
async function startSession() {
    if (!authToken) {
        alert('ログインしてください');
        return;
    }
    
    const industry = document.getElementById('session_industry').value;
    const value_proposition = document.getElementById('session_value_proposition').value;
    const customer_persona = document.getElementById('session_customer_persona').value;
    const customer_pain = document.getElementById('session_customer_pain').value;
    
    showLoading('sessionStartResult');
    
    try {
        const response = await fetch(`${API_BASE_URL}/session/start/`, {
            method: 'POST',
            headers: {
                'Authorization': `Token ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                industry,
                value_proposition,
                customer_persona: customer_persona || undefined,
                customer_pain: customer_pain || undefined
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            currentSessionId = data.id;
            document.getElementById('sessionIdDisplay').textContent = currentSessionId;
            document.getElementById('sessionStartResult').style.display = 'block';
        } else {
            showError('sessionStartResult', 'セッション開始に失敗しました: ' + (data.message || data.error));
        }
    } catch (error) {
        showError('sessionStartResult', 'エラー: ' + error.message);
    }
}

// チャットに進む
function proceedToChat() {
    showStep(3);
    loadChatHistory();
}

// ステップ3: チャット
async function sendChatMessage() {
    if (!authToken || !currentSessionId) {
        alert('セッションを開始してください');
        return;
    }
    
    const messageInput = document.getElementById('chatMessageInput');
    const message = messageInput.value.trim();
    
    if (!message) {
        alert('メッセージを入力してください');
        return;
    }
    
    // 送信中のメッセージを表示
    addChatMessage('salesperson', message);
    messageInput.value = '';
    
    showChatLoading();
    
    try {
        const response = await fetch(`${API_BASE_URL}/session/chat/`, {
            method: 'POST',
            headers: {
                'Authorization': `Token ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: currentSessionId,
                message: message
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // 会話履歴を更新
            updateChatMessages(data.conversation);
        } else {
            showChatError('メッセージ送信に失敗しました: ' + (data.message || data.error));
        }
    } catch (error) {
        showChatError('エラー: ' + error.message);
    }
}

// Enterキーで送信
function handleChatKeyPress(event) {
    if (event.key === 'Enter') {
        sendChatMessage();
    }
}

// チャットメッセージの追加
function addChatMessage(role, message) {
    const container = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const roleLabel = role === 'salesperson' ? '営業担当者' : 'AI顧客';
    const timestamp = new Date().toLocaleTimeString('ja-JP');
    
    messageDiv.innerHTML = `
        <div class="message-header">${roleLabel} - ${timestamp}</div>
        <div class="message-content">${message}</div>
    `;
    
    container.appendChild(messageDiv);
    container.scrollTop = container.scrollHeight;
}

// チャット履歴の更新
function updateChatMessages(conversation) {
    const container = document.getElementById('chatMessages');
    if (!container) {
        console.error('chatMessages要素が見つかりません');
        return;
    }
    
    container.innerHTML = '';
    
    conversation.forEach(msg => {
        addChatMessage(msg.role, msg.message);
    });
}

// チャット履歴の読み込み
async function loadChatHistory() {
    if (!currentSessionId) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/session/${currentSessionId}/`, {
            method: 'GET',
            headers: {
                'Authorization': `Token ${authToken}`
            }
        });
        
        const data = await response.json();
        
        if (response.ok && data.messages) {
            updateChatMessages(data.messages);
        }
    } catch (error) {
        console.error('チャット履歴の読み込みに失敗:', error);
    }
}

// ステップ4: セッション終了・スコアリング
async function finishSession() {
    if (!authToken || !currentSessionId) {
        alert('セッションを開始してください');
        return;
    }
    
    if (!confirm('セッションを終了してスコアリングを実行しますか？')) {
        return;
    }
    
    showLoading('scoringResult');
    showStep(4);
    
    try {
        const response = await fetch(`${API_BASE_URL}/session/finish/`, {
            method: 'POST',
            headers: {
                'Authorization': `Token ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: currentSessionId
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            currentReportId = data.report_id;
            displayScoringResult(data);
        } else {
            showError('scoringResult', 'スコアリングに失敗しました: ' + (data.message || data.error));
        }
    } catch (error) {
        showError('scoringResult', 'エラー: ' + error.message);
    }
}

// スコアリング結果の表示
function displayScoringResult(data) {
    const container = document.getElementById('scoringResult');
    if (!container) {
        console.error('scoringResult要素が見つかりません');
        return;
    }
    
    const scores = data.spin_scores;
    const totalScore = scores.total;
    
    // スコアに応じた色を決定
    let scoreColor = '#667eea';
    if (totalScore >= 80) scoreColor = '#28a745';
    else if (totalScore >= 60) scoreColor = '#ffc107';
    else scoreColor = '#dc3545';
    
    container.innerHTML = `
        <div class="score-card">
            <div class="score-total" style="color: ${scoreColor}">${totalScore.toFixed(1)}点</div>
            <div class="score-details">
                <div class="score-item">
                    <div class="score-item-label">Situation</div>
                    <div class="score-item-value">${scores.situation}点</div>
                </div>
                <div class="score-item">
                    <div class="score-item-label">Problem</div>
                    <div class="score-item-value">${scores.problem}点</div>
                </div>
                <div class="score-item">
                    <div class="score-item-label">Implication</div>
                    <div class="score-item-value">${scores.implication}点</div>
                </div>
                <div class="score-item">
                    <div class="score-item-label">Need</div>
                    <div class="score-item-value">${scores.need}点</div>
                </div>
            </div>
        </div>
        <div class="feedback-section">
            <h3>フィードバック</h3>
            <div class="feedback-text">${data.feedback}</div>
        </div>
        <div class="feedback-section">
            <h3>次回アクション</h3>
            <div class="feedback-text">${data.next_actions}</div>
        </div>
    `;
}

// ステップ5: レポート詳細表示
async function viewReport() {
    if (!currentReportId) {
        alert('レポートIDが設定されていません');
        return;
    }
    
    showStep(5);
    showLoading('reportDetails');
    
    try {
        const response = await fetch(`${API_BASE_URL}/report/${currentReportId}/`, {
            method: 'GET',
            headers: {
                'Authorization': `Token ${authToken}`
            }
        });
        
        const data = await response.json();
        
        if (response.ok) {
            displayReportDetails(data);
        } else {
            showError('reportDetails', 'レポート取得に失敗しました: ' + (data.message || data.error));
        }
    } catch (error) {
        showError('reportDetails', 'エラー: ' + error.message);
    }
}

// レポート詳細の表示
function displayReportDetails(report) {
    const container = document.getElementById('reportDetails');
    if (!container) {
        console.error('reportDetails要素が見つかりません');
        return;
    }
    
    const scores = report.spin_scores;
    
    let detailsHTML = `
        <div class="score-card">
            <h3>スコア概要</h3>
            <div class="score-total">${scores.total.toFixed(1)}点</div>
            <div class="score-details">
                <div class="score-item">
                    <div class="score-item-label">Situation</div>
                    <div class="score-item-value">${scores.situation}点</div>
                </div>
                <div class="score-item">
                    <div class="score-item-label">Problem</div>
                    <div class="score-item-value">${scores.problem}点</div>
                </div>
                <div class="score-item">
                    <div class="score-item-label">Implication</div>
                    <div class="score-item-value">${scores.implication}点</div>
                </div>
                <div class="score-item">
                    <div class="score-item-label">Need</div>
                    <div class="score-item-value">${scores.need}点</div>
                </div>
            </div>
        </div>
        <div class="feedback-section">
            <h3>フィードバック</h3>
            <div class="feedback-text">${report.feedback}</div>
        </div>
        <div class="feedback-section">
            <h3>次回アクション</h3>
            <div class="feedback-text">${report.next_actions}</div>
        </div>
    `;
    
    if (report.scoring_details) {
        detailsHTML += '<div class="feedback-section"><h3>詳細スコア</h3>';
        
        Object.keys(report.scoring_details).forEach(key => {
            const detail = report.scoring_details[key];
            const labels = {
                'situation': 'Situation（状況確認）',
                'problem': 'Problem（問題発見）',
                'implication': 'Implication（示唆）',
                'need': 'Need（ニーズ確認）'
            };
            
            detailsHTML += `
                <div style="margin-bottom: 20px; padding: 15px; background: white; border-radius: 6px;">
                    <h4>${labels[key] || key} - ${detail.score}点</h4>
                    <p><strong>コメント:</strong> ${detail.comments}</p>
                    ${detail.strengths && detail.strengths.length > 0 ? `
                        <p><strong>強み:</strong></p>
                        <ul>
                            ${detail.strengths.map(s => `<li>${s}</li>`).join('')}
                        </ul>
                    ` : ''}
                    ${detail.weaknesses && detail.weaknesses.length > 0 ? `
                        <p><strong>改善点:</strong></p>
                        <ul>
                            ${detail.weaknesses.map(w => `<li>${w}</li>`).join('')}
                        </ul>
                    ` : ''}
                </div>
            `;
        });
        
        detailsHTML += '</div>';
    }
    
    container.innerHTML = detailsHTML;
}

// セッション一覧の表示
async function viewSessionList() {
    if (!authToken) {
        alert('ログインしてください');
        return;
    }
    
    showStep('sessionList');
    showLoading('sessionListContent');
    
    try {
        const response = await fetch(`${API_BASE_URL}/session/list/`, {
            method: 'GET',
            headers: {
                'Authorization': `Token ${authToken}`
            }
        });
        
        const data = await response.json();
        
        if (response.ok) {
            displaySessionList(data.results);
        } else {
            showError('sessionListContent', 'セッション一覧取得に失敗しました: ' + (data.message || data.error));
        }
    } catch (error) {
        showError('sessionListContent', 'エラー: ' + error.message);
    }
}

// セッション一覧の表示
function displaySessionList(sessions) {
    const container = document.getElementById('sessionListContent');
    
    if (!container) {
        console.error('sessionListContent要素が見つかりません');
        return;
    }
    
    if (sessions.length === 0) {
        container.innerHTML = '<p>セッションがありません</p>';
        return;
    }
    
    container.innerHTML = sessions.map(session => `
        <div class="session-item" onclick="viewSessionDetail('${session.id}')">
            <div class="session-item-header">
                <span class="session-item-id">${session.id}</span>
                <span class="session-item-status ${session.status}">${session.status === 'active' ? '進行中' : '完了'}</span>
            </div>
            <div class="session-item-info">
                <div><strong>業界:</strong> ${session.industry}</div>
                <div><strong>価値提案:</strong> ${session.value_proposition}</div>
                <div><strong>開始日時:</strong> ${new Date(session.started_at).toLocaleString('ja-JP')}</div>
                ${session.finished_at ? `<div><strong>終了日時:</strong> ${new Date(session.finished_at).toLocaleString('ja-JP')}</div>` : ''}
            </div>
        </div>
    `).join('');
}

// セッション一覧の更新
function refreshSessionList() {
    viewSessionList();
}

// セッション詳細の表示
async function viewSessionDetail(sessionId) {
    currentSessionId = sessionId;
    showStep(3);
    await loadChatHistory();
}

// 新しいセッションを開始
function startNewSession() {
    currentSessionId = null;
    currentReportId = null;
    resetToStep1();
}

// ステップ1にリセット
function resetToStep1() {
    showStep(1);
    const spinResult = document.getElementById('spinQuestionsResult');
    if (spinResult) spinResult.style.display = 'none';
    
    const sessionResult = document.getElementById('sessionStartResult');
    if (sessionResult) sessionResult.style.display = 'none';
    
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) chatMessages.innerHTML = '';
    
    const chatInput = document.getElementById('chatMessageInput');
    if (chatInput) chatInput.value = '';
}

// ステップの表示切り替え
function showStep(stepNumber) {
    // すべてのステップを非表示
    const sections = document.querySelectorAll('.step-section');
    if (sections && sections.length > 0) {
        sections.forEach(section => {
            section.classList.remove('active');
            section.style.display = 'none';
        });
    }
    
    // 指定されたステップを表示
    const stepId = typeof stepNumber === 'string' ? stepNumber : `step${stepNumber}`;
    const stepElement = document.getElementById(stepId);
    if (stepElement) {
        stepElement.classList.add('active');
        stepElement.style.display = 'block';
    } else {
        console.warn(`ステップ要素が見つかりません: ${stepId}`);
    }
}

// ローディング表示
function showLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        // 既存のローディング要素を削除
        const existingLoading = element.querySelector('.loading');
        if (existingLoading) {
            existingLoading.remove();
        }
        
        // ローディング要素を追加（既存の内容は保持）
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'loading';
        loadingDiv.innerHTML = '<div class="spinner"></div><p>読み込み中...</p>';
        
        // 要素の先頭に挿入（既存の内容の前）
        element.insertBefore(loadingDiv, element.firstChild);
        element.style.display = 'block';
    } else {
        console.warn(`ローディング要素が見つかりません: ${elementId}`);
    }
}

// エラー表示
function showError(elementId, message) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = message;
        element.style.display = 'block';
    }
}

// 成功メッセージ表示
function showSuccess(message) {
    alert(message);
}

// チャットローディング表示
function showChatLoading() {
    // 実装済み（送信中の表示）
}

// チャットエラー表示
function showChatError(message) {
    addChatMessage('customer', `[エラー] ${message}`);
}

