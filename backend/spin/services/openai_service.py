import logging

from openai import OpenAI

logger = logging.getLogger(__name__)


def test_connection():
    """
    OpenAI API への疎通テスト用ユーティリティ関数。

    manage.py shell から:

        from spin.services.openai_service import test_connection
        test_connection()

    を実行して確認してください。
    """
    client = OpenAI()

    try:
        client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "test"}],
        )
        print("OpenAI API connection OK")
    except Exception as e:
        logger.error("OpenAI connection error: %s", e, exc_info=True)
        print("OpenAI connection error:", e)



