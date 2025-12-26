# このファイルは email_management アプリのモデル定義ファイルです
# 実際のモデルは spin.models に定義されていますが、
# ここで再エクスポートすることで、このアプリのモデルとして管理画面に表示されます

from spin.models import SystemEmailAddress, EmailTemplate

__all__ = ['SystemEmailAddress', 'EmailTemplate']
