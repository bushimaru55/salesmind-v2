"""
Google Analytics Data API サービス
Django管理画面でGAデータを表示するためのサービス
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class GoogleAnalyticsService:
    """Google Analytics Data APIを使用してデータを取得するサービス"""
    
    def __init__(self):
        self.property_id = getattr(settings, 'GA_PROPERTY_ID', os.getenv('GA_PROPERTY_ID', ''))
        self._client = None
        self._available = None
    
    @property
    def is_available(self) -> bool:
        """GA APIが利用可能かチェック"""
        if self._available is not None:
            return self._available
        
        if not self.property_id:
            logger.warning("GA_PROPERTY_ID is not configured")
            self._available = False
            return False
        
        try:
            from google.analytics.data_v1beta import BetaAnalyticsDataClient
            self._client = BetaAnalyticsDataClient()
            self._available = True
        except Exception as e:
            logger.error(f"Failed to initialize GA client: {e}")
            self._available = False
        
        return self._available
    
    @property
    def client(self):
        """Analytics Data APIクライアントを取得"""
        if self._client is None and self.is_available:
            from google.analytics.data_v1beta import BetaAnalyticsDataClient
            self._client = BetaAnalyticsDataClient()
        return self._client
    
    def get_realtime_users(self) -> int:
        """リアルタイムユーザー数を取得"""
        if not self.is_available:
            return 0
        
        try:
            from google.analytics.data_v1beta.types import (
                RunRealtimeReportRequest,
                Metric,
            )
            
            request = RunRealtimeReportRequest(
                property=f"properties/{self.property_id}",
                metrics=[Metric(name="activeUsers")],
            )
            
            response = self.client.run_realtime_report(request)
            
            if response.rows:
                return int(response.rows[0].metric_values[0].value)
            return 0
        except Exception as e:
            logger.error(f"Error fetching realtime users: {e}")
            return 0
    
    def get_today_stats(self) -> Dict[str, int]:
        """今日の統計情報を取得"""
        if not self.is_available:
            return {"users": 0, "pageviews": 0, "sessions": 0, "new_users": 0}
        
        try:
            from google.analytics.data_v1beta.types import (
                RunReportRequest,
                DateRange,
                Metric,
            )
            
            request = RunReportRequest(
                property=f"properties/{self.property_id}",
                date_ranges=[DateRange(start_date="today", end_date="today")],
                metrics=[
                    Metric(name="activeUsers"),
                    Metric(name="screenPageViews"),
                    Metric(name="sessions"),
                    Metric(name="newUsers"),
                ],
            )
            
            response = self.client.run_report(request)
            
            if response.rows:
                row = response.rows[0]
                return {
                    "users": int(row.metric_values[0].value),
                    "pageviews": int(row.metric_values[1].value),
                    "sessions": int(row.metric_values[2].value),
                    "new_users": int(row.metric_values[3].value),
                }
            return {"users": 0, "pageviews": 0, "sessions": 0, "new_users": 0}
        except Exception as e:
            logger.error(f"Error fetching today stats: {e}")
            return {"users": 0, "pageviews": 0, "sessions": 0, "new_users": 0}
    
    def get_weekly_trend(self) -> List[Dict[str, Any]]:
        """過去7日間のトレンドデータを取得"""
        if not self.is_available:
            return []
        
        try:
            from google.analytics.data_v1beta.types import (
                RunReportRequest,
                DateRange,
                Dimension,
                Metric,
            )
            
            request = RunReportRequest(
                property=f"properties/{self.property_id}",
                date_ranges=[DateRange(start_date="7daysAgo", end_date="today")],
                dimensions=[Dimension(name="date")],
                metrics=[
                    Metric(name="activeUsers"),
                    Metric(name="screenPageViews"),
                    Metric(name="sessions"),
                ],
            )
            
            response = self.client.run_report(request)
            
            trend_data = []
            for row in response.rows:
                date_str = row.dimension_values[0].value
                # YYYYMMDD形式をYYYY-MM-DD形式に変換
                formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
                trend_data.append({
                    "date": formatted_date,
                    "users": int(row.metric_values[0].value),
                    "pageviews": int(row.metric_values[1].value),
                    "sessions": int(row.metric_values[2].value),
                })
            
            # 日付順にソート
            trend_data.sort(key=lambda x: x["date"])
            return trend_data
        except Exception as e:
            logger.error(f"Error fetching weekly trend: {e}")
            return []
    
    def get_top_pages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """人気ページTop Nを取得"""
        if not self.is_available:
            return []
        
        try:
            from google.analytics.data_v1beta.types import (
                RunReportRequest,
                DateRange,
                Dimension,
                Metric,
                OrderBy,
            )
            
            request = RunReportRequest(
                property=f"properties/{self.property_id}",
                date_ranges=[DateRange(start_date="7daysAgo", end_date="today")],
                dimensions=[Dimension(name="pagePath")],
                metrics=[
                    Metric(name="screenPageViews"),
                    Metric(name="activeUsers"),
                ],
                order_bys=[
                    OrderBy(
                        metric=OrderBy.MetricOrderBy(metric_name="screenPageViews"),
                        desc=True,
                    )
                ],
                limit=limit,
            )
            
            response = self.client.run_report(request)
            
            pages = []
            for row in response.rows:
                pages.append({
                    "page": row.dimension_values[0].value,
                    "pageviews": int(row.metric_values[0].value),
                    "users": int(row.metric_values[1].value),
                })
            return pages
        except Exception as e:
            logger.error(f"Error fetching top pages: {e}")
            return []
    
    def get_traffic_sources(self) -> List[Dict[str, Any]]:
        """トラフィックソースを取得"""
        if not self.is_available:
            return []
        
        try:
            from google.analytics.data_v1beta.types import (
                RunReportRequest,
                DateRange,
                Dimension,
                Metric,
                OrderBy,
            )
            
            request = RunReportRequest(
                property=f"properties/{self.property_id}",
                date_ranges=[DateRange(start_date="7daysAgo", end_date="today")],
                dimensions=[Dimension(name="sessionSource")],
                metrics=[
                    Metric(name="sessions"),
                    Metric(name="activeUsers"),
                ],
                order_bys=[
                    OrderBy(
                        metric=OrderBy.MetricOrderBy(metric_name="sessions"),
                        desc=True,
                    )
                ],
                limit=10,
            )
            
            response = self.client.run_report(request)
            
            sources = []
            for row in response.rows:
                sources.append({
                    "source": row.dimension_values[0].value or "(direct)",
                    "sessions": int(row.metric_values[0].value),
                    "users": int(row.metric_values[1].value),
                })
            return sources
        except Exception as e:
            logger.error(f"Error fetching traffic sources: {e}")
            return []
    
    def get_device_breakdown(self) -> List[Dict[str, Any]]:
        """デバイス別内訳を取得"""
        if not self.is_available:
            return []
        
        try:
            from google.analytics.data_v1beta.types import (
                RunReportRequest,
                DateRange,
                Dimension,
                Metric,
            )
            
            request = RunReportRequest(
                property=f"properties/{self.property_id}",
                date_ranges=[DateRange(start_date="7daysAgo", end_date="today")],
                dimensions=[Dimension(name="deviceCategory")],
                metrics=[
                    Metric(name="sessions"),
                    Metric(name="activeUsers"),
                ],
            )
            
            response = self.client.run_report(request)
            
            devices = []
            total_sessions = 0
            for row in response.rows:
                sessions = int(row.metric_values[0].value)
                total_sessions += sessions
                devices.append({
                    "device": row.dimension_values[0].value,
                    "sessions": sessions,
                    "users": int(row.metric_values[1].value),
                })
            
            # パーセンテージを計算
            for device in devices:
                if total_sessions > 0:
                    device["percentage"] = round(device["sessions"] / total_sessions * 100, 1)
                else:
                    device["percentage"] = 0
            
            return devices
        except Exception as e:
            logger.error(f"Error fetching device breakdown: {e}")
            return []
    
    def get_country_breakdown(self) -> List[Dict[str, Any]]:
        """国別内訳を取得"""
        if not self.is_available:
            return []
        
        try:
            from google.analytics.data_v1beta.types import (
                RunReportRequest,
                DateRange,
                Dimension,
                Metric,
                OrderBy,
            )
            
            request = RunReportRequest(
                property=f"properties/{self.property_id}",
                date_ranges=[DateRange(start_date="7daysAgo", end_date="today")],
                dimensions=[Dimension(name="country")],
                metrics=[
                    Metric(name="sessions"),
                    Metric(name="activeUsers"),
                ],
                order_bys=[
                    OrderBy(
                        metric=OrderBy.MetricOrderBy(metric_name="sessions"),
                        desc=True,
                    )
                ],
                limit=10,
            )
            
            response = self.client.run_report(request)
            
            countries = []
            for row in response.rows:
                countries.append({
                    "country": row.dimension_values[0].value,
                    "sessions": int(row.metric_values[0].value),
                    "users": int(row.metric_values[1].value),
                })
            return countries
        except Exception as e:
            logger.error(f"Error fetching country breakdown: {e}")
            return []
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """ダッシュボード用のすべてのデータを取得"""
        return {
            "realtime_users": self.get_realtime_users(),
            "today": self.get_today_stats(),
            "weekly_trend": self.get_weekly_trend(),
            "top_pages": self.get_top_pages(5),
            "traffic_sources": self.get_traffic_sources(),
            "devices": self.get_device_breakdown(),
            "countries": self.get_country_breakdown(),
            "is_available": self.is_available,
            "property_id": self.property_id,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }


# シングルトンインスタンス
_ga_service = None


def get_ga_service() -> GoogleAnalyticsService:
    """GAサービスのシングルトンインスタンスを取得"""
    global _ga_service
    if _ga_service is None:
        _ga_service = GoogleAnalyticsService()
    return _ga_service

