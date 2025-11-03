"""
マイグレーション後のデータ整合性チェックスクリプト

使用方法:
    cd backend
    python manage.py shell < ../scripts/check_migration.py
"""

from spin.models import Session

def check_data_integrity():
    """マイグレーション後のデータ整合性をチェック"""
    
    print("=" * 60)
    print("データ整合性チェックを開始します")
    print("=" * 60)
    
    # 1. すべてのセッションにmodeが設定されているか
    total_sessions = Session.objects.count()
    sessions_with_mode = Session.objects.exclude(mode__isnull=True).count()
    
    if total_sessions != sessions_with_mode:
        print(f"❌ エラー: modeが設定されていないセッションがあります")
        print(f"  総セッション数: {total_sessions}")
        print(f"  mode設定済み: {sessions_with_mode}")
        return False
    
    # 2. companyがあるのにmode='simple'のセッションがないか
    simple_with_company = Session.objects.filter(
        company__isnull=False, 
        mode='simple'
    ).count()
    
    if simple_with_company > 0:
        print(f"❌ エラー: companyがあるのにmode='simple'のセッションが{simple_with_company}件あります")
        print("  以下が該当セッションです:")
        for session in Session.objects.filter(company__isnull=False, mode='simple'):
            print(f"    - Session {session.id}: company={session.company}, mode={session.mode}")
        return False
    
    # 3. companyがないのにmode='detailed'のセッションがないか
    detailed_without_company = Session.objects.filter(
        company__isnull=True, 
        mode='detailed'
    ).count()
    
    if detailed_without_company > 0:
        print(f"❌ エラー: companyがないのにmode='detailed'のセッションが{detailed_without_company}件あります")
        print("  以下が該当セッションです:")
        for session in Session.objects.filter(company__isnull=True, mode='detailed'):
            print(f"    - Session {session.id}: company=None, mode={session.mode}")
        return False
    
    # 4. 統計情報
    simple_count = Session.objects.filter(mode='simple').count()
    detailed_count = Session.objects.filter(mode='detailed').count()
    
    print("\n" + "=" * 60)
    print("✓ データ整合性チェック成功")
    print("=" * 60)
    print(f"  簡易診断モード: {simple_count}件")
    print(f"  詳細診断モード: {detailed_count}件")
    print(f"  合計: {total_sessions}件")
    print("=" * 60)
    
    return True

if __name__ == '__main__':
    check_data_integrity()

