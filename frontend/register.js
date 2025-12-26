const API_BASE_URL = 'https://salesmind.mind-bridge.tech/api';

document.getElementById('registerForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = {
        username: document.getElementById('username').value.trim(),
        email: document.getElementById('email').value.trim(),
        password: document.getElementById('password').value,
        industry: document.getElementById('industry').value,
        sales_experience: document.getElementById('sales_experience').value || null,
        usage_purpose: document.getElementById('usage_purpose').value || null,
    };
    
    // バリデーション
    if (!formData.username) {
        showError('ユーザー名を入力してください');
        return;
    }
    
    if (!formData.email) {
        showError('メールアドレスを入力してください');
        return;
    }
    
    if (!formData.password || formData.password.length < 6) {
        showError('パスワードは6文字以上で入力してください');
        return;
    }
    
    if (!formData.industry) {
        showError('業種を選択してください');
        return;
    }
    
    // エラーメッセージをクリア
    hideMessages();
    
    try {
        const response = await fetch(`${API_BASE_URL}/auth/register/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData),
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showSuccess(data.message || '登録が完了しました。メールを確認して認証を完了してください。');
            
            // 5秒後にログインページにリダイレクト
            setTimeout(() => {
                window.location.href = 'index.html';
            }, 5000);
        } else {
            let errorMsg = '登録に失敗しました';
            if (data.details) {
                const errors = Object.values(data.details).flat();
                errorMsg = errors.join('\n');
            } else if (data.message) {
                errorMsg = data.message;
            }
            showError(errorMsg);
        }
    } catch (error) {
        showError('サーバーに接続できませんでした: ' + error.message);
    }
});

function showError(message) {
    const errorDiv = document.getElementById('error');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    document.getElementById('success').style.display = 'none';
}

function showSuccess(message) {
    const successDiv = document.getElementById('success');
    successDiv.textContent = message;
    successDiv.style.display = 'block';
    document.getElementById('error').style.display = 'none';
}

function hideMessages() {
    document.getElementById('error').style.display = 'none';
    document.getElementById('success').style.display = 'none';
}

