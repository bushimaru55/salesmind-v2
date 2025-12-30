// API設定
// ローカル開発環境（ポート8080）の場合は直接Djangoサーバー（ポート8000）に接続
// 本番環境（nginx経由）の場合は相対パスを使用
const API_BASE_URL = (window.location.port === '8080' || window.location.hostname === 'localhost') 
    ? 'http://localhost:8000/api' 
    : window.location.origin + '/api';
let authToken = localStorage.getItem('authToken');
let currentSessionId = null;
let currentReportId = null;
let currentMode = localStorage.getItem('currentMode') || null; // 'simple' or 'detailed'
let currentCompanyId = null; // 取得した企業情報のIDを保持
let currentCompanyInfo = null; // 取得した企業情報の内容を保存
let currentSessionInfo = null; // セッション情報（ペルソナ、価値提案など）を保持

// リアルタイム会話関連
let conversationMode = 'text'; // 'text' or 'realtime'
let realtimeClient = null;
let isRealtimeTalking = false;

// コーチングヒント関連
let coachingHintsEnabled = true;
let previousTemperatureScore = null;

// 成功率履歴関連
let successRateHistory = [];
const MAX_SUCCESS_HISTORY = 10;

// ページロード時の処理
window.onload = function() {
    // ロガーを初期化（logger.jsで自動的に初期化される）
    if (window.logger) {
        window.logger.info('SalesMindアプリケーションが起動しました');
    }
    checkAuth();
    initMode();
    initTTSSettings();  // TTS設定を初期化
    initCoachingSettings();  // コーチングヒント設定を初期化
};

// モード初期化
function initMode() {
    // 既にモードが選択されている場合は、そのモードの最初のステップを表示
    if (currentMode) {
        if (currentMode === 'simple') {
            showStep('step1-simple'); // 簡易診断モードのステップ1
        } else if (currentMode === 'detailed') {
            showStep('step1-detailed'); // 詳細診断モードのステップ1（企業情報取得）
        }
    } else {
        // モード未選択の場合は、モード選択画面を表示
        showStep(0);
    }
}

// モード選択
function selectMode(mode) {
    if (window.logger) {
        window.logger.info('モードを選択', { mode });
    }
    
    currentMode = mode;
    localStorage.setItem('currentMode', mode);

    // 詳細診断モードで保持していた企業情報をリセット
    if (mode === 'simple') {
        currentCompanyId = null;
        currentCompanyInfo = null;
        currentSessionInfo = null;

        const companySummary = document.getElementById('companySummary');
        if (companySummary) {
            companySummary.remove();
        }

        const companyInfoResult = document.getElementById('companyInfoResult');
        if (companyInfoResult) {
            companyInfoResult.style.display = 'none';
            companyInfoResult.innerHTML = '';
        }
    }
    
    if (mode === 'simple') {
        // 簡易診断モードの最初のステップへ
        showStep('step1-simple');
    } else if (mode === 'detailed') {
        // 詳細診断モードの最初のステップへ（企業情報取得）
        showStep('step1-detailed');
    }
}

// モード選択画面に戻る
function returnToModeSelection() {
    if (window.logger) {
        window.logger.info('モード選択画面に戻る');
    }
    
    // セッションが進行中の場合は確認を求める
    if (currentSessionId) {
        const confirmed = confirm(
            'セッションが進行中です。モード選択に戻ると、現在のセッションが中断されます。\n\n' +
            '本当にモード選択に戻りますか？'
        );
        
        if (!confirmed) {
            return;
        }
    }
    
    // モードとセッション情報をリセット
    currentMode = null;
    currentSessionId = null;
    currentReportId = null;
    currentCompanyId = null;
    currentCompanyInfo = null;
    currentSessionInfo = null;
    
    localStorage.removeItem('currentMode');
    
    // モード選択画面に戻る
    showStep(0);
    
    // 状態をリセット
    resetToStep1();
    
    if (window.logger) {
        window.logger.info('モード選択画面に戻りました');
    }
}

// 認証状態の確認
function checkAuth() {
    if (authToken) {
        const loginForm = document.getElementById('loginForm');
        const registerForm = document.getElementById('registerForm');
        const authTabs = document.getElementById('authTabs');
        const userInfo = document.getElementById('userInfo');
        const usernameDisplay = document.getElementById('usernameDisplay');
        
        if (loginForm) {
            loginForm.style.display = 'none';
        }
        if (registerForm) {
            registerForm.style.display = 'none';
        }
        if (authTabs) {
            authTabs.style.display = 'none';
        }
        if (userInfo) {
            userInfo.style.display = 'block';
        }
        if (usernameDisplay) {
            usernameDisplay.textContent = localStorage.getItem('username') || 'ユーザー';
        }
        // Tokenが有効か確認（実際の実装ではAPIで確認）
    } else {
        // ログインしていない場合
        const loginForm = document.getElementById('loginForm');
        const registerForm = document.getElementById('registerForm');
        const authTabs = document.getElementById('authTabs');
        const userInfo = document.getElementById('userInfo');
        
        if (loginForm) {
            loginForm.style.display = 'block';
        }
        if (registerForm) {
            registerForm.style.display = 'none';
        }
        if (authTabs) {
            authTabs.style.display = 'flex';
        }
        if (userInfo) {
            userInfo.style.display = 'none';
        }
    }
}

// ログインタブ表示
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
        const loginUrl = `${API_BASE_URL}/auth/login/`;
        console.log('Login URL:', loginUrl);
        console.log('Login request:', { username, password: '***' });
        
        const response = await fetch(loginUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username,
                password
            })
        });
        
        console.log('Login response status:', response.status);
        console.log('Login response headers:', response.headers);
        
        // レスポンスをテキストとして読み取り、その後JSONとして解析
        const responseText = await response.text();
        let data;
        try {
            data = JSON.parse(responseText);
            console.log('Login response data:', data);
        } catch (jsonError) {
            console.error('Failed to parse JSON response:', jsonError);
            console.error('Response text:', responseText);
            showError('loginError', 'サーバーからの応答を解析できませんでした: ' + responseText);
            return;
        }
        
        // メール認証が必要な場合のエラーハンドリング
        if (response.status === 403 && data.email_verification_required) {
            showError('loginError', data.message || 'メールアドレスが認証されていません。登録時に送信されたメールを確認して、認証リンクをクリックしてください。');
            return;
        }
        
        if (response.ok) {
            // ログイン成功 - Tokenを保存
            if (!data.token) {
                console.error('Token not found in response:', data);
                showError('loginError', 'トークンが取得できませんでした');
                return;
            }
            
            authToken = data.token;
            localStorage.setItem('authToken', authToken);
            if (data.user && data.user.username) {
                localStorage.setItem('username', data.user.username);
            }
            
            console.log('Login successful, token saved');
            showSuccess('ログインに成功しました');
            
            // ログイン状態にする
            // ログインフォームと登録フォームを非表示
            const loginForm = document.getElementById('loginForm');
            const registerForm = document.getElementById('registerForm');
            const authTabs = document.getElementById('authTabs');
            if (loginForm) {
                loginForm.style.display = 'none';
            }
            if (registerForm) {
                registerForm.style.display = 'none';
            }
            if (authTabs) {
                authTabs.style.display = 'none';
            }
            
            checkAuth();
            const userInfoDiv = document.getElementById('userInfo');
            const usernameDisplay = document.getElementById('usernameDisplay');
            if (userInfoDiv) {
                userInfoDiv.style.display = 'block';
            }
            if (usernameDisplay && data.user && data.user.username) {
                usernameDisplay.textContent = data.user.username;
            }
        } else {
            // エラー表示
            let errorMsg = 'ログインに失敗しました';
            if (data.message) {
                errorMsg = data.message;
            } else if (data.error) {
                errorMsg = data.error;
            } else if (data.detail) {
                errorMsg = data.detail;
            }
            console.error('Login failed:', errorMsg, data);
            showError('loginError', errorMsg);
        }
    } catch (error) {
        console.error('Login error:', error);
        showError('loginError', 'エラーが発生しました: ' + error.message);
    }
}

// ログアウト
function logout() {
    authToken = null;
    currentMode = null;
    localStorage.removeItem('authToken');
    localStorage.removeItem('username');
    localStorage.removeItem('currentMode');
    
    // ログインフォームとタブを表示
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const authTabs = document.getElementById('authTabs');
    const userInfo = document.getElementById('userInfo');
    
    if (loginForm) {
        loginForm.style.display = 'block';
    }
    if (registerForm) {
        registerForm.style.display = 'none';
    }
    if (authTabs) {
        authTabs.style.display = 'flex';
    }
    if (userInfo) {
        userInfo.style.display = 'none';
    }
    
    // モード選択画面に戻る
    showStep(0);
    resetToStep1();
}

// 診断開始（簡易診断モード用：セッション開始＋チャット画面へ直接遷移）
async function startDiagnosis() {
    // トークンを最新の状態で取得
    authToken = localStorage.getItem('authToken');
    
    if (!authToken) {
        alert('ログインしてください');
        showStep(0); // ログイン画面に戻る
        return;
    }
    
    const industry = document.getElementById('industry').value.trim();
    const value_proposition = document.getElementById('value_proposition').value.trim();
    const customer_persona = document.getElementById('customer_persona').value.trim();
    
    if (window.logger) {
        window.logger.info('診断開始（簡易診断モード）', { industry, value_proposition, customer_persona });
    }
    
    if (!industry || !value_proposition) {
        if (window.logger) {
            window.logger.warning('診断開始: 必須項目が不足しています', { industry, value_proposition });
        }
        alert('業界と価値提案は必須です');
        return;
    }
    
    showLoading('diagnosisStartResult');
    
    try {
        // セッションを開始
        const response = await fetch(`${API_BASE_URL}/session/start/`, {
            method: 'POST',
            headers: {
                'Authorization': `Token ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                mode: 'simple',  // 明示的にmodeを指定
                industry,
                value_proposition,
                customer_persona: customer_persona || undefined,
                customer_pain: null // 顧客の課題は聞き出すべきなので、入力しない
            })
        });
        
        // 401エラーの場合は、JSON解析前にチェック
        if (response.status === 401) {
            // 認証エラー - トークンをクリアしてログイン画面に戻る
            authToken = null;
            localStorage.removeItem('authToken');
            localStorage.removeItem('username');
            
            if (window.logger) {
                window.logger.warning('認証エラー（401）: トークンが無効です。ログイン画面に戻ります。');
            }
            
            alert('ログインセッションが期限切れです。再度ログインしてください。');
            logout(); // ログアウト処理で画面をリセット
            return;
        }
        
        const data = await response.json();
        
        if (response.ok) {
            currentSessionId = data.id;
            currentCompanyId = null; // 簡易診断モードでは企業情報なし
            
            // セッション情報を保存（リアルタイム会話用）
            currentSessionInfo = {
                industry: industry,
                value_proposition: value_proposition,
                customer_persona: customer_persona || null,
                company_name: null
            };
            
            if (window.logger) {
                window.logger.info('セッション開始成功、チャット画面へ遷移', { sessionId: currentSessionId, sessionInfo: currentSessionInfo });
            }
            
            // 直接チャット画面へ遷移
            showStep(3);
            loadChatHistory();
        } else {
            // バリデーションエラーなどの場合
            let errorMsg = 'セッション開始に失敗しました';
            if (data.industry) {
                errorMsg += ': ' + (Array.isArray(data.industry) ? data.industry[0] : data.industry);
            } else if (data.value_proposition) {
                errorMsg += ': ' + (Array.isArray(data.value_proposition) ? data.value_proposition[0] : data.value_proposition);
            } else if (data.mode) {
                errorMsg += ': ' + (Array.isArray(data.mode) ? data.mode[0] : data.mode);
            } else if (data.message) {
                errorMsg += ': ' + data.message;
            } else if (data.error) {
                errorMsg += ': ' + data.error;
            }
            
            if (window.logger) {
                window.logger.error('セッション開始エラー', { status: response.status, data });
            }
            
            showError('diagnosisStartResult', errorMsg);
        }
    } catch (error) {
        let errorMsg = 'エラーが発生しました: ' + error.message;
        if (error.message.includes('Failed to fetch') || error.name === 'TypeError') {
            errorMsg = 'サーバーに接続できませんでした。\nバックエンドサーバー（http://localhost:8000）が起動しているか確認してください。';
        }
        if (window.logger) {
            window.logger.error('診断開始エラー', { mode: currentMode, message: error.message, stack: error.stack, errorType: error.name });
        }
        showError('diagnosisStartResult', errorMsg);
    }
}

async function fetchCompanyInfo() {
    if (!authToken) {
        alert('ログインしてください');
        return;
    }
    
    const company_url = document.getElementById('company_url').value.trim();
    const value_proposition = document.getElementById('detailed_value_proposition').value.trim();
    
    if (window.logger) {
        window.logger.info('企業情報取得を開始', { company_url, value_proposition });
    }
    
    if (!company_url || !value_proposition) {
        if (window.logger) {
            window.logger.warning('企業情報取得: 必須項目が不足しています', { company_url, value_proposition });
        }
        alert('企業URLと価値提案は必須です');
        return;
    }
    
    // URL形式の簡易チェック
    try {
        new URL(company_url);
    } catch (e) {
        alert('有効なURLを入力してください');
        return;
    }
    
    showLoading('companyInfoResult');
    
    try {
        const response = await fetch(`${API_BASE_URL}/company/scrape/`, {
            method: 'POST',
            headers: {
                'Authorization': `Token ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url: company_url,
                value_proposition: value_proposition
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            currentCompanyId = data.id;
            
            if (window.logger) {
                window.logger.info('企業情報取得成功', { companyId: currentCompanyId });
            }
            
            // 企業情報を表示
            displayCompanyInfo(data);
        } else {
            let errorMessage = '企業情報の取得に失敗しました: ';
            if (response.status === 401) {
                errorMessage = '認証エラーが発生しました。再度ログインしてください。';
                // トークンをクリア
                authToken = null;
                localStorage.removeItem('authToken');
                // ログイン画面に戻る
                setTimeout(() => {
                    alert('セッションが期限切れです。再度ログインしてください。');
                    document.getElementById('loginForm').style.display = 'block';
                    document.getElementById('userInfo').style.display = 'none';
                    showStep(0);
                }, 1000);
            } else if (data.detail) {
                errorMessage += data.detail;
            } else if (data.message) {
                errorMessage += data.message;
            } else if (data.error) {
                errorMessage += data.error;
            } else if (typeof data === 'object' && Object.keys(data).length > 0) {
                errorMessage += JSON.stringify(data);
            } else {
                errorMessage += '不明なエラー';
            }
            if (window.logger) {
                window.logger.error('企業情報取得エラー詳細', { status: response.status, data });
            }
            showError('companyInfoResult', errorMessage);
        }
    } catch (error) {
        let errorMsg = 'エラーが発生しました: ' + error.message;
        if (error.message.includes('Failed to fetch') || error.name === 'TypeError') {
            errorMsg = 'サーバーに接続できませんでした。\nバックエンドサーバー（http://localhost:8000）が起動しているか確認してください。';
        }
        if (window.logger) {
            window.logger.error('企業情報取得エラー', { message: error.message, stack: error.stack, errorType: error.name });
        }
        showError('companyInfoResult', errorMsg);
    }
}

// 企業情報を表示
function displayCompanyInfo(companyData) {
    const resultElement = document.getElementById('companyInfoResult');
    if (!resultElement) {
        if (window.logger) {
            window.logger.error('companyInfoResult要素が見つかりません');
        }
        return;
    }
    
    // ローディングをクリア
    const loadingElement = resultElement.querySelector('.loading');
    if (loadingElement) {
        loadingElement.remove();
    }
    
    const companyInfoHtml = `
        <h3>企業情報を取得しました</h3>
        <div class="company-info-display">
            <div class="company-info-item">
                <strong>企業名:</strong> ${escapeHtml(companyData.company_name || '未設定')}
            </div>
            ${companyData.industry ? `
            <div class="company-info-item">
                <strong>業界:</strong> ${escapeHtml(companyData.industry)}
            </div>
            ` : ''}
            ${companyData.business_description ? `
            <div class="company-info-item">
                <strong>事業内容:</strong> ${escapeHtml(companyData.business_description)}
            </div>
            ` : ''}
            ${companyData.location ? `
            <div class="company-info-item">
                <strong>所在地:</strong> ${escapeHtml(companyData.location)}
            </div>
            ` : ''}
            ${companyData.employee_count ? `
            <div class="company-info-item">
                <strong>従業員数:</strong> ${escapeHtml(companyData.employee_count)}
            </div>
            ` : ''}
            ${companyData.established_year ? `
            <div class="company-info-item">
                <strong>設立年:</strong> ${escapeHtml(String(companyData.established_year))}
            </div>
            ` : ''}
        </div>
        <button onclick="startDetailedDiagnosis()" class="btn-primary">診断開始</button>
    `;
    
    resultElement.innerHTML = companyInfoHtml;
    resultElement.style.display = 'block';
}

// 詳細診断開始（企業情報をセッションに紐付けてチャット開始）
async function startDetailedDiagnosis() {
    // トークンを最新の状態で取得
    authToken = localStorage.getItem('authToken');
    
    if (!authToken) {
        alert('ログインしてください');
        showStep(0); // ログイン画面に戻る
        return;
    }
    
    if (!currentCompanyId) {
        alert('企業情報が取得されていません');
        return;
    }
    
    const company_url = document.getElementById('company_url').value.trim();
    const value_proposition = document.getElementById('detailed_value_proposition').value.trim();
    const customer_persona = document.getElementById('detailed_customer_persona').value.trim();
    
    // 企業情報を取得
    let companyData = null;
    try {
        // スクレイピング済みの企業情報を取得（セッション作成時に使用）
        // ここではセッション作成時にcompany_idを指定するだけでOK
        companyData = { id: currentCompanyId };
    } catch (error) {
        if (window.logger) {
            window.logger.error('企業情報取得エラー', { error });
        }
        alert('企業情報の取得に失敗しました');
        return;
    }
    
    if (window.logger) {
        window.logger.info('詳細診断開始', { companyId: currentCompanyId, value_proposition, customer_persona });
    }
    
    // スクレイピング時に業界情報も取得できているはずなので、企業情報から業界を取得
    // セッション開始時にcompany_idを指定してセッションを作成
    // セッション開始APIを確認して、company_idを指定できるか確認する必要がある
    
    showLoading('companyInfoResult');
    
    try {
        // セッションを開始（企業情報を紐付け）
        const response = await fetch(`${API_BASE_URL}/session/start/`, {
            method: 'POST',
            headers: {
                'Authorization': `Token ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                mode: 'detailed',  // 明示的にmodeを指定
                // company_idがある場合は業界は不要（企業情報から取得される）
                // industry: '', // company_idがある場合は送らない
                value_proposition: value_proposition,
                customer_persona: customer_persona || undefined,
                customer_pain: null,
                company_id: currentCompanyId // 企業情報のID
            })
        });
        
        // 401エラーの場合は、JSON解析前にチェック
        if (response.status === 401) {
            // 認証エラー - トークンをクリアしてログイン画面に戻る
            authToken = null;
            localStorage.removeItem('authToken');
            localStorage.removeItem('username');
            
            if (window.logger) {
                window.logger.warning('認証エラー（401）: トークンが無効です。ログイン画面に戻ります。');
            }
            
            alert('ログインセッションが期限切れです。再度ログインしてください。');
            logout(); // ログアウト処理で画面をリセット
            return;
        }
        
        const data = await response.json();
        
        if (response.ok) {
            currentSessionId = data.id;
            
            // チャット画面に企業情報を保存（表示用）
            currentCompanyInfo = companyData;
            
            // セッション情報を保存（リアルタイム会話用）
            currentSessionInfo = {
                industry: companyData?.industry || null,
                value_proposition: value_proposition,
                customer_persona: customer_persona || null,
                company_name: companyData?.company_name || null
            };
            
            if (window.logger) {
                window.logger.info('詳細診断セッション開始成功、チャット画面へ遷移', { sessionId: currentSessionId, companyId: currentCompanyId, sessionInfo: currentSessionInfo });
            }
            
            // 直接チャット画面へ遷移
            showStep(3);
            loadChatHistory();
        } else {
            // エラーレスポンスの詳細を表示
            let errorMessage = 'セッション開始に失敗しました: ';
            if (data.industry) {
                errorMessage += data.industry[0] || '';
            } else if (data.value_proposition) {
                errorMessage += data.value_proposition[0] || '';
            } else if (data.company_id) {
                errorMessage += data.company_id[0] || '';
            } else if (typeof data === 'object' && Object.keys(data).length > 0) {
                errorMessage += JSON.stringify(data);
            } else {
                errorMessage += data.message || data.error || '不明なエラー';
            }
            if (window.logger) {
                window.logger.error('セッション開始エラー詳細', { status: response.status, data });
            }
            showError('companyInfoResult', errorMessage);
        }
    } catch (error) {
        let errorMsg = 'エラーが発生しました: ' + error.message;
        if (error.message.includes('Failed to fetch') || error.name === 'TypeError') {
            errorMsg = 'サーバーに接続できませんでした。\nバックエンドサーバー（http://localhost:8000）が起動しているか確認してください。';
        }
        if (window.logger) {
            window.logger.error('詳細診断開始エラー', { mode: currentMode, message: error.message, stack: error.stack, errorType: error.name });
        }
        showError('companyInfoResult', errorMsg);
    }
}

// ステップ1: SPIN質問生成（使用されませんが、互換性のために残しています）
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
            window.logger.error('SPIN質問生成エラー', { message: error.message, stack: error.stack, errorType: error.name });
        }
        
        // Failed to fetchエラーの場合、サーバー接続の問題である可能性が高い
        let errorMsg = 'エラー: ' + error.message;
        if (error.message.includes('Failed to fetch') || error.name === 'TypeError') {
            errorMsg = 'サーバーに接続できませんでした。\nバックエンドサーバー（http://localhost:8000）が起動しているか確認してください。';
        }
        showError('spinQuestionsResult', errorMsg);
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
            showError('sessionStartResult', 'セッション開始に失敗しました: ' + (data.detail || data.message || data.error || '不明なエラー'));
        }
    } catch (error) {
        showError('sessionStartResult', 'エラー: ' + error.message);
    }
}

// チャットに進む
function proceedToChat() {
    showStep(3);
    loadChatHistory();
    // 温度スコアパネルを初期化
    initTemperatureScorePanel();
}

// ステップ3: チャット（ストリーミング対応）
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
    
    // AI顧客のメッセージエリアを作成（ストリーミング用）
    const customerMessageId = `customer-${Date.now()}`;
    const customerMessageDiv = document.createElement('div');
    customerMessageDiv.className = 'message customer';
    customerMessageDiv.id = customerMessageId;
    customerMessageDiv.innerHTML = `
        <div class="message-header">
            <span class="message-role">AI顧客</span>
            <span class="message-time">${new Date().toLocaleTimeString('ja-JP')}</span>
        </div>
        <div class="message-content"></div>
    `;
    document.getElementById('chatMessages').appendChild(customerMessageDiv);
    
    const customerMessageContent = customerMessageDiv.querySelector('.message-content');
    let fullResponse = '';
    
    try {
        // ストリーミングAPIを呼び出し
        const response = await fetch(`${API_BASE_URL}/session/chat/stream/`, {
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
        
        if (!response.ok) {
            throw new Error('ストリーミングリクエストに失敗しました');
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        while (true) {
            const { done, value } = await reader.read();
            
            if (done) {
                break;
            }
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n\n');
            buffer = lines.pop() || ''; // 最後の不完全な行を保持
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        
                        if (data.type === 'chunk') {
                            fullResponse += data.content;
                            // タイピング効果で表示
                            customerMessageContent.textContent = fullResponse;
                            // 自動スクロール
                            const chatMessages = document.getElementById('chatMessages');
                            chatMessages.scrollTop = chatMessages.scrollHeight;
                        } else if (data.type === 'done') {
                            // ストリーミング完了
                            fullResponse = data.full_response || fullResponse;
                            customerMessageContent.textContent = fullResponse;
                            
                            // 温度スコアの更新
                            if (data.current_temperature !== undefined) {
                                updateTemperatureScore(data.current_temperature, data.temperature_details || {});
                            }
                            if (data.temperature_history && data.temperature_history.length > 0) {
                                updateTemperatureChart(data.temperature_history);
                            }
                            
                            // コーチングヒントを生成
                            // 詳細診断モードの場合はsuccess_deltaを優先的に使用
                            const scoreForHint = data.success_probability !== undefined 
                                ? data.success_probability 
                                : data.current_temperature;
                            const deltaForHint = data.success_delta !== undefined 
                                ? data.success_delta 
                                : (previousTemperatureScore !== null 
                                    ? data.current_temperature - previousTemperatureScore 
                                    : 0);
                            
                            console.log('[Coaching] ストリーミング完了、ヒント生成開始');
                            console.log('[Coaching] ヒント用データ:', {
                                fullResponse: fullResponse?.substring(0, 50) + '...',
                                scoreForHint,
                                deltaForHint,
                                current_spin_stage: data.current_spin_stage,
                                success_probability: data.success_probability,
                                success_delta: data.success_delta
                            });
                            
                            generateCoachingHint(
                                fullResponse, 
                                scoreForHint, 
                                deltaForHint,
                                data.current_spin_stage
                            );
                            previousTemperatureScore = data.current_temperature;
                            
                            // 失注確定の場合、失注情報を表示
                            if (data.loss_response) {
                                displayLossResponse(data.loss_response);
                                if (data.should_end_session) {
                                    setTimeout(() => {
                                        if (confirm('商談が失注となりました。セッションを終了してスコアリングに進みますか？')) {
                                            finishSession();
                                        }
                                    }, 2000);
                                }
                            }
                            
                            // クロージング提案がある場合は表示
                            if (data.closing_proposal) {
                                displayClosingProposal(data.closing_proposal);
                            }
                            
                            // 会話フェーズがCLOSING_READYまたはCLOSING_ACTIONの場合、UIに表示
                            if (data.conversation_phase === 'CLOSING_READY' || data.conversation_phase === 'CLOSING_ACTION') {
                                showClosingPhaseIndicator(data.conversation_phase);
                            }
                            
                            // 失注候補または失注確定の場合、UIに表示
                            if (data.conversation_phase === 'LOSS_CANDIDATE' || data.conversation_phase === 'LOSS_CONFIRMED') {
                                showLossPhaseIndicator(data.conversation_phase);
                            }
                            
                            // 詳細診断モードの場合、TTSボタンを追加
                            if (currentMode === 'detailed' && fullResponse) {
                                console.log('[TTS] TTSボタンを追加中...');
                                // TTSボタンを追加
                                const ttsButton = document.createElement('button');
                                ttsButton.className = 'tts-play-btn';
                                ttsButton.title = '音声で再生';
                                ttsButton.textContent = '🔊';
                                // fullResponseを保持するためにクロージャを使用
                                const responseText = fullResponse;
                                ttsButton.onclick = function() {
                                    console.log('[TTS] 🔊ボタンがクリックされました');
                                    playCustomerVoice(responseText);
                                };
                                const header = customerMessageDiv.querySelector('.message-header');
                                if (header) {
                                    header.appendChild(ttsButton);
                                    console.log('[TTS] TTSボタンを追加しました');
                                } else {
                                    console.warn('[TTS] message-headerが見つかりません');
                                }
                                
                                // 自動再生が有効な場合は音声を再生
                                if (autoPlayVoice) {
                                    console.log('[TTS] 自動再生開始');
                                    playCustomerVoice(fullResponse);
                                }
                            }
                            
                            // 詳細診断モードの場合、成功率情報を更新
                            console.log('[Score] 成功率データ確認:', {
                                currentMode,
                                success_probability: data.success_probability,
                                success_delta: data.success_delta,
                                analysis_reason: data.analysis_reason,
                                current_spin_stage: data.current_spin_stage
                            });
                            if (currentMode === 'detailed' && data.success_probability !== undefined) {
                                console.log('[Score] 成功率更新を実行します');
                                updateSuccessProbability(data.success_probability, data.success_delta, data.analysis_reason, {
                                    currentStage: data.current_spin_stage,
                                    messageSpinType: data.message_spin_type,
                                    stepAppropriateness: data.step_appropriateness,
                                    stageEvaluation: data.stage_evaluation,
                                    sessionStage: data.session_spin_stage,
                                    systemNotes: data.system_notes
                                });
                                
                                if (window.logger) {
                                    window.logger.info('成功率更新（ストリーミング）', {
                                        success_probability: data.success_probability,
                                        success_delta: data.success_delta,
                                        analysis_reason: data.analysis_reason,
                                        current_spin_stage: data.current_spin_stage,
                                        message_spin_type: data.message_spin_type,
                                        step_appropriateness: data.step_appropriateness,
                                        stage_evaluation: data.stage_evaluation,
                                        session_spin_stage: data.session_spin_stage,
                                        conversation_phase: data.conversation_phase
                                    });
                                }
                            }
                        } else if (data.type === 'error') {
                            // 有償プランへの誘導が必要な場合
                            if (data.upgrade_required) {
                                const upgradeMessage = data.error || '有償プランであればさらにご利用頂けます';
                                const landingUrl = data.landing_page_url || '/landing.html';
                                showChatUpgradeMessage(upgradeMessage, landingUrl);
                            } else {
                                throw new Error(data.error);
                            }
                        }
                    } catch (e) {
                        console.error('ストリームデータのパースエラー:', e);
                        if (window.logger) {
                            window.logger.error('ストリームデータのパースエラー', { error: e });
                        }
                    }
                }
            }
        }
        
    } catch (error) {
        console.error('メッセージ送信エラー:', error);
        customerMessageContent.textContent = 'エラーが発生しました: ' + error.message;
        if (window.logger) {
            window.logger.error('メッセージ送信エラー', { error });
        }
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
function addChatMessage(role, message, temperature = null, temperatureChange = null, tempDelta = null) {
    // ウェルカムメッセージを非表示にする
    hideWelcomeMessage();
    
    const container = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const roleLabel = role === 'salesperson' ? '営業担当者' : 'AI顧客';
    const timestamp = new Date().toLocaleTimeString('ja-JP');
    
    // 温度スコアアイコン（顧客メッセージのみ）
    let temperatureIcon = '';
    let reactionBadge = '';
    if (role === 'customer' && temperature !== null && temperature !== undefined) {
        const iconClass = temperatureChange === '↑' ? 'temp-up' : temperatureChange === '↓' ? 'temp-down' : 'temp-same';
        temperatureIcon = `<span class="temperature-icon ${iconClass}">${temperatureChange || ''}</span>`;
        
        // 反応クラスを追加
        if (temperatureChange === '↑') {
            messageDiv.classList.add('reaction-positive');
            reactionBadge = '<span class="message-reaction-badge positive">👍 好反応</span>';
        } else if (temperatureChange === '↓') {
            messageDiv.classList.add('reaction-negative');
            reactionBadge = '<span class="message-reaction-badge negative">📉 要改善</span>';
        }
        
        // 大きな変化の場合はより強い反応クラスに変更
        if (tempDelta !== null) {
            if (tempDelta > 5) {
                messageDiv.classList.remove('reaction-positive');
                messageDiv.classList.add('reaction-very-positive');
                reactionBadge = '<span class="message-reaction-badge positive">🔥 絶好調！</span>';
            } else if (tempDelta < -5) {
                messageDiv.classList.remove('reaction-negative');
                messageDiv.classList.add('reaction-very-negative');
                reactionBadge = '<span class="message-reaction-badge negative">⚠️ 要注意</span>';
            }
        }
    }
    
    // 音声再生ボタン（詳細診断モードの顧客メッセージのみ）
    let ttsButton = '';
    if (role === 'customer' && currentMode === 'detailed') {
        const escapedMessage = message.replace(/'/g, "\\'").replace(/"/g, '\\"');
        ttsButton = `
            <button class="tts-play-btn" onclick="playCustomerVoice('${escapedMessage}')" title="音声で再生">
                🔊
            </button>
        `;
    }
    
    messageDiv.innerHTML = `
        <div class="message-header">
            ${roleLabel} - ${timestamp}
            ${temperatureIcon}
            ${reactionBadge}
            ${ttsButton}
        </div>
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
    
    // ウェルカムメッセージ以外をクリア
    const welcome = document.getElementById('chatWelcome');
    container.innerHTML = '';
    if (welcome && conversation.length === 0) {
        container.appendChild(welcome);
        showWelcomeMessage();
    } else if (conversation.length > 0) {
        hideWelcomeMessage();
    }
    
    let previousTemperature = null;
    conversation.forEach((msg, index) => {
        const temperature = msg.temperature_score;
        const temperatureChange = getTemperatureChangeIcon(previousTemperature, temperature);
        addChatMessage(msg.role, msg.message, temperature, temperatureChange);
        if (temperature !== undefined && temperature !== null) {
            previousTemperature = temperature;
        }
    });
}

// 温度スコアの変化アイコンを取得
function getTemperatureChangeIcon(previousTemp, currentTemp) {
    if (previousTemp === null || previousTemp === undefined || currentTemp === null || currentTemp === undefined) {
        return null;
    }
    
    const diff = currentTemp - previousTemp;
    if (diff > 5) {
        return '↑'; // 上昇
    } else if (diff < -5) {
        return '↓'; // 下降
    } else {
        return '→'; // 変化なし
    }
}

// ===== Text-to-Speech (TTS) 関連 =====

// 現在選択されている音声
let selectedVoice = 'nova';
// 音声の自動再生設定
let autoPlayVoice = false;
// 現在再生中のAudio要素
let currentAudio = null;

// 顧客の応答を音声で再生
async function playCustomerVoice(text) {
    console.log('[TTS] playCustomerVoice called with text:', text?.substring(0, 50) + '...');
    
    if (!text || !text.trim()) {
        console.warn('[TTS] 再生するテキストがありません');
        return;
    }
    
    // 現在再生中の音声があれば停止
    if (currentAudio) {
        console.log('[TTS] 既存の音声を停止');
        currentAudio.pause();
        currentAudio = null;
    }
    
    try {
        // 再生ボタンを読み込み中状態に
        const playButtons = document.querySelectorAll('.tts-play-btn');
        playButtons.forEach(btn => btn.disabled = true);
        
        // 顧客ペルソナを取得
        const persona = currentSessionInfo?.customer_persona || '';
        const autoDetect = localStorage.getItem('ttsAutoDetect') === 'true';
        
        console.log('[TTS] API呼び出し開始:', { voice: selectedVoice, autoDetect, persona: persona?.substring(0, 30) });
        console.log('[TTS] API URL:', `${API_BASE_URL}/tts/generate/`);
        
        const response = await fetch(`${API_BASE_URL}/tts/generate/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Token ${authToken}`
            },
            body: JSON.stringify({
                text: text,
                voice: selectedVoice,
                auto_detect: autoDetect,
                persona: persona
            })
        });
        
        console.log('[TTS] APIレスポンス:', response.status, response.statusText);
        
        if (!response.ok) {
            const errorData = await response.json();
            console.error('[TTS] APIエラー:', errorData);
            throw new Error(errorData.error || '音声生成に失敗しました');
        }
        
        // 使用された音声を取得
        const voiceUsed = response.headers.get('X-Voice-Used');
        console.log('[TTS] 使用された音声:', voiceUsed);
        
        // 音声データをBlobとして取得
        const audioBlob = await response.blob();
        console.log('[TTS] Blobサイズ:', audioBlob.size, 'bytes');
        const audioUrl = URL.createObjectURL(audioBlob);
        
        // 音声を再生
        console.log('[TTS] 音声再生開始');
        currentAudio = new Audio(audioUrl);
        currentAudio.onended = () => {
            console.log('[TTS] 音声再生終了');
            currentAudio = null;
            URL.revokeObjectURL(audioUrl);
        };
        currentAudio.onerror = (e) => {
            console.error('[TTS] 音声再生エラー:', e);
            currentAudio = null;
            URL.revokeObjectURL(audioUrl);
        };
        
        await currentAudio.play();
        
    } catch (error) {
        console.error('[TTS] エラー:', error);
        console.error('[TTS] スタックトレース:', error.stack);
        alert('音声再生に失敗しました: ' + error.message);
    } finally {
        // ボタンを再度有効化
        const playButtons = document.querySelectorAll('.tts-play-btn');
        playButtons.forEach(btn => btn.disabled = false);
    }
}

// 音声再生を停止
function stopVoicePlayback() {
    if (currentAudio) {
        currentAudio.pause();
        currentAudio = null;
    }
}

// 音声設定を変更
function setVoice(voice) {
    if (voice === 'auto') {
        // 自動選択モード：ペルソナから判定するため、novaをデフォルトに
        selectedVoice = 'nova';
        localStorage.setItem('ttsVoice', 'auto');
        localStorage.setItem('ttsAutoDetect', 'true');
    } else {
        selectedVoice = voice;
        localStorage.setItem('ttsVoice', voice);
        localStorage.setItem('ttsAutoDetect', 'false');
    }
    console.log(`音声を変更: ${voice}`);
}

// 自動再生設定を変更
function setAutoPlayVoice(enabled) {
    autoPlayVoice = enabled;
    localStorage.setItem('ttsAutoPlay', enabled ? 'true' : 'false');
    console.log(`自動再生: ${enabled ? 'ON' : 'OFF'}`);
}

// TTS設定を初期化
function initTTSSettings() {
    const savedVoice = localStorage.getItem('ttsVoice');
    if (savedVoice && savedVoice !== 'auto') {
        selectedVoice = savedVoice;
    }
    
    const savedAutoPlay = localStorage.getItem('ttsAutoPlay');
    if (savedAutoPlay === 'true') {
        autoPlayVoice = true;
    }
    
    // UI要素を初期化
    const voiceSelect = document.getElementById('voiceSelect');
    if (voiceSelect) {
        const ttsAutoDetect = localStorage.getItem('ttsAutoDetect');
        if (ttsAutoDetect === 'true' || savedVoice === 'auto') {
            voiceSelect.value = 'auto';
        } else if (savedVoice) {
            voiceSelect.value = savedVoice;
        }
    }
    
    const autoPlayCheckbox = document.getElementById('autoPlayVoice');
    if (autoPlayCheckbox) {
        autoPlayCheckbox.checked = autoPlayVoice;
    }
}

// ===== コーチングヒント機能 =====

// コーチングヒント設定を初期化
function initCoachingSettings() {
    const savedState = localStorage.getItem('coachingHintsEnabled');
    coachingHintsEnabled = savedState !== 'false'; // デフォルトはtrue
    
    const toggle = document.getElementById('coachingHintToggle');
    if (toggle) {
        toggle.checked = coachingHintsEnabled;
    }
    
    updateCoachingPanelVisibility();
}

// コーチングヒントの表示/非表示を切り替え
function toggleCoachingHints(enabled) {
    coachingHintsEnabled = enabled;
    localStorage.setItem('coachingHintsEnabled', enabled.toString());
    updateCoachingPanelVisibility();
    
    if (window.logger) {
        window.logger.info('コーチングヒント設定を変更', { enabled });
    }
}

// コーチングパネルの表示状態を更新
function updateCoachingPanelVisibility() {
    const panel = document.getElementById('coachingHintPanel');
    if (panel) {
        if (coachingHintsEnabled) {
            panel.classList.remove('hidden');
        } else {
            panel.classList.add('hidden');
        }
    }
}

// コーチングパネルの展開/折りたたみ切り替え
function toggleCoachingPanelExpand() {
    const panel = document.getElementById('coachingHintPanel');
    if (panel) {
        panel.classList.toggle('collapsed');
    }
}

// コーチングヒントのプレビューを更新
function updateCoachingHintPreview(text) {
    const preview = document.getElementById('coachingHintPreview');
    if (preview) {
        preview.textContent = text || '会話を開始してください';
    }
}

// コーチングヒントを更新
function updateCoachingHint(hintType, message, icon = null) {
    if (!coachingHintsEnabled) return;
    
    const content = document.getElementById('coachingHintContent');
    if (!content) return;
    
    // アイコンを決定
    const icons = {
        'info': '📝',
        'success': '✅',
        'warning': '⚠️',
        'danger': '🚨',
        'tip': '💡'
    };
    const hintIcon = icon || icons[hintType] || '📝';
    
    // 新しいヒントを作成
    const hintHtml = `
        <div class="coaching-hint-item hint-${hintType}">
            <span class="hint-icon">${hintIcon}</span>
            <span class="hint-text">${message}</span>
        </div>
    `;
    
    content.innerHTML = hintHtml;
}

// 複数のコーチングヒントを表示
function updateCoachingHints(hints) {
    console.log('[Coaching] updateCoachingHints called:', hints);
    
    if (!coachingHintsEnabled) {
        console.log('[Coaching] ヒント機能が無効');
        return;
    }
    
    const content = document.getElementById('coachingHintContent');
    if (!content) {
        console.log('[Coaching] coachingHintContent要素が見つかりません');
        return;
    }
    
    const icons = {
        'info': '📝',
        'success': '✅',
        'warning': '⚠️',
        'danger': '🚨',
        'tip': '💡'
    };
    
    let hintsHtml = '';
    hints.forEach(hint => {
        const hintIcon = hint.icon || icons[hint.type] || '📝';
        const pulseClass = hint.pulse ? ' hint-pulse' : '';
        hintsHtml += `
            <div class="coaching-hint-item hint-${hint.type}${pulseClass}">
                <span class="hint-icon">${hintIcon}</span>
                <span class="hint-text">${hint.message}</span>
            </div>
        `;
    });
    
    content.innerHTML = hintsHtml;
    
    // ヒントパネルにアニメーションを追加
    const panel = document.getElementById('coachingHintPanel');
    if (panel) {
        panel.classList.add('hint-updated');
        setTimeout(() => panel.classList.remove('hint-updated'), 1000);
    }
    
    // プレビューを更新（最初のヒントのテキストを使用）
    if (hints.length > 0) {
        const firstHint = hints[0];
        const previewText = firstHint.message.replace(/^[^\s]+\s/, ''); // 絵文字を除去
        updateCoachingHintPreview(previewText.substring(0, 50) + (previewText.length > 50 ? '...' : ''));
    }
    
    console.log('[Coaching] ヒントHTML更新完了');
}

// 顧客の応答に基づいてコーチングヒントを生成
function generateCoachingHint(customerMessage, temperatureScore, temperatureChange, spinStage) {
    if (!coachingHintsEnabled) {
        console.log('[Coaching] ヒント機能が無効化されています');
        return;
    }
    
    console.log('[Coaching] ヒント生成開始:', { 
        messageLength: customerMessage?.length, 
        temperatureScore, 
        temperatureChange, 
        spinStage 
    });
    
    const hints = [];
    const message = customerMessage || '';
    
    // 温度スコアの変化に基づくヒント
    if (temperatureChange !== null && temperatureChange !== undefined) {
        if (temperatureChange > 5) {
            hints.push({
                type: 'success',
                message: '🔥 良い反応です！この調子で続けましょう。顧客の興味が高まっています。',
                icon: '🔥'
            });
        } else if (temperatureChange > 0) {
            hints.push({
                type: 'success',
                message: '👍 良い方向に進んでいます。質問を続けてください。',
                icon: '👍'
            });
        } else if (temperatureChange < -5) {
            hints.push({
                type: 'warning',
                message: '📉 顧客の興味が下がっています。質問の方向性を変えてみましょう。',
                icon: '📉',
                pulse: true
            });
        } else if (temperatureChange < 0) {
            hints.push({
                type: 'warning',
                message: '⚠️ 少し慎重な反応です。別の角度からアプローチしてみましょう。',
                icon: '⚠️'
            });
        }
    }
    
    // 温度スコアの絶対値に基づくヒント
    if (temperatureScore !== null && temperatureScore !== undefined && hints.length === 0) {
        if (temperatureScore >= 80) {
            hints.push({
                type: 'tip',
                message: '🎯 クロージングのタイミングです。具体的な提案に移行しましょう。',
                icon: '🎯'
            });
        } else if (temperatureScore >= 60) {
            hints.push({
                type: 'success',
                message: '✨ 顧客の関心が高まっています。深掘り質問をしましょう。',
                icon: '✨'
            });
        } else if (temperatureScore >= 40) {
            hints.push({
                type: 'info',
                message: '📊 中程度の関心です。課題を明確にする質問を続けましょう。',
                icon: '📊'
            });
        } else if (temperatureScore <= 30) {
            hints.push({
                type: 'danger',
                message: '⚡ 顧客の関心が低い状態です。課題やニーズを再度確認してみましょう。',
                icon: '⚡',
                pulse: true
            });
        }
    }
    
    // キーワード検出に基づくヒント（日本語は大文字小文字変換不要）
    // ポジティブなキーワード
    if (message.includes('興味') || message.includes('面白い') || message.includes('いいですね')) {
        hints.push({
            type: 'success',
            message: '👀 顧客が興味を示しています！詳しく説明するチャンスです。',
            icon: '👀'
        });
    }
    
    if (message.includes('詳しく') || message.includes('もっと教えて') || message.includes('具体的に')) {
        hints.push({
            type: 'success',
            message: '📝 詳細説明を求められています。具体的な事例やデータを示しましょう。',
            icon: '📝'
        });
    }
    
    // 予算・コスト関連
    if (message.includes('予算') || message.includes('費用') || message.includes('コスト') || message.includes('金額') || message.includes('いくら') || message.includes('値段')) {
        hints.push({
            type: 'tip',
            message: '💰 予算の話題です。ROIや費用対効果を説明しましょう。',
            icon: '💰'
        });
    }
    
    // 検討・決定関連
    if (message.includes('検討') || message.includes('考え') || message.includes('相談')) {
        hints.push({
            type: 'info',
            message: '🤔 検討段階です。決裁者や導入スケジュールを確認しましょう。',
            icon: '🤔'
        });
    }
    
    if (message.includes('上司') || message.includes('上長') || message.includes('決裁') || message.includes('承認')) {
        hints.push({
            type: 'tip',
            message: '👔 決裁プロセスの話題です。意思決定者への提案資料を提案しましょう。',
            icon: '👔'
        });
    }
    
    // 競合関連
    if (message.includes('他社') || message.includes('競合') || message.includes('比較') || message.includes('○○社')) {
        hints.push({
            type: 'warning',
            message: '⚔️ 競合の話題です。差別化ポイントを明確に伝えましょう。',
            icon: '⚔️'
        });
    }
    
    // スケジュール関連
    if (message.includes('いつ') || message.includes('スケジュール') || message.includes('納期') || message.includes('期間') || message.includes('時期')) {
        hints.push({
            type: 'success',
            message: '📅 時期に関心があります。導入タイムラインを提示しましょう。',
            icon: '📅'
        });
    }
    
    // ネガティブなキーワード
    if (message.includes('難しい') || message.includes('無理') || message.includes('できない') || message.includes('厳しい')) {
        hints.push({
            type: 'danger',
            message: '🔧 否定的な反応です。具体的な懸念点を確認しましょう。',
            icon: '🔧',
            pulse: true
        });
    }
    
    if (message.includes('必要ない') || message.includes('間に合ってる') || message.includes('今は') || message.includes('タイミング')) {
        hints.push({
            type: 'warning',
            message: '⏰ タイミングの問題かもしれません。将来の課題について聞いてみましょう。',
            icon: '⏰'
        });
    }
    
    if (message.includes('わからない') || message.includes('よくわかり') || message.includes('どういう')) {
        hints.push({
            type: 'info',
            message: '❓ 理解が不十分なようです。わかりやすい例で説明しましょう。',
            icon: '❓'
        });
    }
    
    // 課題・問題関連
    if (message.includes('課題') || message.includes('問題') || message.includes('困って') || message.includes('悩み')) {
        hints.push({
            type: 'tip',
            message: '🎯 課題が見えてきました！その影響を深掘りしましょう（I質問）。',
            icon: '🎯'
        });
    }
    
    // SPIN段階に基づくヒント
    if (spinStage && hints.length < 2) {
        const spinHints = {
            'S': { type: 'info', message: '🔍 状況確認中です。現状をもっと詳しく聞きましょう。', icon: '🔍' },
            'P': { type: 'info', message: '❓ 問題発掘中です。課題の影響を具体化しましょう。', icon: '❓' },
            'I': { type: 'tip', message: '💭 示唆質問の段階です。問題を放置した影響を考えさせましょう。', icon: '💭' },
            'N': { type: 'success', message: '✨ ニード確認段階です。解決策のメリットを共有しましょう。', icon: '✨' }
        };
        
        const stageKey = spinStage.toUpperCase();
        if (spinHints[stageKey]) {
            hints.push(spinHints[stageKey]);
        }
    }
    
    // ヒントがない場合のデフォルト（メッセージ内容に基づく）
    if (hints.length === 0) {
        // 挨拶系
        if (message.includes('よろしく') || message.includes('こんにちは') || message.includes('ありがとう')) {
            hints.push({
                type: 'info',
                message: '👋 良いスタートです。まずは状況を確認する質問から始めましょう。',
                icon: '👋'
            });
        } else if (message.length < 30) {
            hints.push({
                type: 'info',
                message: '💬 短い返答です。開いた質問で詳しく話してもらいましょう。',
                icon: '💬'
            });
        } else {
            hints.push({
                type: 'info',
                message: '📝 会話を続けましょう。顧客の発言から課題を見つけてください。',
                icon: '📝'
            });
        }
    }
    
    console.log('[Coaching] 生成されたヒント:', hints);
    
    // 最大2つまで表示
    updateCoachingHints(hints.slice(0, 2));
}

// ウェルカムメッセージのセッション情報を更新
function updateWelcomeSessionInfo() {
    const card = document.getElementById('sessionInfoCard');
    if (!card) return;
    
    let html = '';
    
    if (currentSessionInfo) {
        if (currentSessionInfo.company_name) {
            html += `<div class="info-item"><span class="info-label">企業:</span><span class="info-value">${currentSessionInfo.company_name}</span></div>`;
        }
        if (currentSessionInfo.industry) {
            html += `<div class="info-item"><span class="info-label">業界:</span><span class="info-value">${currentSessionInfo.industry}</span></div>`;
        }
        if (currentSessionInfo.customer_persona) {
            html += `<div class="info-item"><span class="info-label">顧客像:</span><span class="info-value">${currentSessionInfo.customer_persona}</span></div>`;
        }
        if (currentSessionInfo.value_proposition) {
            html += `<div class="info-item"><span class="info-label">提案:</span><span class="info-value">${currentSessionInfo.value_proposition}</span></div>`;
        }
    }
    
    if (!html) {
        html = '<p style="color: #888; font-size: 0.9em;">セッション情報を準備中...</p>';
    }
    
    card.innerHTML = html;
}

// ウェルカムメッセージを非表示にする
function hideWelcomeMessage() {
    const welcome = document.getElementById('chatWelcome');
    if (welcome) {
        welcome.style.display = 'none';
    }
}

// ウェルカムメッセージを表示する
function showWelcomeMessage() {
    const welcome = document.getElementById('chatWelcome');
    if (welcome) {
        welcome.style.display = 'flex';
    }
    updateWelcomeSessionInfo();
}

// コーチングヒントをリセット
function resetCoachingHints() {
    previousTemperatureScore = null;
    updateCoachingHint('info', '会話を開始すると、顧客の反応に応じたアドバイスが表示されます', '📝');
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
        
        if (response.ok) {
            // 企業情報がある場合は表示（詳細診断モード）
            if (data.company) {
                displayCompanySummary(data.company);
            }
            
            // 詳細診断モードの場合、成功率パネルを表示
            if (currentMode === 'detailed') {
                showSuccessMeter();
                // 初期成功率を表示（セッションの成功率）
                const initialProbability = data.success_probability !== undefined ? data.success_probability : 50;
                updateSuccessProbability(initialProbability, 0, null, {
                    currentStage: data.current_spin_stage,
                    sessionStage: data.current_spin_stage
                });
            } else {
                // 簡易診断モードの場合は非表示
                hideSuccessMeter();
            }
            
            // メッセージがある場合は表示、なければウェルカムメッセージを表示
            if (data.messages && data.messages.length > 0) {
                updateChatMessages(data.messages);
            } else {
                // メッセージがない場合はウェルカムメッセージを表示
                showWelcomeMessage();
            }
        }
    } catch (error) {
        console.error('チャット履歴の読み込みに失敗:', error);
        if (window.logger) {
            window.logger.error('チャット履歴読み込みエラー', { error });
        }
    }
}

// 企業概要をチャット画面の上部に表示
function displayCompanySummary(companyData) {
    const chatContainer = document.querySelector('.chat-container');
    if (!chatContainer) {
        if (window.logger) {
            window.logger.warning('chat-container要素が見つかりません');
        }
        return;
    }
    
    // 既存の企業概要表示を削除
    const existingSummary = document.getElementById('companySummary');
    if (existingSummary) {
        existingSummary.remove();
    }
    
    // 企業概要表示エリアを作成
    const summaryDiv = document.createElement('div');
    summaryDiv.id = 'companySummary';
    summaryDiv.className = 'company-summary';
    
    const summaryHTML = `
        <div class="company-summary-header">
            <h3>📋 企業概要</h3>
        </div>
        <div class="company-summary-content">
            <div class="company-summary-item">
                <strong>企業名:</strong> ${escapeHtml(companyData.company_name || '未設定')}
            </div>
            ${companyData.industry ? `
            <div class="company-summary-item">
                <strong>業界:</strong> ${escapeHtml(companyData.industry)}
            </div>
            ` : ''}
            ${companyData.business_description ? `
            <div class="company-summary-item">
                <strong>事業内容:</strong> ${escapeHtml(companyData.business_description)}
            </div>
            ` : ''}
            ${companyData.location ? `
            <div class="company-summary-item">
                <strong>所在地:</strong> ${escapeHtml(companyData.location)}
            </div>
            ` : ''}
            ${companyData.employee_count ? `
            <div class="company-summary-item">
                <strong>従業員数:</strong> ${escapeHtml(companyData.employee_count)}
            </div>
            ` : ''}
            ${companyData.established_year ? `
            <div class="company-summary-item">
                <strong>設立年:</strong> ${escapeHtml(String(companyData.established_year))}
            </div>
            ` : ''}
        </div>
    `;
    
    summaryDiv.innerHTML = summaryHTML;
    
    // チャットコンテナの最初に挿入（chatMessagesの前）
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages && chatMessages.parentNode) {
        chatMessages.parentNode.insertBefore(summaryDiv, chatMessages);
    } else {
        // chatMessagesが見つからない場合は、chat-containerの最初に挿入
        chatContainer.insertBefore(summaryDiv, chatContainer.firstChild);
    }
}

// 成功率パネルを表示
function showSuccessMeter() {
    // 旧パネルは非表示（スペース節約のため）
    const successMeter = document.getElementById('successMeter');
    if (successMeter) {
        successMeter.style.display = 'none';  // 'block' → 'none' に変更してスペース節約
    }
    // ステータスバーを表示（新UI）
    const statusBar = document.getElementById('chatStatusBar');
    if (statusBar) {
        statusBar.style.display = 'flex';
    }
}

// 成功率パネルを非表示
function hideSuccessMeter() {
    const successMeter = document.getElementById('successMeter');
    if (successMeter) {
        successMeter.style.display = 'none';
    }
    // ステータスバーも非表示
    const statusBar = document.getElementById('chatStatusBar');
    if (statusBar) {
        statusBar.style.display = 'none';
    }
    const spinMeta = document.getElementById('successSpinMeta');
    if (spinMeta) {
        spinMeta.style.display = 'none';
    }
    const reasonDisplay = document.getElementById('successReasonDisplay');
    if (reasonDisplay) {
        reasonDisplay.style.display = 'none';
    }
    const deltaDisplay = document.getElementById('successDeltaDisplay');
    if (deltaDisplay) {
        deltaDisplay.style.display = 'none';
    }
    const systemNotes = document.getElementById('successSystemNotes');
    if (systemNotes) {
        systemNotes.style.display = 'none';
        systemNotes.textContent = '';
    }
}

// 成功率を更新
function updateSuccessProbability(probability, delta, reason, metadata = {}) {
    console.log('[Score] updateSuccessProbability呼び出し:', { probability, delta, reason, metadata });
    
    // 旧UI要素
    const probabilityValue = document.getElementById('successProbabilityValue');
    const deltaDisplay = document.getElementById('successDeltaDisplay');
    const deltaValue = document.getElementById('successDeltaValue');
    const reasonDisplay = document.getElementById('successReasonDisplay');
    const reasonText = document.getElementById('successReasonText');
    const spinMeta = document.getElementById('successSpinMeta');
    const stageEl = document.getElementById('successSpinStage');
    const messageEl = document.getElementById('successSpinMessage');
    const stepEl = document.getElementById('successSpinAppropriateness');
    const evaluationEl = document.getElementById('successSpinEvaluation');
    const sessionStageEl = document.getElementById('successSpinSessionStage');
    const systemNotesEl = document.getElementById('successSystemNotes');
    
    // 新ステータスバー要素
    const statusBar = document.getElementById('chatStatusBar');
    const statusScoreValue = document.getElementById('statusScoreValue');
    const statusDelta = document.getElementById('statusDelta');
    const statusTrendArrow = document.getElementById('statusTrendArrow');
    const statusTrendText = document.getElementById('statusTrendText');
    const statusStageBadge = document.getElementById('statusStageBadge');
    const statusHistory = document.getElementById('statusHistory');
    
    const { currentStage, messageSpinType, stepAppropriateness, stageEvaluation, sessionStage, systemNotes } = metadata;
    
    // 旧UIの更新
    if (probabilityValue) {
        console.log('[Score] 成功率表示を更新:', probability);
        probabilityValue.classList.add('updating');
        setTimeout(() => {
            probabilityValue.textContent = probability;
            probabilityValue.classList.remove('updating');
        }, 100);
    }
    
    // 新ステータスバーの更新
    if (statusScoreValue) {
        statusScoreValue.classList.add('updating');
        setTimeout(() => {
            statusScoreValue.textContent = Math.round(probability);
            statusScoreValue.classList.remove('updating');
        }, 100);
    }
    
    // ステータスバーの変動表示
    if (statusDelta && delta !== 0) {
        statusDelta.textContent = (delta > 0 ? '+' : '') + delta;
        statusDelta.className = 'status-delta ' + (delta > 0 ? 'positive' : 'negative');
        statusDelta.style.display = 'inline-block';
        
        // ステータスバーにパルスエフェクト
        if (statusBar) {
            statusBar.classList.add(delta > 0 ? 'pulse-positive' : 'pulse-negative');
            setTimeout(() => {
                statusBar.classList.remove('pulse-positive', 'pulse-negative');
            }, 1500);
        }
        
        // 5秒後に非表示
        setTimeout(() => {
            if (statusDelta) statusDelta.style.display = 'none';
        }, 5000);
    } else if (statusDelta) {
        statusDelta.style.display = 'none';
    }
    
    // ステータスバーのトレンド表示
    if (statusTrendArrow && statusTrendText) {
        statusTrendArrow.className = 'status-trend-arrow';
        if (delta > 5) {
            statusTrendArrow.textContent = '↑↑';
            statusTrendArrow.classList.add('up');
            statusTrendText.textContent = '急上昇！';
        } else if (delta > 0) {
            statusTrendArrow.textContent = '↑';
            statusTrendArrow.classList.add('up');
            statusTrendText.textContent = '上昇';
        } else if (delta < -5) {
            statusTrendArrow.textContent = '↓↓';
            statusTrendArrow.classList.add('down');
            statusTrendText.textContent = '急下降';
        } else if (delta < 0) {
            statusTrendArrow.textContent = '↓';
            statusTrendArrow.classList.add('down');
            statusTrendText.textContent = '下降';
        } else {
            statusTrendArrow.textContent = '→';
            statusTrendArrow.classList.add('stable');
            statusTrendText.textContent = '安定';
        }
    }
    
    // 変動量を表示（バッジ形式）- 旧UI
    if (deltaDisplay && deltaValue && delta !== 0) {
        deltaDisplay.style.display = 'inline-flex';
        deltaDisplay.className = 'success-delta-badge ' + (delta > 0 ? 'positive' : 'negative');
        deltaValue.textContent = (delta > 0 ? '+' : '') + delta;
        
        console.log('[Score] 変動表示:', { delta, className: deltaDisplay.className });
        
        setTimeout(() => {
            deltaDisplay.style.display = 'none';
        }, 5000);
    } else if (deltaDisplay && delta === 0) {
        deltaDisplay.style.display = 'none';
    }
    
    // 変動理由を表示
    if (reasonDisplay && reasonText && reason) {
        reasonDisplay.style.display = 'block';
        reasonText.textContent = reason;
    } else if (reasonDisplay && !reason) {
        reasonDisplay.style.display = 'none';
        if (reasonText) {
            reasonText.textContent = '';
        }
    }
    
    const stageLabelMap = {
        S: 'S（状況確認）',
        P: 'P（課題顕在化）',
        I: 'I（示唆）',
        N: 'N（解決メリット）',
        unknown: '判定不能'
    };
    const stepLabelMap = {
        ideal: '理想的な進行',
        appropriate: '適切',
        jump: '段階を飛ばした',
        regression: '逆戻り',
        unknown: '判定不能'
    };
    const evalLabelMap = {
        advance: '段階が前進しました',
        repeat: '同じ段階での深掘り',
        regression: '段階が逆戻りしています',
        jump: '段階を飛び越えています',
        unknown: '段階を判定できません'
    };
    
    // SPIN段階バッジの更新（コンパクトUI用）
    const currentStageKey = currentStage || sessionStage || 'S';
    if (stageEl) {
        const stageLabel = stageLabelMap[currentStageKey] || currentStageKey;
        stageEl.textContent = stageLabel;
        console.log('[Score] SPIN段階更新:', stageLabel);
    }
    if (messageEl) {
        const messageLabel = messageSpinType ? (stageLabelMap[messageSpinType] || messageSpinType) : '';
        if (messageLabel) {
            messageEl.textContent = `→ ${messageLabel}`;
            messageEl.style.display = 'inline-block';
        } else {
            messageEl.style.display = 'none';
        }
    }
    
    // ステータスバーのSPIN段階バッジ更新
    if (statusStageBadge) {
        statusStageBadge.textContent = currentStageKey;
        // バッジの色を段階に応じて変更
        const stageColors = {
            'S': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            'P': 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
            'I': 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
            'N': 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)'
        };
        statusStageBadge.style.background = stageColors[currentStageKey] || stageColors['S'];
    }
    
    // レガシー要素の処理（互換性のため）
    if (spinMeta) {
        const hasMeta = Boolean(currentStage || messageSpinType || stepAppropriateness || stageEvaluation || sessionStage);
        spinMeta.style.display = hasMeta ? 'block' : 'none';
    }
    if (stepEl) {
        const stepLabel = stepAppropriateness ? (stepLabelMap[stepAppropriateness] || stepAppropriateness) : '';
        stepEl.textContent = stepLabel;
    }
    if (evaluationEl) {
        const evalLabel = stageEvaluation ? (evalLabelMap[stageEvaluation] || stageEvaluation) : '';
        evaluationEl.textContent = evalLabel;
    }
    if (sessionStageEl) {
        const sessionStageLabel = sessionStage ? (stageLabelMap[sessionStage] || sessionStage) : '';
        sessionStageEl.textContent = sessionStageLabel;
    }
    if (systemNotesEl) {
        if (systemNotes) {
            systemNotesEl.textContent = systemNotes;
            systemNotesEl.style.display = 'block';
        } else {
            systemNotesEl.textContent = '';
            systemNotesEl.style.display = 'none';
        }
    }
    
    // 成功率履歴を更新
    updateSuccessHistory(probability, delta);
    
    // トレンドインジケーターを更新
    updateSuccessTrend(delta);
    
    // チャット背景エフェクトを適用
    applyChatReactionEffect(delta);
    
    // 成功率メーターにハイライト効果を追加（変動があった場合）
    const successMeter = document.getElementById('successMeter');
    if (successMeter && delta !== 0) {
        successMeter.classList.add(delta > 0 ? 'meter-positive-pulse' : 'meter-negative-pulse');
        setTimeout(() => {
            successMeter.classList.remove('meter-positive-pulse', 'meter-negative-pulse');
        }, 1500);
    }
    
    console.log('[Score] 成功率更新完了:', { probability, delta, historyLength: successRateHistory.length });
}

// 成功率履歴バーを更新
function updateSuccessHistory(probability, delta) {
    successRateHistory.push({ probability, delta });
    if (successRateHistory.length > MAX_SUCCESS_HISTORY) {
        successRateHistory.shift();
    }
    
    // 履歴バーを更新する共通関数
    function renderHistoryBar(container) {
        if (!container) return;
        container.innerHTML = '';
        
        successRateHistory.forEach((item, index) => {
            const barItem = document.createElement('div');
            barItem.className = 'history-bar-item';
            
            if (item.delta > 0) {
                barItem.classList.add('positive');
            } else if (item.delta < 0) {
                barItem.classList.add('negative');
            } else {
                barItem.classList.add('neutral');
            }
            
            const heightPercent = Math.max(20, item.probability);
            barItem.style.height = `${heightPercent}%`;
            
            container.appendChild(barItem);
        });
    }
    
    // 旧UIの履歴バー
    renderHistoryBar(document.getElementById('successHistoryBar'));
    
    // ステータスバーの履歴
    renderHistoryBar(document.getElementById('statusHistory'));
}

// 成功率トレンドインジケーターを更新
function updateSuccessTrend(delta) {
    const trendIndicator = document.getElementById('successTrendIndicator');
    const trendArrow = document.getElementById('trendArrow');
    const trendDescription = document.getElementById('trendDescription');
    
    if (!trendIndicator || !trendArrow || !trendDescription) return;
    
    trendIndicator.style.display = 'flex';
    
    // 矢印とクラスを設定
    trendArrow.className = 'trend-arrow';
    
    if (delta > 5) {
        trendArrow.textContent = '↑↑';
        trendArrow.classList.add('up');
        trendDescription.textContent = '大幅上昇！';
    } else if (delta > 0) {
        trendArrow.textContent = '↑';
        trendArrow.classList.add('up');
        trendDescription.textContent = '上昇中';
    } else if (delta < -5) {
        trendArrow.textContent = '↓↓';
        trendArrow.classList.add('down');
        trendDescription.textContent = '大幅下降...';
    } else if (delta < 0) {
        trendArrow.textContent = '↓';
        trendArrow.classList.add('down');
        trendDescription.textContent = '下降中';
    } else {
        trendArrow.textContent = '→';
        trendArrow.classList.add('stable');
        trendDescription.textContent = '安定';
    }
}

// チャット背景に反応エフェクトを適用
function applyChatReactionEffect(delta) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;
    
    // 既存のreactionクラスを削除
    chatMessages.classList.remove(
        'reaction-positive', 
        'reaction-negative', 
        'reaction-very-positive', 
        'reaction-very-negative'
    );
    
    // 既存のインジケーターを削除
    const existingIndicator = chatMessages.querySelector('.reaction-indicator');
    if (existingIndicator) {
        existingIndicator.remove();
    }
    
    // deltaに基づいてエフェクトを適用
    let reactionClass = '';
    let indicatorClass = '';
    let indicatorText = '';
    let indicatorIcon = '';
    
    if (delta > 5) {
        reactionClass = 'reaction-very-positive';
        indicatorClass = 'positive';
        indicatorIcon = '🔥';
        indicatorText = '好反応！';
    } else if (delta > 0) {
        reactionClass = 'reaction-positive';
        indicatorClass = 'positive';
        indicatorIcon = '👍';
        indicatorText = 'Good!';
    } else if (delta < -5) {
        reactionClass = 'reaction-very-negative';
        indicatorClass = 'negative';
        indicatorIcon = '⚠️';
        indicatorText = '要注意';
    } else if (delta < 0) {
        reactionClass = 'reaction-negative';
        indicatorClass = 'negative';
        indicatorIcon = '📉';
        indicatorText = '下降';
    }
    
    if (reactionClass) {
        chatMessages.classList.add(reactionClass);
        
        // インジケーターを追加
        const indicator = document.createElement('div');
        indicator.className = `reaction-indicator ${indicatorClass}`;
        indicator.innerHTML = `<span>${indicatorIcon}</span><span>${indicatorText}</span>`;
        chatMessages.appendChild(indicator);
        
        // 5秒後にエフェクトをフェードアウト
        setTimeout(() => {
            chatMessages.classList.remove(reactionClass);
            const ind = chatMessages.querySelector('.reaction-indicator');
            if (ind) {
                ind.style.opacity = '0';
                setTimeout(() => ind.remove(), 300);
            }
        }, 5000);
    }
}

// 成功率履歴をリセット
function resetSuccessHistory() {
    successRateHistory = [];
    const historyBar = document.getElementById('successHistoryBar');
    if (historyBar) {
        historyBar.innerHTML = '';
    }
    
    const trendIndicator = document.getElementById('successTrendIndicator');
    if (trendIndicator) {
        trendIndicator.style.display = 'none';
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
            // DRFのAPIExceptionは data.detail で返される
            const errorMessage = data.detail || data.message || data.error || '不明なエラー';
            showError('scoringResult', 'スコアリングに失敗しました: ' + errorMessage);
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
    
    // エラーハンドリング: spin_scoresが存在しない場合
    if (!data || !data.spin_scores) {
        console.error('スコアリング結果が不正です:', data);
        showError('scoringResult', 'スコアリング結果の取得に失敗しました。データが不正です。');
        return;
    }
    
    const scores = data.spin_scores;
    const totalScore = scores.total || 0;
    
    // 新しい5要素スコアリングに対応
    const explorationScore = scores.exploration || 0;
    const implicationScore = scores.implication || 0;
    const valuePropositionScore = scores.value_proposition || 0;
    const customerResponseScore = scores.customer_response || 0;
    const advancementScore = scores.advancement || 0;
    
    // 後方互換性のため、SPIN要素も取得
    const situationScore = scores.situation || explorationScore / 2;
    const problemScore = scores.problem || explorationScore / 2;
    const needScore = scores.need || valuePropositionScore;
    
    // スコアに応じた色を決定
    let scoreColor = '#667eea';
    if (totalScore >= 80) scoreColor = '#28a745';
    else if (totalScore >= 60) scoreColor = '#ffc107';
    else scoreColor = '#dc3545';
    
    // 新しい5要素スコアリングの内訳を表示
    const hasNewScoring = explorationScore > 0 || implicationScore > 0 || valuePropositionScore > 0 || customerResponseScore > 0 || advancementScore > 0;
    
    container.innerHTML = `
        <div class="score-card">
            <div class="score-total" style="color: ${scoreColor}">${totalScore.toFixed(1)}点</div>
            ${hasNewScoring ? `
            <div class="score-details">
                <h4 style="margin-top: 20px; margin-bottom: 10px; font-size: 16px; color: #333;">評価内訳（5要素）</h4>
                <div class="score-item">
                    <div class="score-item-label">① 探索力（Situation/Problem 深掘り）</div>
                    <div class="score-item-value">${explorationScore}/20点</div>
                </div>
                <div class="score-item">
                    <div class="score-item-label">② 影響の引き出し（Implication）</div>
                    <div class="score-item-value">${implicationScore}/20点</div>
                </div>
                <div class="score-item">
                    <div class="score-item-label">③ 価値提案の的確さ（Need-payoff）</div>
                    <div class="score-item-value">${valuePropositionScore}/20点</div>
                </div>
                <div class="score-item">
                    <div class="score-item-label">④ 顧客の反応と整合性</div>
                    <div class="score-item-value">${customerResponseScore}/20点</div>
                </div>
                <div class="score-item">
                    <div class="score-item-label">⑤ 商談前進度（デモ・体験・資料など）</div>
                    <div class="score-item-value">${advancementScore}/20点</div>
                </div>
            </div>
            ` : `
            <div class="score-details">
                <div class="score-item">
                    <div class="score-item-label">Situation</div>
                    <div class="score-item-value">${situationScore}点</div>
                </div>
                <div class="score-item">
                    <div class="score-item-label">Problem</div>
                    <div class="score-item-value">${problemScore}点</div>
                </div>
                <div class="score-item">
                    <div class="score-item-label">Implication</div>
                    <div class="score-item-value">${implicationScore}点</div>
                </div>
                <div class="score-item">
                    <div class="score-item-label">Need</div>
                    <div class="score-item-value">${needScore}点</div>
                </div>
            </div>
            `}
        </div>
        <div class="feedback-section">
            <h3>フィードバック</h3>
            <div class="feedback-text">${data.feedback || 'フィードバックがありません。'}</div>
        </div>
        <div class="feedback-section">
            <h3>次回アクション</h3>
            <div class="feedback-text">${data.next_actions || '次回アクションがありません。'}</div>
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
            showError('reportDetails', 'レポート取得に失敗しました: ' + (data.detail || data.message || data.error || '不明なエラー'));
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
            showError('sessionListContent', 'セッション一覧取得に失敗しました: ' + (data.detail || data.message || data.error || '不明なエラー'));
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
    // セッション関連の状態をすべてリセット
    currentSessionId = null;
    currentReportId = null;
    currentCompanyId = null;
    currentCompanyInfo = null;
    currentSessionInfo = null;
    
    // チャート関連もリセット
    temperatureChartData = [];
    
    // 会話モードをテキストに戻す
    conversationMode = 'text';
    
    // コーチングヒント関連をリセット
    previousTemperatureScore = null;
    resetCoachingHints();
    
    // 成功率履歴をリセット
    resetSuccessHistory();
    
    // フォームの値もクリア
    clearAllForms();
    
    // ステップ1に戻る
    resetToStep1();
    
    if (window.logger) {
        window.logger.info('新しいセッションを開始しました');
    }
}

// すべてのフォームをクリア
function clearAllForms() {
    // 簡易診断モードのフォーム
    const simpleFormFields = ['industry', 'value_proposition', 'customer_persona'];
    simpleFormFields.forEach(id => {
        const field = document.getElementById(id);
        if (field) field.value = '';
    });
    
    // 詳細診断モードのフォーム
    const detailedFormFields = ['companyUrl', 'scrapingStatus', 'value_proposition_detailed', 'customer_persona_detailed'];
    detailedFormFields.forEach(id => {
        const field = document.getElementById(id);
        if (field) {
            if (id === 'scrapingStatus') {
                field.innerHTML = '';
                field.style.display = 'none';
            } else {
                field.value = '';
            }
        }
    });
    
    // 企業情報表示をクリア
    const companyInfoDisplay = document.getElementById('companyInfoDisplay');
    if (companyInfoDisplay) {
        companyInfoDisplay.innerHTML = '';
        companyInfoDisplay.style.display = 'none';
    }
    
    // スコアリング結果をクリア
    const scoringResult = document.getElementById('scoringResult');
    if (scoringResult) scoringResult.innerHTML = '';
    
    // レポート詳細をクリア
    const reportDetails = document.getElementById('reportDetails');
    if (reportDetails) reportDetails.innerHTML = '';
}

// ステップ1にリセット
function resetToStep1() {
    // モードが選択されていない場合は、モード選択画面に戻る
    if (!currentMode) {
        showStep(0);
        return;
    }
    
    // モードが選択されている場合は、そのモードの最初のステップに戻る
    if (currentMode === 'simple') {
        showStep('step1-simple');
    } else if (currentMode === 'detailed') {
        // 詳細診断モードの最初のステップ（企業情報取得）
        showStep('step1-detailed');
    }
    
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
    
    // チャット画面（step3）の場合、モードに応じてリアルタイム会話オプションを制御
    if (stepId === 'step3') {
        updateChatModeAvailability();
    }
}

/**
 * チャットモードの利用可能性を更新
 * 簡易診断モード: テキストのみ
 * 詳細診断モード: テキスト + リアルタイム会話
 */
function updateChatModeAvailability() {
    const modeToggle = document.querySelector('.mode-toggle');
    const realtimeOption = document.querySelector('input[name="chatMode"][value="realtime"]');
    const realtimeLabel = realtimeOption ? realtimeOption.closest('.mode-option') : null;
    
    if (currentMode === 'simple') {
        // 簡易診断モード: リアルタイム会話を非表示
        if (realtimeLabel) {
            realtimeLabel.style.display = 'none';
        }
        // テキストモードを強制選択
        const textOption = document.querySelector('input[name="chatMode"][value="text"]');
        if (textOption) {
            textOption.checked = true;
            switchChatMode('text');
        }
        if (window.logger) {
            window.logger.info('簡易診断モード: リアルタイム会話は無効');
        }
    } else if (currentMode === 'detailed') {
        // 詳細診断モード: リアルタイム会話を表示
        if (realtimeLabel) {
            realtimeLabel.style.display = '';
        }
        if (window.logger) {
            window.logger.info('詳細診断モード: リアルタイム会話が利用可能');
        }
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

// 有償プランへの誘導メッセージを表示
function showChatUpgradeMessage(message, landingUrl) {
    const container = document.getElementById('chatMessages');
    if (!container) return;
    
    const upgradeDiv = document.createElement('div');
    upgradeDiv.className = 'upgrade-message';
    upgradeDiv.innerHTML = `
        <div class="upgrade-content">
            <p class="upgrade-text">${message}</p>
            <a href="${landingUrl}" class="upgrade-button" target="_blank">ランディングページへ</a>
        </div>
    `;
    
    container.appendChild(upgradeDiv);
    container.scrollTop = container.scrollHeight;
}

// クロージング提案を表示
function displayClosingProposal(proposal) {
    const container = document.getElementById('chatMessages');
    if (!container) return;
    
    const proposalDiv = document.createElement('div');
    proposalDiv.className = 'closing-proposal';
    proposalDiv.innerHTML = `
        <div class="closing-proposal-header">💡 次のステップ提案</div>
        <div class="closing-proposal-content">
            <p><strong>${proposal.action_type}</strong></p>
            <p>${proposal.proposal_message}</p>
        </div>
    `;
    
    container.appendChild(proposalDiv);
    container.scrollTop = container.scrollHeight;
}

// クロージングフェーズのインジケーターを表示
function showClosingPhaseIndicator(phase) {
    const indicator = document.getElementById('closingPhaseIndicator');
    if (!indicator) {
        // インジケーターが存在しない場合は作成
        const chatContainer = document.getElementById('chatMessages');
        if (chatContainer) {
            const newIndicator = document.createElement('div');
            newIndicator.id = 'closingPhaseIndicator';
            newIndicator.className = 'closing-phase-indicator';
            chatContainer.parentElement.insertBefore(newIndicator, chatContainer);
        }
    }
    
    const indicatorEl = document.getElementById('closingPhaseIndicator');
    if (indicatorEl) {
        const phaseLabels = {
            'CLOSING_READY': '🎯 クロージング準備完了 - 次のステップを提案しましょう',
            'CLOSING_ACTION': '✅ クロージング実行中 - 会話を収束させましょう'
        };
        indicatorEl.textContent = phaseLabels[phase] || 'クロージング段階';
        indicatorEl.style.display = 'block';
    }
}

// 失注フェーズのインジケーターを表示
function showLossPhaseIndicator(phase) {
    const indicator = document.getElementById('lossPhaseIndicator');
    if (!indicator) {
        // インジケーターが存在しない場合は作成
        const chatContainer = document.getElementById('chatMessages');
        if (chatContainer) {
            const newIndicator = document.createElement('div');
            newIndicator.id = 'lossPhaseIndicator';
            newIndicator.className = 'loss-phase-indicator';
            chatContainer.parentElement.insertBefore(newIndicator, chatContainer);
        }
    }
    
    const indicatorEl = document.getElementById('lossPhaseIndicator');
    if (indicatorEl) {
        const phaseLabels = {
            'LOSS_CANDIDATE': '⚠️ 失注候補 - 商談が失注に向かっています',
            'LOSS_CONFIRMED': '❌ 失注確定 - 商談が失注となりました'
        };
        indicatorEl.textContent = phaseLabels[phase] || '失注段階';
        indicatorEl.style.display = 'block';
    }
}

// 失注確定時の応答を表示
function displayLossResponse(lossResponse) {
    const container = document.getElementById('chatMessages');
    if (!container) return;
    
    const lossDiv = document.createElement('div');
    lossDiv.className = 'loss-response';
    lossDiv.innerHTML = `
        <div class="loss-response-header">❌ 失注確定</div>
        <div class="loss-response-content">
            <p><strong>失注理由:</strong> ${lossResponse.loss_reason_label}</p>
            <p>${lossResponse.response_message}</p>
        </div>
    `;
    
    container.appendChild(lossDiv);
    container.scrollTop = container.scrollHeight;
}

// 温度スコアを更新
function updateTemperatureScore(temperature, details) {
    const panel = document.getElementById('temperatureScorePanel');
    if (panel) {
        panel.style.display = 'flex';
    }
    
    // 円形ゲージを更新
    const gaugeCircle = document.getElementById('gaugeCircle');
    const gaugeText = document.getElementById('gaugeText');
    
    if (gaugeCircle && gaugeText) {
        const circumference = 2 * Math.PI * 50; // r=50
        const offset = circumference - (temperature / 100) * circumference;
        gaugeCircle.style.strokeDashoffset = offset;
        gaugeText.textContent = Math.round(temperature);
        
        // 色を温度に応じて変更
        if (temperature >= 70) {
            gaugeCircle.style.stroke = '#28a745'; // 緑
        } else if (temperature >= 40) {
            gaugeCircle.style.stroke = '#ffc107'; // 黄
        } else {
            gaugeCircle.style.stroke = '#dc3545'; // 赤
        }
    }
}

// 温度スコアの折れ線グラフを更新
let temperatureChartData = [];
let temperatureChartCanvas = null;
let temperatureChartCtx = null;

function initTemperatureChart() {
    temperatureChartCanvas = document.getElementById('temperatureChart');
    if (temperatureChartCanvas) {
        temperatureChartCtx = temperatureChartCanvas.getContext('2d');
    }
}

function updateTemperatureChart(history) {
    if (!temperatureChartCtx) {
        initTemperatureChart();
    }
    
    if (!temperatureChartCtx || !history || history.length === 0) {
        return;
    }
    
    temperatureChartData = history.map(h => ({
        sequence: h.sequence,
        temperature: h.temperature,
        created_at: h.created_at
    }));
    
    drawTemperatureChart();
}

function drawTemperatureChart() {
    if (!temperatureChartCtx || temperatureChartData.length === 0) {
        return;
    }
    
    const canvas = temperatureChartCanvas;
    const ctx = temperatureChartCtx;
    const width = canvas.width;
    const height = canvas.height;
    const padding = 20;
    
    // クリア
    ctx.clearRect(0, 0, width, height);
    
    if (temperatureChartData.length < 2) {
        return;
    }
    
    // データの範囲を計算
    const minTemp = Math.min(...temperatureChartData.map(d => d.temperature));
    const maxTemp = Math.max(...temperatureChartData.map(d => d.temperature));
    const tempRange = maxTemp - minTemp || 100;
    
    // グラフ領域
    const graphWidth = width - padding * 2;
    const graphHeight = height - padding * 2;
    
    // グリッド線を描画
    ctx.strokeStyle = '#e0e0e0';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
        const y = padding + (graphHeight / 4) * i;
        ctx.beginPath();
        ctx.moveTo(padding, y);
        ctx.lineTo(width - padding, y);
        ctx.stroke();
    }
    
    // 折れ線を描画
    ctx.strokeStyle = '#667eea';
    ctx.lineWidth = 2;
    ctx.beginPath();
    
    temperatureChartData.forEach((data, index) => {
        const x = padding + (graphWidth / (temperatureChartData.length - 1)) * index;
        const y = padding + graphHeight - ((data.temperature - minTemp) / tempRange) * graphHeight;
        
        if (index === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    });
    
    ctx.stroke();
    
    // 点を描画
    ctx.fillStyle = '#667eea';
    temperatureChartData.forEach((data, index) => {
        const x = padding + (graphWidth / (temperatureChartData.length - 1)) * index;
        const y = padding + graphHeight - ((data.temperature - minTemp) / tempRange) * graphHeight;
        
        ctx.beginPath();
        ctx.arc(x, y, 3, 0, 2 * Math.PI);
        ctx.fill();
    });
    
    // ラベルを描画
    ctx.fillStyle = '#666';
    ctx.font = '10px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('0', padding - 10, height - padding + 5);
    ctx.fillText('100', padding - 10, padding + 5);
}

// 温度スコアパネルの初期化
function initTemperatureScorePanel() {
    initTemperatureChart();
    const panel = document.getElementById('temperatureScorePanel');
    if (panel) {
        panel.style.display = 'none';
    }
}

// ランキング表示
async function showRanking(mode) {
    if (window.logger) {
        window.logger.info('ランキングを表示', { mode });
    }
    
    showStep('ranking');
    
    const rankingTitle = document.getElementById('rankingTitle');
    const rankingLoading = document.getElementById('rankingLoading');
    const rankingTable = document.getElementById('rankingTable');
    const rankingEmpty = document.getElementById('rankingEmpty');
    
    // タイトルを設定
    if (rankingTitle) {
        rankingTitle.textContent = mode === 'simple' ? '簡易診断モード ランキング' : '詳細診断モード ランキング';
    }
    
    // ローディング表示
    if (rankingLoading) rankingLoading.style.display = 'block';
    if (rankingTable) rankingTable.style.display = 'none';
    if (rankingEmpty) rankingEmpty.style.display = 'none';
    
    try {
        const endpoint = mode === 'simple' ? 'ranking/simple/' : 'ranking/detailed/';
        const response = await fetch(`${API_BASE_URL}/${endpoint}`);
        
        if (!response.ok) {
            throw new Error(`ランキング取得に失敗しました: ${response.status}`);
        }
        
        const data = await response.json();
        
        // ローディング非表示
        if (rankingLoading) rankingLoading.style.display = 'none';
        
        if (!data.ranking || data.ranking.length === 0) {
            // データがない場合
            if (rankingEmpty) rankingEmpty.style.display = 'block';
        } else {
            // ランキングテーブルを表示
            displayRanking(data, mode);
            if (rankingTable) rankingTable.style.display = 'block';
        }
    } catch (error) {
        console.error('ランキング取得エラー:', error);
        if (window.logger) {
            window.logger.error('ランキング取得エラー', { error: error.message });
        }
        
        if (rankingLoading) rankingLoading.style.display = 'none';
        if (rankingTable) {
            rankingTable.innerHTML = `<div class="error-message">ランキングの取得に失敗しました: ${error.message}</div>`;
            rankingTable.style.display = 'block';
        }
    }
}

// ランキングテーブルを表示
function displayRanking(data, mode) {
    const rankingTable = document.getElementById('rankingTable');
    if (!rankingTable) return;
    
    const ranking = data.ranking || [];
    
    let html = '<table class="ranking-table">';
    html += '<thead><tr>';
    
    if (mode === 'simple') {
        html += '<th>順位</th><th>ユーザー名</th><th>業界</th><th>総合スコア</th><th>S</th><th>P</th><th>I</th><th>N</th><th>メッセージ数</th><th>完了日時</th>';
    } else {
        html += '<th>順位</th><th>ユーザー名</th><th>企業名</th><th>総合評価</th><th>スコア</th><th>成功率</th><th>S</th><th>P</th><th>I</th><th>N</th><th>メッセージ数</th><th>完了日時</th>';
    }
    
    html += '</tr></thead><tbody>';
    
    ranking.forEach((entry, index) => {
        const rankClass = index < 3 ? `rank-${index + 1}` : '';
        html += '<tr class="' + rankClass + '">';
        html += `<td class="rank-cell">${entry.rank}</td>`;
        html += `<td class="username-cell">${escapeHtml(entry.username)}</td>`;
        
        if (mode === 'simple') {
            html += `<td class="industry-cell">${escapeHtml(entry.industry || '-')}</td>`;
            html += `<td class="score-cell total">${entry.total_score}点</td>`;
            html += `<td class="score-cell">${entry.situation_score}点</td>`;
            html += `<td class="score-cell">${entry.problem_score}点</td>`;
            html += `<td class="score-cell">${entry.implication_score}点</td>`;
            html += `<td class="score-cell">${entry.need_score}点</td>`;
            html += `<td class="count-cell">${entry.message_count}件</td>`;
            const finishedDate = entry.finished_at ? new Date(entry.finished_at).toLocaleString('ja-JP') : '-';
            html += `<td class="date-cell">${finishedDate}</td>`;
        } else {
            html += `<td class="company-cell">${escapeHtml(entry.company_name || entry.industry || '-')}</td>`;
            html += `<td class="score-cell composite">${entry.composite_score}点</td>`;
            html += `<td class="score-cell">${entry.total_score}点</td>`;
            html += `<td class="score-cell">${entry.success_probability}%</td>`;
            html += `<td class="score-cell">${entry.situation_score}点</td>`;
            html += `<td class="score-cell">${entry.problem_score}点</td>`;
            html += `<td class="score-cell">${entry.implication_score}点</td>`;
            html += `<td class="score-cell">${entry.need_score}点</td>`;
            html += `<td class="count-cell">${entry.message_count}件</td>`;
            const finishedDate = entry.finished_at ? new Date(entry.finished_at).toLocaleString('ja-JP') : '-';
            html += `<td class="date-cell">${finishedDate}</td>`;
        }
        
        html += '</tr>';
    });
    
    html += '</tbody></table>';
    
    rankingTable.innerHTML = html;
}

// HTMLエスケープ
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}


// モーダル関連の関数
function showLoginModal() {
    // authModal要素が存在しない場合は、ログインフォームを表示する
    const authModal = document.getElementById('authModal');
    if (authModal) {
        authModal.style.display = 'flex';
    } else {
        // authModalが存在しない場合は、ログインフォームとタブを表示
        const loginForm = document.getElementById('loginForm');
        const registerForm = document.getElementById('registerForm');
        const authTabs = document.getElementById('authTabs');
        if (loginForm) {
            loginForm.style.display = 'block';
        }
        if (registerForm) {
            registerForm.style.display = 'none';
        }
        if (authTabs) {
            authTabs.style.display = 'flex';
        }
    }
    showLoginTab();
}

function showRegisterModal() {
    // authModal要素が存在しない場合は、登録フォームを表示する
    const authModal = document.getElementById('authModal');
    if (authModal) {
        authModal.style.display = 'flex';
    } else {
        // authModalが存在しない場合は、登録フォームとタブを表示
        const loginForm = document.getElementById('loginForm');
        const registerForm = document.getElementById('registerForm');
        const authTabs = document.getElementById('authTabs');
        if (loginForm) {
            loginForm.style.display = 'none';
        }
        if (registerForm) {
            registerForm.style.display = 'block';
        }
        if (authTabs) {
            authTabs.style.display = 'flex';
        }
    }
    showRegisterTab();
}

function closeAuthModal() {
    // authModal要素が存在しない場合は、ログインフォームと登録フォームを非表示にする
    const authModal = document.getElementById('authModal');
    if (authModal) {
        authModal.style.display = 'none';
    } else {
        // authModalが存在しない場合は、ログインフォームと登録フォームを非表示
        const loginForm = document.getElementById('loginForm');
        const registerForm = document.getElementById('registerForm');
        if (loginForm) {
            loginForm.style.display = 'none';
        }
        if (registerForm) {
            registerForm.style.display = 'none';
        }
    }
}

// 既存のcheckAuth関数を更新（ヘッダーのユーザー情報表示）
const originalCheckAuth = checkAuth;
checkAuth = function() {
    originalCheckAuth.call(this);
    
    const headerUserInfo = document.getElementById('headerUserInfo');
    const headerAuthButtons = document.getElementById('headerAuthButtons');
    const headerUsernameDisplay = document.getElementById('headerUsernameDisplay');
    
    if (authToken) {
        const username = localStorage.getItem('username');
        if (headerUsernameDisplay && username) {
            headerUsernameDisplay.textContent = username;
        }
        if (headerUserInfo) headerUserInfo.style.display = 'flex';
        if (headerAuthButtons) headerAuthButtons.style.display = 'none';
    } else {
        if (headerUserInfo) headerUserInfo.style.display = 'none';
        if (headerAuthButtons) headerAuthButtons.style.display = 'flex';
    }
};

// ログイン成功時にモーダルを閉じる
const originalHandleLoginSuccess = function(data) {
    authToken = data.token;
    localStorage.setItem('authToken', authToken);
    localStorage.setItem('username', data.user.username);
    
    closeAuthModal();
    checkAuth();
    initMode();
};

// サイドバーナビゲーション
function navigateTo(page, evt) {
    // すべてのサイドバーアイテムからactiveクラスを削除
    document.querySelectorAll('.sidebar-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // クリックされたアイテムにactiveクラスを追加
    const clickedElement = evt ? evt.currentTarget : (event ? event.currentTarget : null);
    if (clickedElement) {
        clickedElement.classList.add('active');
    }
    
    switch(page) {
        case 'home':
            returnToModeSelection();
            break;
        case 'dashboard':
            // ダッシュボード画面
            showStep('dashboard');
            loadDashboard();
            break;
        case 'diagnosis':
            // モードが選択されている場合はそのモードの最初のステップへ
            if (currentMode === 'simple') {
                showStep('step1-simple');
            } else if (currentMode === 'detailed') {
                showStep('step1-detailed');
            } else {
                // モード未選択の場合はモード選択画面へ
                showStep(0);
            }
            break;
        case 'history':
            // 履歴画面（将来的に実装）
            alert('履歴機能は近日公開予定です');
            break;
        case 'ranking':
            showStep('ranking');
            break;
        case 'settings':
            // 設定画面（将来的に実装）
            alert('設定機能は近日公開予定です');
            break;
        default:
            showStep(0);
    }
}

// ダッシュボードを読み込む
async function loadDashboard() {
    if (window.logger) {
        window.logger.info('ダッシュボードを読み込み中');
    }
    
    // ログインしていない場合はエラー表示
    if (!authToken) {
        displayDashboardError('ダッシュボードを表示するにはログインが必要です');
        return;
    }
    
    // 統計カードをローディング状態に
    document.getElementById('totalSessionsCount').textContent = '...';
    document.getElementById('averageScoreValue').textContent = '...';
    document.getElementById('highestScoreValue').textContent = '...';
    document.getElementById('recentSessionsList').innerHTML = '<p class="loading-text">セッション履歴を読み込み中...</p>';
    
    try {
        // セッション一覧を取得
        const response = await fetch(`${API_BASE_URL}/session/list/`, {
            method: 'GET',
            headers: {
                'Authorization': `Token ${authToken}`
            }
        });
        
        if (!response.ok) {
            if (response.status === 401) {
                displayDashboardError('ログインセッションが期限切れです。再度ログインしてください。');
                return;
            }
            throw new Error(`セッション取得に失敗しました: ${response.status}`);
        }
        
        const data = await response.json();
        const sessions = data.results || data || [];
        
        // 統計情報を計算・表示
        displayDashboardStats(sessions);
        
        // 直近のセッション履歴を表示
        displayRecentSessions(sessions);
        
        if (window.logger) {
            window.logger.info('ダッシュボード読み込み完了', { sessionCount: sessions.length });
        }
    } catch (error) {
        console.error('ダッシュボード読み込みエラー:', error);
        if (window.logger) {
            window.logger.error('ダッシュボード読み込みエラー', { error: error.message });
        }
        displayDashboardError('ダッシュボードの読み込みに失敗しました: ' + error.message);
    }
}

// ダッシュボードエラー表示
function displayDashboardError(message) {
    document.getElementById('totalSessionsCount').textContent = '-';
    document.getElementById('averageScoreValue').textContent = '-';
    document.getElementById('highestScoreValue').textContent = '-';
    document.getElementById('recentSessionsList').innerHTML = `<p class="error-message">${escapeHtml(message)}</p>`;
}

// 統計情報を表示
function displayDashboardStats(sessions) {
    // 総セッション数
    const totalSessions = sessions.length;
    document.getElementById('totalSessionsCount').textContent = totalSessions;
    
    // 完了済みセッション（スコアがあるもの）をフィルタ
    const scoredSessions = sessions.filter(s => s.status === 'finished' && s.report);
    
    if (scoredSessions.length > 0) {
        // 平均スコア計算
        let totalScore = 0;
        let highestScore = 0;
        
        scoredSessions.forEach(session => {
            // report内のスコアを取得
            const report = session.report;
            if (report && report.spin_scores && report.spin_scores.total !== undefined) {
                const score = report.spin_scores.total;
                totalScore += score;
                if (score > highestScore) {
                    highestScore = score;
                }
            }
        });
        
        const avgScore = totalScore / scoredSessions.length;
        document.getElementById('averageScoreValue').textContent = avgScore.toFixed(1) + '点';
        document.getElementById('highestScoreValue').textContent = highestScore.toFixed(1) + '点';
    } else {
        document.getElementById('averageScoreValue').textContent = '-';
        document.getElementById('highestScoreValue').textContent = '-';
    }
}

// 直近のセッション履歴を表示
function displayRecentSessions(sessions) {
    const container = document.getElementById('recentSessionsList');
    if (!container) return;
    
    if (sessions.length === 0) {
        container.innerHTML = `
            <div class="empty-sessions-message">
                <i class="fas fa-inbox"></i>
                <p>まだセッションがありません</p>
                <p>診断を開始して、営業スキルをトレーニングしましょう</p>
                <button class="btn-primary" onclick="navigateTo('home')">診断を開始する</button>
            </div>
        `;
        return;
    }
    
    // 直近5件を表示
    const recentSessions = sessions.slice(0, 5);
    
    let html = '';
    recentSessions.forEach(session => {
        const date = new Date(session.started_at);
        const dateStr = `${date.getMonth() + 1}/${date.getDate()}`;
        
        const modeClass = session.mode === 'simple' ? 'simple' : 'detailed';
        const modeLabel = session.mode === 'simple' ? '簡易' : '詳細';
        
        // スコアの取得
        let scoreDisplay = '';
        if (session.report && session.report.spin_scores && session.report.spin_scores.total !== undefined) {
            scoreDisplay = `<span class="recent-session-score">${session.report.spin_scores.total.toFixed(1)}点</span>`;
        } else if (session.status === 'active') {
            scoreDisplay = `<span class="recent-session-score no-score">進行中</span>`;
        } else {
            scoreDisplay = `<span class="recent-session-score no-score">-</span>`;
        }
        
        html += `
            <div class="recent-session-item" onclick="resumeSession('${session.id}')">
                <span class="recent-session-date">${dateStr}</span>
                <div class="recent-session-info">
                    <span class="recent-session-industry">${escapeHtml(session.industry || '-')}</span>
                    <span class="recent-session-mode ${modeClass}">${modeLabel}</span>
                </div>
                ${scoreDisplay}
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// セッションを再開
function resumeSession(sessionId) {
    if (window.logger) {
        window.logger.info('セッションを再開', { sessionId });
    }
    
    currentSessionId = sessionId;
    showStep(3);
    loadChatHistory();
}

// サイドバーのユーザー状態を更新
function updateSidebarUserState() {
    const sidebarUserBtn = document.getElementById('sidebarUserBtn');
    const sidebarUserTooltip = document.getElementById('sidebarUserTooltip');
    
    if (!sidebarUserBtn || !sidebarUserTooltip) return;
    
    if (authToken) {
        const username = localStorage.getItem('username');
        sidebarUserTooltip.textContent = username || 'ユーザー';
        sidebarUserBtn.onclick = function() {
            if (confirm('ログアウトしますか？')) {
                logout();
            }
        };
        sidebarUserBtn.innerHTML = '<i class="fas fa-user-check"></i><span class="sidebar-tooltip" id="sidebarUserTooltip">' + (username || 'ユーザー') + '</span>';
    } else {
        sidebarUserTooltip.textContent = 'ログイン';
        sidebarUserBtn.onclick = showLoginModal;
        sidebarUserBtn.innerHTML = '<i class="fas fa-user"></i><span class="sidebar-tooltip" id="sidebarUserTooltip">ログイン</span>';
    }
}

// 既存のcheckAuth関数を拡張してサイドバーも更新
const originalCheckAuthForSidebar = checkAuth;
checkAuth = function() {
    originalCheckAuthForSidebar.call(this);
    updateSidebarUserState();
};

// ==================== 音声入力機能 ====================

let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let recordingStartTime = null;
let recordingTimer = null;

// 音声録音の開始/停止
async function toggleVoiceRecording() {
    if (!authToken) {
        alert('ログインしてください');
        return;
    }
    
    if (isRecording) {
        // 録音停止
        stopRecording();
    } else {
        // 録音開始
        await startRecording();
    }
}

// 録音開始
async function startRecording() {
    try {
        // マイクアクセス許可を取得
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        // MediaRecorderを初期化
        // 優先順位: webm opus > webm > デフォルト
        let options = {};
        if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
            options.mimeType = 'audio/webm;codecs=opus';
        } else if (MediaRecorder.isTypeSupported('audio/webm')) {
            options.mimeType = 'audio/webm';
        } else {
            // デフォルトを使用
            options.mimeType = '';
        }
        
        // 音声品質の設定（オプション）
        if (options.mimeType) {
            options.audioBitsPerSecond = 128000; // 128kbps
        }
        
        mediaRecorder = new MediaRecorder(stream, options);
        audioChunks = [];
        
        // データが利用可能になったときの処理
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };
        
        // 録音停止時の処理
        mediaRecorder.onstop = async () => {
            // ストリームを停止
            stream.getTracks().forEach(track => track.stop());
            
            // 音声データをBlobに変換
            const audioBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType });
            
            // バックエンドに送信してテキスト変換
            await transcribeAudio(audioBlob);
            
            // タイマーを停止
            if (recordingTimer) {
                clearInterval(recordingTimer);
                recordingTimer = null;
            }
            
            // UIを更新
            updateRecordingUI(false);
        };
        
        // 録音開始
        mediaRecorder.start();
        isRecording = true;
        recordingStartTime = Date.now();
        
        // 録音時間の表示を開始
        startRecordingTimer();
        
        // UIを更新
        updateRecordingUI(true);
        
        if (window.logger) {
            window.logger.info('音声録音を開始しました');
        }
    } catch (error) {
        console.error('録音開始エラー:', error);
        if (window.logger) {
            window.logger.error('録音開始エラー', { error: error.message });
        }
        
        if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
            alert('マイクへのアクセスが拒否されました。\nブラウザの設定でマイクのアクセス許可を有効にしてください。');
        } else if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
            alert('マイクが見つかりませんでした。\nマイクが接続されているか確認してください。');
        } else {
            alert('録音を開始できませんでした: ' + error.message);
        }
    }
}

// 録音停止
function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        
        if (window.logger) {
            window.logger.info('音声録音を停止しました');
        }
    }
}

// 録音時間のタイマー
function startRecordingTimer() {
    const timeDisplay = document.getElementById('recordingTime');
    if (!timeDisplay) return;
    
    recordingTimer = setInterval(() => {
        if (recordingStartTime) {
            const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
            const minutes = Math.floor(elapsed / 60);
            const seconds = elapsed % 60;
            timeDisplay.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
        }
    }, 100);
}

// 録音UIの更新
function updateRecordingUI(recording) {
    const micButton = document.getElementById('micButton');
    const timeDisplay = document.getElementById('recordingTime');
    
    if (micButton) {
        if (recording) {
            micButton.classList.add('recording');
            micButton.innerHTML = '<i class="fas fa-stop"></i>';
            micButton.title = '録音を停止';
        } else {
            micButton.classList.remove('recording');
            micButton.innerHTML = '<i class="fas fa-microphone"></i>';
            micButton.title = '音声入力';
        }
    }
    
    if (timeDisplay) {
        timeDisplay.style.display = recording ? 'inline-block' : 'none';
        if (!recording) {
            timeDisplay.textContent = '00:00';
        }
    }
}

// 音声をテキストに変換
async function transcribeAudio(audioBlob) {
    const messageInput = document.getElementById('chatMessageInput');
    if (!messageInput) return;
    
    try {
        // ローディング表示
        if (messageInput) {
            messageInput.placeholder = '音声を変換中...';
            messageInput.disabled = true;
        }
        
        // FormDataを作成
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.webm');
        formData.append('language_code', 'ja-JP');
        
        // バックエンドに送信
        const response = await fetch(`${API_BASE_URL}/speech/transcribe/`, {
            method: 'POST',
            headers: {
                'Authorization': `Token ${authToken}`
            },
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            if (data.text && data.text.trim().length > 0) {
                // 変換されたテキストを入力欄に設定
                messageInput.value = data.text;
                messageInput.placeholder = '営業担当者の質問を入力...';
                messageInput.disabled = false;
                
                // 入力欄にフォーカス
                messageInput.focus();
                
                if (window.logger) {
                    window.logger.info('音声変換成功', { 
                        text_length: data.text.length,
                        confidence: data.confidence 
                    });
                }
            } else {
                // テキストが空の場合
                throw new Error('音声が認識できませんでした。音声が短すぎるか、無音の可能性があります。もう一度録音してください。');
            }
        } else {
            throw new Error(data.error || data.detail || '音声変換に失敗しました');
        }
    } catch (error) {
        console.error('音声変換エラー:', error);
        if (window.logger) {
            window.logger.error('音声変換エラー', { error: error.message });
        }
        
        alert('音声変換に失敗しました: ' + error.message);
        
        // 入力欄を復元
        if (messageInput) {
            messageInput.placeholder = '営業担当者の質問を入力...';
            messageInput.disabled = false;
        }
    }
}
