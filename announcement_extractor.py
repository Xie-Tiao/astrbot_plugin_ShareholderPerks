# announcement_extractor.py
import json
import requests
from datetime import datetime

def extract_latest_announcement_from_url(json_url):
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

    # 整理结果
    return {
        "股票代码(secCode)": latest_ann["secCode"],
        "公司名(announcementTitle)": clean_title,
        "公告PDF链接": pdf_url
    }

# ------------------- 核心：打包完整逻辑为无参函数 -------------------
def run_latest_announcement_extraction():
    """
    无参函数：固定链接 + 提取 + 打印结果
    直接调用即可自动运行，无需传递任何参数
    """
    # 固定的 JSON 在线链接（内置在函数中，无需外部传入）
    DEFAULT_JSON_URL = "https://www.cninfo.com.cn/new/fulltextSearch/full?searchkey=%E8%82%A1%E4%B8%9C%E5%9B%9E%E9%A6%88&sdate=&edate=&isfulltext=false&sortName=pubdate&sortType=desc&pageNum=1&pageSize=20&type="

    try:
        latest_announcement = extract_latest_announcement_from_url(DEFAULT_JSON_URL)
        # 自动打印结果
        print("=" * 80)
        print("最新公告信息提取成功：")
        print("=" * 80)
        for key, value in latest_announcement.items():
            print(f"{key}：{value}")
        print("=" * 80)

        # 关键修改：将公告信息拼接成字符串返回
        announcement_str = "\n".join([f"{key}：{value}" for key, value in latest_announcement.items()])
        # 可选：添加标题和分割线，让回复更美观
        return f"最新公告信息提取成功：\n{announcement_str}\n"
    
    except Exception as e:
        error_msg = f"提取失败：{e}"
        print(f"\033[91m{error_msg}\033[0m")
        # 失败时也返回错误信息，让插件能显示
        return error_msg

# 保留模块独立运行的能力（可选，不影响 main.py 调用）
if __name__ == "__main__":
    run_latest_announcement_extraction()