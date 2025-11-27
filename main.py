import asyncio
import datetime
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
from astrbot.core.message.message_event_result import MessageChain
import json
import requests

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
    announcement_time = datetime.datetime.fromtimestamp(latest_ann["announcementTime"] / 1000).strftime("%Y-%m-%d")
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
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.groups = getattr(self.config, "groups", []) # 接收推送的群组列表
        self.push_time = getattr(self.config, "push_time", "08:00") # 定时推送时间
        self.json_url = getattr(self.config, "json_url", "https://www.cninfo.com.cn/new/fulltextSearch/full?searchkey=%E8%82%A1%E4%B8%9C%E5%9B%9E%E9%A6%88&sdate=&edate=&isfulltext=false&sortName=pubdate&sortType=desc&pageNum=1&pageSize=20&type=")  # 推送数据源 JSON 地址
        # 创建定时任务
        self._scheduler_task = asyncio.create_task(self._daily_scheduler())

    # 注册指令的装饰器。指令名为 sheep。注册成功后，发送 `/sheep` 就会触发这个指令
    @filter.command("sheep")
    async def get_sheep(self, event: AstrMessageEvent):
        '''主动获取股东回馈公告的指令''' 
        logger.info("触发sheep指令!")
        DEFAULT_JSON_URL = self.json_url
        sheep_msg = extract_latest_announcement_from_url(DEFAULT_JSON_URL)
        if sheep_msg:
            yield event.plain_result(sheep_msg)
    
    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("sheep_status")
    async def check_status(self, event: AstrMessageEvent):
        """查看定时任务状态（仅管理员）"""
        sleep_time = self._calculate_sleep_time()
        hours = int(sleep_time // 3600)
        minutes = int((sleep_time % 3600) // 60)
        yield event.plain_result(
            f"股东回馈插件运行中\n"
            f"推送时间：{self.push_time}\n"
            f"目标群组数量：{len(self.groups)}\n"
            f"距离下次推送：{hours}小时{minutes}分钟"
        )

    def _calculate_sleep_time(self) -> float:
        """计算距离下次推送的秒数"""
        now = datetime.datetime.now()
        # 解析配置的推送时间
        hour, minute = map(int, self.push_time.split(":"))
        next_push = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        # 如果当前时间已过今日推送时间，则顺延至明日
        if next_push <= now:
            next_push += datetime.timedelta(days=1)
        return (next_push - now).total_seconds()
    
    async def _send_to_groups(self):
        """向所有目标群组发送消息"""
        if not self.groups:
            logger.warning("未配置推送群组，跳过推送")
            return

        try:
            # 先获取最新公告时间并校验是否为今天
            sheep_time = extract_latest_announcement_from_url(self.json_url, return_format="only_time")
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            
            if sheep_time != today:
                logger.info(f"最新股东回馈公告时间({sheep_time})非今日({today})，跳过推送")
                return

            # 校验通过，获取完整消息并推送
            sheep_msg = extract_latest_announcement_from_url(self.json_url)
            # 遍历所有群组发送
            for group in self.groups:
                await self.context.send_message(group, MessageChain().message(sheep_msg))
                await asyncio.sleep(2)  # 避免频率过高
            logger.info(f"已向 {len(self.groups)} 个群组推送股东回馈消息")
        except Exception as e:
            logger.error(f"推送失败：{str(e)}")
            raise

    async def _daily_scheduler(self):
        """定时任务主循环"""
        while True:
            try:
                # 计算休眠时间并等待
                sleep_time = self._calculate_sleep_time()
                logger.info(f"股东回馈定时任务：下次推送将在 {sleep_time/3600:.2f} 小时后")
                await asyncio.sleep(sleep_time)
                
                # 执行推送
                await self._send_to_groups()
                
                # 避免重复推送（等待1分钟后再进入下一次循环）
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"定时任务出错：{str(e)}")
                # 出错后等待5分钟再重试
                await asyncio.sleep(300)

    async def terminate(self):
        """插件卸载时取消定时任务"""
        if hasattr(self, "_scheduler_task"):
            self._scheduler_task.cancel()
        logger.info("股东回馈插件：定时任务已停止")
