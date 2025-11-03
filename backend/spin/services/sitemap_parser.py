"""
sitemap.xmlパーサー
sitemap.xmlファイルまたはURLからURL一覧を抽出する
"""
import logging
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse
import requests
from typing import List, Optional

logger = logging.getLogger(__name__)


def parse_sitemap_from_file(file_content: bytes) -> List[str]:
    """
    sitemap.xmlファイルからURL一覧を抽出
    
    Args:
        file_content: sitemap.xmlファイルのバイトデータ
    
    Returns:
        URL一覧（リスト）
    """
    logger.info("sitemap.xmlファイルの解析を開始")
    try:
        # XMLをパース
        root = ET.fromstring(file_content)
        
        urls = []
        # XML名前空間を処理
        namespaces = {
            'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'
        }
        
        # <url><loc>要素を検索
        url_elements = root.findall('.//sm:url/sm:loc', namespaces)
        if not url_elements:
            # 名前空間なしの場合を試す
            url_elements = root.findall('.//url/loc')
        
        for url_elem in url_elements:
            if url_elem.text:
                urls.append(url_elem.text.strip())
        
        logger.info(f"sitemap.xmlから {len(urls)} 件のURLを抽出しました")
        return urls
    
    except ET.ParseError as e:
        logger.error(f"sitemap.xmlの解析エラー: {e}", exc_info=True)
        raise ValueError(f"sitemap.xmlの解析に失敗しました: {e}")
    except Exception as e:
        logger.error(f"sitemap.xmlの処理エラー: {e}", exc_info=True)
        raise ValueError(f"sitemap.xmlの処理に失敗しました: {e}")


def parse_sitemap_from_url(sitemap_url: str, timeout: int = 30) -> List[str]:
    """
    sitemap.xml URLからURL一覧を抽出
    
    Args:
        sitemap_url: sitemap.xmlのURL
        timeout: リクエストタイムアウト（秒）
    
    Returns:
        URL一覧（リスト）
    """
    logger.info(f"sitemap.xml URLの解析を開始: {sitemap_url}")
    try:
        # HTTPリクエストでsitemap.xmlを取得
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(sitemap_url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        # ファイルとしてパース
        urls = parse_sitemap_from_file(response.content)
        
        logger.info(f"sitemap.xml URLから {len(urls)} 件のURLを抽出しました")
        return urls
    
    except requests.RequestException as e:
        logger.error(f"sitemap.xml URLの取得エラー: {sitemap_url}, Error: {e}", exc_info=True)
        raise ValueError(f"sitemap.xml URLの取得に失敗しました: {e}")
    except Exception as e:
        logger.error(f"sitemap.xml URLの処理エラー: {sitemap_url}, Error: {e}", exc_info=True)
        raise ValueError(f"sitemap.xml URLの処理に失敗しました: {e}")


def parse_sitemap_index(sitemap_url: str, timeout: int = 30) -> List[str]:
    """
    sitemap index（sitemapのインデックス）を解析して、全てのsitemapのURLを取得
    
    Args:
        sitemap_url: sitemap indexのURL
        timeout: リクエストタイムアウト（秒）
    
    Returns:
        全てのsitemapから抽出されたURL一覧（リスト）
    """
    logger.info(f"sitemap indexの解析を開始: {sitemap_url}")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(sitemap_url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        namespaces = {
            'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'
        }
        
        all_urls = []
        
        # sitemap indexの場合、<sitemap><loc>要素を検索
        sitemap_elements = root.findall('.//sm:sitemap/sm:loc', namespaces)
        if not sitemap_elements:
            sitemap_elements = root.findall('.//sitemap/loc')
        
        if sitemap_elements:
            # sitemap indexの場合、各sitemapからURLを取得
            logger.info(f"sitemap indexから {len(sitemap_elements)} 件のsitemapを検出")
            for sitemap_elem in sitemap_elements:
                if sitemap_elem.text:
                    sitemap_url = sitemap_elem.text.strip()
                    try:
                        urls = parse_sitemap_from_url(sitemap_url, timeout)
                        all_urls.extend(urls)
                    except Exception as e:
                        logger.warning(f"sitemapの取得に失敗: {sitemap_url}, Error: {e}")
                        continue
        else:
            # 通常のsitemapの場合
            urls = parse_sitemap_from_file(response.content)
            all_urls.extend(urls)
        
        logger.info(f"sitemap indexから合計 {len(all_urls)} 件のURLを抽出しました")
        return all_urls
    
    except requests.RequestException as e:
        logger.error(f"sitemap index URLの取得エラー: {sitemap_url}, Error: {e}", exc_info=True)
        raise ValueError(f"sitemap index URLの取得に失敗しました: {e}")
    except Exception as e:
        logger.error(f"sitemap indexの処理エラー: {sitemap_url}, Error: {e}", exc_info=True)
        raise ValueError(f"sitemap indexの処理に失敗しました: {e}")

