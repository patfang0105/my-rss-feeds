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
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        items = []
        
        # 查找所有条目
        for element in soup.select(item_selector):
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

def main():
    """主函数"""
    if len(sys.argv) < 4:
        print("用法: python rss_generator.py <网站URL> <条目选择器> <标题选择器> [链接选择器] [描述选择器] [时间选择器]")
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
