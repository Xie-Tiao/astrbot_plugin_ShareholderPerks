from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger # 使用 astrbot 提供的 logger 接口
import json
import requests
from datetime import datetime

def extract_latest_announcement_from_url(json_url, return_format="full"):
    """核心提取函数（内部使用，无需外部传参）"""
    # 1. 发送请求获取 JSON 数据
    try:
        response = requests.get(json_url, timeout=10)
        response.raise_for_status()
        json_data = response.json()
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"获取 JSON 数据失败：{e}")
    except json.JSONDecodeError:
        raise ValueError("获取的内容不是有效的 JSON 格式")

    # 2. 提取公告列表
    if isinstance(json_data, dict) and "announcements" in json_data and isinstance(json_data["announcements"], list):
        announcement_list = json_data["announcements"]
    else:
        raise ValueError(f"JSON 数据格式不符合预期，未找到 'announcements' 列表。实际结构: {json.dumps(json_data, indent=2)[:200]}...")

    if not announcement_list:
        raise ValueError("获取到的公告列表为空")

    # 3. 筛选有效公告
    valid_announcements = []
    required_fields = ["secCode", "announcementTitle", "orgId", "announcementId", "announcementTime"]
    for item in announcement_list:
        if all(field in item and item[field] is not None for field in required_fields):
            valid_announcements.append(item)

    if not valid_announcements:
        raise ValueError("无有效公告数据（缺少关键字段）")

    # 4. 取最新公告
    latest_ann = max(valid_announcements, key=lambda x: x["announcementTime"])

    # 5. 清理标题和拼接 PDF 链接
    clean_title = latest_ann["announcementTitle"].replace("\u003Cem\u003E", "").replace("\u003C/em\u003E", "")
    announcement_time = datetime.fromtimestamp(latest_ann["announcementTime"] / 1000).strftime("%Y-%m-%d")
    pdf_url = (
        f"https://www.cninfo.com.cn/new/disclosure/detail"
        f"?orgId={latest_ann['orgId']}"
        f"&announcementId={latest_ann['announcementId']}"
        f"&announcementTime={announcement_time}"
    )

    # 5. 根据返回格式返回结果
    if return_format == "only_time":
        return announcement_time  # 仅返回时间字符串

    # 整理结果
    return (f"最新股东回馈消息：\n"
            f"公告时间：{announcement_time}\n"
            f"股票代码：{latest_ann['secCode']}\n"
            f"公告标题：{clean_title}\n"
            f"公告链接(在PC端打开)：{pdf_url}")

@register("astrbot_plugin_ShareholderPerks", "XieTiao", "一个简单的自动提醒股东薅羊毛插件", "1.0.0", "https://github.com/Xie-Tiao/astrbot_plugin_ShareholderPerks")
class XTSheepPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    # 注册指令的装饰器。指令名为 sheep。注册成功后，发送 `/sheep` 就会触发这个指令
    @filter.command("sheep")
    async def get_sheep(self, event: AstrMessageEvent):
        '''主动获取股东回馈公告的指令''' 
        logger.info("触发sheep指令!")
        DEFAULT_JSON_URL = "https://www.cninfo.com.cn/new/fulltextSearch/full?searchkey=%E8%82%A1%E4%B8%9C%E5%9B%9E%E9%A6%88&sdate=&edate=&isfulltext=false&sortName=pubdate&sortType=desc&pageNum=1&pageSize=20&type="
        sheep_time = extract_latest_announcement_from_url(DEFAULT_JSON_URL, return_format="only_time")
        logger.info(f"获取到的最新股东回馈公告时间为: {sheep_time}")
        sheep_msg = extract_latest_announcement_from_url(DEFAULT_JSON_URL)
        if sheep_msg:
            yield event.plain_result(sheep_msg)
