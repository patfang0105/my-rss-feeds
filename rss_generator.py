#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
波士顿大学全球发展政策中心 RSS 生成器
专门为 https://www.bu.edu/gdp/ 网站生成RSS订阅源
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
    ET.SubElement(channel, "generator").text = "BU GDP RSS Generator"
    ET.SubElement(channel, "language").text = "en-US"
    
    # 添加条目
    for item in items:
        item_elem = ET.SubElement(channel, "item")
        ET.SubElement(item_elem, "title").text = item.get('title', '无标题')
        ET.SubElement(item_elem, "link").text = item.get('link', link)
        ET.SubElement(item_elem, "description").text = item.get('description', '')
        ET.SubElement(item_elem, "pubDate").text = item.get('date', datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT"))
        ET.SubElement(item_elem, "guid").text = item.get('link', link)
        if item.get('author'):
            ET.SubElement(item_elem, "author").text = item.get('author')
    
    # 格式化XML输出
    rough_string = ET.tostring(rss, encoding='unicode')
    reparsed = ET.fromstring(rough_string)
    return ET.tostring(reparsed, encoding='unicode', xml_declaration=True)

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
    """抓取波士顿大学GDP中心网站内容"""
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
            # 基于您提供的选择器调整
            'section.homepage-newsFeed ul li',
            '.homepage-newsFeed li',
            'section.homepage-newsEvents section.homepage-newsFeed ul li',
            'ul li.has-thumb',
            'li.post_31410',
            # 更通用的选择器
            'article',
            '.post',
            'li[class*="post"]',
            'div[class*="news"]',
            'div[class*="item"]',
            # 尝试查找所有包含新闻的div
            'div[class*="news"] div',
            'section div',
            'div.content-container div'
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
                        'date': date_str,
                        'author': 'Boston University Global Development Policy Center'
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
                        'date': date_str,
                        'author': 'Boston University Global Development Policy Center'
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
                    'date': date_str,
                    'author': 'Boston University Global Development Policy Center'
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

def main():
    """主函数"""
    print("🎓 波士顿大学全球发展政策中心 RSS 生成器")
    print("=" * 60)
    
    # 抓取内容
    items = scrape_bu_gdp_website()
    
    if not items:
        print("❌ 没有找到任何内容，请检查网站结构是否发生变化")
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
    print(f"\n📋 RSS订阅链接: file://{filename}")
    print(f"   或者: https://your-domain.com/{filename}")

if __name__ == "__main__":
    main()
