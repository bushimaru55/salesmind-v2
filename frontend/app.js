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

// ページロード時の処理
window.onload = function() {
    // ロガーを初期化（logger.jsで自動的に初期化される）
    if (window.logger) {
        window.logger.info('SalesMindアプリケーションが起動しました');
    }
    checkAuth();
    initMode();
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
    const email = document.getElementById('registerEmail').value.trim() || null;  // 空の場合はnull
    const password = document.getElementById('registerPassword').value;
    
    if (!username || !username.trim()) {
        showError('registerError', 'ユーザー名は必須です');
        return;
    }
    
    if (!password) {
        showError('registerError', 'パスワードは必須です');
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
            // 登録成功
            let successMsg;
            if (data.email_verification_required && data.user.email) {
                // メール認証が必要な場合
                successMsg = `メールアドレス（${data.user.email}）に認証リンクを送信しました。\n\nメールを確認して、認証リンクをクリックしてください。\n認証完了後、ログインできるようになります。`;
            } else {
                // メール認証が不要な場合（メールアドレス未入力）
                successMsg = 'ユーザー登録が完了しました。\n\nログインできます。';
            }
            
            // 成功メッセージを表示
            const successDiv = document.getElementById('registerSuccess');
            successDiv.textContent = successMsg;
            successDiv.style.display = 'block';
            successDiv.style.color = '#28a745';
            successDiv.style.backgroundColor = '#d4edda';
            successDiv.style.border = '1px solid #c3e6cb';
            successDiv.style.borderRadius = '4px';
            successDiv.style.padding = '10px';
            successDiv.style.marginTop = '10px';
            successDiv.style.whiteSpace = 'pre-line';
            
            // エラーメッセージを非表示
            document.getElementById('registerError').style.display = 'none';
            
            // フォームをクリア
            document.getElementById('registerUsername').value = '';
            document.getElementById('registerEmail').value = '';
            document.getElementById('registerPassword').value = '';
            
            // 5秒後にログインフォームに切り替え
            setTimeout(() => {
                showLoginTab();
                document.getElementById('registerSuccess').style.display = 'none';
            }, 5000);
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
        let errorMsg = 'エラーが発生しました: ' + error.message;
        if (error.message.includes('Failed to fetch') || error.name === 'TypeError') {
            errorMsg = 'サーバーに接続できませんでした。\nバックエンドサーバー（http://localhost:8000）が起動しているか確認してください。';
        } else if (error.message.includes('ERR_EMPTY_RESPONSE')) {
            errorMsg = 'サーバーから応答がありませんでした。\nバックエンドサーバーのターミナルでエラーメッセージを確認してください。';
        }
        if (window.logger) {
            window.logger.error('ユーザー登録エラー', { message: error.message, stack: error.stack, errorType: error.name });
        }
        showError('registerError', errorMsg);
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
            
            if (window.logger) {
                window.logger.info('セッション開始成功、チャット画面へ遷移', { sessionId: currentSessionId });
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
            
            if (window.logger) {
                window.logger.info('詳細診断セッション開始成功、チャット画面へ遷移', { sessionId: currentSessionId, companyId: currentCompanyId });
            }
            
            // チャット画面に企業情報を保存（表示用）
            currentCompanyInfo = companyData;
            
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
                            
                            // 詳細診断モードの場合、成功率情報を更新
                            if (currentMode === 'detailed' && data.success_probability !== undefined) {
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
function addChatMessage(role, message, temperature = null, temperatureChange = null) {
    const container = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const roleLabel = role === 'salesperson' ? '営業担当者' : 'AI顧客';
    const timestamp = new Date().toLocaleTimeString('ja-JP');
    
    // 温度スコアアイコン（顧客メッセージのみ）
    let temperatureIcon = '';
    if (role === 'customer' && temperature !== null && temperature !== undefined) {
        const iconClass = temperatureChange === '↑' ? 'temp-up' : temperatureChange === '↓' ? 'temp-down' : 'temp-same';
        temperatureIcon = `<span class="temperature-icon ${iconClass}">${temperatureChange || ''}</span>`;
    }
    
    messageDiv.innerHTML = `
        <div class="message-header">
            ${roleLabel} - ${timestamp}
            ${temperatureIcon}
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
    
    container.innerHTML = '';
    
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
            
            // メッセージがある場合は表示
            if (data.messages) {
                updateChatMessages(data.messages);
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
    const successMeter = document.getElementById('successMeter');
    if (successMeter) {
        successMeter.style.display = 'block';
    }
}

// 成功率パネルを非表示
function hideSuccessMeter() {
    const successMeter = document.getElementById('successMeter');
    if (successMeter) {
        successMeter.style.display = 'none';
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
    const { currentStage, messageSpinType, stepAppropriateness, stageEvaluation, sessionStage, systemNotes } = metadata;
    
    if (probabilityValue) {
        // アニメーションを追加
        probabilityValue.classList.add('updating');
        setTimeout(() => {
            probabilityValue.textContent = probability;
            probabilityValue.classList.remove('updating');
        }, 100);
    }
    
    // 変動量を表示
    if (deltaDisplay && deltaValue && delta !== 0) {
        deltaDisplay.style.display = 'flex';
        deltaValue.textContent = (delta > 0 ? '+' : '') + delta;
        deltaValue.className = 'success-delta-value ' + (delta > 0 ? 'positive' : 'negative');
        
        // 3秒後に非表示
        setTimeout(() => {
            deltaDisplay.style.display = 'none';
        }, 3000);
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
    
    if (spinMeta) {
        const hasMeta = Boolean(currentStage || messageSpinType || stepAppropriateness || stageEvaluation || sessionStage);
        if (hasMeta) {
            spinMeta.style.display = 'block';
            if (stageEl) {
                const stageLabel = currentStage ? (stageLabelMap[currentStage] || currentStage) : '未判定';
                stageEl.textContent = `現在の段階: ${stageLabel}`;
                stageEl.style.display = 'block';
            }
            if (messageEl) {
                const messageLabel = messageSpinType ? (stageLabelMap[messageSpinType] || messageSpinType) : '';
                messageEl.textContent = messageLabel ? `今回の発言: ${messageLabel}` : '';
                messageEl.style.display = messageLabel ? 'block' : 'none';
            }
            if (stepEl) {
                const stepLabel = stepAppropriateness ? (stepLabelMap[stepAppropriateness] || stepAppropriateness) : '';
                stepEl.textContent = stepLabel ? `ステップ適切性: ${stepLabel}` : '';
                stepEl.style.display = stepLabel ? 'block' : 'none';
            }
            if (evaluationEl) {
                const evalLabel = stageEvaluation ? (evalLabelMap[stageEvaluation] || stageEvaluation) : '';
                evaluationEl.textContent = evalLabel ? `段階評価: ${evalLabel}` : '';
                evaluationEl.style.display = evalLabel ? 'block' : 'none';
            }
            if (sessionStageEl) {
                const sessionStageLabel = sessionStage ? (stageLabelMap[sessionStage] || sessionStage) : '';
                sessionStageEl.textContent = sessionStageLabel ? `システム段階: ${sessionStageLabel}` : '';
                sessionStageEl.style.display = sessionStageLabel ? 'block' : 'none';
            }
        } else {
            spinMeta.style.display = 'none';
            if (stageEl) {
                stageEl.textContent = '';
                stageEl.style.display = 'none';
            }
            if (messageEl) {
                messageEl.textContent = '';
                messageEl.style.display = 'none';
            }
            if (stepEl) {
                stepEl.textContent = '';
                stepEl.style.display = 'none';
            }
            if (evaluationEl) {
                evaluationEl.textContent = '';
                evaluationEl.style.display = 'none';
            }
            if (sessionStageEl) {
                sessionStageEl.textContent = '';
                sessionStageEl.style.display = 'none';
            }
        }
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
