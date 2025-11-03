"""
企業情報スクレイピング機能
BeautifulSoup + Requestsを使用して企業情報を取得する
"""
import logging
import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional, List
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


def scrape_company_info(url: str, timeout: int = 30) -> Dict[str, any]:
    """
    単一URLから企業情報をスクレイピング
    
    Args:
        url: スクレイピング対象URL
        timeout: リクエストタイムアウト（秒）
    
    Returns:
        企業情報の辞書
    """
    logger.info(f"企業情報のスクレイピングを開始: {url}")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        # HTMLをパース
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 企業情報を抽出
        company_info = extract_company_info_from_html(soup, url)
        
        logger.info(f"企業情報のスクレイピングが完了: {url}")
        return company_info
    
    except requests.RequestException as e:
        logger.error(f"スクレイピングエラー: {url}, Error: {e}", exc_info=True)
        raise ValueError(f"スクレイピングに失敗しました: {e}")
    except Exception as e:
        logger.error(f"スクレイピング処理エラー: {url}, Error: {e}", exc_info=True)
        raise ValueError(f"スクレイピング処理に失敗しました: {e}")


def extract_company_info_from_html(soup: BeautifulSoup, url: str) -> Dict[str, any]:
    """
    HTMLから企業情報を抽出
    
    Args:
        soup: BeautifulSoupオブジェクト
        url: 元のURL
    
    Returns:
        企業情報の辞書
    """
    company_info = {
        'company_name': None,
        'industry': None,
        'business_description': None,
        'location': None,
        'employee_count': None,
        'established_year': None,
        'raw_html': str(soup)[:5000],  # 最初の5000文字を保存（OpenAIで処理するため）
        'url': url
    }
    
    # タイトルから会社名を推測
    title = soup.find('title')
    if title:
        company_info['company_name'] = title.text.strip()
    
    # meta descriptionから事業内容を推測
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc and meta_desc.get('content'):
        company_info['business_description'] = meta_desc.get('content').strip()[:500]
    
    # よくある企業情報のセレクタを試す
    # h1, h2タグから会社名を探す
    h1_tags = soup.find_all('h1', limit=3)
    for h1 in h1_tags:
        text = h1.text.strip()
        if text and len(text) < 100:
            if not company_info['company_name']:
                company_info['company_name'] = text
            break
    
    # class名にcompany, about, profileなどが含まれる要素を探す
    company_sections = soup.find_all(['div', 'section'], class_=lambda x: x and any(keyword in x.lower() for keyword in ['company', 'about', 'profile', 'corporate']))
    for section in company_sections[:5]:  # 最初の5つまで
        text = section.get_text(separator=' ', strip=True)[:1000]
        if not company_info['business_description'] and text:
            company_info['business_description'] = text[:500]
        if not company_info['industry'] and any(keyword in text.lower() for keyword in ['業界', 'industry', '分野']):
            # 業界情報を抽出（簡易版）
            company_info['industry'] = extract_industry(text)
    
    return company_info


def extract_industry(text: str) -> Optional[str]:
    """
    テキストから業界情報を抽出（簡易版）
    
    Args:
        text: テキスト
    
    Returns:
        業界名（見つからない場合はNone）
    """
    # よくある業界名を検索
    industries = ['IT', '製造', '小売', '金融', '不動産', '建設', '医療', '教育', '飲食', '運輸']
    text_lower = text.lower()
    
    for industry in industries:
        if industry in text:
            return industry
    
    return None


def scrape_multiple_urls(urls: List[str], max_urls: int = 50, timeout: int = 30) -> Dict[str, any]:
    """
    複数URLから企業情報をスクレイピングし、統合する
    
    Args:
        urls: スクレイピング対象URL一覧
        max_urls: 最大スクレイピング数（制限）
        timeout: リクエストタイムアウト（秒）
    
    Returns:
        統合された企業情報の辞書
    """
    logger.info(f"複数URLからの企業情報スクレイピングを開始: {len(urls)} 件")
    
    # URL数制限
    urls_to_scrape = urls[:max_urls]
    
    all_info = []
    scraped_urls = []
    failed_urls = []
    
    for i, url in enumerate(urls_to_scrape, 1):
        try:
            logger.debug(f"スクレイピング中 ({i}/{len(urls_to_scrape)}): {url}")
            info = scrape_company_info(url, timeout)
            all_info.append(info)
            scraped_urls.append(url)
        except Exception as e:
            logger.warning(f"スクレイピング失敗: {url}, Error: {e}")
            failed_urls.append(url)
            continue
    
    # 情報を統合
    merged_info = merge_company_info(all_info)
    merged_info['scraped_urls'] = scraped_urls
    merged_info['failed_urls'] = failed_urls
    merged_info['urls_found'] = len(urls)
    merged_info['urls_scraped'] = len(scraped_urls)
    merged_info['urls_failed'] = len(failed_urls)
    
    logger.info(f"複数URLからのスクレイピングが完了: 成功 {len(scraped_urls)} 件、失敗 {len(failed_urls)} 件")
    return merged_info


def merge_company_info(info_list: List[Dict[str, any]]) -> Dict[str, any]:
    """
    複数の企業情報を統合
    
    Args:
        info_list: 企業情報のリスト
    
    Returns:
        統合された企業情報の辞書
    """
    if not info_list:
        return {
            'company_name': None,
            'industry': None,
            'business_description': None,
            'location': None,
            'employee_count': None,
            'established_year': None
        }
    
    merged = {
        'company_name': None,
        'industry': None,
        'business_description': None,
        'location': None,
        'employee_count': None,
        'established_year': None,
        'raw_html_list': []
    }
    
    # 各フィールドを統合（最初に見つかった非None値を優先）
    for info in info_list:
        if not merged['company_name'] and info.get('company_name'):
            merged['company_name'] = info['company_name']
        if not merged['industry'] and info.get('industry'):
            merged['industry'] = info['industry']
        if not merged['business_description'] and info.get('business_description'):
            merged['business_description'] = info['business_description']
        if not merged['location'] and info.get('location'):
            merged['location'] = info['location']
        if not merged['employee_count'] and info.get('employee_count'):
            merged['employee_count'] = info['employee_count']
        if not merged['established_year'] and info.get('established_year'):
            merged['established_year'] = info['established_year']
        
        # raw_htmlをリストに追加
        if info.get('raw_html'):
            merged['raw_html_list'].append(info['raw_html'])
    
    return merged

