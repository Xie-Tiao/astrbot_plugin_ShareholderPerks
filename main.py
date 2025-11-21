import json
import requests
import asyncio
import datetime
from typing import List
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

# 全局变量，用于存储上一次发送的公告ID，防止重复发送
LAST_ANNOUNCEMENT_ID = None

def extract_latest_announcement():
    """
    从指定URL提取最新公告信息。
    :return: 一个包含公告详情的字典，如果失败则返回None。
    """
    JSON_URL = "https://www.cninfo.com.cn/new/fulltextSearch/full?searchkey=%E8%82%A1%E4%B8%9C%E5%9B%9E%E9%A6%88&sdate=&edate=&isfulltext=false&sortName=pubdate&sortType=desc&pageNum=1&pageSize=20&type="
    
    try:
        response = requests.get(JSON_URL, timeout=15)
        response.raise_for_status()
        json_data = response.json()
        
        if not isinstance(json_data, dict) or "announcements" not in json_data or not isinstance(json_data["announcements"], list):
            logger.error(f"获取的JSON数据格式不正确，无法找到'announcements'列表。")
            return None
        
        announcement_list = json_data["announcements"]
        if not announcement_list:
            logger.warning("公告列表为空。")
            return None
        
        # 筛选出包含所有必要字段的公告
        required_fields = ["secCode", "announcementTitle", "orgId", "announcementId", "announcementTime"]
        valid_announcements = [ann for ann in announcement_list if all(field in ann and ann[field] is not None for field in required_fields)]
        
        if not valid_announcements:
            logger.warning("未找到有效字段的公告。")
            return None
        
        # 获取最新的公告
        latest_ann = max(valid_announcements, key=lambda x: x["announcementTime"])
        
        # 清理标题中的HTML标签
        clean_title = latest_ann["announcementTitle"].replace("\u003Cem\u003E", "").replace("\u003C/em\u003E", "")
        
        # 格式化时间
        announcement_datetime = datetime.datetime.fromtimestamp(latest_ann["announcementTime"] / 1000)
        announcement_date_str = announcement_datetime.strftime("%Y-%m-%d")
        
        # 拼接PDF链接
        pdf_url = (
            f"https://www.cninfo.com.cn/new/disclosure/detail"
            f"?orgId={latest_ann['orgId']}"
            f"&announcementId={latest_ann['announcementId']}"
            f"&announcementTime={announcement_date_str}"
        )
        
        return {
            "secCode": latest_ann["secCode"],
            "title": clean_title,
            "pdf_url": pdf_url,
            "announcementId": latest_ann["announcementId"],
            "announcementDate": announcement_date_str,
        }
        
    except requests.exceptions.RequestException as e:
        logger.error(f"网络请求失败: {e}")
        return None
    except Exception as e:
        logger.error(f"处理公告数据时发生未知错误: {e}", exc_info=True)
        return None

@register("shareholder_feedback_monitor", "XieTiao", "股东回馈公告监控插件", "1.0.0")
class ShareholderFeedbackMonitor(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.scheduled_task = None
        self.notify_group_id = None  # 用于存储接收通知的群组ID

    async def on_load(self):
        """插件加载时执行"""
        logger.info("股东回馈公告监控插件已加载，准备启动定时任务。")
        self.scheduled_task = asyncio.create_task(self.schedule_daily_check())

    async def on_unload(self):
        """插件卸载时执行"""
        logger.info("股东回馈公告监控插件即将卸载，正在取消定时任务。")
        if self.scheduled_task:
            self.scheduled_task.cancel()
            try:
                await self.scheduled_task
            except asyncio.CancelledError:
                logger.info("定时任务已成功取消。")

    def get_next_run_time(self, now: datetime.datetime) -> datetime.datetime:
        """计算下一次12:00的运行时间"""
        next_run = now.replace(hour=12, minute=0, second=0, microsecond=0)
        if now >= next_run:
            next_run += datetime.timedelta(days=1)
        return next_run

    async def schedule_daily_check(self):
        """定时任务主循环"""
        while True:
            now = datetime.datetime.now()
            next_run_time = self.get_next_run_time(now)
            
            wait_seconds = (next_run_time - now).total_seconds()
            logger.info(f"下一次公告检查将在 {next_run_time.strftime('%Y-%m-%d %H:%M:%S')} 执行，等待 {wait_seconds:.2f} 秒。")
            
            try:
                await asyncio.sleep(wait_seconds)
            except asyncio.CancelledError:
                break

            logger.info("开始执行每日公告检查...")
            await self._perform_check_and_notify()

    async def _perform_check_and_notify(self):
        """执行检查并向指定群组发送通知"""
        global LAST_ANNOUNCEMENT_ID
        
        if not self.notify_group_id:
            logger.warning("通知群组ID尚未设置，跳过本次通知。请管理员使用 /set_shareholder_group 指令设置。")
            return

        latest_ann = extract_latest_announcement()
        
        if not latest_ann:
            message = "今日股东回馈消息无更新（获取公告失败）。"
            logger.warning(message)
            # 使用 bot.say 向指定群组发送消息
            await self.bot.say(self.notify_group_id, message)
            return

        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        if latest_ann["announcementDate"] != today_str:
            logger.info(f"今日股东回馈消息无更新。最新公告日期为 {latest_ann['announcementDate']}。")
            await self.bot.say(self.notify_group_id, "今日股东回馈消息无更新。")
            return

        if latest_ann["announcementId"] == LAST_ANNOUNCEMENT_ID:
            logger.info(f"公告 {latest_ann['announcementId']} 已发送过，本次跳过。")
            return

        # 准备并发送新公告
        message = (
            f"📢 **最新股东回馈公告** 📢\n\n"
            f"**股票代码:** {latest_ann['secCode']}\n"
            f"**公告标题:** {latest_ann['title']}\n"
            f"**发布时间:** {latest_ann['announcementDate']}\n"
            f"**查看链接:** [点击查看]({latest_ann['pdf_url']})"
        )
        logger.info(f"发现新公告，准备发送给群组 {self.notify_group_id}。")
        await self.bot.say(self.notify_group_id, message)
        
        LAST_ANNOUNCEMENT_ID = latest_ann["announcementId"]

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("set_shareholder_group")
    async def handle_set_shareholder_group(self, event: AstrMessageEvent):
        """[管理员命令] 设置接收通知的群组ID。用法: /set_shareholder_group [group_id]"""
        # 直接将当前所在的群组ID设为通知群组，无需手动输入ID
        group_id = event.group_id
        if not group_id:
            yield event.plain_result("❌ 此命令必须在群组中使用。")
            return

        self.notify_group_id = group_id
        logger.info(f"管理员 {event.sender_id} 已将通知群组设置为: {group_id}")
        yield event.plain_result(f"✅ 成功设置通知群组为当前群组 (ID: `{group_id}`)。每日公告将在此群组推送。")

    @filter.command("shareholderperks")
    async def handle_manual_check(self, event: AstrMessageEvent):
        """手动触发一次公告检查并在当前会话返回结果。"""
        logger.info(f"用户 {event.sender_id} 触发了手动检查。")
        
        latest_ann = extract_latest_announcement()
        
        if not latest_ann:
            yield event.plain_result("❌ 无法获取公告信息，请稍后重试。")
            return
            
        message = (
            f"🔍 **最新公告查询结果** 🔍\n\n"
            f"**股票代码:** {latest_ann['secCode']}\n"
            f"**公告标题:** {latest_ann['title']}\n"
            f"**发布时间:** {latest_ann['announcementDate']}\n"
            f"**查看链接:** [点击查看]({latest_ann['pdf_url']})"
        )
        yield event.plain_result(message)