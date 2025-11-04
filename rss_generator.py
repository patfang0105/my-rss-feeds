#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的 RSS 生成器
为不支持 RSS 的网站生成订阅源
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse
import sys
import json
import time
import random
import re

def create_rss_feed(title, link, description, items):
    """创建 RSS XML"""
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    
    # 频道信息
    ET.SubElement(channel, "title").text = title
    ET.SubElement(channel, "link").text = link
    ET.SubElement(channel, "description").text = description
    ET.SubElement(channel, "lastBuildDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")
    ET.SubElement(channel, "generator").text = "RSSHub-lite Python"
    
    # 添加条目
    for item in items:
        item_elem = ET.SubElement(channel, "item")
        ET.SubElement(item_elem, "title").text = item.get('title', '无标题')
        ET.SubElement(item_elem, "link").text = item.get('link', link)
        ET.SubElement(item_elem, "description").text = item.get('description', '')
        ET.SubElement(item_elem, "pubDate").text = item.get('date', datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT"))
        ET.SubElement(item_elem, "guid").text = item.get('link', link)
    
    return ET.tostring(rss, encoding='unicode', xml_declaration=True)

def scrape_website(url, item_selector, title_selector, link_selector=None, desc_selector=None, time_selector=None):
    """抓取网站内容"""
    try:
        # 随机选择 User-Agent
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0'
        ]
        
        headers = {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.google.com/'
        }
        # 添加随机延时，模拟人类行为
        time.sleep(random.uniform(1, 3))
        
        # 使用 Session 保持连接
        session = requests.Session()
        session.headers.update(headers)
        
        # 重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = session.get(url, timeout=15)
                response.raise_for_status()
                
                # 检查响应内容
                if len(response.content) < 1000:
                    print(f"响应内容过短，可能被重定向或需要 JavaScript")
                    if attempt < max_retries - 1:
                        time.sleep(3)
                        continue
                
                break
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"请求失败，{2}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                    time.sleep(2)
                else:
                    raise e
        
        soup = BeautifulSoup(response.content, 'html.parser')
        items = []
        
        # 调试：显示页面标题和找到的元素数量
        page_title = soup.find('title')
        if page_title:
            print(f"页面标题: {page_title.get_text()}")
        
        # 调试：显示找到的条目数量
        found_elements = soup.select(item_selector)
        print(f"找到 {len(found_elements)} 个条目元素")
        
        if len(found_elements) == 0:
            print("尝试更通用的选择器...")
            # 尝试更通用的选择器
            generic_selectors = ['div', 'article', 'li', '.item', '.post']
            for selector in generic_selectors:
                elements = soup.select(selector)
                if len(elements) > 5:  # 如果找到超过5个元素，可能是有用的
                    print(f"选择器 '{selector}' 找到 {len(elements)} 个元素")
        
        # 查找所有条目
        for element in found_elements:
            title_elem = element.select_one(title_selector)
            if not title_elem:
                continue
                
            title = title_elem.get_text(strip=True)
            
            # 获取链接
            if link_selector:
                link_elem = element.select_one(link_selector)
                if link_elem:
                    href = link_elem.get('href') or link_elem.get_text(strip=True)
                    link = urljoin(url, href)
                else:
                    link = url
            else:
                link = url
                
            # 获取描述
            description = ""
            if desc_selector:
                desc_elem = element.select_one(desc_selector)
                if desc_elem:
                    description = str(desc_elem)
            
            # 获取时间
            date_str = datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")
            if time_selector:
                time_elem = element.select_one(time_selector)
                if time_elem:
                    time_text = time_elem.get_text(strip=True)
                    # 解析时间文本，例如 "— September 26, 2025"
                    try:
                        # 移除开头的 "— " 符号
                        clean_time = time_text.replace("— ", "").strip()
                        # 解析日期
                        parsed_date = datetime.strptime(clean_time, "%B %d, %Y")
                        date_str = parsed_date.strftime("%a, %d %b %Y %H:%M:%S GMT")
                    except:
                        # 如果解析失败，使用当前时间
                        pass
            
            items.append({
                'title': title,
                'link': link,
                'description': description,
                'date': date_str
            })
        
        return items
        
    except Exception as e:
        print(f"抓取失败: {e}", file=sys.stderr)
        return []

def parse_date_from_url(url):
    """从URL中解析日期"""
    try:
        # 匹配URL中的日期格式，如 /2025/10/10/
        date_match = re.search(r'/(\d{4})/(\d{1,2})/(\d{1,2})/', url)
        if date_match:
            year, month, day = date_match.groups()
            date_obj = datetime(int(year), int(month), int(day))
            return date_obj.strftime("%a, %d %b %Y %H:%M:%S GMT")
    except:
        pass
    return datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")

def scrape_bu_gdp_website():
    """专门抓取波士顿大学GDP中心网站内容"""
    url = "https://www.bu.edu/gdp/"
    
    try:
        # 设置请求头
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        headers = {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        print(f"正在抓取: {url}")
        
        # 使用 Session 保持连接
        session = requests.Session()
        session.headers.update(headers)
        
        # 重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = session.get(url, timeout=15)
                response.raise_for_status()
                break
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"请求失败，2秒后重试... (尝试 {attempt + 1}/{max_retries})")
                    time.sleep(2)
                else:
                    raise e
        
        soup = BeautifulSoup(response.content, 'html.parser')
        items = []
        
        # 调试：显示页面标题
        page_title = soup.find('title')
        if page_title:
            print(f"页面标题: {page_title.get_text()}")
        
        # 尝试多种选择器来找到新闻条目
        selectors_to_try = [
            'section.homepage-newsFeed ul li',
            '.homepage-newsFeed li',
            'section.homepage-newsEvents section.homepage-newsFeed ul li',
            'ul li.has-thumb',
            'li.post_31410',
            'article',
            '.post',
            'li[class*="post"]',
            'div[class*="news"]',
            'div[class*="item"]'
        ]
        
        found_elements = []
        used_selector = None
        
        for selector in selectors_to_try:
            elements = soup.select(selector)
            if len(elements) > 0:
                print(f"选择器 '{selector}' 找到 {len(elements)} 个元素")
                found_elements = elements
                used_selector = selector
                break
        
        if not found_elements:
            print("未找到任何新闻条目，尝试查找所有可能的链接...")
            # 查找所有包含"Read more"的链接
            read_more_links = soup.find_all('a', string=re.compile(r'Read more', re.I))
            print(f"找到 {len(read_more_links)} 个 'Read more' 链接")
            
            for link in read_more_links:
                # 尝试找到父级元素中的标题
                parent = link.parent
                title_elem = None
                
                # 向上查找标题
                for _ in range(5):  # 最多向上查找5层
                    if parent:
                        title_elem = parent.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                        if title_elem:
                            break
                        parent = parent.parent
                    else:
                        break
                
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    article_link = urljoin(url, link.get('href', ''))
                    
                    # 从链接中提取日期
                    date_str = parse_date_from_url(article_link)
                    
                    items.append({
                        'title': title,
                        'link': article_link,
                        'description': f"来自波士顿大学全球发展政策中心: {title}",
                        'date': date_str
                    })
        
        # 如果仍然没有找到内容，尝试更广泛的方法
        if not items:
            print("尝试更广泛的内容提取...")
            # 查找所有可能包含新闻标题的h4元素
            h4_elements = soup.find_all('h4')
            print(f"找到 {len(h4_elements)} 个 h4 元素")
            
            for h4 in h4_elements:
                title = h4.get_text(strip=True)
                if title and len(title) > 10:  # 过滤掉太短的标题
                    # 查找相关的链接
                    link_elem = h4.find('a') or h4.parent.find('a') if h4.parent else None
                    if link_elem:
                        article_link = urljoin(url, link_elem.get('href', ''))
                    else:
                        # 查找"Read more"链接
                        read_more = h4.find_next('a', string=re.compile(r'Read more', re.I))
                        if read_more:
                            article_link = urljoin(url, read_more.get('href', ''))
                        else:
                            continue
                    
                    # 从链接中提取日期
                    date_str = parse_date_from_url(article_link)
                    
                    items.append({
                        'title': title,
                        'link': article_link,
                        'description': f"来自波士顿大学全球发展政策中心: {title}",
                        'date': date_str
                    })
        
        else:
            print(f"使用选择器: {used_selector}")
            
            # 处理找到的元素
            for element in found_elements:
                title_elem = None
                link_elem = None
                
                # 查找标题 - 尝试多种可能的选择器
                title_selectors = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', '.title', '[class*="title"]']
                for selector in title_selectors:
                    title_elem = element.select_one(selector)
                    if title_elem:
                        break
                
                if not title_elem:
                    # 如果没找到标题，尝试查找链接中的文本
                    link_elem = element.find('a')
                    if link_elem:
                        title_elem = link_elem
                
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                if not title:
                    continue
                
                # 查找链接
                if not link_elem:
                    link_elem = element.find('a')
                
                if link_elem and link_elem.get('href'):
                    article_link = urljoin(url, link_elem.get('href'))
                else:
                    # 查找"Read more"链接
                    read_more = element.find('a', string=re.compile(r'Read more', re.I))
                    if read_more:
                        article_link = urljoin(url, read_more.get('href'))
                    else:
                        article_link = url
                
                # 从链接中提取日期
                date_str = parse_date_from_url(article_link)
                
                # 查找描述
                description = ""
                desc_selectors = ['p', '.excerpt', '.summary', '[class*="desc"]']
                for selector in desc_selectors:
                    desc_elem = element.select_one(selector)
                    if desc_elem:
                        description = desc_elem.get_text(strip=True)
                        break
                
                if not description:
                    description = f"来自波士顿大学全球发展政策中心: {title}"
                
                items.append({
                    'title': title,
                    'link': article_link,
                    'description': description,
                    'date': date_str
                })
        
        # 去重（基于链接）
        seen_links = set()
        unique_items = []
        for item in items:
            if item['link'] not in seen_links:
                seen_links.add(item['link'])
                unique_items.append(item)
        
        return unique_items
        
    except Exception as e:
        print(f"抓取失败: {e}", file=sys.stderr)
        return []

def scrape_rhg_china_website():
    """专门抓取RHG中国研究网站内容"""
    url = "https://rhg.com/china/research/"
    
    try:
        # 设置更真实的请求头
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        headers = {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.google.com/'
        }
        
        print(f"正在抓取: {url}")
        
        # 使用 Session 保持连接
        session = requests.Session()
        session.headers.update(headers)
        
        # 重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = session.get(url, timeout=15)
                response.raise_for_status()
                break
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"请求失败，2秒后重试... (尝试 {attempt + 1}/{max_retries})")
                    time.sleep(2)
                else:
                    raise e
        
        soup = BeautifulSoup(response.content, 'html.parser')
        items = []
        
        # 调试：显示页面标题
        page_title = soup.find('title')
        if page_title:
            print(f"页面标题: {page_title.get_text()}")
        
        # 尝试多种选择器来找到文章条目
        selectors_to_try = [
            # 基于您提供的选择器
            'article',
            '.c-card__content',
            'div.c-card__content',
            '.c-listing__list article',
            '#listing article',
            # 更通用的选择器
            'div[class*="card"]',
            'div[class*="article"]',
            'div[class*="item"]'
        ]
        
        found_elements = []
        used_selector = None
        
        for selector in selectors_to_try:
            elements = soup.select(selector)
            if len(elements) > 0:
                print(f"选择器 '{selector}' 找到 {len(elements)} 个元素")
                found_elements = elements
                used_selector = selector
                break
        
        if not found_elements:
            print("未找到任何文章条目，尝试使用您提供的选择器...")
            # 使用您提供的选择器
            try:
                # 基于您提供的选择器: #listing > div > div > div.c-listing__content > div.c-listing__list > article:nth-child(1) > div.c-card__content > div.c-card__text-wrapper > h3 > a
                listing_elements = soup.select('#listing')
                if listing_elements:
                    print(f"找到 #listing 元素")
                    articles = listing_elements[0].select('article')
                    print(f"找到 {len(articles)} 个 article 元素")
                    
                    for article in articles:
                        # 查找标题链接
                        title_link = article.select_one('h3 a')
                        if title_link:
                            title_text = title_link.get_text(strip=True)
                            href = title_link.get('href', '')
                            
                            if title_text and href:
                                # 确保链接是完整的URL
                                if not href.startswith('http'):
                                    href = urljoin(url, href)
                                
                                # 查找描述
                                description = ""
                                desc_elem = article.select_one('.c-card__text-wrapper p')
                                if desc_elem:
                                    description = desc_elem.get_text(strip=True)
                                
                                if not description:
                                    description = f"来自荣鼎集团中国研究: {title_text}"
                                
                                items.append({
                                    'title': title_text,
                                    'link': href,
                                    'description': description,
                                    'date': datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")
                                })
                
                # 如果还是没找到，尝试查找所有包含链接的标题
                if not items:
                    print("尝试查找所有可能的链接...")
                    title_links = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                    for title in title_links:
                        link = title.find('a')
                        if link:
                            title_text = title.get_text(strip=True)
                            href = link.get('href', '')
                            if title_text and href and len(title_text) > 10:
                                # 确保链接是完整的URL
                                if not href.startswith('http'):
                                    href = urljoin(url, href)
                                
                                items.append({
                                    'title': title_text,
                                    'link': href,
                                    'description': f"来自荣鼎集团中国研究: {title_text}",
                                    'date': datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")
                                })
            except Exception as e:
                print(f"使用自定义选择器失败: {e}")
                # 最后的备用方案
                print("使用最后的备用方案...")
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    text = link.get_text(strip=True)
                    href = link.get('href', '')
                    if text and href and len(text) > 10 and any(keyword in text.lower() for keyword in ['china', 'research', 'analysis', 'report']):
                        if not href.startswith('http'):
                            href = urljoin(url, href)
                        items.append({
                            'title': text,
                            'link': href,
                            'description': f"来自荣鼎集团中国研究: {text}",
                            'date': datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")
                        })
        else:
            print(f"使用选择器: {used_selector}")
            
            # 处理找到的元素
            for element in found_elements:
                title_elem = None
                link_elem = None
                
                # 查找标题 - 尝试多种可能的选择器
                title_selectors = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', '.c-card__title', '[class*="title"]']
                for selector in title_selectors:
                    title_elem = element.select_one(selector)
                    if title_elem:
                        break
                
                if not title_elem:
                    # 如果没找到标题，尝试查找链接中的文本
                    link_elem = element.find('a')
                    if link_elem:
                        title_elem = link_elem
                
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                if not title or len(title) < 5:
                    continue
                
                # 查找链接
                if not link_elem:
                    link_elem = element.find('a')
                
                if link_elem and link_elem.get('href'):
                    article_link = urljoin(url, link_elem.get('href'))
                else:
                    article_link = url
                
                # 查找描述
                description = ""
                desc_selectors = ['p', '.c-card__text', '.excerpt', '.summary', '[class*="desc"]', '[class*="text"]']
                for selector in desc_selectors:
                    desc_elem = element.select_one(selector)
                    if desc_elem:
                        description = desc_elem.get_text(strip=True)
                        break
                
                if not description:
                    description = f"来自荣鼎集团中国研究: {title}"
                
                # 查找日期
                date_str = datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")
                date_selectors = ['time', '.date', '.c-card__date', '[class*="date"]']
                for selector in date_selectors:
                    date_elem = element.select_one(selector)
                    if date_elem:
                        date_attr = date_elem.get('datetime') or date_elem.get_text(strip=True)
                        if date_attr:
                            try:
                                # 尝试解析日期
                                if 'T' in date_attr:
                                    parsed_date = datetime.fromisoformat(date_attr.replace('Z', '+00:00'))
                                else:
                                    # 尝试其他日期格式
                                    parsed_date = datetime.strptime(date_attr, "%Y-%m-%d")
                                date_str = parsed_date.strftime("%a, %d %b %Y %H:%M:%S GMT")
                            except:
                                pass
                        break
                
                items.append({
                    'title': title,
                    'link': article_link,
                    'description': description,
                    'date': date_str
                })
        
        # 去重（基于链接）
        seen_links = set()
        unique_items = []
        for item in items:
            if item['link'] not in seen_links:
                seen_links.add(item['link'])
                unique_items.append(item)
        
        return unique_items
        
    except Exception as e:
        print(f"抓取失败: {e}", file=sys.stderr)
        return []

def scrape_cfr_economics_website():
    """专门抓取CFR经济学页面内容"""
    url = "https://www.cfr.org/economics"
    
    try:
        # 设置请求头
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        headers = {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.google.com/'
        }
        
        print(f"正在抓取: {url}")
        
        # 使用 Session 保持连接
        session = requests.Session()
        session.headers.update(headers)
        
        # 重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = session.get(url, timeout=15)
                response.raise_for_status()
                break
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"请求失败，2秒后重试... (尝试 {attempt + 1}/{max_retries})")
                    time.sleep(2)
                else:
                    raise e
        
        soup = BeautifulSoup(response.content, 'html.parser')
        items = []
        
        # 调试：显示页面标题
        page_title = soup.find('title')
        if page_title:
            print(f"页面标题: {page_title.get_text()}")
        
        # 策略1: 查找所有指向文章或博客的链接
        all_links = soup.find_all('a', href=True)
        seen_links = set()
        
        for link in all_links:
            href = link.get('href', '')
            title_text = link.get_text(strip=True)
            
            # 过滤条件: 链接包含文章路径,标题长度合理,且不是重复的
            # 只处理真正的文章和博客,不处理主题分类页面
            if (title_text and len(title_text) > 15 and 
                href and ('/article/' in href or '/blog/' in href) and
                href not in seen_links and not href.startswith('#')):
                
                # 构建完整URL
                if href.startswith('http'):
                    full_url = href.strip()
                elif href.startswith('/'):
                    full_url = f'https://www.cfr.org{href.strip()}'
                else:
                    full_url = urljoin(url, href.strip())
                
                # 跳过主页和分类页面
                if full_url in ['https://www.cfr.org/', 'https://www.cfr.org/economics']:
                    continue
                
                seen_links.add(full_url)
                
                # 查找父元素中的日期和描述信息
                parent = link.parent
                date_str = datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")
                description = ""
                
                # 向上查找包含日期和描述的容器
                for _ in range(5):
                    if parent:
                        parent_text = parent.get_text()
                        
                        # 查找日期模式 (例如: "October 30, 2025")
                        date_patterns = [
                            r'(\w+\s+\d{1,2},\s+\d{4})',  # October 30, 2025
                            r'(\d{1,2}\s+\w+\s+\d{4})',   # 30 October 2025
                        ]
                        for pattern in date_patterns:
                            date_match = re.search(pattern, parent_text)
                            if date_match:
                                try:
                                    date_str_clean = date_match.group(1)
                                    # 尝试解析日期
                                    parsed_date = datetime.strptime(date_str_clean, "%B %d, %Y")
                                    date_str = parsed_date.strftime("%a, %d %b %Y %H:%M:%S GMT")
                                    break
                                except:
                                    try:
                                        parsed_date = datetime.strptime(date_str_clean, "%d %B %Y")
                                        date_str = parsed_date.strftime("%a, %d %b %Y %H:%M:%S GMT")
                                        break
                                    except:
                                        pass
                        
                        # 查找描述 (通常是段落文本)
                        desc_elem = parent.find('p')
                        if desc_elem:
                            description = desc_elem.get_text(strip=True)
                            if len(description) > 10:
                                break
                        
                        parent = parent.parent
                    else:
                        break
                
                if not description:
                    description = f"来自CFR经济学: {title_text}"
                
                items.append({
                    'title': title_text,
                    'link': full_url,
                    'description': description[:500],  # 限制描述长度
                    'date': date_str
                })
        
        # 策略2: 查找包含特定CSS类的元素
        selectors_to_try = [
            'article',
            '.article',
            'div[class*="card"]',
            'div[class*="item"]',
            'li[class*="item"]',
            'section[class*="content"]'
        ]
        
        for selector in selectors_to_try:
            elements = soup.select(selector)
            if len(elements) > 0:
                print(f"选择器 '{selector}' 找到 {len(elements)} 个元素")
                
                for element in elements:
                    # 查找标题链接
                    title_link = element.find('a', href=True)
                    if not title_link:
                        continue
                    
                    title = title_link.get_text(strip=True)
                    href = title_link.get('href', '')
                    
                    if not title or len(title) < 15:
                        continue
                    
                    # 构建完整URL
                    if href.startswith('http'):
                        full_url = href.strip()
                    elif href.startswith('/'):
                        full_url = f'https://www.cfr.org{href.strip()}'
                    else:
                        full_url = urljoin(url, href.strip())
                    
                    # 跳过已存在的链接
                    if full_url in seen_links:
                        continue
                    
                    # 只处理文章和博客链接,不处理主题分类页面
                    if '/article/' not in full_url and '/blog/' not in full_url:
                        continue
                    
                    seen_links.add(full_url)
                    
                    # 查找描述
                    description = ""
                    desc_elem = element.find('p')
                    if desc_elem:
                        description = desc_elem.get_text(strip=True)
                    
                    # 查找日期
                    date_str = datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")
                    element_text = element.get_text()
                    date_match = re.search(r'(\w+\s+\d{1,2},\s+\d{4})', element_text)
                    if date_match:
                        try:
                            parsed_date = datetime.strptime(date_match.group(1), "%B %d, %Y")
                            date_str = parsed_date.strftime("%a, %d %b %Y %H:%M:%S GMT")
                        except:
                            pass
                    
                    if not description:
                        description = f"来自CFR经济学: {title}"
                    
                    items.append({
                        'title': title,
                        'link': full_url,
                        'description': description[:500],
                        'date': date_str
                    })
        
        # 去重（基于链接）
        final_items = []
        final_seen = set()
        for item in items:
            if item['link'] not in final_seen:
                final_seen.add(item['link'])
                final_items.append(item)
        
        # 按日期排序（最新的在前）
        try:
            final_items.sort(key=lambda x: x['date'], reverse=True)
        except:
            pass
        
        return final_items
        
    except Exception as e:
        print(f"抓取失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return []

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python rss_generator.py <网站URL> [条目选择器] [标题选择器] [链接选择器] [描述选择器] [时间选择器]")
        print("特殊用法: python rss_generator.py bu-gdp        # 使用专门的BU GDP抓取器")
        print("特殊用法: python rss_generator.py rhg-china     # 使用专门的RHG中国研究抓取器")
        print("特殊用法: python rss_generator.py cfr-economics # 使用专门的CFR经济学抓取器")
        print("示例: python rss_generator.py 'https://news.ycombinator.com/' 'span.titleline' 'a' 'a'")
        print("示例: python rss_generator.py 'https://example.com/news' '.news-item' '.title' '.link' '.summary' '.date'")
        sys.exit(1)
    
    # 检查是否是BU GDP特殊处理
    if sys.argv[1] == "bu-gdp":
        print("🎓 使用波士顿大学全球发展政策中心专用抓取器")
        print("=" * 60)
        
        # 抓取内容
        items = scrape_bu_gdp_website()
        
        if not items:
            print("❌ 没有找到任何内容")
            sys.exit(1)
        
        print(f"✅ 找到 {len(items)} 个条目:")
        for i, item in enumerate(items[:5], 1):  # 只显示前5个
            print(f"{i}. {item['title']}")
            print(f"   链接: {item['link']}")
            print(f"   日期: {item['date']}")
            print()
        if len(items) > 5:
            print(f"... 还有 {len(items) - 5} 个条目")
        
        # 生成 RSS
        title = "Boston University Global Development Policy Center"
        description = "Latest research and commentary from the Boston University Global Development Policy Center"
        url = "https://www.bu.edu/gdp/"
        
        rss_xml = create_rss_feed(title, url, description, items)
        
        # 保存到文件
        filename = "rss_bu_gdp.xml"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(rss_xml)
        
        print(f"\n🎉 RSS文件已生成: {filename}")
        print(f"📱 你可以用RSS阅读器打开这个文件")
        print(f"🌐 或者部署到服务器上供他人订阅")
        return
    
    # 检查是否是RHG特殊处理
    if sys.argv[1] == "rhg-china":
        print("🏛️ 使用荣鼎集团中国研究专用抓取器")
        print("=" * 60)
        
        # 抓取内容
        items = scrape_rhg_china_website()
        
        if not items:
            print("❌ 没有找到任何内容")
            sys.exit(1)
        
        print(f"✅ 找到 {len(items)} 个条目:")
        for i, item in enumerate(items[:5], 1):  # 只显示前5个
            print(f"{i}. {item['title']}")
            print(f"   链接: {item['link']}")
            print(f"   日期: {item['date']}")
            print()
        if len(items) > 5:
            print(f"... 还有 {len(items) - 5} 个条目")
        
        # 生成 RSS
        title = "Rhodium Group China Research"
        description = "Latest research and analysis on China from Rhodium Group"
        url = "https://rhg.com/china/research/"
        
        rss_xml = create_rss_feed(title, url, description, items)
        
        # 保存到文件
        filename = "rss_rhg_china.xml"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(rss_xml)
        
        print(f"\n🎉 RSS文件已生成: {filename}")
        print(f"📱 你可以用RSS阅读器打开这个文件")
        print(f"🌐 或者部署到服务器上供他人订阅")
        return
    
    # 检查是否是CFR经济学特殊处理
    if sys.argv[1] == "cfr-economics":
        print("🌐 使用CFR经济学专用抓取器")
        print("=" * 60)
        
        # 抓取内容
        items = scrape_cfr_economics_website()
        
        if not items:
            print("❌ 没有找到任何内容")
            sys.exit(1)
        
        print(f"✅ 找到 {len(items)} 个条目:")
        for i, item in enumerate(items[:5], 1):  # 只显示前5个
            print(f"{i}. {item['title']}")
            print(f"   链接: {item['link']}")
            print(f"   日期: {item['date']}")
            print()
        if len(items) > 5:
            print(f"... 还有 {len(items) - 5} 个条目")
        
        # 生成 RSS
        title = "CFR Economics"
        description = "Latest economics articles and analysis from the Council on Foreign Relations"
        url = "https://www.cfr.org/economics"
        
        rss_xml = create_rss_feed(title, url, description, items)
        
        # 保存到文件
        filename = "rss_cfr_economics.xml"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(rss_xml)
        
        print(f"\n🎉 RSS文件已生成: {filename}")
        print(f"📱 你可以用RSS阅读器打开这个文件")
        print(f"🌐 或者部署到服务器上供他人订阅")
        return
    
    # 原有的通用处理逻辑
    if len(sys.argv) < 4:
        print("用法: python rss_generator.py <网站URL> <条目选择器> <标题选择器> [链接选择器] [描述选择器] [时间选择器]")
        print("特殊用法: python rss_generator.py bu-gdp  # 使用专门的BU GDP抓取器")
        print("示例: python rss_generator.py 'https://news.ycombinator.com/' 'span.titleline' 'a' 'a'")
        print("示例: python rss_generator.py 'https://example.com/news' '.news-item' '.title' '.link' '.summary' '.date'")
        sys.exit(1)
    
    url = sys.argv[1]
    item_selector = sys.argv[2]
    title_selector = sys.argv[3]
    link_selector = sys.argv[4] if len(sys.argv) > 4 else None
    desc_selector = sys.argv[5] if len(sys.argv) > 5 else None
    time_selector = sys.argv[6] if len(sys.argv) > 6 else None
    
    print(f"正在抓取: {url}")
    print(f"条目选择器: {item_selector}")
    print(f"标题选择器: {title_selector}")
    if link_selector:
        print(f"链接选择器: {link_selector}")
    if desc_selector:
        print(f"描述选择器: {desc_selector}")
    if time_selector:
        print(f"时间选择器: {time_selector}")
    print("-" * 50)
    
    # 抓取内容
    items = scrape_website(url, item_selector, title_selector, link_selector, desc_selector, time_selector)
    
    if not items:
        print("没有找到任何内容，请检查选择器是否正确")
        sys.exit(1)
    
    print(f"找到 {len(items)} 个条目:")
    for i, item in enumerate(items[:5], 1):  # 只显示前5个
        print(f"{i}. {item['title']}")
    if len(items) > 5:
        print(f"... 还有 {len(items) - 5} 个条目")
    
    # 生成 RSS
    domain = urlparse(url).netloc
    title = f"{domain} - RSS订阅"
    description = f"为 {url} 生成的RSS订阅源"
    
    rss_xml = create_rss_feed(title, url, description, items)
    
    # 保存到文件
    filename = f"rss_{domain.replace('.', '_')}.xml"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(rss_xml)
    
    print(f"\nRSS文件已生成: {filename}")
    print(f"你可以用RSS阅读器打开这个文件，或者部署到服务器上")

if __name__ == "__main__":
    main()
