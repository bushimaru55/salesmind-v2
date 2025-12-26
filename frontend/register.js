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
            const message = `登録が完了しました！

📧 ${data.email || formData.email} 宛てに認証メールを送信しました。

⚠️ Gmailをご利用の場合、迷惑メールフォルダに入っている可能性があります。
受信トレイと迷惑メールフォルダの両方をご確認ください。

メール内のリンクをクリックして認証を完了してください。`;
            
            showSuccess(message);
            
            // メッセージをしっかり読んでもらうため、自動リダイレクトは削除
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
    // 改行を保持するため、textContentではなくinnerHTMLを使用し、改行を<br>に変換
    successDiv.innerHTML = message.split('\n').map(line => line.trim()).filter(line => line).join('<br>');
    successDiv.style.display = 'block';
    document.getElementById('error').style.display = 'none';
}

function hideMessages() {
    document.getElementById('error').style.display = 'none';
    document.getElementById('success').style.display = 'none';
}

