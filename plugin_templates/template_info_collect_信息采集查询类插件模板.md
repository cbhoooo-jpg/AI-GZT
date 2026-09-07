---
template_id: info_collect
name: 信息采集查询类插件模板
scene: 适合网页信息采集、舆情监测、数据爬取、RPA自动化操作、公开信息聚合、多源数据检索等场景的插件
default_permission: network,write_file,read_file
default_config:
  - key: default_extract_mode
    label: 默认提取模式
    type: select
    default: "structured"
    options: [
      {"label": "结构化模式（正文+可操作入口）", "value": "structured"},
      {"label": "纯文本模式（仅正文）", "value": "pure_text"},
      {"label": "原始HTML模式（完整页面结构）", "value": "raw"}
    ]
    required: true
  - key: save_path
    label: 采集结果保存路径
    type: input
    default: "D:/AI仓库文件夹/搜索报告/"
    placeholder: 采集报告保存的本地目录
    required: false
  - key: request_timeout
    label: 请求超时时间（秒）
    type: input
    default: "60"
    placeholder: 单页面采集的最长等待时间
    required: true
  - key: collect_mode
    label: 默认采集模式
    type: select
    default: "browser"
    options: [
      {"label": "普通爬虫模式（速度快，适合静态页面）", "value": "normal"},
      {"label": "内置浏览器模式（兼容动态/登录页，支持网页操作）", "value": "browser"}
    ]
    required: true
  - key: default_result_count
    label: 默认采集结果条数
    type: input
    default: "10"
    placeholder: "最多采集的搜索结果条数"
    required: true
  - key: auto_save
    label: 自动保存采集结果
    type: switch
    default: true
    required: true
  - key: redundant_keywords
    label: 冗余内容过滤关键词 
    type: textarea
    default: "关于我们\n联系方式\n版权所有\n友情链接\n网站地图\n备案号\n免责声明\n广告\n登录\n注册\n评论\n分享\n收藏\n点赞\n下载APP\n关注公众号\n扫一扫\n返回顶部\n更多"
    placeholder: 每行一个关键词，包含这些关键词的行将被自动过滤
    required: false
default_params:
  - name: query
    description: 采集关键词/目标URL，支持关键词搜索或指定页面URL
    required: true
  - name: time_range
    description: 信息时间范围，支持1天/1周/1月/1年/不限
    required: false
  - name: extract_mode
    description: 提取模式，覆盖默认配置，支持structured/pure_text/raw
    required: false
---
### [FILE] main.py
```python
import os
import re
import json
import time
import requests
import chardet
from bs4 import BeautifulSoup
from datetime import datetime
from newspaper import Article

# 全局插件配置（自动注入）
plugin_config = {}
# 全局浏览器单例实例
browser_instance = None

def init(config: dict):
    """插件初始化方法，安装/启用/配置修改时自动调用"""
    global plugin_config
    plugin_config = config
    
    # 自动创建保存目录
    save_path = plugin_config.get("default_save_path", "./仓库文件夹/搜索报告").strip()
    os.makedirs(save_path, exist_ok=True)
    return True

def _get_redundant_keywords():
    """从配置中读取冗余关键词列表"""
    keywords_str = plugin_config.get("redundant_keywords", "")
    if not keywords_str:
        # 默认通用冗余关键词
        keywords_str = "关于我们\n联系方式\n版权所有\n友情链接\n网站地图\n备案号\n免责声明\n广告\n登录\n注册\n评论\n分享\n收藏\n点赞\n下载APP\n关注公众号\n扫一扫\n返回顶部\n更多"
    return [k.strip() for k in keywords_str.split("\n") if k.strip()]

def _generate_xpath(element, soup):
    """为DOM元素生成xpath选择器"""
    xpath = ""
    current = element
    while current and current.name != '[document]':
        parent = current.parent
        siblings = parent.find_all(current.name, recursive=False)
        idx = siblings.index(current) + 1 if len(siblings) > 1 else 0
        xpath = f"/{current.name}{f'[{idx}]' if idx else ''}" + xpath
        current = parent
    return xpath

def _filter_content(content):
    """过滤冗余内容和无效内容"""
    redundant_keywords = _get_redundant_keywords()
    filtered_lines = []
    for line in content.split("\n"):
        line = line.strip()
        if not line:
            continue
        # 跳过包含冗余关键词的行
        if any(keyword in line for keyword in redundant_keywords):
            continue
        filtered_lines.append(line)
    content = "\n".join(filtered_lines)
    return content
def _detect_encoding(response):
    """自动检测网页编码，解决GBK/UTF-8乱码问题"""
    # 1. 优先使用HTTP响应头中的charset
    content_type = response.headers.get("Content-Type", "").lower()
    if "charset=" in content_type:
        charset = content_type.split("charset=")[-1].split(";")[0].strip()
        try:
            response.encoding = charset
            return response.text
        except:
            pass
    
    # 2. 使用chardet自动检测编码
    raw_data = response.content
    detected = chardet.detect(raw_data)
    confidence = detected.get("confidence", 0)
    encoding = detected.get("encoding", "utf-8")
    
    # chardet置信度大于0.7才使用检测结果，否则默认utf-8
    if confidence > 0.7 and encoding:
        try:
            response.encoding = encoding
            return response.text
        except:
            pass
    
    # 3. 兜底使用utf-8
    response.encoding = "utf-8"
    return response.text


def _check_anti_crawl(content):
    """检测是否触发反爬虫安全验证页面"""
    anti_crawl_keywords = [
        "安全验证", "百度安全验证", "网络不给力", "请稍后重试",
        "验证码", "人机验证", "访问验证", "安全检查中",
        "请输入验证码", "滑动验证", "点击验证"
    ]
    
    # 检测页面内容是否过短且包含反爬关键词（正常页面不会只有这些词）
    if len(content) < 500:
        for keyword in anti_crawl_keywords:
            if keyword in content:
                return True, f"⚠️ 检测到反爬虫安全验证页面（触发关键词: {keyword}），建议更换信息源或稍后重试"
    
    return False, ""


def _fetch_url(url, proxies, timeout, headers=None):
    """统一的URL请求函数，自动处理编码检测和反爬虫检测"""
    if headers is None:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,zh-TW;q=0.8,zh-HK;q=0.7",
            "Referer": "https://www.baidu.com/",
            "Connection": "keep-alive",
            "Accept-Encoding": "gzip, deflate, br"
        }
    
    response = requests.get(url, proxies=proxies, timeout=timeout, headers=headers)
    response.raise_for_status()
    
    # 自动检测编码
    html_text = _detect_encoding(response)
    
    # 检测反爬虫验证页面
    is_anti_crawl, anti_crawl_msg = _check_anti_crawl(html_text)
    if is_anti_crawl:
        raise Exception(anti_crawl_msg)
    
    return html_text

def search_baidu(query, time_range, default_count, proxies):
    """百度搜索，获取结果列表"""
    baidu_url = "https://www.baidu.com/s"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Cookie": "BAIDUID=ABCDEF1234567890ABCDEF1234567890:FG=1; BIDUPSID=ABCDEF1234567890; PSTM=1717200000; BD_UPN=12314753; H_PS_PSSID=40245_40080_39669_40481_40448_40324_39936_40434_40284_40385_26350; BDORZ=B490B5EBF6F3CD402E515D22BCDA1598;"
    }

    # 时间范围转换为百度搜索的时间过滤参数
    now_ts = int(time.time())
    time_map = {
        "1天": 86400,
        "1周": 86400 * 7,
        "1月": 86400 * 30,
        "1年": 86400 * 365,
        "不限": 0
    }
    time_span = time_map.get(time_range, 86400 * 7)
    gpc = ""
    if time_span > 0:
        start_ts = now_ts - time_span
        gpc = f"stf={start_ts},{now_ts}|stftype=1"

    req_params = {
        "wd": query,
        "rn": default_count,
        "gpc": gpc,
        "ie": "utf-8",
        "tn": "baidu",
        "cl": 3
    }

    timeout = int(plugin_config.get("request_timeout", 30))
    response = requests.get(baidu_url, headers=headers, params=req_params, proxies=proxies, timeout=timeout)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    # 解析百度搜索结果（兼容新旧页面结构）
    search_results = []
    result_items = soup.select("div.result.c-container")
    if not result_items:
        result_items = soup.select("div.c-container.xpath-log")
    if not result_items:
        result_items = soup.select("div.tpl-seo-result")
    
    for item in result_items[:default_count]:
        title_tag = item.select_one("h3 a")
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        url = title_tag["href"]
        snippet_tag = item.select_one("span.content-right_8Zs40")
        if not snippet_tag:
            snippet_tag = item.select_one("div.c-abstract")
        if not snippet_tag:
            snippet_tag = item.select_one("p.c-line-clamp1")
        snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
        date_published = ""
        date_tag = item.select_one("span.c-color-gray2")
        if not date_tag:
            date_tag = item.select_one("span.c-time")
        if date_tag:
            date_published = date_tag.get_text(strip=True)
        
        skip_domains = ["wenku.baidu.com", "docin.com", "book118.com", "max.book118.com"]
        if any(domain in url for domain in skip_domains):
            continue
        
        search_results.append({
            "title": title,
            "url": url,
            "snippet": snippet,
            "datePublished": date_published
        })
    
    return search_results
def crawl_page_content(url, snippet, date_published, proxies):
    """爬取单个网页正文内容（统一使用requests库，线程安全无崩溃）"""
    content = snippet
    structured_content = {}
    soup = None
    
    try:
        timeout = int(plugin_config.get("request_timeout", 15))
        
        # 统一使用requests库爬取，彻底移除PySide6跨线程调用，避免工作台崩溃
        html_text = _fetch_url(url, proxies, timeout)
        soup = BeautifulSoup(html_text, "html.parser")
        
        # 优先用newspaper3k提取正文，准确率更高
        try:
            article = Article(url, language='zh')
            article.set_html(str(soup))
            article.parse()
            structured_content = {
                "title": article.title,
                "publish_time": article.publish_date.strftime("%Y-%m-%d %H:%M:%S") if article.publish_date else date_published,
                "author": article.authors,
                "content": article.text,
                "images": list(article.images),
                "links": list(article.links)
            }
            content = article.text
        except Exception as e:
            # newspaper提取失败兜底用原来的bs4方式
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            content = soup.get_text(strip=True, separator="\n")
            structured_content = {
                "title": "",
                "publish_time": date_published,
                "author": [],
                "content": content,
                "images": [],
                "links": []
            }
        
        # 提取可操作入口
        entries = extract_entries(soup)
        structured_content["entries"] = entries
        
        # 过长内容截断
        if len(content) > 5000:
            content = content[:5000] + "【内容过长已截断】"
        structured_content["content"] = content
        
    except Exception as e:
        content = f"⚠️ 网页内容爬取失败，仅显示摘要:{snippet}"
        structured_content = {
            "title": "",
            "publish_time": date_published,
            "author": [],
            "content": content,
            "images": [],
            "links": [],
            "entries": []
        }
    
    return content, structured_content

def extract_entries(soup):
    """提取可操作入口"""
    entries = []
    try:
        # 1. 提取所有真实HTTP链接（a标签）
        skip_domains = ["wenku.baidu.com", "docin.com", "book118.com", "max.book118.com"]
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith(("http://", "https://")) and not any(domain in href for domain in skip_domains):
                link_text = a.get_text(strip=True)[:20] or "网页链接"
                entries.append({
                    "name": link_text,
                    "url": href,
                    "type": "link",
                    "description": f"跳转到{link_text}页面"
                })
        
        # 2. 提取所有可点击按钮，生成虚拟操作链接
        button_selectors = ["button", "input[type='button']", "input[type='submit']", "div[role='button']", "a[role='button']"]
        for selector in button_selectors:
            for btn in soup.select(selector):
                btn_text = btn.get_text(strip=True)[:20] or btn.get("value", "").strip()[:20] or "操作按钮"
                xpath = _generate_xpath(btn, soup)
                if xpath:
                    entries.append({
                        "name": btn_text,
                        "url": f"action://click?selector=xpath:{xpath}",
                        "type": "action",
                        "description": f"点击「{btn_text}」按钮"
                    })
        
        # 3. 提取所有输入框，生成虚拟操作链接
        input_selectors = ["input[type='text']", "input[type='search']", "textarea", "input[type='password']", "input[type='email']"]
        for selector in input_selectors:
            for inp in soup.select(selector):
                placeholder = inp.get("placeholder", "").strip()[:20] or "输入框"
                name = inp.get("name", "").strip()
                xpath = _generate_xpath(inp, soup)
                if xpath:
                    entries.append({
                        "name": placeholder,
                        "url": f"action://input?selector=xpath:{xpath}&name={name}",
                        "type": "action",
                        "description": f"在「{placeholder}」中输入内容"
                    })
        
        # 去重entries，避免重复链接
        seen_urls = set()
        unique_entries = []
        for entry in entries:
            if entry["url"] not in seen_urls and len(entry["name"]) > 1:
                seen_urls.add(entry["url"])
                unique_entries.append(entry)
        entries = unique_entries[:20] # 最多返回20个操作入口，避免过多
    except Exception as e:
        # 元素提取失败不影响主流程
        entries = []
    
    return entries

def format_output(query, time_range, collected_data, extract_mode):
    """格式化输出内容"""
    output_content = f"# 「{query}」信息采集报告\n\n"
    output_content += f"📅 采集时间:{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    output_content += f"⏰ 时间范围:{time_range}\n"
    output_content += f"📊 采集条数:{len(collected_data)}条\n\n"
    output_content += "---\n\n"

    for idx, item in enumerate(collected_data, 1):
        output_content += f"## {idx}. {item['title']}\n"
        output_content += f"🔗 来源链接:[{item['url']}]({item['url']})\n"
        if item['date_published']:
            output_content += f"📅 发布时间:{item['date_published']}\n"
        # 按提取模式展示对应内容
        if extract_mode == "raw":
            # 原始HTML模式输出完整HTML，过长截断避免内容爆炸
            raw_html = item["structured_content"].get("raw_html", str(item.get("content", "")))
            output_content += f"📝 原始HTML内容（过长已截断，完整内容已存到结构化字段）:\nhtml\n{raw_html[:10000]}\n\n\n"
        else:
            output_content += f"📝 内容摘要:\n{item['content']}\n\n"
            # 结构化模式下展示可操作入口
            if extract_mode == "structured" and item.get("entries"):
                output_content += f"🔧 可操作入口（共{len(item['entries'])}个）:\n"
                for entry in item["entries"]:
                    output_content += f"- [{entry['name']}]({entry['url']}):{entry['description']}\n"
                output_content += "\n"
        output_content += "---\n\n"
    
    return output_content

def save_to_file(query, output_content, default_save_path, custom_save_path):
    """保存到本地文件"""
    save_result = ""
    auto_save = plugin_config.get("auto_save", "true")
    if str(auto_save).lower() == "true":
        # 1. 过滤query中的非法字符，生成安全文件名
        safe_query = re.sub(r'[\\/:*?"<>|\s]', '_', query)
        base_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{safe_query}"
        
        # 2. 强制以配置的默认路径为唯一根目录，杜绝路径乱跳
        root_save_path = default_save_path
        os.makedirs(root_save_path, exist_ok=True)
        
        # 3. 安全过滤custom_save_path:仅保留合法二级目录名，过滤所有路径穿越/非法字符
        safe_sub_dir = ""
        if custom_save_path:
            # 过滤路径穿越字符（../、绝对路径标识、路径分隔符）
            safe_sub_dir = re.sub(r'(\.\./|\.\\|[A-Za-z]:[/\\]|/|\\)', '', custom_save_path)
            # 过滤其他非法文件名字符
            safe_sub_dir = re.sub(r'[:*?"<>|\s]', '_', safe_sub_dir).strip()
        
        # 4. 拼接最终保存路径
        if safe_sub_dir:
            # 有合法二级目录，自动创建子目录归档
            final_save_path = os.path.join(root_save_path, safe_sub_dir)
            os.makedirs(final_save_path, exist_ok=True)
            file_path = os.path.join(final_save_path, f"{base_name}.md")
        else:
            # 无二级目录，直接保存到默认根目录
            file_path = os.path.join(root_save_path, f"{base_name}.md")
        
        # 固定保存为MD格式
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(output_content)
        
        save_result = f"\n✅ 采集结果已自动保存到:{os.path.abspath(file_path)}"
    
    return save_result

# 插件入口函数，固定格式
def run(params: dict):
    """插件主入口，按action参数分发到6种原子操作模式"""
    try:
        action = params.get("action", "search").strip().lower()
        
        # 按action分发到对应的操作函数
        if action == "search":
            return _action_search(params)
        elif action == "open":
            return _action_open(params)
        elif action == "click":
            return _action_click(params)
        elif action == "input":
            return _action_input(params)
        elif action == "extract":
            return _action_extract(params)
        elif action == "finish":
            return _action_finish(params)
        else:
            return f"❌ 不支持的操作类型: {action}，支持: search/open/click/input/extract/finish"
    
    except Exception as e:
        return f"❌ 操作执行失败:{str(e)}"

def _action_search(params):
    """搜索模式:百度搜索关键词，仅返回搜索结果列表（标题、URL、摘要），不爬取正文"""
    try:
        # 1. 配置校验（零密钥，直接使用，无任何必填配置）
        default_count = int(plugin_config.get("default_result_count", 10))
        proxies = None # 百度搜索国内网络直接访问，无需代理

        # 2. 入参提取
        query = params.get("query", "").strip()
        if not query:
            return "❌ 请指定要采集的信息主题/关键词"
        
        time_range = params.get("time_range", "1周").strip()

        # 3. 百度搜索
        search_results = search_baidu(query, time_range, default_count, proxies)
        
        if not search_results:
            return f"⚠️ 未采集到「{query}」相关的{time_range}内的信息，请尝试调整关键词或时间范围"

        # 4. 格式化输出搜索结果列表
        output_content = f"🔍 百度搜索「{query}」完成！共找到{len(search_results)}条{time_range}内的相关信息\n\n"
        output_content += "请分析以下搜索结果，选择最相关的链接使用 action=open 打开页面获取详细内容：\n\n"
        output_content += "---\n\n"

        for idx, item in enumerate(search_results, 1):
            output_content += f"## {idx}. {item['title']}\n"
            output_content += f"🔗 链接地址: {item['url']}\n"
            if item['datePublished']:
                output_content += f"📅 发布时间: {item['datePublished']}\n"
            output_content += f"📝 内容摘要: {item['snippet']}\n\n"
            output_content += "---\n\n"

        output_content += "【指令执行结果已经返回:请基于以上搜索结果，决定下一步要打开哪个链接（action=open）进行详细信息采集】"

        return output_content

    except Exception as e:
        return f"❌ 信息采集失败:{str(e)}"
def _parse_selector(selector):
    """解析选择器格式，支持 xpath:xxx 和 css:xxx 两种格式"""
    if selector.startswith("xpath:"):
        return "xpath", selector[6:]
    elif selector.startswith("css:"):
        return "css", selector[4:]
    else:
        # 默认当作css选择器处理
        return "css", selector


def _action_open(params):
    """打开页面模式:打开指定URL，获取页面内容和可操作入口"""
    try:
        url = params.get("query", "").strip()
        if not url:
            return "❌ 请指定要打开的页面URL"
        
        # 百度跳转链接解析:检测是否为百度搜索结果跳转链接，解析出真实URL
        if "baidu.com/link?url=" in url:
            try:
                timeout = int(plugin_config.get("request_timeout", 15))
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9,zh-TW;q=0.8,zh-HK;q=0.7",
                    "Referer": "https://www.baidu.com/",
                    "Connection": "keep-alive"
                }
                # 不跟随重定向，直接获取响应头中的真实URL
                response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=False)
                if response.status_code in (301, 302, 303, 307, 308):
                    real_url = response.headers.get("Location", "")
                    if real_url:
                        url = real_url
                else:
                    # 如果没有重定向，尝试从响应内容中提取真实URL
                    html_text = _detect_encoding(response)
                    soup = BeautifulSoup(html_text, "html.parser")
                    meta_refresh = soup.find("meta", attrs={"http-equiv": "refresh"})
                    if meta_refresh:
                        content_attr = meta_refresh.get("content", "")
                        if "url=" in content_attr:
                            real_url = content_attr.split("url=")[-1].strip()
                            if real_url:
                                url = real_url
            except Exception as e:
                # 解析失败不中断流程，继续使用原URL
                pass
        
        # 复用现有的爬虫逻辑打开页面并提取内容
        content, structured_content = crawl_page_content(url, "", "", None)
        
        # 格式化输出
        page_title = structured_content.get("title", url)
        output = f"📄 已打开页面: {page_title}\n"
        output += f"🔗 页面URL: {url}\n\n"
        output += f"📝 页面内容:\n{content}\n\n"
        
        # 输出可操作入口，供AI助手下一步操作使用
        entries = structured_content.get("entries", [])
        if entries:
            output += f"🔧 可操作入口（共{len(entries)}个，可使用action=click/input执行操作）:\n"
            for entry in entries:
                output += f"- [{entry['name']}]({entry['url']}):{entry['description']}\n"
        
        output += "\n\n【指令执行结果已经返回:请基于以上采集到的页面内容判断信息是否足够丰富:1.信息已经足够，请整理成文档并调用create_file工具保存到AI仓库文件夹的搜索报告文件夹中；2.信息量太少或为行情数据页，请根据搜索结果更换其他链接使用action=open重新采集】"
        return output
    
    except Exception as e:
        return f"❌ 打开页面失败:{str(e)}"


def _action_click(params):
    """点击元素模式:点击页面上的指定元素，获取新页面内容（通过信号槽桥接主线程执行，线程安全）"""
    try:
        selector = params.get("selector", "").strip()
        if not selector:
            return "❌ 请指定要点击的元素选择器（xpath或css）"
        
        # 解析选择器格式
        selector_type, selector_value = _parse_selector(selector)
        
        # 通过全局信号总线发送操作请求到主线程，避免子线程直接操作PySide6对象导致崩溃
        import queue
        import main
        result_queue = queue.Queue()
        request = {
            "action": "click",
            "params": {"selector": selector_value},
            "result_queue": result_queue
        }
        main.global_signal_bus.browser_operation_request.emit(request)
        
        # 阻塞等待主线程执行完毕，最多等30秒
        try:
            result = result_queue.get(timeout=30)
        except queue.Empty:
            return "❌ 点击操作超时，请稍后重试"
        
        if "error" in result:
            return f"❌ 点击操作失败: {result['error']}"
        
        click_result = result.get("result", "")
        if "success" not in str(click_result).lower():
            return f"❌ 点击操作失败: {click_result}"
        
        # 点击成功后，获取新页面内容
        # 通过全局信号总线发送获取HTML的请求
        result_queue2 = queue.Queue()
        request2 = {
            "action": "get_html",
            "params": {},
            "result_queue": result_queue2
        }
        main.global_signal_bus.browser_operation_request.emit(request2)
        
        try:
            result2 = result_queue2.get(timeout=30)
        except queue.Empty:
            return "❌ 获取新页面内容超时"
        
        if "error" in result2:
            return f"❌ 获取新页面内容失败: {result2['error']}"
        
        html = result2.get("result", "")
        if not html.strip():
            return "❌ 点击后获取新页面内容失败"
        
        # 解析新页面内容
        soup = BeautifulSoup(html, "html.parser")
        
        # 提取正文内容
        try:
            article = Article("", language='zh')
            article.set_html(str(soup))
            article.parse()
            content = article.text
            structured_content = {
                "title": article.title,
                "publish_time": "",
                "author": article.authors,
                "content": article.text,
                "images": list(article.images),
                "links": list(article.links)
            }
        except Exception:
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            content = soup.get_text(strip=True, separator="\n")
            structured_content = {
                "title": "",
                "publish_time": "",
                "author": [],
                "content": content,
                "images": [],
                "links": []
            }
        
        # 提取可操作入口
        entries = extract_entries(soup)
        structured_content["entries"] = entries
        
        # 过长内容截断
        if len(content) > 5000:
            content = content[:5000] + "【内容过长已截断】"
        structured_content["content"] = content
        
        output = f"✅ 已点击元素，当前页面已更新\n"
        output += f"📝 新页面内容:\n{content}\n\n"
        
        entries = structured_content.get("entries", [])
        if entries:
            output += f"🔧 可操作入口（共{len(entries)}个）:\n"
            for entry in entries:
                output += f"- [{entry['name']}]({entry['url']}):{entry['description']}\n"
        
        output += "\n\n【指令执行结果已经返回:请基于以上采集到的全部信息，根据用户需求进行下一步操作】"
        return output
    
    except Exception as e:
        return f"❌ 点击操作执行失败:{str(e)}"


def _action_input(params):
    """输入内容模式:在指定输入框中输入内容并触发提交（通过信号槽桥接主线程执行，线程安全）"""
    try:
        selector = params.get("selector", "").strip()
        value = params.get("value", "").strip()
        if not selector or not value:
            return "❌ 请指定输入框选择器(selector)和输入内容"
        
        # 解析选择器格式
        selector_type, selector_value = _parse_selector(selector)
        
        # 通过全局信号总线发送输入操作请求到主线程
        import queue
        import main
        result_queue = queue.Queue()
        request = {
            "action": "input",
            "params": {"selector": selector_value, "value": value},
            "result_queue": result_queue
        }
        main.global_signal_bus.browser_operation_request.emit(request)
        
        # 阻塞等待主线程执行完毕
        try:
            result = result_queue.get(timeout=30)
        except queue.Empty:
            return "❌ 输入操作超时，请稍后重试"
        
        if "error" in result:
            return f"❌ 输入操作失败: {result['error']}"
        
        input_result = result.get("result", "")
        if "success" not in str(input_result).lower():
            return f"❌ 输入操作失败: {input_result}"
        
        # 输入成功后，获取结果页面内容
        result_queue2 = queue.Queue()
        request2 = {
            "action": "get_html",
            "params": {},
            "result_queue": result_queue2
        }
        main.global_signal_bus.browser_operation_request.emit(request2)
        
        try:
            result2 = result_queue2.get(timeout=30)
        except queue.Empty:
            return "❌ 获取结果页面超时"
        
        if "error" in result2:
            return f"❌ 获取结果页面失败: {result2['error']}"
        
        html = result2.get("result", "")
        if not html.strip():
            return "❌ 输入后获取结果页面失败"
        
        # 解析结果页面内容
        soup = BeautifulSoup(html, "html.parser")
        
        try:
            article = Article("", language='zh')
            article.set_html(str(soup))
            article.parse()
            content = article.text
            structured_content = {
                "title": article.title,
                "publish_time": "",
                "author": article.authors,
                "content": article.text,
                "images": list(article.images),
                "links": list(article.links)
            }
        except Exception:
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            content = soup.get_text(strip=True, separator="\n")
            structured_content = {
                "title": "",
                "publish_time": "",
                "author": [],
                "content": content,
                "images": [],
                "links": []
            }
        
        entries = extract_entries(soup)
        structured_content["entries"] = entries
        
        if len(content) > 5000:
            content = content[:5000] + "【内容过长已截断】"
        structured_content["content"] = content
        
        output = f"✅ 已在输入框中输入「{value}」并提交\n"
        output += f"📝 结果页面内容:\n{content}\n\n"
        
        entries = structured_content.get("entries", [])
        if entries:
            output += f"🔧 可操作入口（共{len(entries)}个）:\n"
            for entry in entries:
                output += f"- [{entry['name']}]({entry['url']}):{entry['description']}\n"
        
        output += "\n\n【指令执行结果已经返回:请基于以上采集到的全部信息，根据用户需求进行下一步操作】"
        return output
    
    except Exception as e:
        return f"❌ 输入操作执行失败:{str(e)}"


def _action_extract(params):
    """提取信息模式:从当前页面提取指定关键词相关的信息（通过信号槽桥接主线程执行，线程安全）"""
    try:
        keyword = params.get("query", "").strip()
        
        # 通过全局信号总线发送提取操作请求到主线程
        import queue
        import main
        result_queue = queue.Queue()
        request = {
            "action": "extract",
            "params": {"query": keyword},
            "result_queue": result_queue
        }
        main.global_signal_bus.browser_operation_request.emit(request)
        
        # 阻塞等待主线程执行完毕
        try:
            result = result_queue.get(timeout=30)
        except queue.Empty:
            return "❌ 提取操作超时，请稍后重试"
        
        if "error" in result:
            return f"❌ 信息提取失败: {result['error']}"
        
        extracted_content = result.get("result", "")
        if not extracted_content.strip():
            return "❌ 获取当前页面文本内容失败"
        
        output = f"📋 已从当前页面提取信息"
        if keyword:
            output += f"（关键词: {keyword}）"
        output += f"\n\n📝 提取内容:\n{extracted_content}\n"
        output += "\n\n【指令执行结果已经返回:请基于以上提取到的内容判断信息是否足够丰富:1.信息已经足够，请整理成文档并调用create_file工具保存到AI仓库文件夹的搜索报告文件夹中；2.信息量太少或未找到相关内容，请根据搜索结果更换其他链接使用action=open重新采集】"
        return output
    
    except Exception as e:
        return f"❌ 信息提取失败:{str(e)}"


def _action_finish(params):
    """完成整理模式:提示AI助手整理信息并保存"""
    try:
        topic = params.get("query", "信息采集报告").strip()
        
        output = f"✅ 网页操作已完成\n"
        output += f"📌 采集主题: {topic}\n"
        output += f"📁 【强制要求】请立即调用 create_file 工具，将整理后的完整报告保存为Markdown文件。\n"
        output += f"   - 保存路径: D:/AI仓库文件夹/搜索报告/\n"
        output += f"   - 文件命名: 时间+采集主题，例如: 20260715_1113_最近一周黄金市场信息.md\n"
        output += f"   - 文件内容: 包含采集时间、信息来源、核心观点、详细分析等完整结构化报告\n"
        output += "\n\n【指令执行结果已经返回:请立即调用create_file工具整理信息并保存为Markdown文件】"
        return output
    
    except Exception as e:
        return f"❌ 完成操作失败:{str(e)}"
```
### [FILE] plugin.json
```json
{
  "plugin_id": "{{plugin_id}}",
  "name": "{{plugin_name}}",
  "description": "{{description}}",
  "version": "{{version}}",
  "author": "{{author}}",
  "trigger_keyword": "{{trigger_keyword}}",
  "entry": "main.py",
  "permissions": [
    "network",
    "write_file",
    "read_file"
  ],
  "enabled": true,
  "config": [
    {
      "key": "default_extract_mode",
      "label": "默认提取模式",
      "type": "select",
      "default": "structured",
      "options": [
        {"label": "结构化模式（正文+可操作入口）", "value": "structured"},
        {"label": "纯文本模式（仅正文）", "value": "pure_text"},
        {"label": "原始HTML模式（完整页面结构）", "value": "raw"}
      ],
      "required": true
    },
    {
      "key": "default_save_path",
      "label": "采集结果保存路径",
      "type": "input",
      "default": "D:/AI仓库文件夹/搜索报告/",
      "placeholder": "采集报告保存的本地目录",
      "required": false
    },
    {
      "key": "request_timeout",
      "label": "请求超时时间（秒）",
      "type": "input",
      "default": "60",
      "placeholder": "单页面采集的最长等待时间",
      "required": true
    },
    {
      "key": "default_result_count",
      "label": "默认采集条数",
      "type": "input",
      "default": "10",
      "placeholder": "每次采集返回的最大结果数量",
      "required": true
    },
    {
      "key": "auto_save",
      "label": "自动保存到本地",
      "type": "select",
      "default": "true",
      "options": [
        {"label": "是", "value": "true"},
        {"label": "否", "value": "false"}
      ],
      "required": false
    },
    {
      "key": "collect_mode",
      "label": "采集模式",
      "type": "select",
      "default": "browser",
      "options": [
        {"label": "普通爬虫模式（速度快，兼容性一般）", "value": "normal"},
        {"label": "浏览器引擎模式（速度慢，兼容性强，支持动态页面）", "value": "browser"}
      ],
      "required": true
    },
    {
      "key": "redundant_keywords",
      "label": "冗余内容过滤关键词",
      "type": "textarea",
      "default": "关于我们\n联系方式\n版权所有\n友情链接\n网站地图\n备案号\n免责声明\n广告\n登录\n注册\n评论\n分享\n收藏\n点赞\n下载APP\n关注公众号\n扫一扫\n返回顶部\n更多",
      "placeholder": "每行一个关键词，包含这些关键词的行将被自动过滤",
      "required": false
    }
  ],
  "parameters": [
    {
      "name": "query",
      "description": "采集关键词/目标URL，支持关键词搜索或指定页面URL",
      "required": true
    },
    {
      "name": "time_range",
      "description": "信息时间范围，支持1天/1周/1月/1年/不限",
      "required": false
    },
    {
      "name": "extract_mode",
      "description": "提取模式，覆盖默认配置，支持pure_text/structured/raw",
      "required": false
    },
    {
      "name": "save_path",
      "description": "自定义保存子目录名（仅目录名，非完整路径）",
      "required": false
    },
    {
      "name": "action",
      "description": "操作类型:search(搜索)/open(打开页面)/click(点击元素)/input(输入内容)/extract(提取信息)/finish(完成整理)",
      "required": false
    },
    {
      "name": "selector",
      "description": "操作目标元素的选择器，用于click/input操作，格式: xpath:xxx 或 css:xxx",
      "required": false
    },
    {
      "name": "value",
      "description": "输入内容，用于input操作",
      "required": false
    },
    {{extra_parameters}}
  ]
}
```
### [FILE] README.md
```markdown
# {{plugin_name}}
## 插件说明
{{description}}

## 版本信息
- 版本:{{version}}
- 作者:{{author}}
- 触发关键词:{{trigger_keyword}}

## 配置说明
| 配置项 | 说明 | 类型 | 默认值 | 必填 |
| --- | --- | --- | --- | --- |
| default_extract_mode | 默认提取模式 | select | structured | 是 |
| default_save_path | 采集结果保存路径 | input | D:/AI仓库文件夹/搜索报告/ | 否 |
| request_timeout | 请求超时时间（秒） | input | 30 | 是 |
| default_result_count | 默认采集条数 | input | 10 | 是 |
| auto_save | 自动保存到本地 | select | true | 否 |
| collect_mode | 采集模式 | select | browser | 是 |
| redundant_keywords | 冗余内容过滤关键词 | textarea | 关于我们\n联系方式\n版权所有... | 否 |

### 配置项详细说明

#### default_extract_mode（默认提取模式）
| 选项 | 值 | 说明 |
|------|------|------|
| 结构化模式（正文+可操作入口） | structured | 返回正文+标准化可操作入口（HTTP/action://链接），适合AI二次操作 |
| 纯文本模式（仅正文） | pure_text | 仅返回纯净正文内容，自动过滤冗余信息，适合内容分析 |
| 原始HTML模式（完整页面结构） | raw | 返回完整原始HTML，完整结构保留，适合特殊站点自定义解析 |

#### collect_mode（采集模式）
| 选项 | 值 | 说明 |
|------|------|------|
| 普通爬虫模式 | normal | 速度快，兼容性一般，适合静态页面 |
| 浏览器引擎模式 | browser | 速度慢，兼容性强，支持动态页面渲染 |

#### auto_save（自动保存）
| 选项 | 值 | 说明 |
|------|------|------|
| 是 | true | 采集完成后自动保存为Markdown文件到配置的保存路径 |
| 否 | false | 仅返回采集结果，不保存文件 |

## 参数说明
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| query | string | 是 | 采集关键词/目标URL，支持关键词搜索或指定页面URL |
| time_range | string | 否 | 信息时间范围，支持1天/1周/1月/1年/不限，默认1周 |
| extract_mode | string | 否 | 提取模式，覆盖默认配置，支持pure_text/structured/raw |
| save_path | string | 否 | 自定义保存子目录名（仅目录名，非完整路径） |
| action | string | 否 | 操作类型:search/open/click/input/extract/finish，默认search |
| selector | string | 否 | 操作目标元素的选择器，用于click/input操作，格式: xpath:xxx 或 css:xxx |
| value | string | 否 | 输入内容，用于input操作 |
---

## 🎯 操作模式说明

本插件支持6种原子操作模式，通过 `action` 参数指定，支持多轮次组合操作完成复杂任务。

### 1. 搜索模式（search）
**功能**:百度搜索关键词，仅返回搜索结果列表（标题、URL、摘要），不爬取正文。
**适用场景**:信息采集的第一步，获取相关链接列表供后续操作。
**参数**:`query`（关键词）、`time_range`（时间范围，可选）

### 2. 打开页面模式（open）
**功能**:打开指定URL，获取页面内容和可操作入口。
**适用场景**:基于搜索结果或指定URL，获取页面详细内容。
**参数**:`query`（URL地址）
**特殊能力**:自动解析百度跳转链接获取真实URL。

### 3. 点击元素模式（click）
**功能**:点击页面上的指定元素，获取新页面内容。
**适用场景**:翻页、展开详情、切换Tab标签等交互操作。
**参数**:`selector`（元素选择器，支持xpath/css格式）

### 4. 输入内容模式（input）
**功能**:在指定输入框中输入内容并触发提交，获取结果页面。
**适用场景**:站内搜索、表单提交、登录操作等。
**参数**:`selector`（输入框选择器）、`value`（输入内容）

### 5. 提取信息模式（extract）
**功能**:从当前页面提取指定关键词相关的信息。
**适用场景**:精准提取页面中的特定内容，如价格、日期、数据指标等。
**参数**:`query`（提取关键词，可选）

### 6. 完成整理模式（finish）
**功能**:提示AI助手整理信息并保存为Markdown文件。
**适用场景**:信息采集完成后的最后一步，触发报告整理和保存。
**参数**:`query`（采集主题，用于文件命名）


## 自定义修改指南
### 1. 采集源更换说明
#### 搜索引擎更换
- 默认使用百度新闻搜索，可替换为必应/谷歌/行业垂直搜索引擎
- 修改核心逻辑中关键词搜索的请求地址、解析规则即可
#### 定向站点采集
- 直接传入目标站点URL即可采集，特殊站点可自定义XPath/CSS选择器提取内容
- 需登录的站点可添加Cookie配置项，请求时携带Cookie即可
### 2. 参数调整说明
#### 新增/删除参数
- 先修改`plugin.json`中`parameters`数组，添加/删除对应参数配置
- 同步修改`main.py`中参数校验、参数提取部分代码
- 同步更新本README.md中使用说明和示例部分
#### 参数规则修改
- 如调整采集条数上限、提取内容长度限制、时间范围选项等，需同步修改3处:
  1. `main.py`中参数校验适配逻辑
  2. `plugin.json`中对应参数的description说明
  3. 本README.md中配置/参数说明文档
### 3. 核心业务逻辑修改说明
- 所有自定义业务逻辑请写在`{{core_business_logic}}`标记的核心逻辑区间内
- 通用配置校验、页面预处理、结果保存逻辑无需修改，已对齐全局系统规范
- 如需添加反爬规避、代理池、验证码识别等能力，可在核心逻辑中添加对应代码
---
## 常见问题&注意事项
1. **采集失败/返回空内容**:请检查目标站点是否有反爬限制，可适当调大超时时间或添加代理配置
2. **内容提取不准确**:特殊站点可使用raw模式获取原始HTML，自定义解析规则提取内容
3. **可操作入口识别不全**:可修改核心逻辑中入口提取的CSS选择器，适配目标站点结构
4. **登录态站点采集**:可新增Cookie配置项，请求时携带登录态Cookie即可绕过登录验证
5. **参数兼容注意**:所有模型专属参数请添加到`plugin.json`的`extra_parameters`占位符位置，不要修改通用默认参数结构


## 🔌 插件再开发说明
### 1. plugin.json 完整格式规范
#### 顶层必填字段
| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| plugin_id | string | 是 | 插件全局唯一ID，仅支持小写字母、数字、下划线，不能和其他插件重复 |
| name | string | 是 | 插件显示名称，会展示在插件市场和配置页 |
| description | string | 是 | 插件功能描述，会自动注入AI上下文帮助识别触发场景 |
| version | string | 是 | 版本号，遵循semver规范（x.y.z），例如1.0.0 |
| author | string | 是 | 插件作者信息 |
| trigger_keyword | string/array | 是 | 触发关键词，支持字符串或字符串数组，AI会匹配用户消息中的关键词自动调用插件 |
| entry | string | 是 | 插件入口文件，固定为main.py |
| permissions | array | 是 | 插件所需权限列表，可选值:`network`（网络访问）、`file_read`（文件读取）、`file_write`（文件写入），信息采集类插件默认需要三个权限 |
| enabled | boolean | 是 | 插件默认启用状态，固定为true |
| config | array | 否 | 插件配置项列表，会渲染到前端配置页面，用户可修改 |
| parameters | array | 是 | 插件调用参数列表，AI会根据这些说明自动生成调用参数 |
| dependencies | array | 否 | 插件依赖的Python包列表，安装插件时会自动安装 |

#### config配置项字段规范
| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| key | string | 是 | 配置项唯一键，代码中通过`plugin_config.get(key)`读取 |
| label | string | 是 | 配置项显示名称，展示在前端页面 |
| type | string | 是 | 配置项类型，支持:`input`（输入框）、`password`（密码框）、`select`（下拉选择）、`switch`（开关）、`textarea`（多行文本）、`button`（按钮） |
| default | any | 否 | 配置项默认值 |
| placeholder | string | 否 | 输入框占位提示文字 |
| required | boolean | 否 | 是否必填，默认false |
| options | array | 条件必填 | 当type为select时必填，下拉选项列表，格式为`[{"label":"显示名","value":"值"}]` |
| action | string | 条件必填 | 当type为button时必填，按钮动作类型，目前支持`openUrl` |
| url | string | 条件必填 | 当action为openUrl时必填，按钮点击后跳转的地址 |

#### parameters参数项字段规范
| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| name | string | 是 | 参数名，代码中通过`params.get(name)`读取，信息采集类插件固定包含action/query/selector/value等通用参数 |
| type | string | 否 | 参数类型，支持string/integer/boolean/array/object，默认string |
| required | boolean | 是 | 是否必填，AI调用时会自动校验必填参数 |
| description | string | 是 | 参数说明，会注入AI上下文，帮助AI理解参数含义和生成规则，特别是action参数的可选值必须写清楚 |
| default | any | 否 | 参数默认值 |

---
### 2. 功能变更配置更新 Checklist
#### ✅ 新增采集/操作功能时
1.  在`main.py`中新增对应的`_action_xxx`处理函数，实现对应业务逻辑
2.  在`run`方法的action分发分支中添加新action的路由
3.  在`plugin.json`的`parameters`中更新action参数的description，补充新的操作类型说明
4.  如果需要新增参数，在`parameters`数组中添加对应参数配置
5.  如果需要用户配置全局参数（如代理、Cookie等），在`config`数组中添加对应的配置项
6.  如果新增了依赖包，同步更新`dependencies`字段和`requirements.txt`
7.  更新本README.md中的操作模式说明、参数说明、使用示例部分
8.  如果新增了触发场景，补充`trigger_keyword`关键词

#### ✅ 删除功能时
1.  从`run`方法中移除对应action的路由分支
2.  删除`main.py`中对应的`_action_xxx`处理函数
3.  更新`plugin.json`中action参数的description，移除已删除的操作类型
4.  清理不再使用的参数、配置项
5.  检查`requirements.txt`，移除不再使用的依赖包
6.  更新README.md，删除对应功能的说明和示例

#### ✅ 修改现有功能时
1.  如果修改了action参数规则、支持的操作类型，同步更新`plugin.json`中action参数的description
2.  同步修改`main.py`中对应处理函数的逻辑
3.  更新README.md中的对应说明
4.  升级`version`版本号（小修改升补丁版本，功能新增升次版本，不兼容修改升主版本）

---
### 3. 上下文自动注入说明
系统启动时会自动读取所有插件的`plugin.json`信息，注入到AI上下文中，AI会自动识别:
1.  插件的`name`和`description`:理解插件功能和适用场景
2.  `trigger_keyword`:匹配用户消息中的触发词，自动决定是否调用插件
3.  `parameters`列表:理解每个参数的含义、类型、是否必填，特别是action支持的6种操作模式，会自动规划多轮采集流程
4.  `config`配置项:用户在前端配置的所有值会自动注入到`plugin_config`全局变量中，插件代码可直接读取，无需额外处理

**注意**:修改`plugin.json`后需要重启插件/重启程序才能让新的配置信息生效，注入到AI上下文。信息采集类插件支持多轮次调用，AI会自动根据上一轮返回的可操作入口，生成下一轮的click/input操作参数。

---
### 4. 配置校验规则&常见错误
1.  `plugin_id`必须全局唯一，不能包含中文、特殊字符，只能用小写字母、数字、下划线，否则插件无法加载
2.  `version`必须符合x.y.z的数字格式，不能带v前缀等其他字符
3.  `permissions`必须根据插件实际需要申请，信息采集类插件必须申请network权限，浏览器操作类功能需要确保主线程信号总线可用
4.  所有`required: true`的配置项，必须在`init`方法中做校验，缺失时给出友好提示
5.  `parameters`中的action参数说明必须清晰列出所有支持的操作类型，AI完全依赖description理解多轮操作流程，描述模糊会导致流程中断
6.  新增的自定义参数必须放在`{{extra_parameters}}`占位符之前，不要修改默认的通用参数结构，避免后续模板升级冲突
7.  浏览器操作（click/input）必须通过信号总线桥接到主线程执行，禁止在子线程中直接操作PySide6对象，否则会导致工作台崩溃
## 📝 使用示例

### 示例1:完整的信息采集流程（多轮次操作）

**第1轮:搜索关键词**
🔹 非执行示例，仅作参考
```
action: search
query: 最近一周黄金期货最新动态
time_range: 1周
```

**第2轮:打开搜索结果中的链接**
🔹 非执行示例，仅作参考
```
action: open
query: https://finance.sina.com.cn/...
```

**第3轮:提取特定信息**
🔹 非执行示例，仅作参考
```
action: extract
query: 价格
```

**第4轮:完成整理并保存**
🔹 非执行示例，仅作参考
```
action: finish
query: 最近一周黄金期货最新动态
```

### 示例2:直接打开指定URL采集内容

🔹 非执行示例，仅作参考
```
action: open
query: https://news.baidu.com/
```

### 示例3:站内搜索并提取内容

**第1轮:在输入框中输入搜索词**
🔹 非执行示例，仅作参考
```
action: input
selector: xpath:/html/body/div[1]/div[2]/div[1]/div[1]/div/form/input[1]
value: 人工智能最新进展
```

**第2轮:提取搜索结果**
🔹 非执行示例，仅作参考
```
action: extract
query: 人工智能
```

**第3轮:完成整理并保存**
🔹 非执行示例，仅作参考
```
action: finish
query: 人工智能最新进展
```
```
### [FILE] requirements.txt
```
requests>=2.31.0
newspaper3k>=0.2.8
lxml>=4.9.3
beautifulsoup4>=4.12.2
chardet>=5.2.0
{{extra_dependencies}}
```