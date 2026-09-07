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
        output += f"   - 保存路径: 仓库目录下的「搜索报告」文件夹（仓库路径可在系统设置中查看/修改）\n"
        output += f"   - 文件命名: 时间+采集主题，例如: 20260715_1113_最近一周黄金市场信息.md\n"
        output += f"   - 文件内容: 包含采集时间、信息来源、核心观点、详细分析等完整结构化报告\n"
        output += "\n\n【指令执行结果已经返回:请立即调用create_file工具整理信息并保存为Markdown文件】"
        return output
    
    except Exception as e:
        return f"❌ 完成操作失败:{str(e)}"