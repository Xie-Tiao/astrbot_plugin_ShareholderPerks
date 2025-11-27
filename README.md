# astrbot_plugin_ShareholderPerks

## 项目简介

`astrbot_plugin_ShareholderPerks` 是一个为 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 设计的“股东回馈提醒”插件，用于获取并推送最新的股东回馈相关公告，支持定时自动推送和命令手动获取，帮助用户及时了解股东权益相关信息。

## 功能特性

- 定时自动推送最新股东回馈公告到指定群组
- 管理员维护命令：查看任务状态
- 普通用户可通过命令主动获取最新股东回馈公告
- 统一的群组与推送时间配置
- 实时拉取公告信息，不进行本地缓存保存
- 兼容 AstrBot 支持的主要平台

## 安装与部署

1. 克隆或下载本插件到 AstrBot 插件（/data/plugin/）目录：
   ```bash
   git clone https://github.com/Xie-Tiao/astrbot_plugin_ShareholderPerks.git
   ```
2. 进入AstrBot webUI插件配置界面，调整相关配置，并保存。

只支持AstrBot4.0及以上版本

解释说明：群聊唯一标识符分为: 前缀:中缀:后缀

下面是所有可选的群组唯一标识符前缀:
| 平台 | 群组唯一标识符前缀 |
|--|--|
| qq, napcat, Lagrange 之类的 | aiocqhttp |
| qq 官方 bot | qq_official |
| telegram | telegram |
| 钉钉 | dingtalk |
| wechatpadpro微信 | wechatpadpro |
| gewechat 微信(虽然已经停止维护) | gewechat |
| lark | lark |
| qq webhook 方法 | qq_official_webhook |
| astrbot 网页聊天界面 | webchat |

下面是所有可选的群组唯一标识符中缀:
| 群组唯一标识符中缀 | 描述 |
|--|--|
| GroupMessage | 群组消息 |
| FriendMessage | 私聊消息 |
| OtherMessage | 其他消息 |

前缀为`机器人类型`，中缀为`GroupMessage`，后缀为`QQ群号或QQ号`
可以通过`/sid`查询
最终组合结果类似：
```text
aiocqhttp:GroupMessage:QQ群号
```

## 使用方法

- 自动推送：插件启动后会在配置的时间自动推送到指定群组。
- 普通查询指令（无需参数）：
  - 股东回馈公告：`/sheep`
- 管理员命令：
  - 查看插件状态：`/sheep_status`

## 配置说明

- 通用：
  - `groups`：接收推送的群组唯一标识符列表。
  - `push_time`：定时推送时间，格式 `HH:MM`。
  - `json_url`：公告数据源 JSON 地址，默认 `https://www.cninfo.com.cn/new/fulltextSearch/full?searchkey=%E8%82%A1%E4%B8%9C%E5%9B%9E%E9%A6%88&sdate=&edate=&isfulltext=false&sortName=pubdate&sortType=desc&pageNum=1&pageSize=20&type=`

## 项目结构说明

- `main.py`：插件主程序，包含公告获取、推送、命令注册、定时任务等核心逻辑。
- `metadata.yaml`：插件元数据配置文件（需自行创建）。
- `_conf_schema.json`：插件配置项的 JSON Schema（需自行创建）。
- `LICENSE`：开源许可证文件（建议添加）。
- `README.md`：项目说明文档。

## 许可证说明

本项目可采用合适的开源许可证（如 MIT、AGPL-3.0 等），具体详见 LICENSE 文件。