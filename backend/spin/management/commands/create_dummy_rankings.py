"""
ダミーランキングデータ作成コマンド
詳細診断モードのランキングを賑やかにするためのダミーデータを生成
"""
import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from spin.models import Session, Report, ChatMessage


class Command(BaseCommand):
    help = '詳細診断モードのダミーランキングデータを作成します'

    # よくある日本人のローマ字ニックネーム
    NICKNAMES = [
        # 男性系
        'taro', 'jiro', 'yuta', 'kenji', 'takeshi', 'hiroshi', 'daisuke', 'kenta',
        'shota', 'ryota', 'yuki', 'naoki', 'kazuki', 'tomoya', 'shun', 'ryo',
        'koji', 'masaki', 'tatsuya', 'yuichi', 'satoshi', 'akira', 'makoto', 'shin',
        'hayato', 'daiki', 'koichi', 'takuya', 'sho', 'ken', 'jun', 'masa',
        'hide', 'nori', 'tomo', 'yasu', 'tetsu', 'hiro', 'kazu', 'taku',
        # 女性系
        'yuko', 'miki', 'yumi', 'emi', 'rina', 'saki', 'mai', 'haruka',
        'ayaka', 'misaki', 'nana', 'moe', 'aoi', 'sakura', 'hina', 'risa',
        'asuka', 'megumi', 'tomoko', 'keiko', 'naomi', 'kaori', 'mari', 'aya',
        'chika', 'yuka', 'mika', 'kana', 'anna', 'rena', 'miho', 'shiori',
        # ユニーク系
        'sales_pro', 'top_seller', 'nego_master', 'biz_king', 'deal_maker',
        'closer', 'pitch_ace', 'lead_gen', 'client_pro', 'revenue_up',
    ]

    # サフィックス
    SUFFIXES = ['', '01', '02', '21', '22', '88', '99', '_sales', '_biz', '_pro', '_jp']

    # 業界リスト
    INDUSTRIES = [
        '不動産（売買・賃貸）', '保険（生保・損保）', 'IT・SaaS', '人材（派遣・紹介）',
        '広告・マーケティング', '自動車（販売・リース）', '金融（銀行・証券）',
        '製造業', '小売・EC', '通信', '医療・ヘルスケア', '教育', 'コンサルティング'
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=120,
            help='作成するダミーアカウント数（デフォルト: 120）'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='既存のダミーデータを削除してから作成'
        )

    def handle(self, *args, **options):
        count = options['count']
        clear = options['clear']

        if clear:
            self.stdout.write('既存のダミーデータを削除中...')
            dummy_users = User.objects.filter(email__endswith='@dummy.salesmind.local')
            deleted_count = dummy_users.count()
            dummy_users.delete()
            self.stdout.write(f'  {deleted_count}件のダミーユーザーを削除しました')

        self.stdout.write(f'{count}件のダミーアカウントを作成中...')

        created_count = 0
        used_usernames = set(User.objects.values_list('username', flat=True))

        for i in range(count):
            # ユニークなユーザー名を生成
            username = self._generate_unique_username(used_usernames)
            if not username:
                self.stdout.write(self.style.WARNING(f'  ユニークなユーザー名を生成できませんでした（{i+1}件目）'))
                continue

            used_usernames.add(username)

            # ユーザーを作成
            user = User.objects.create_user(
                username=username,
                email=f'{username}@dummy.salesmind.local',
                password='DummyPass123!',
                is_active=True
            )

            # ダミーセッションとレポートを作成
            self._create_dummy_session_and_report(user, i)
            created_count += 1

            if (i + 1) % 20 == 0:
                self.stdout.write(f'  {i + 1}件作成完了...')

        self.stdout.write(self.style.SUCCESS(f'完了！ {created_count}件のダミーアカウントを作成しました'))
        self.stdout.write('')
        self.stdout.write('【管理者向け情報】')
        self.stdout.write(f'  ダミーユーザーのメールアドレス: *@dummy.salesmind.local')
        self.stdout.write(f'  初期パスワード: DummyPass123!')
        self.stdout.write(f'  パスワードは管理画面から変更できます')

    def _generate_unique_username(self, used_usernames):
        """ユニークなユーザー名を生成"""
        attempts = 0
        max_attempts = 100

        while attempts < max_attempts:
            base_name = random.choice(self.NICKNAMES)
            suffix = random.choice(self.SUFFIXES)
            username = f'{base_name}{suffix}'

            if username not in used_usernames and len(username) <= 30:
                return username

            attempts += 1

        # フォールバック: ランダムな数字を追加
        for _ in range(100):
            username = f'{random.choice(self.NICKNAMES)}_{random.randint(100, 9999)}'
            if username not in used_usernames and len(username) <= 30:
                return username

        return None

    def _create_dummy_session_and_report(self, user, index):
        """ダミーセッションとレポートを作成"""
        # スコアの分布を作成（幅広く分布）
        rand = random.random()
        if rand < 0.15:
            base_score = random.uniform(80, 100)
        elif rand < 0.40:
            base_score = random.uniform(60, 80)
        elif rand < 0.75:
            base_score = random.uniform(40, 60)
        elif rand < 0.95:
            base_score = random.uniform(20, 40)
        else:
            base_score = random.uniform(5, 20)

        # SPIN各スコア（バランスよく分散、各20点満点）
        s_score = max(1, min(20, int(base_score * 0.2 + random.randint(-3, 3))))
        p_score = max(1, min(20, int(base_score * 0.2 + random.randint(-3, 3))))
        i_score = max(1, min(20, int(base_score * 0.2 + random.randint(-3, 3))))
        n_score = max(1, min(20, int(base_score * 0.2 + random.randint(-3, 3))))

        total_score = s_score + p_score + i_score + n_score

        # 成功率（スコアに相関させつつランダム性を持たせる）
        success_probability = max(10, min(100, int(base_score + random.randint(-15, 15))))

        # メッセージ数（リアルな範囲で）
        message_count = random.randint(8, 60)

        # 完了日時（過去30日以内でランダム）
        days_ago = random.randint(0, 30)
        hours_ago = random.randint(0, 23)
        finished_at = timezone.now() - timedelta(days=days_ago, hours=hours_ago)

        # 業界をランダムに選択
        industry = random.choice(self.INDUSTRIES)

        # セッション作成
        session = Session.objects.create(
            user=user,
            mode='detailed',
            status='finished',
            industry=industry,
            value_proposition='ダミーデータ',
            success_probability=success_probability,
            finished_at=finished_at
        )

        # ダミーメッセージを作成（メッセージ数をカウントするため）
        for seq in range(1, message_count + 1):
            ChatMessage.objects.create(
                session=session,
                role='salesperson' if seq % 2 == 1 else 'customer',
                message=f'ダミーメッセージ {seq}',
                sequence=seq
            )

        # レポート作成（spin_scoresはJSONField）
        spin_scores = {
            'situation': s_score,
            'problem': p_score,
            'implication': i_score,
            'need': n_score,
            'total': total_score
        }

        Report.objects.create(
            session=session,
            spin_scores=spin_scores,
            feedback='ダミーデータのフィードバック',
            next_actions='ダミーデータの次のアクション'
        )

