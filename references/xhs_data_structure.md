# 小红书数据结构参考

## 搜索结果字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `note_id` | string | 笔记唯一 ID（24位十六进制） |
| `url` | string | 笔记完整 URL |
| `title` | string | 笔记标题 |
| `author` | string | 作者昵称 |
| `cover_image` | string | 封面图 URL |
| `likes` | string | 点赞数（可能为 "1.2万" 等格式） |
| `type` | string | 笔记类型：`图文` 或 `视频` |

## 笔记详情字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `note_id` | string | 笔记唯一 ID |
| `url` | string | 笔记 URL |
| `title` | string | 标题 |
| `content` | string | 正文全文 |
| `author` | string | 作者昵称 |
| `author_avatar` | string | 作者头像 URL |
| `tags` | list[string] | 话题标签（以 # 开头） |
| `images` | list[string] | 图片 URL 列表 |
| `video_url` | string | 视频 URL（仅视频笔记） |
| `type` | string | `图文` 或 `视频` |
| `publish_time` | string | 发布时间 |
| `ip_location` | string | IP 归属地 |
| `interactions` | object | 互动数据 |
| `interactions.likes` | string | 点赞数 |
| `interactions.collects` | string | 收藏数 |
| `interactions.comments` | string | 评论数 |
| `interactions.shares` | string | 分享数 |

## 搜索 URL 格式

```
https://www.xiaohongshu.com/search_result?keyword={编码后的关键词}&source=web_search_result_notes
```

## 笔记 URL 格式

```
https://www.xiaohongshu.com/explore/{note_id}
```

其中 `note_id` 为 24 位十六进制字符串，例如 `6578a1234b567c890d123456`。

## Cookie 关键字段

| Cookie 名 | 说明 |
|-----------|------|
| `web_session` | 用户会话标识，登录后生成 |
| `a1` | 设备指纹标识 |
| `webId` | Web 端用户 ID |

> **注意**: Cookie 有效期通常为 7-30 天，过期后需重新获取。
